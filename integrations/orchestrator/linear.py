"""Optional Linear link for one project table: pull, push or full, scoped to my issues or a label.

Each project links to one Linear workspace (checked against the key before anything
else) and one team. Personal API key from the project's .mstack/secrets. Matching is
by Linear identifier; agent-only fields never leave Anytype.

Imported work waits: new Linear issues land in Backlog, and Linear status changes
never move a task into Todo or In Progress. Only a plan the owner approves on the
board makes it Todo, so the always-on loop never starts work straight from Linear.
Finished or canceled in Linear does carry over.
"""
import json
import re
import time
import urllib.error
import urllib.request

from board import KINDS, SCHEMA, titled

PREFIX = re.compile(r'^(\[[A-Z0-9]+\])+\s*')


def bare(title):
    """Title without the board's [APP][KIND] prefix, for Linear."""
    return PREFIX.sub('', title or '')

STATE_OF = dict(SCHEMA['linear_sync']['status_map'], **{'Awaiting Approval': 'unstarted'})
# Incoming Linear states: only endings carry over; everything else waits in Backlog.
STATUS_OF = {'completed': 'Done', 'canceled': 'Canceled'}
PRIORITY_OF = {1: 'Urgent', 2: 'High', 3: 'Medium', 4: 'Low'}
WHO = '''query { organization { urlKey name } viewer { id } }'''
TEAMS = '''query { teams(first: 100) { nodes { key name } } }'''


def central_keys(path):
    """Rows of the owner's key file: id, account, workspace, teams (a quoted comma list), keyname, keyvalue."""
    rows = {}
    for line in path.read_text().splitlines()[1:]:
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split(',')]
        rows[cells[0]] = {'account': cells[1], 'workspace': cells[2],
                          'teams': [t.strip(" '") for t in cells[3:-2]], 'keyname': cells[-2], 'key': cells[-1]}
    return rows
ISSUES = '''query($filter: IssueFilter, $after: String) { issues(first: 100, after: $after, filter: $filter) {
  nodes { id identifier title url priority updatedAt state { type } labels { nodes { name } } }
  pageInfo { hasNextPage endCursor } } }'''


def all_issues(post, filter_):
    """Every matching issue, following pages (full history, not just the first 100)."""
    out, after = [], None
    while True:
        page = post(ISSUES, {'filter': filter_, 'after': after})['issues']
        out += page['nodes']
        info = page.get('pageInfo') or {}
        if not info.get('hasNextPage'):
            return out
        after = info['endCursor']
TEAM = '''query($key: String!) { teams(filter: {key: {eq: $key}}) { nodes {
  id states { nodes { id type position } } labels { nodes { id name } } } } }'''
ONE = '''query($id: String!) { issue(id: $id) { id identifier title url priority updatedAt state { type } } }'''
LABEL = '''mutation($input: IssueLabelCreateInput!) { issueLabelCreate(input: $input) { issueLabel { id } } }'''
CREATE = '''mutation($input: IssueCreateInput!) { issueCreate(input: $input) {
  issue { id identifier url updatedAt } } }'''
UPDATE = '''mutation($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) {
  issue { updatedAt } } }'''


def http(key, attempts=5, pause=3.0, opener=urllib.request.urlopen):
    """GraphQL poster. Network failures (slow proxy TLS, resets) are retried with backoff;
    HTTP and GraphQL errors (bad key, bad query) are not."""
    def post(query, variables):
        req = urllib.request.Request('https://api.linear.app/graphql', method='POST',
                                     data=json.dumps({'query': query, 'variables': variables}).encode(),
                                     headers={'Authorization': key, 'Content-Type': 'application/json'})
        for attempt in range(attempts):
            try:
                with opener(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                break
            except urllib.error.HTTPError:
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                if attempt == attempts - 1:
                    raise RuntimeError('Linear unreachable after %d attempts: %s' % (attempts, error))
                time.sleep(pause * (attempt + 1))
        if data.get('errors'):
            raise RuntimeError('Linear: ' + data['errors'][0].get('message', 'error'))
        return data['data']
    return post


def scope_filter(link):
    mine = {'or': [{'assignee': {'isMe': {'eq': True}}}, {'creator': {'isMe': {'eq': True}}}]}
    parts = [mine, {'team': {'key': {'eq': link['team']}}}]
    if link.get('scope') == 'label':
        parts.append({'labels': {'name': {'eq': link['label']}}})
    return {'and': parts}


def check_workspace(link, post):
    """Refuse to touch anything if the key belongs to a different workspace than configured."""
    org = post(WHO, {})['organization']
    if org['urlKey'] != link['workspace']:
        raise ValueError('Linear key is for workspace %r, but this project links to %r'
                         % (org['urlKey'], link['workspace']))
    return org


def mine(task, app, others):
    """Tasks a link owns: an app link owns its app's tasks; a table-wide link owns the rest."""
    return task.get('task_app') == app if app else task.get('task_app') not in others


def sync(board, project, table, link, post, app=None, others=()):
    """One reconciliation pass for one link (table-wide, or one app's). Returns what changed."""
    org = check_workspace(link, post)
    tasks = {t['linear_identifier']: t for t in board.tasks(table)
             if t.get('linear_identifier') and mine(t, app, others)}
    mode, out = link['mode'], {'pulled': [], 'updated_in_anytype': [], 'pushed': [], 'updated_in_linear': []}
    issues = all_issues(post, scope_filter(link))
    seen = {}
    for issue in issues:
        seen[issue['identifier']] = issue
        task = tasks.get(issue['identifier'])
        ending = STATUS_OF.get(issue['state']['type'])
        kind = next((l['name'].upper() for l in (issue.get('labels') or {}).get('nodes', [])
                     if l['name'].upper() in KINDS), None)
        if task is None and mode in ('pull', 'full'):
            props = {'task_project': project, 'task_status': ending or 'Backlog', 'task_source': 'linear',
                     'task_priority': PRIORITY_OF.get(issue['priority'], 'Medium'),
                     'task_agent': 'unassigned', 'linear_identifier': issue['identifier'],
                     'linear_url': issue['url'], 'linear_updated_at': issue['updatedAt']}
            if app:
                props['task_app'] = app
            if kind:
                props['task_kind'] = kind
            made = board.call('POST', 'objects?create_missing_options=true', {
                'type': SCHEMA['type']['key'], 'name': titled(issue['title'], app, kind), 'template': 'none',
                'markdown': 'Mirrored from Linear ' + issue['url'], 'properties': props})
            try:
                board.add(table, [made['id']])
            except RuntimeError:
                board.call('DELETE', 'objects/' + made['id'])     # never leave an orphan outside the table
                raise
            out['pulled'].append(issue['identifier'])
            tasks[issue['identifier']] = {'id': made['id']}
        elif task and mode in ('pull', 'full') and issue['updatedAt'] > (task.get('linear_updated_at') or ''):
            change = {}
            if bare(task.get('name')) != issue['title']:
                change['name'] = titled(issue['title'], task.get('task_app'), task.get('task_kind'))
            if ending and task.get('task_status') != ending:
                change['task_status'] = ending
            if change:
                board.set(task['id'], linear_updated_at=issue['updatedAt'], **change)
                out['updated_in_anytype'].append(issue['identifier'])
    out['workspace'] = org['urlKey']
    if mode == 'pull':
        return out
    team = None

    def label_ids():
        if link.get('scope') != 'label':
            return []
        found = [l['id'] for l in team['labels']['nodes'] if l['name'] == link['label']]
        if not found:
            found = [post(LABEL, {'input': {'name': link['label'], 'teamId': team['id']}})
                     ['issueLabelCreate']['issueLabel']['id']]
            team['labels']['nodes'].append({'id': found[0], 'name': link['label']})
        return found

    for task in board.tasks(table):
        if not mine(task, app, others):
            continue
        labels = task.get('task_labels') or []
        labels = labels if isinstance(labels, list) else [labels]
        if link.get('scope') == 'label' and link['label'] not in labels:
            continue
        ident = task.get('linear_identifier')
        if not ident and task.get('task_source') == 'anytype':
            team = team or post(TEAM, {'key': link['team']})['teams']['nodes'][0]
            made = post(CREATE, {'input': {'teamId': team['id'], 'title': bare(task.get('name')) or 'Untitled',
                                           'description': board.body(task['id']),
                                           'labelIds': label_ids()}})['issueCreate']['issue']
            board.set(task['id'], linear_identifier=made['identifier'], linear_url=made['url'],
                      linear_updated_at=made['updatedAt'])
            out['pushed'].append(made['identifier'])
            continue
        if ident and ident not in seen:
            # Linked earlier but outside this pull's filter (e.g. created here): look it up directly.
            found = post(ONE, {'id': ident}).get('issue')
            if found:
                seen[ident] = found
        if ident in seen and STATE_OF.get(task.get('task_status')) != seen[ident]['state']['type'] \
                and (task.get('linear_updated_at') or '') >= seen[ident]['updatedAt']:
            team = team or post(TEAM, {'key': link['team']})['teams']['nodes'][0]
            want = STATE_OF.get(task.get('task_status'))
            states = sorted((s for s in team['states']['nodes'] if s['type'] == want), key=lambda s: s['position'])
            if states:
                done = post(UPDATE, {'id': seen[ident]['id'], 'input': {'stateId': states[0]['id']}})
                board.set(task['id'], linear_updated_at=done['issueUpdate']['issue']['updatedAt'])
                out['updated_in_linear'].append(ident)
    return out
