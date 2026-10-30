"""The owner's personal, read-only "My tasks" table in Anytype, fed one way from the hub (design 014).

Source: the hub's Postgres — `orchestrator.issues` (the local Linear issue table that `mirror` keeps for every
Linear board) plus board_state `runs`, `task_tables` and `tables`. Sink: one collection "My tasks" of the
existing "Agent Task" type (infra/taskboard/schema.json, plus a Scope property) in the board's existing channel,
through the same macOS bridge and key the board already uses (no new grant). The old per-project collections are
never read or written.

One way only: rows are upserted by `<board>/<issue>`. Unchanged rows are skipped; every `FULL_EVERY` seconds
(and on `sync --full`) every row is written again, so hand edits in Anytype are overwritten. Inside the hub
watcher a pass writes at most `BATCH` rows, so the first build (and each hourly rewrite) is spread over a few
ticks instead of stalling event delivery; the rest follow `BACKLOG_EVERY` seconds later. Rows are never
deleted: a closed issue stays as Done/Canceled, and an issue that left the source keeps its last values.
"""
from datetime import datetime, timezone
import hashlib
import json
import time

from board import SCHEMA

STATE_KEY = 'status_table'
COLLECTION = 'My tasks'
EVERY = 60                   # seconds between passes inside the hub watcher (no Anytype calls when nothing changed)
BATCH = 40                   # rows written per watcher pass at most
BACKLOG_EVERY = 15           # seconds before the next pass while rows are still waiting
FULL_EVERY = 3600            # seconds between passes that rewrite every row (overwrites hand edits)
RECENT_DAYS = 30             # closed issues the board never touched are shown this long after their last update
TYPE = SCHEMA['type']        # the existing Agent Task type (agent_task), reused
SPEC = {p['key']: p for p in SCHEMA['properties']}
STATUSES = [o['name'] for o in SPEC['task_status']['options']]
# Table columns, in order: Issue, Project, Scope, Status, Worker session, Last update, Link (all Agent Task properties).
COLUMNS = ['linear_identifier', 'task_project', 'task_scope', 'task_status', 'agent_session', 'linear_updated_at',
           'linear_url']
OF_TYPE = {'backlog': 'Backlog', 'triage': 'Backlog', 'unstarted': 'Todo', 'started': 'In Progress',
           'completed': 'Done', 'canceled': 'Canceled', 'duplicate': 'Canceled'}
CLOSED = ('completed', 'canceled', 'duplicate')

ISSUES_SQL = ("SELECT row_to_json(i) FROM (SELECT board, identifier, title, state, state_type, scopes, managed, "
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


def age_days(iso, now):
    if not iso:
        return float('inf')
    then = datetime.strptime(iso[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
    return (now - then) / 86400


def desired(issues, board_state, private, now=None):
    """Rows the table should show, keyed `<board>/<issue>`. `private` maps a board to True when its
    issues must carry no Linear link (private boards, or boards whose config can't be read)."""
    now = time.time() if now is None else now
    runs, scopes = {}, {}
    for run in board_state.get('runs', {}).values():
        if run.get('issue'):
            key = '%s/%s' % (run.get('table'), run['issue'])
            if (run.get('dispatched_at') or '') >= (runs.get(key, {}).get('dispatched_at') or ''):
                runs[key] = run
    for ident, record in board_state.get('task_tables', {}).items():
        if isinstance(record, dict) and record.get('scope'):
            scopes['%s/%s' % (record.get('table'), ident)] = record['scope']
    shown = set((board_state.get(STATE_KEY) or {}).get('rows', {}))
    rows = {}
    for issue in issues:
        key = '%s/%s' % (issue['board'], issue['identifier'])
        run = runs.get(key) or {}
        keep = (issue.get('state_type') not in CLOSED or issue.get('managed') or run or key in shown
                or age_days(issue.get('updated_at'), now) <= RECENT_DAYS)
        if not keep or (not issue.get('present', True) and key not in shown):
            continue
        scope = run.get('scope') or scopes.get(key) or issue.get('scopes') or ''
        props = {'linear_identifier': issue['identifier'], 'task_project': issue['board'], 'task_scope': scope,
                 'task_status': status_of(issue), 'agent_session': run.get('session') or '',
                 'linear_updated_at': issue.get('updated_at') or None,
                 'linear_url': None if private.get(issue['board'], True) else issue.get('url')}
        rows[key] = {'name': '%s %s' % (issue['identifier'], issue.get('title') or ''),
                     'properties': {k: v for k, v in props.items() if v not in (None, '')}}
    return rows


def fingerprint(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16]


class StatusTable:
    """Anytype side. `call(method, channel_relative_path, body=None)` is board.macctl (or a fake in tests)."""
    def __init__(self, call):
        self.call = call
        self.partial = None          # after a failed sync: what was written before the failure

    def ensure(self, known):
        """The Agent Task type brought up to date (missing properties created and added to it), the "My tasks"
        collection with Table and Board views, and a sidebar widget. Reuses what `known`
        (board_state[STATE_KEY]) already names; safe to repeat."""
        known = dict(known or {})
        if known.get('collection'):
            return known
        self.ensure_type()
        collection = self.call('POST', 'collections', {'name': COLLECTION})['id']
        known.update(collection=collection, rows={})
        self.partial = known                 # a later failure must not lead to a second "My tasks"
        self.call('PATCH', 'objects/' + collection, {'ops': [
            {'op': 'insert_view', 'name': 'Table', 'position': 'first', 'set': {'type': 'table'}},
            {'op': 'insert_view', 'name': 'Board', 'set': {'type': 'kanban', 'group_by': 'task_status'}}]})
        views = self.call('GET', 'collections/%s/views' % collection).get('data') or []
        noise = {k: None for k in ('type', 'created_date', 'creator', 'last_modified_date', 'last_modified_by',
                                   'lastOpenedDate', 'backlinks', 'tag', 'description')}
        ops = []
        for view in views:
            if view['name'] in ('Table', 'Board'):
                ops.append({'op': 'update_view', 'view': view['id'], 'columns': {**noise, **{k: {} for k in COLUMNS}}})
            elif view['name'] == 'All' and len(views) > 1:
                ops.append({'op': 'delete_view', 'view': view['id']})
        if ops:
            self.call('PATCH', 'objects/' + collection, {'ops': ops})
        widget = self.call('POST', 'widgets', {'target': collection, 'scope': 'space', 'layout': 'view',
                                               'position': 'first'}).get('id')
        known['widget'] = widget
        return known

    def ensure_type(self):
        """Reuse agent_task: create any schema property the channel lacks, then add the table's columns that the
        type doesn't carry yet (e.g. Scope). A channel without the type gets it from the schema."""
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
        found = found.get('type', found)
        on_type = {p.get('key') for p in found.get('properties') or [] if isinstance(p, dict)}
        for key in COLUMNS:
            if key not in on_type or key in added:
                self.call('PATCH', 'types/' + TYPE['key'], {'ops': [
                    {'op': 'add_property', 'property': key, 'section': SPEC[key].get('section', 'featured')}]})

    def rename_channel(self, name):
        """Rename the granted channel (the space itself, path ".")."""
        return self.call('PATCH', '.', {'name': name})

    def sync(self, rows, known, full=False, limit=None):
        """Upsert `rows` (from desired), writing at most `limit` of them. Returns (known with row ids and
        fingerprints, counts); counts['pending'] is how many changed rows wait for the next pass. A full pass
        forgets every fingerprint first, so it carries on across passes until every row was rewritten."""
        self.partial = known
        known = self.ensure(known)
        stored = {k: dict(v, hash=None) if full else v for k, v in (known.get('rows') or {}).items()}
        counts = {'created': 0, 'updated': 0, 'unchanged': 0, 'pending': 0}
        self.partial = known
        try:
            for key, row in sorted(rows.items()):
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
                    blank = {k: '' for k in COLUMNS if k not in row['properties'] and k in ('task_scope', 'agent_session')}
                    self.call('PATCH', 'objects/%s?create_missing_options=true' % held['id'],
                              {'ops': [{'op': 'set_properties', 'set': {'name': row['name'], **blank, **row['properties']}}]})
                    counts['updated'] += 1
                else:
                    made = self.call('POST', 'objects?create_missing_options=true', {
                        'type': TYPE['key'], 'name': row['name'], 'template': 'none', 'properties': row['properties'],
                        'markdown': 'Read-only: written by the mstack hub (docs/design/014-STATUS-TABLE.md). '
                                    'Edits here are overwritten.'})
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
