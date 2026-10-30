"""The owner's "My tasks" table in Anytype: every session and issue across projects, fed from the hub (design 014).

Source: the hub's Postgres — `orchestrator.issues` (the local Linear issue table that `mirror` keeps for every
Linear board) plus board_state `runs`, `related`, `task_tables`, `tables`, `orchestrators` and the hub's session
observations, and each project's role registry. Sink: one collection "My tasks" of the existing "Agent Task" type
(infra/taskboard/schema.json) in the board's channel, through the same macOS bridge and key the board already uses.

Rows: one per session (orchestrator, worker, helper), keyed `session/<id>`; worker and helper rows also carry their
issue. An issue with no session keeps an issue row, keyed `<board>/<issue>`. Every row says where it comes from
(`item_source`: `<workspace>/<team>`, `session` or `hub`) with a link to it (`source_url`: a session's chat link,
else the Linear issue URL) and its scope (`—` when none applies). An issue's Linear
parent is shown as `parent_issue` and as the "Parent Task" relation to the parent's row; a shown issue's parent is
always shown too.

Everything is written one way, except the CTA column (`session_cta`), which only the owner sets and only the hub
resets. Unchanged rows are skipped; every `FULL_EVERY` seconds (and on `sync --full`) every row is written again,
so hand edits to other columns are overwritten. Inside the hub watcher a pass writes at most `BATCH` rows; the rest
follow `BACKLOG_EVERY` seconds later. Rows are never deleted.
"""
from datetime import datetime, timezone
import hashlib
import json
import re
import time

from board import SCHEMA

STATE_KEY = 'status_table'
COLLECTION = 'My tasks'
LAYOUT = 4                   # bump when properties, type fields or views change: an existing table is upgraded
EVERY = 60                   # seconds between passes inside the hub watcher (no Anytype writes when nothing changed)
BATCH = 40                   # rows written per watcher pass at most
BACKLOG_EVERY = 15           # seconds before the next pass while rows are still waiting
FULL_EVERY = 3600            # seconds between passes that rewrite every row (overwrites hand edits)
RECENT_DAYS = 30             # closed issues the board never touched are shown this long after their last update
TYPE = SCHEMA['type']        # the existing Agent Task type (agent_task), reused
SPEC = {p['key']: p for p in SCHEMA['properties']}
STATUSES = [o['name'] for o in SPEC['task_status']['options']]
# Table columns, in order: issue (id, parent, project, source, source link, scope, status, link, last update), then the session.
COLUMNS = ['linear_identifier', 'parent_issue', 'task_parent', 'task_project', 'item_source', 'source_url', 'task_scope',
           'task_status', 'linear_url', 'linear_updated_at', 'agent_session', 'session_type', 'session_agent', 'session_parent', 'session_state', 'session_report',
           'session_cta', 'session_action']
WRITTEN = [c for c in COLUMNS if c != 'session_cta']        # the sync never writes the owner's CTA
CLEARABLE = ('task_scope', 'parent_issue', 'task_parent', 'linear_url', 'source_url', 'agent_session', 'session_parent',
             'session_report', 'session_action')
NO_SCOPE = '—'
CTAS = [o['name'] for o in SPEC['session_cta']['options']]   # noop, continue, archive, delete, forbidden
ACTIONS = ('continue', 'archive', 'delete')                  # what the hub chat carries out
OF_TYPE = {'backlog': 'Backlog', 'triage': 'Backlog', 'unstarted': 'Todo', 'started': 'In Progress',
           'completed': 'Done', 'canceled': 'Canceled', 'duplicate': 'Canceled'}
CLOSED = ('completed', 'canceled', 'duplicate')
REPORT_CHARS = 600
CHAT_LINK = 'claude://claude.ai/epitaxy/%s'   # opens a session's chat in Claude Desktop, when the hub saw no link
TITLED = re.compile(r'([A-Z][A-Z0-9]*-\d+)\b')  # a session titled "IRO-84: …" or "IRO-84 storage …" works on IRO-84

ISSUES_SQL = ("SELECT row_to_json(i) FROM (SELECT board, identifier, team, app, parent, title, state, state_type, "
              "scopes, managed, "
              "agent_phase, url, to_char(updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') AS updated_at, "
              "present FROM orchestrator.issues ORDER BY board, identifier) i;\n")


def read_issues(run_sql):
    out = run_sql(ISSUES_SQL, fetch=True) or ''
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def status_of(issue):
    """Closed in Linear wins; otherwise the board's phase for issues it manages (Awaiting Approval,
    In Review …), else the Linear state when it is one of ours, else its state type."""
    kind = issue.get('state_type')
    if kind in CLOSED:
        return OF_TYPE[kind]
    for name in (issue.get('agent_phase') if issue.get('managed') else None, issue.get('state')):
        if name in STATUSES:
            return name
    return OF_TYPE.get(kind, 'Backlog')


def agent_of(runner):
    runner = (runner or 'claude').lower()
    for name in ('claude', 'codex', 'deepseek'):
        if name in runner:
            return name
    return 'other'


def age_days(iso, now):
    if not iso:
        return float('inf')
    then = datetime.strptime(iso[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
    return (now - then) / 86400


def short(text):
    text = ' '.join((text or '').split())
    return text if len(text) <= REPORT_CHARS else text[:REPORT_CHARS - 1] + '…'


def orchestrators(board_state, roles):
    """Orchestrator sessions: {session: {project, scope}}, from the hub registry and the projects' role registries."""
    out = {}
    for entry in board_state.get('orchestrators', {}).values():
        if entry.get('session'):
            out[entry['session']] = {'project': entry['project'], 'scope': entry.get('scope') or ''}
    for project, registry in roles.items():
        for session, role in registry.items():
            if role.get('role') in ('orchestrator', 'sub-orchestrator'):
                out.setdefault(session, {'project': project, 'scope': role.get('scope') or ''})
    return out


def parent_of(project, scope, orchs):
    """The orchestrator a worker reports to: its scope's, else the project's unscoped one, else blank."""
    for want in (scope or '', ''):
        for session, o in sorted(orchs.items()):
            if o['project'] == project and o['scope'] == want:
                return session
    return ''


def source_of(board, issue, ident, sources):
    """`<workspace>/<team>` of an issue (its team, else its identifier's prefix); the team alone when the board's
    links don't name its workspace."""
    team = (issue or {}).get('team') or (ident or '').split('-')[0]
    workspace = ((sources.get(board) or {}).get('teams') or {}).get(team)
    return '%s/%s' % (workspace, team) if workspace else team


def routed(board, issue, ident, sources):
    """The scopes `taskboard.orchestrators` routes the issue's app code to: scopes naming the code (unless they
    exclude the issue or only focus on some issues), else, for a code no scope names, the `*` scopes."""
    confs = (sources.get(board) or {}).get('scopes') or {}
    app = (issue or {}).get('app')
    named = app and any(app in (c.get('apps') or []) for c in confs.values())
    for want in [app] if named else ['*']:
        hit = sorted(s for s, c in confs.items() if want in (c.get('apps') or [])
                     and ident not in (c.get('exclude') or []) and not c.get('focus'))
        if hit:
            return ','.join(hit)
    return ''


def desired(issues, board_state, sources, now=None, roles=None, boards=None):
    """(rows, takes, retire): the rows the table should show; for issue rows that became session rows, the old key
    each takes over; and old issue rows its sessions replace with nothing to take them over (to remove).
    `sources` maps a board to {teams: {team key: Linear workspace}, scopes: its `taskboard.orchestrators`}.
    `roles` maps a board to its project's role registry ({session: {role, scope, task, worker}}).
    `boards`, when given, are the boards shown: rows of any other board (retired or unregistered) are left out, and
    the ones the table still holds are retired.
    A row whose issue has a Linear parent carries `parent`: the key of the parent's row, when it has one."""
    now = time.time() if now is None else now
    dropped = set()
    if boards is not None:
        boards = set(boards)
        issues = [i for i in issues if i.get('board') in boards]
        roles = {p: r for p, r in (roles or {}).items() if p in boards}
        runs = board_state.get('runs', {})
        dead = {k for k, r in runs.items() if r.get('table') not in boards}
        dropped |= {'session/' + runs[k]['session'] for k in dead if runs[k].get('session')}
        dropped |= {'session/' + c['session'] for k in dead for c in board_state.get('related', {}).get(k, [])
                    if c.get('session')}
        dropped |= {'%s/%s' % (r.get('table'), r.get('issue')) for k, r in runs.items() if k in dead}
        board_state = {**board_state, 'runs': {k: r for k, r in runs.items() if k not in dead},
                       'related': {k: v for k, v in board_state.get('related', {}).items() if k not in dead},
                       'orchestrators': {k: o for k, o in board_state.get('orchestrators', {}).items()
                                         if o.get('project') in boards}}
    roles = roles or {}
    seen = board_state.get('sessions_seen') or {}
    known_rows = (board_state.get(STATE_KEY) or {}).get('rows', {})
    actions = (board_state.get(STATE_KEY) or {}).get('actions', {})
    orchs = orchestrators(board_state, roles)
    by_issue = {'%s/%s' % (i['board'], i['identifier']): i for i in issues}
    scopes = {'%s/%s' % (r.get('table'), ident): r['scope'] for ident, r in board_state.get('task_tables', {}).items()
              if isinstance(r, dict) and r.get('scope')}
    rows, takes = {}, {}

    def issue_props(board, ident):
        issue = by_issue.get('%s/%s' % (board, ident))
        props = {'linear_identifier': ident, 'task_project': board, 'item_source': source_of(board, issue, ident, sources)}
        if issue:
            props.update(task_status=status_of(issue), linear_updated_at=issue.get('updated_at') or None,
                         linear_url=issue.get('url'), parent_issue=issue.get('parent'))
        return props, ('%s %s' % (ident, issue.get('title') or '')) if issue else ident

    def scope_of(board, ident, *first):
        """The first of: `first` (the run's or chat's scope), the planning scope, the issue's scopes, the route."""
        issue = by_issue.get('%s/%s' % (board, ident))
        for scope in (*first, scopes.get('%s/%s' % (board, ident)), (issue or {}).get('scopes'),
                      routed(board, issue, ident, sources) if ident else ''):
            if scope:
                return scope
        return NO_SCOPE

    def add(session, props, name, kind, agent, parent, report):
        # Owner rules (2026-10-30): archived/deleted only when observed so. Idle when last seen not running a turn
        # and its issue isn't waiting for review; every other session (never observed, running, just acked) is active.
        state = (seen.get(session) or {}).get('state')
        if state not in ('archived', 'deleted'):
            state = 'idle' if state == 'idle' and props.get('task_status') != 'In Review' else 'active'
        props = {**props, 'source_url': (seen.get(session) or {}).get('link') or CHAT_LINK % session,
                 'agent_session': session, 'session_type': kind, 'session_agent': agent,
                 'session_parent': parent, 'session_state': state, 'session_report': short(report),
                 'session_action': (actions.get(session) or {}).get('text')}
        rows['session/' + session] = {'name': name, 'properties': {k: v for k, v in props.items() if v not in (None, '')}}

    def titled(session):
        """The issue a session's observed title starts with ("IRO-84: …", "IRO-84 storage …"), when exactly one shown
        board has it (identifiers carry the team key); else None."""
        info = seen.get(session) or {}
        found = TITLED.match(info.get('title') or '')
        keys = [k for k in by_issue if found and k.split('/', 1)[1] == found.group(1)]
        return keys[0] if len(keys) == 1 else None

    # Workers: the latest run per session (a session can be adopted for several issues; the newest wins, unless the
    # session's title names one of the shown issues: then that issue labels its row).
    latest = {}
    for run in board_state.get('runs', {}).values():
        if run.get('session') and (run.get('dispatched_at') or '') >= (latest.get(run['session'], {}).get('dispatched_at') or ''):
            latest[run['session']] = run
    newest_for_issue = {}
    for session, run in sorted(latest.items()):
        if titled(session):
            table, ident = titled(session).split('/', 1)
            run = dict(run, table=table, issue=ident, scope=scopes.get(titled(session))
                       or by_issue[titled(session)].get('scopes') or run.get('scope'))
        scope = run.get('scope') or scopes.get('%s/%s' % (run.get('table'), run.get('issue'))) or ''
        props, name = issue_props(run.get('table'), run.get('issue')) if run.get('issue') else \
            ({'task_project': run.get('table'), 'item_source': 'session'}, 'Worker %s' % session)
        props['task_scope'] = scope_of(run.get('table'), run.get('issue'), scope)
        report = (run.get('report') or {}).get('text') or ''
        add(session, props, name, 'worker', agent_of(run.get('runner')), parent_of(run.get('table'), scope, orchs), report)
        if run.get('issue'):
            key = '%s/%s' % (run['table'], run['issue'])
            if (run.get('dispatched_at') or '') >= (newest_for_issue.get(key, ('', ''))[0]):
                newest_for_issue[key] = (run.get('dispatched_at') or '', session)
    # Earlier chats on an issue (`adopt --related`): sessions too, usually ones to archive.
    for task, chats in board_state.get('related', {}).items():
        run = board_state.get('runs', {}).get(task) or {}
        for chat in chats:
            if chat.get('session') and 'session/' + chat['session'] not in rows:
                props, name = issue_props(run.get('table'), run.get('issue')) if run.get('issue') else \
                    ({'item_source': 'session'}, 'Related chat')
                props['task_scope'] = scope_of(run.get('table'), run.get('issue'), chat.get('scope'))
                add(chat['session'], props, name, 'worker', 'claude', parent_of(run.get('table'), chat.get('scope'), orchs),
                    'Earlier chat on this issue (%s)' % (chat.get('note') or 'related'))
    # Orchestrators and helpers.
    for session, o in sorted(orchs.items()):
        if 'session/' + session not in rows:
            label = '%s/%s' % (o['project'], o['scope']) if o['scope'] else o['project']
            add(session, {'task_project': o['project'], 'task_scope': o['scope'] or NO_SCOPE, 'item_source': 'hub'},
                'Orchestrator ' + label,
                'orchestrator', 'claude', '', '')
    for project, registry in sorted(roles.items()):
        for session, role in sorted(registry.items()):
            if role.get('role') == 'helper' and 'session/' + session not in rows:
                props, name = issue_props(project, role['task']) if role.get('task') else ({'task_project': project}, '')
                worker_run = latest.get(role.get('worker')) or {}
                props.update(item_source='hub', task_scope=scope_of(project, role.get('task'), worker_run.get('scope'),
                                                                     role.get('scope')))
                add(session, props, 'Helper: ' + (name or session), 'helper', 'claude',
                    parent_of(project, worker_run.get('scope'), orchs), 'Helper of worker %s' % (role.get('worker') or '?'))
    # Sessions the hub saw but no run records (started outside dispatch/ack), titled "<ISSUE>…": worker rows.
    for session, info in sorted(seen.items()):
        key = titled(session)
        if not key or info.get('state') in ('archived', 'deleted') or 'session/' + session in rows:
            continue
        issue = by_issue[key]
        props, name = issue_props(issue['board'], issue['identifier'])
        props['task_scope'] = scope_of(issue['board'], issue['identifier'])
        add(session, props, name, 'worker', 'claude',
            parent_of(issue['board'], scopes.get(key) or issue.get('scopes') or '', orchs), '')
        newest_for_issue.setdefault(key, ('', session))
    # An issue's old row (from before sessions had rows) becomes its newest worker's row: no orphan, no duplicate.
    for key, (_, session) in newest_for_issue.items():
        if key in known_rows and 'session/' + session not in known_rows:
            takes['session/' + session] = key
    # Issues with no session keep an issue row.
    with_session = set(newest_for_issue) | {'%s/%s' % (p, r['task']) for p, reg in roles.items()
                                           for r in reg.values() if r.get('role') == 'helper' and r.get('task')}
    shown = set(with_session)
    for key, issue in by_issue.items():
        keep = (issue.get('state_type') not in CLOSED or issue.get('managed') or key in known_rows
                or age_days(issue.get('updated_at'), now) <= RECENT_DAYS)
        if keep and (issue.get('present', True) or key in known_rows):
            shown.add(key)
    # A shown issue's parent is shown too (and its parent …), so no "Parent Task" points at nothing.
    todo = sorted(shown)
    while todo:
        issue = by_issue.get(todo.pop())
        up = '%s/%s' % (issue['board'], issue['parent']) if issue and issue.get('parent') else None
        if up in by_issue and up not in shown:
            shown.add(up)
            todo.append(up)
    for key in sorted(shown - with_session):
        issue = by_issue[key]
        props, name = issue_props(issue['board'], issue['identifier'])
        props['task_scope'] = scope_of(issue['board'], issue['identifier'])
        props['source_url'] = issue.get('url')
        rows[key] = {'name': name, 'properties': {k: v for k, v in props.items() if v not in (None, '')}}
    # Each issue's row (its own, else its newest worker's, else a helper's), so a child can point at its parent's.
    row_of = {k: k for k in rows if not k.startswith('session/')}
    for key, row in sorted(rows.items()):
        p = row['properties']
        if p.get('session_type') == 'helper' and p.get('linear_identifier'):
            row_of.setdefault('%s/%s' % (p.get('task_project'), p['linear_identifier']), key)
    row_of.update({key: 'session/' + session for key, (_, session) in newest_for_issue.items()})
    for row in rows.values():
        p = row['properties']
        if p.get('parent_issue') and row_of.get('%s/%s' % (p.get('task_project'), p['parent_issue'])):
            row['parent'] = row_of['%s/%s' % (p['task_project'], p['parent_issue'])]
    retire = sorted(k for k in known_rows if (k in with_session and k not in takes.values())
                    or (k not in rows and (k in dropped or (boards is not None and not k.startswith('session/')
                                                            and k.split('/')[0] not in boards))))
    return rows, takes, retire


def fingerprint(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16]


def parents_first(rows):
    """Row keys ordered so a parent's row is written before its children's (then by key)."""
    def depth(key, seen=()):
        up = rows[key].get('parent')
        return 0 if up not in rows or up in seen else 1 + depth(up, seen + (key,))
    return sorted(rows, key=lambda k: (depth(k), k))


def with_parent(row, stored):
    """The row as written: its "Parent Task" relation set to the parent row's object, once that row exists."""
    held = stored.get(row.get('parent')) if row.get('parent') else None
    props = dict(row['properties'], **({'task_parent': [held['id']]} if held else {}))
    return {'name': row['name'], 'properties': props}


def cta_of(props):
    value = (props or {}).get('session_cta')
    value = value[0] if isinstance(value, list) and value else value
    return value.get('name') if isinstance(value, dict) else value


class StatusTable:
    """Anytype side. `call(method, channel_relative_path, body=None)` is board.macctl (or a fake in tests)."""
    def __init__(self, call):
        self.call = call
        self.partial = None          # after a failed sync: what was written before the failure

    def ensure(self, known):
        """The Agent Task type brought up to date (missing properties created and added to it), the "My tasks"
        collection with Table and Board views, and a sidebar widget. Reuses what `known`
        (board_state[STATE_KEY]) already names; an older layout is upgraded in place. Safe to repeat."""
        known = dict(known or {})
        if known.get('collection') and known.get('layout') == LAYOUT:
            return known
        self.ensure_type()
        if not known.get('collection'):
            collection = self.call('POST', 'collections', {'name': COLLECTION})['id']
            known.update(collection=collection, rows={})
            self.partial = known             # a later failure must not lead to a second "My tasks"
            self.call('PATCH', 'objects/' + collection, {'ops': [
                {'op': 'insert_view', 'name': 'Table', 'position': 'first', 'set': {'type': 'table'}},
                {'op': 'insert_view', 'name': 'Board', 'set': {'type': 'kanban', 'group_by': 'task_status'}}]})
            known['widget'] = self.call('POST', 'widgets', {'target': known['collection'], 'scope': 'space',
                                                            'layout': 'view', 'position': 'first'}).get('id')
        views = self.call('GET', 'collections/%s/views' % known['collection']).get('data') or []
        noise = {k: None for k in ('type', 'created_date', 'creator', 'last_modified_date', 'last_modified_by',
                                   'lastOpenedDate', 'backlinks', 'tag', 'description')}
        ops = []
        for view in views:
            if view['name'] in ('Table', 'Board'):
                ops.append({'op': 'update_view', 'view': view['id'], 'columns': {**noise, **{k: {} for k in COLUMNS}}})
            elif view['name'] == 'All' and len(views) > 1:
                ops.append({'op': 'delete_view', 'view': view['id']})
        if ops:
            self.call('PATCH', 'objects/' + known['collection'], {'ops': ops})
        known['layout'] = LAYOUT
        return known

    def ensure_type(self):
        """Reuse agent_task: create any schema property the channel lacks, then add the table's columns that the
        type doesn't carry yet. A channel without the type gets it from the schema."""
        have = {p['key'] for p in self.call('GET', 'properties?limit=200').get('data') or []}
        added = []
        for prop in SCHEMA['properties']:
            if prop['key'] not in have:
                self.call('POST', 'properties', {k: prop[k] for k in ('key', 'name', 'format', 'options') if k in prop})
                added.append(prop['key'])
        if TYPE['key'] not in {t['key'] for t in self.call('GET', 'types?limit=200').get('data') or []}:
            self.call('POST', 'types', {
                'api_key': TYPE['key'], 'name': TYPE['name'], 'plural_name': TYPE['plural_name'],
                'icon': {'format': 'emoji', 'emoji': TYPE['emoji']}, 'default_view': TYPE['default_view'],
                'layout': 'basic', 'property_definitions': [{'property': p['key'], 'section': p.get('section', 'hidden')}
                                                            for p in SCHEMA['properties']]})
            return
        found = self.call('GET', 'types/' + TYPE['key']) or {}
        on_type = {d.get('property') for d in (found.get('type_settings') or {}).get('property_definitions') or []}
        for key in COLUMNS:
            if key not in on_type or key in added:
                self.call('PATCH', 'types/' + TYPE['key'], {'ops': [
                    {'op': 'add_property', 'property': key, 'section': SPEC[key].get('section', 'featured')}]})

    def rename_channel(self, name):
        """Rename the granted channel (the space itself, path ".")."""
        return self.call('PATCH', '.', {'name': name})

    def ctas(self, known):
        """{object id: cta} for every row whose CTA isn't noop/blank: one paginated search, not one call per row."""
        ids, out, offset = {r['id'] for r in (known.get('rows') or {}).values()}, {}, 0
        while ids:
            page = self.call('POST', 'search?limit=200&offset=%d' % offset, {'type': TYPE['key'], 'fields': ['session_cta']})
            data = page.get('data') or []
            for obj in data:
                cta = cta_of(obj.get('properties'))
                if obj['id'] in ids and cta and cta != 'noop':
                    out[obj['id']] = cta
            offset += len(data)
            if len(data) < 200:
                return out
        return out

    def set_cta(self, object_id, cta='noop'):
        self.call('PATCH', 'objects/%s?create_missing_options=true' % object_id,
                  {'ops': [{'op': 'set_properties', 'set': {'session_cta': cta}}]})

    def sync(self, rows, known, full=False, limit=None, takes=None, retire=()):
        """Upsert `rows` (from desired), writing at most `limit` of them. `takes` maps a new row key to the old key
        whose object it reuses. Returns (known with row ids and fingerprints, counts); counts['pending'] is how many
        changed rows wait for the next pass. A full pass forgets every fingerprint first, so it carries on across
        passes until every row was rewritten."""
        self.partial = known
        known = self.ensure(known)
        stored = {k: dict(v, hash=None) if full else v for k, v in (known.get('rows') or {}).items()}
        for new, old in (takes or {}).items():
            if new not in stored and old in stored and old not in rows:
                stored[new] = dict(stored.pop(old), hash=None, fresh=True)     # gets a CTA (noop) when rewritten
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'pending': 0, 'removed': 0}
        self.partial = known
        try:
            for key in retire:                  # an issue row its sessions now show: removed, never a stale duplicate
                if key in stored and key not in rows:
                    self.call('DELETE', 'objects/' + stored.pop(key)['id'])
                    counts['removed'] += 1
            for key in parents_first(rows):
                row = with_parent(rows[key], stored)
                mark = fingerprint(row)
                held = stored.get(key)
                if held and held['hash'] == mark:
                    counts['unchanged'] += 1
                    continue
                if limit is not None and counts['created'] + counts['updated'] >= limit:
                    counts['pending'] += 1
                    continue
                if held:
                    # Fields that went empty are cleared, so a hand-filled value never survives a rewrite.
                    blank = {k: [] if SPEC[k]['format'] == 'objects' else '' for k in CLEARABLE if k not in row['properties']}
                    if held.get('fresh'):
                        blank['session_cta'] = 'noop'
                    self.call('PATCH', 'objects/%s?create_missing_options=true' % held['id'],
                              {'ops': [{'op': 'set_properties', 'set': {'name': row['name'], **blank, **row['properties']}}]})
                    counts['updated'] += 1
                else:
                    made = self.call('POST', 'objects?create_missing_options=true', {
                        'type': TYPE['key'], 'name': row['name'], 'template': 'none',
                        'properties': {**row['properties'], 'session_cta': 'noop'},
                        'markdown': 'Written by the mstack hub (docs/design/014-STATUS-TABLE.md). Edits are '
                                    'overwritten, except CTA: set it to continue, archive, delete or forbidden.'})
                    try:
                        self.call('PATCH', 'objects/' + known['collection'], {'ops': [{'op': 'add_items', 'items': [made['id']]}]})
                    except RuntimeError:
                        self.call('DELETE', 'objects/' + made['id'])     # never leave an orphan outside the table
                        raise
                    held = {'id': made['id']}
                    counts['created'] += 1
                stored[key] = {'id': held['id'], 'hash': mark}
        finally:
            known['rows'] = stored                                     # what was written so far is kept
        self.partial = None
        return known, counts
