"""Linear as the board (the `board` joint): tasks are the owner's own Linear issues.

A repo with `taskboard.backend: "linear"` uses its links as the board: the default
`taskboard.link` and each app's `apps.<CODE>.link` (workspace, team, key). Only issues
assigned to or created by the owner are in scope. Nothing is mirrored; the orchestrator
reads and writes Linear directly, and the watcher polls (one query per link per tick).

Linear workspaces, teams, states and labels are left exactly as they are: the board
creates no labels or states. Everything agent-specific lives in the orchestrator's own
comments, which it posts at every step anyway:
  🤖❓ Plan ready … (agent: X)      → Awaiting Approval   🤖 Approved, queued … → Todo
  🤖 Dispatched/Handed to …        → In Progress          🤖❓ … finished on branch … → In Review
  🤖 Accepted …                     → Done                 🤖 Dropped.            → Canceled
  🤖 Sent back… / sending your notes back → Todo           🤖 … (status → X)     → X
The Linear state follows with a standard state of the matching type. An issue with no
orchestrator comments is history: it is never polled or dispatched (it reads as Backlog
or its finished state), so nothing starts from old issues. The owner's comments and
reactions are the verdicts, exactly as before; kind comes from existing labels only.

Private mode (`taskboard.private: true`) makes Linear read-only for the board except the status field
(MST-60: the consumer must see where the work is; PRIVATE_STATUS): the orchestrator's comments and phases go to a local journal (`.mstack/journal.json`, or
Postgres orchestrator.journal with the Postgres store)
instead of the issue, creating issues is refused, and Linear comments other than the
orchestrator's earlier ones are ignored, so teammates see nothing and cannot trigger
anything. The owner's words reach the board through `mstack board owner`, recorded in the
same journal and read exactly like Linear comments (`/plan …`, 👍, a reply).

One fetch per board per tick (MST-41): inside `shared()` (a watcher tick) every LinearBoard reading the
same (key, team) reuses one issue list, and parent lookups are shared too, so the signals, verdict poll,
dispatch and mirror of every scope cost one board read. Any write through a link drops that board's copy.
"""
import collections
import contextlib
from datetime import datetime, timezone
import fcntl
import json
import re
from pathlib import Path
import uuid

import linear
import store
from board import ASK, MARK

SHARED = None                       # inside shared(): {(key id, team): issue nodes, ('parents', key id): {ident: parent}}
CALLS = collections.Counter()       # requests sent through links, by team (the watcher logs them per tick)


@contextlib.contextmanager
def shared():
    """Share board reads between every LinearBoard made inside (one watcher tick). Nests."""
    global SHARED
    outer = SHARED
    SHARED = {} if outer is None else outer
    try:
        yield
    finally:
        SHARED = outer

STATE_TYPE = {'Backlog': 'backlog', 'Todo': 'unstarted', 'Awaiting Approval': 'unstarted',
              'In Progress': 'started', 'In Review': 'started', 'Done': 'completed', 'Canceled': 'canceled'}
FROM_TYPE = {'backlog': 'Backlog', 'triage': 'Backlog', 'unstarted': 'Backlog', 'started': 'Backlog',
             'completed': 'Done', 'canceled': 'Canceled', 'duplicate': 'Canceled'}
LABEL_KIND = {'feature': 'FEAT', 'improvement': 'FEAT', 'bug': 'BUG', 'chore': 'CHORE', 'docs': 'DOCS',
              'documentation': 'DOCS', 'test': 'TEST', 'refactor': 'REFACTOR', 'performance': 'PERF',
              'security': 'SEC', 'ops': 'OPS'}
PUBLIC_STATUS = {k: k for k in STATE_TYPE}
PRIVATE_STATUS = {'Todo': 'In Progress', 'In Progress': 'In Progress', 'In Review': 'In Progress'}
CLOSED = ('completed', 'canceled', 'duplicate')
TYPE_ORDER = {'triage': 0, 'backlog': 0, 'unstarted': 1, 'started': 2, 'completed': 3, 'canceled': 3, 'duplicate': 3}


def rank(state):
    """How far along a Linear state is: by type, then by its position (In Review sits after In Progress)."""
    return (TYPE_ORDER.get(state.get('type'), 0), state.get('position') or 0)
PRIORITY = {'Urgent': 1, 'High': 2, 'Medium': 3, 'Low': 4}
PHASES = [  # (pattern on an orchestrator comment, phase); the latest matching comment wins
    (re.compile(r'\(status → ([A-Za-z ]+)\)'), None),
    (re.compile(r'^' + re.escape(ASK) + r' \*\*[a-z0-9-]+\*\* finished'), 'In Review'),
    (re.compile(r'^' + re.escape(ASK)), 'Awaiting Approval'),
    (re.compile(r'^' + re.escape(MARK) + r' (Approved|Sent back|Got it)'), 'Todo'),
    (re.compile(r'^' + re.escape(MARK) + r' (Dispatched|Handed)'), 'In Progress'),
    (re.compile(r'^' + re.escape(MARK) + r' Accepted'), 'Done'),
    (re.compile(r'^' + re.escape(MARK) + r' Dropped'), 'Canceled'),
]
AGENT = re.compile(r'\(agent: ([a-z0-9-]+)\)')

FIELDS = '''id identifier title description url branchName priority createdAt updatedAt
  state { id type name } labels { nodes { name } } parent { id identifier }
  inverseRelations { nodes { type issue { id } } }
  comments(last: 50) { nodes { id body createdAt reactionData } }'''
ISSUES = '''query($filter: IssueFilter, $after: String) { issues(first: 100, after: $after, filter: $filter) {
  nodes { %s } pageInfo { hasNextPage endCursor } } }''' % FIELDS
ONE = '''query($id: String!) { issue(id: $id) { %s } }''' % FIELDS
TEAM = '''query($key: String!) { teams(first: 1, filter: {key: {eq: $key}}) { nodes {
  id states(first: 50) { nodes { id type name position } } labels(first: 100) { nodes { id name } } } } }'''
ME = '''query { viewer { id } }'''
# The key's own Linear user is the owner (MST-60): its notifications say which issues were assigned to it and
# which comments mention it, in every team the key sees. Read only, so private boards use it too.
TRIGGER_TYPES = {'issueAssignedToYou': 'new_issue', 'issueCommentMention': 'mention', 'issueMention': 'mention'}
NOTIFY = '''query($since: DateTimeOrDuration, $types: [String!]) { viewer { id }
  notifications(first: 100, filter: {createdAt: {gt: $since}, type: {in: $types}}) { nodes { id type createdAt
    ... on IssueNotification { issue { id identifier title url description priority team { key } assignee { id name }
        parent { identifier } children(first: 20) { nodes { identifier } } }
      comment { id body createdAt user { id name } } actor { id name } } } } }'''
CREATE = '''mutation($input: IssueCreateInput!) { issueCreate(input: $input) { issue { id identifier } } }'''
UPDATE = '''mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success } }'''
COMMENT = '''mutation($input: CommentCreateInput!) { commentCreate(input: $input) { comment { id } } }'''
ATTACHMENTS = '''query($id: String!) { issue(id: $id) { attachments(first: 100) { nodes { url } } } }'''
ATTACH = '''mutation($issueId: String!, $url: String!, $title: String) {
  attachmentLinkURL(issueId: $issueId, url: $url, title: $title) { success } }'''


def phase_of(comments):
    """(phase, agent) from the orchestrator's comments; (None, None) if it never touched the issue."""
    phase = agent = None
    for c in comments:
        body = c['body']
        if not body.startswith(MARK):
            continue
        found = AGENT.search(body)
        agent = found.group(1) if found else agent
        for pattern, value in PHASES:
            m = pattern.search(body)
            if m:
                phase = value or m.group(1).strip()
                break
    return phase, agent


class Journal:
    """Private mode's stand-in for issue comments: {issue id: [comment, ...]} in the project.
    With the Postgres store (design 011) the rows live in orchestrator.journal; the project's
    journal.json is still written and is read whenever Postgres does not answer."""
    def __init__(self, project):
        self.path = Path(project)/'.mstack/journal.json'
        self.pg = store.journal_backend(project)
        self.dirty = self.path.with_suffix('.pg-dirty')
        self.synced = self.path.with_suffix('.pg-synced')

    @contextlib.contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_suffix('.lock'), 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(self.path.read_text()) if self.path.exists() else {}
            yield data
            self.path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
            self.path.chmod(0o600)

    def _file(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def _pg(self, action):
        """Run a Postgres action, pushing the file first if it may be ahead; False when Postgres is down."""
        if not self.pg:
            return False
        try:
            if self.dirty.exists() or not self.synced.exists():
                self.pg.add_all(self._file())      # rows only added (ON CONFLICT DO NOTHING): a missing file deletes nothing
                self.dirty.unlink(missing_ok=True)
                self.synced.touch()
            action()
            return True
        except store.PG_ERRORS as error:
            store.warn('journal in Postgres unavailable, using %s: %s' % (self.path, str(error)[:200]))
            self.dirty.touch()
            self.pg = None                         # this board instance stays on the file
            return False

    def comments(self, issue):
        found = []
        if self._pg(lambda: found.extend(self.pg.comments(issue))):
            return found
        return self._file().get(issue, [])

    def add(self, issue, body):
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        comment = {'id': 'local-' + uuid.uuid4().hex[:12], 'body': body, 'createdAt': now, 'reactionData': []}
        with self._locked() as data:
            data.setdefault(issue, []).append(comment)
        self._pg(lambda: self.pg.add_all({issue: [comment]}))
        return comment


class Link:
    """One (app, workspace, team, key) the board reads and writes."""
    def __init__(self, app, conf, project, http=linear.http):
        self.app, self.conf = app, conf
        key = (Path(project)/conf['credential_file']).read_text().strip()
        self.kid = linear.key_id(key)
        self.raw = http(key)
        self._team = self._me = None

    def post(self, query, variables):
        CALLS[self.conf['team']] += 1
        if SHARED is not None and query.lstrip().startswith('mutation'):
            SHARED.pop(self.board_key(), None)        # a write: the next read of this board goes to Linear
        return self.raw(query, variables)

    def board_key(self):
        return (self.kid, self.conf['team'])

    def parents(self):
        """Parent lookups shared by every board on this key in the current tick ({} outside one)."""
        return {} if SHARED is None else SHARED.setdefault(('parents', self.kid), {})

    def team(self):
        if self._team is None:
            self._team = self.post(TEAM, {'key': self.conf['team']})['teams']['nodes'][0]
        return self._team

    def me(self):
        if self._me is None:
            self._me = self.post(ME, {})['viewer']['id']
        return self._me

    def notifications(self, since):
        """(viewer id, owner notifications of the trigger types since `since`); one read per key per tick."""
        key = ('notify', self.kid, since)
        if SHARED is not None and key in SHARED:
            return SHARED[key]
        got = self.post(NOTIFY, {'since': since, 'types': sorted(TRIGGER_TYPES)})
        found = (got['viewer']['id'], got['notifications']['nodes'])
        self._me = self._me or found[0]
        if SHARED is not None:
            SHARED[key] = found
        return found

    def state_for(self, status):
        """The team's state for a board status: the one of that name, else the nearest of its type (MST-53: a team
        with no "In Review" gets its last started state, e.g. In Progress). States are never created."""
        nodes = self.team()['states']['nodes']
        named = [s for s in nodes if (s.get('name') or '').lower() == status.lower()]
        if named:
            return named[0]
        want = STATE_TYPE[status]
        typed = sorted((s for s in nodes if s['type'] == want), key=lambda s: s['position'])
        if status == 'In Review':
            typed = [s for s in typed if 'review' in (s.get('name') or '').lower()] or typed[::-1]
        return typed[0]

    def state_id(self, status):
        return self.state_for(status)['id']

    def existing_label(self, kind):
        """A kind label only if the team already has one; never created."""
        for label in self.team()['labels']['nodes']:
            if LABEL_KIND.get(label['name'].lower()) == kind:
                return label['id']
        return None


class LinearBoard:
    """Same interface the orchestrator uses for the Anytype board, backed by Linear.

    `scope` (an entry of taskboard.orchestrators) narrows the board for one orchestrator:
    `apps` picks its links ("*" is the table-wide link) and `focus` lists root issues: only
    those and their sub-issues are worked on. `all_issues=True` ignores focus (the mirror)."""
    def __init__(self, project, settings, http=linear.http, scope=None, all_issues=False):
        apps = set((scope or {}).get('apps') or [])
        self.links = [Link(code, link, project, http) for code, link in links_of(settings)
                      if not apps or (code or '*') in apps]
        if not self.links:
            raise ValueError('Linear board needs taskboard.link or apps.<CODE>.link (in this scope)')
        self.focus = set((scope or {}).get('focus') or [])
        self.exclude = set((scope or {}).get('exclude') or [])      # root issues another scope owns
        self.all_issues = all_issues
        self.cache, self.owner_of, self.parents = {}, {}, {}
        self.journal = Journal(project) if settings.get('private') else None
        # Board phase → Linear status (MST-60). Private boards push the status field only, and Linear's statuses
        # are for the consumer there: queued or building is In Progress, a finished worker is still In Progress
        # (not landed); `merged` says when it is landed or on Preview. `never_done` scopes leave Done to the
        # consumer. taskboard / scope `linear_status` overrides single entries (a null keeps Linear as it is).
        self.status_map = dict(PRIVATE_STATUS if self.journal else PUBLIC_STATUS)
        for conf in (settings, scope or {}):
            self.status_map.update(conf.get('linear_status') or {})
        self.never_done = bool((scope or {}).get('never_done', settings.get('never_done')))
        self.landing = (scope or {}).get('landing') or settings.get('landing')
        self.pushed = []                    # Linear status changes made by this board: {issue, wanted, linear}
        self.mapped = {}                    # (team, wanted status) → the team's state standing in for it

    def _comments(self, issue):
        """The issue's thread. Private: only the orchestrator's earlier Linear comments, plus the journal."""
        nodes = issue['comments']['nodes']
        if self.journal:
            nodes = [c for c in nodes if c['body'].startswith(MARK)] + self.journal.comments(issue['id'])
        return sorted(nodes, key=lambda c: c['createdAt'])

    # ---- reading ---------------------------------------------------------
    def _task(self, issue, link):
        phase, agent = phase_of(self._comments(issue))
        names = [l['name'].lower() for l in issue['labels']['nodes']]
        self.cache[issue['id']], self.owner_of[issue['id']] = issue, link
        state_type = issue['state']['type']
        closed = state_type in ('completed', 'canceled', 'duplicate')
        # You closed or canceled it in Linear while the orchestrator still had it open.
        closed_by_owner = closed and phase not in (None, 'Done', 'Canceled')
        status = FROM_TYPE[state_type] if closed_by_owner else (phase or FROM_TYPE.get(state_type, 'Backlog'))
        self.parents[issue['identifier']] = (issue.get('parent') or {}).get('identifier')
        return {'id': issue['id'], 'name': issue['title'], 'task_status': status,
                'parent': (issue.get('parent') or {}).get('identifier'),
                'managed': phase is not None, 'closed_by_owner': closed_by_owner, 'linear_state_type': state_type, 'task_agent': agent, 'task_app': link.app,
                'task_kind': next((LABEL_KIND[n] for n in names if n in LABEL_KIND), None),
                'task_blocked_by': [r['issue']['id'] for r in issue['inverseRelations']['nodes'] if r['type'] == 'blocks'],
                'task_priority': {v: k for k, v in PRIORITY.items()}.get(issue['priority']),
                'task_source': 'linear', 'linear_identifier': issue['identifier'], 'linear_url': issue['url'],
                'branch': issue['branchName'], 'linear_state': issue['state'].get('name')}

    def in_focus(self, ident, link=None):
        """True if the issue is in this scope: under a focus root (when there are any) and under no excluded root."""
        if self.exclude and self.under(ident, self.exclude, link):
            return False
        return not self.focus or self.under(ident, self.focus, link)

    def under(self, ident, roots, link=None):
        """True if the issue is one of roots or below one (parents are looked up as needed)."""
        seen = 0
        while ident and seen < 8:
            if ident in roots:
                return True
            if ident not in self.parents and link:
                known = link.parents()
                if ident not in known:
                    try:
                        found = link.post(ONE, {'id': ident})['issue']
                    except linear.RateLimited:
                        raise
                    except RuntimeError:
                        return False
                    known[ident] = (found.get('parent') or {}).get('identifier') if found else None
                self.parents[ident] = known[ident]
            ident, seen = self.parents.get(ident), seen + 1
        return False

    def tasks(self, table=None, kind=None):
        rows = self._all()
        if self.all_issues or not (self.focus or self.exclude):
            return rows
        return [t for t in rows if self.in_focus(t['linear_identifier'], self.owner_of[t['id']])]

    def _all(self):
        return [self._task(i, link) for link in self.links for i in self._fetch(link)]

    @staticmethod
    def _fetch(link):
        """Every issue of one link, once per tick when shared() is on."""
        if SHARED is not None and link.board_key() in SHARED:
            return SHARED[link.board_key()]
        mine = {'or': [{'assignee': {'isMe': {'eq': True}}}, {'creator': {'isMe': {'eq': True}}}]}
        filt = {'and': [mine, {'team': {'key': {'eq': link.conf['team']}}}]}
        nodes, after = [], None
        while True:
            page = link.post(ISSUES, {'filter': filt, 'after': after})['issues']
            nodes += page['nodes']
            if not page['pageInfo']['hasNextPage']:
                break
            after = page['pageInfo']['endCursor']
        if SHARED is not None:
            SHARED[link.board_key()] = nodes
        return nodes

    def _issue(self, task):
        if task not in self.cache:
            for link in self.links:
                found = next((i for i in (SHARED or {}).get(link.board_key()) or [] if task in (i['id'], i['identifier'])), None)
                try:
                    found = found or link.post(ONE, {'id': task})['issue']
                except linear.RateLimited:
                    raise
                except RuntimeError:
                    continue
                if found:
                    self._task(found, link)
                    self.cache[task], self.owner_of[task] = found, link    # also reachable as IRO-123
                    break
            else:
                raise ValueError('Linear issue %s is not on this board' % task)
        return self.cache[task], self.owner_of[task]

    def get(self, task):
        issue, link = self._issue(task)
        found = self._task(issue, link)
        if task != found['id']:                                # looked up by identifier (IRO-123)
            self.cache[found['id']] = issue
        return found

    def fresh(self, task):
        """The task read again from Linear and the journal, past every cache: verdicts are applied only after this."""
        self.forget(task)
        if self.journal and self.journal.pg:
            self.journal.pg._rows = None
        for link in self.links:
            found = link.post(ONE, {'id': task})['issue']
            if found:
                self.cache[task], self.owner_of[task] = found, link
                return self._task(found, link)
        raise ValueError('Linear issue %s is not on this board' % task)

    def body(self, task):
        return (self._issue(task)[0].get('description') or '').strip()

    def messages(self, task):
        issue, _ = self._issue(task)
        out = []
        for c in self._comments(issue):
            reactions = {}
            for r in (c.get('reactionData') or []):
                reactions[r.get('emoji', '')] = reactions.get(r.get('emoji', ''), 0) + len(r.get('userIds') or [1])
            out.append({'id': c['id'], 'order': c['createdAt'], 'text': c['body'], 'reactions': reactions})
        return out

    def triggers(self, since):
        """New issues assigned to the owner and comments mentioning them, in this board's teams and scope
        (MST-60). Each: {kind: new_issue|mention, id: notification id, task, issue, title, url, ...}; mentions
        also carry the comment id, author and text. The owner's own comments never count."""
        out = []
        for link in self.links:
            me, nodes = link.notifications(since)
            for n in sorted(nodes, key=lambda n: n['createdAt']):
                issue, kind = n.get('issue') or {}, TRIGGER_TYPES.get(n.get('type'))
                if not kind or (issue.get('team') or {}).get('key') != link.conf['team']:
                    continue
                if not (self.all_issues or not (self.focus or self.exclude) or self.in_focus(issue['identifier'], link)):
                    continue
                item = {'kind': kind, 'id': n['id'], 'task': issue['id'], 'issue': issue['identifier'],
                        'title': issue.get('title'), 'url': issue.get('url'), 'at': n['createdAt'], 'app': link.app,
                        'triage': triage(issue)}
                if kind == 'new_issue':
                    if (issue.get('assignee') or {}).get('id') != me:
                        continue                                   # reassigned away again since
                    item['assignee'] = me
                else:
                    comment = n.get('comment') or {}
                    author = comment.get('user') or n.get('actor') or {}
                    if author.get('id') == me:
                        continue
                    item.update(comment=comment.get('id') or 'issue:%s' % n['id'], author=author.get('name'),
                                text=(comment.get('body') or '').strip())
                out.append(item)
        return out

    # ---- writing ---------------------------------------------------------
    def link_for(self, app):
        for link in self.links:
            if link.app == app:
                return link
        default = [l for l in self.links if l.app is None]
        if default:
            return default[0]
        raise ValueError('No Linear link for app %s and no table-wide link' % app)

    def create(self, project, title, plan, agent='codex', priority='Medium', labels=(), collection=None,
               app=None, kind=None, parent=None):
        if self.journal:
            raise ValueError('private board: issues are never created in Linear; create it yourself, '
                             'then `mstack board owner --task <ISSUE> "/plan …"`')
        link = self.link_for(app)
        inp = {'teamId': link.team()['id'], 'title': title, 'description': '## Plan\n\n' + plan.strip() + '\n',
               'assigneeId': link.me(), 'priority': PRIORITY.get(priority, 3),
               'stateId': link.state_id('Awaiting Approval')}
        if parent:
            inp['parentId'] = self.get(parent)['id']          # Linear sub-issue (accepts IRO-123 or an id)
        label = link.existing_label(kind) if kind else None
        if label:
            inp['labelIds'] = [label]
        made = link.post(CREATE, {'input': inp})['issueCreate']['issue']
        self.owner_of[made['id']] = link
        self.pending_agent = agent
        return made['id']

    def forget(self, task):
        """Drop every cached copy of an issue (it may be cached under its id and its IRO-123 name)."""
        issue = self.cache.get(task)
        ident = issue and issue.get('identifier')
        for key in [k for k, v in self.cache.items() if v is issue or k in (task, ident)]:
            self.cache.pop(key, None)

    def linear_target(self, status):
        """The Linear status a board phase shows as (None: leave Linear as it is)."""
        target = self.status_map.get(status)
        return None if target == 'Done' and self.never_done else target

    def set(self, task, linear=..., back=False, explicit=False, **props):
        """Board fields. `task_status` also moves the Linear status (on private boards too: the status field
        only) to `linear`, by default the phase's linear_target; None leaves Linear as it is. Linear never moves
        backwards (In Review → In Progress) unless `back` (a verdict sent the work back)."""
        issue, link = self._issue(task)
        real = issue['id']
        change = {}
        if 'task_status' in props:
            if self.journal:
                self.journal.add(real, '%s (status → %s)' % (MARK, props['task_status']))
            target = self.linear_target(props['task_status']) if linear is ... else linear
            moved = self._status_change(issue, link, target, back or explicit, explicit) if target else None
            if moved:
                change['stateId'] = moved
        if 'name' in props and not self.journal:
            change['title'] = props['name']
        if change:
            link.post(UPDATE, {'id': real, 'input': change})
        self.forget(task)

    def push_status(self, task, target, back=False, explicit=False):
        """Move only the Linear status (no phase note): for callers whose own note already records the phase."""
        issue, link = self._issue(task)
        moved = self._status_change(issue, link, target, back or explicit, explicit) if target else None
        if moved:
            link.post(UPDATE, {'id': issue['id'], 'input': {'stateId': moved}})
            self.forget(task)

    def _status_change(self, issue, link, target, back=False, explicit=False):
        """The state id to move the issue to, or None: already there, closed in Linear (never reopened), or
        behind where Linear already is (only `back`, a verdict sending the work back, moves it backwards).
        `explicit` (someone ran `note --status X`): exactly X, backwards or Done on a never_done scope included."""
        state = link.state_for(target)
        if (state.get('name') or '').lower() != target.lower():
            self.mapped[(link.conf['team'], target)] = state.get('name') or state['type']
        current = issue.get('state') or {}
        if state['id'] == current.get('id') or (current.get('type') in CLOSED and state['type'] not in CLOSED):
            return None
        if self.never_done and state['type'] == 'completed' and not explicit:
            return None
        if not back and current.get('type') and rank(state) < rank(current):
            return None
        self.pushed.append({'issue': issue['identifier'], 'team': link.conf['team'], 'wanted': target,
                            'linear': state.get('name') or state['type'], 'mapped': (state.get('name') or '').lower() != target.lower()})
        return state['id']

    def say(self, task, text, ask=False, reply_to=None):
        issue, link = self._issue(task)
        agent = getattr(self, 'pending_agent', None)
        if ask and agent and text.startswith('Plan ready'):
            text += ' (agent: %s)' % agent
        body = (ASK if ask else MARK) + ' ' + text
        if self.journal:
            self.journal.add(issue['id'], body)
        else:
            link.post(COMMENT, {'input': {'issueId': issue['id'], 'body': body}})
        self.forget(task)

    def add_resource(self, task, url, title):
        """Link a URL under the issue's Resources (a Linear link attachment) unless it is there already.
        True when added; False when it was there or the board is private (Linear stays read-only)."""
        if self.journal:
            return False
        issue, link = self._issue(task)
        have = link.post(ATTACHMENTS, {'id': issue['id']})['issue']['attachments']['nodes']
        if any(a['url'] == url for a in have):
            return False
        link.post(ATTACH, {'issueId': issue['id'], 'url': url, 'title': title})
        return True

    def owner_says(self, task, text):
        """Private boards: record the owner's words (given in the orchestrator chat) on the issue's thread."""
        if not self.journal:
            raise ValueError('not a private board: comment on the issue in Linear instead')
        issue, _ = self._issue(task)
        if text.startswith(MARK):
            raise ValueError('owner text cannot start with %s' % MARK)
        comment = self.journal.add(issue['id'], text)
        self.forget(task)
        return comment

    def ensure_table(self, project, known=None):
        return known or {'backend': 'linear'}

    def tidy_views(self, collection):
        pass


MIN_BRIEF = 20      # characters of description below which an issue says too little about what and where (a first, rough check)


def triage(issue):
    """The triage gate for an issue that reached the board from Linear (owner, 2026-10-30): not every issue is
    worked at once. Priority, assignee and a description saying what and where (the scope) are required; the
    hierarchy is read first. `missing` lists what the product owner still has to add before anyone plans it."""
    priority = {v: k for k, v in PRIORITY.items()}.get(issue.get('priority'))
    missing = [field for field, ok in (('priority', priority), ('assignee', (issue.get('assignee') or {}).get('id')),
                                       ('scope/description', len((issue.get('description') or '').strip()) >= MIN_BRIEF))
               if not ok]
    return {'priority': priority, 'urgent': priority == 'Urgent', 'missing': missing,
            'parent': (issue.get('parent') or {}).get('identifier'),
            'children': [c['identifier'] for c in ((issue.get('children') or {}).get('nodes') or [])]}


def links_of(settings):
    out = [(None, settings['link'])] if settings.get('link') else []
    out += [(code, app['link']) for code, app in sorted((settings.get('apps') or {}).items()) if app.get('link')]
    return out
