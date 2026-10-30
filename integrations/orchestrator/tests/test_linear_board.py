"""The Linear board end to end against an in-memory fake of Linear's GraphQL API."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cli
import linear_board

ME = 'user-me'


class FakeLinear:
    def __init__(self):
        self.issues, self.labels, self.n, self.attachments, self.notes = {}, [], 0, {}, []
        self.states = [{'id': 's-' + t, 'type': t, 'name': t.title(), 'position': i} for i, t in
                       enumerate(['backlog', 'unstarted', 'started', 'completed', 'canceled'])]

    def node(self, i):
        return {**i, 'labels': {'nodes': [l for l in self.labels if l['id'] in i.get('labelIds', [])]},
                'state': next(s for s in self.states if s['id'] == i['stateId']),
                'inverseRelations': {'nodes': i.get('blockedBy', [])}, 'comments': {'nodes': i['comments']}}

    def post(self, query, v):
        if 'notifications(' in query:
            return {'viewer': {'id': ME}, 'notifications': {'nodes': [n for n in self.notes
                    if n['createdAt'] > v['since'] and n['type'] in v['types']]}}
        if 'viewer' in query:
            return {'viewer': {'id': ME}}
        if 'teams(' in query:
            return {'teams': {'nodes': [{'id': 'team-mst', 'states': {'nodes': self.states},
                                         'labels': {'nodes': list(self.labels)}}]}}
        if 'issueLabelCreate' in query:
            label = {'id': 'l%d' % len(self.labels), 'name': v['input']['name']}
            self.labels.append(label)
            return {'issueLabelCreate': {'issueLabel': label}}
        if 'issueCreate' in query:
            self.n += 1
            iid = str(uuid.UUID(int=self.n))
            inp = v['input']
            self.parent_of = getattr(self, 'parent_of', {})
            if inp.get('parentId'):
                self.parent_of[iid] = inp['parentId']
            self.issues[iid] = {'id': iid, 'identifier': 'MST-%d' % self.n, 'title': inp['title'],
                                'description': inp['description'], 'url': 'u', 'branchName': 'me/mst-%d-x' % self.n,
                                'priority': inp['priority'], 'createdAt': '2026', 'updatedAt': '2026',
                                'labelIds': inp.get('labelIds', []), 'stateId': inp['stateId'], 'comments': [],
                                'assignee': {'id': inp['assigneeId']}, 'creator': {'id': ME},
                                'parent': ({'id': inp['parentId'], 'identifier': self.issues[inp['parentId']]['identifier']}
                                           if inp.get('parentId') else None)}
            return {'issueCreate': {'issue': {'id': iid, 'identifier': 'MST-%d' % self.n}}}
        if 'issueUpdate' in query:
            i = self.issues[v['id']]
            i['stateId'] = v['input'].get('stateId', i['stateId'])
            i['labelIds'] = v['input'].get('labelIds', i.get('labelIds', []))
            i['title'] = v['input'].get('title', i['title'])
            return {'issueUpdate': {'success': True}}
        if 'commentCreate' in query:
            self.comment(v['input']['issueId'], v['input']['body'])
            return {'commentCreate': {'comment': {'id': 'c'}}}
        if 'attachmentLinkURL' in query:
            self.attachments.setdefault(v['issueId'], []).append({'url': v['url'], 'title': v['title']})
            return {'attachmentLinkURL': {'success': True}}
        if 'attachments(' in query:
            return {'issue': {'attachments': {'nodes': list(self.attachments.get(v['id'], []))}}}
        if 'issue(id' in query:
            key = v['id']
            if key not in self.issues:                       # lookup by identifier, like Linear
                key = next((i for i, x in self.issues.items() if x['identifier'] == key), None)
            return {'issue': self.node(self.issues[key]) if key else None}
        if 'issues(' in query:
            return {'issues': {'nodes': [self.node(i) for i in self.issues.values()],
                               'pageInfo': {'hasNextPage': False, 'endCursor': None}}}
        raise AssertionError(query)

    def comment(self, issue, body, reactions=()):
        c = self.issues[issue]['comments']
        c.append({'id': 'c%d' % len(c), 'body': body, 'createdAt': '2026-%04d' % len(c),
                  'reactionData': [{'emoji': e, 'userIds': [ME]} for e in reactions]})
        return c[-1]

    def notify(self, kind, issue, body=None, author=('u-po', 'Product Owner'), at='2099-01-01T00:00:00Z', assignee=ME):
        """A notification for the key's user (MST-60): issueAssignedToYou or issueCommentMention."""
        i = self.issues[issue]
        i['assignee'] = {'id': assignee}
        n = {'id': 'n%d' % len(self.notes), 'type': kind, 'createdAt': at, 'actor': {'id': author[0], 'name': author[1]},
             'issue': {'id': issue, 'identifier': i['identifier'], 'title': i['title'], 'url': i['url'],
                       'description': i['description'], 'priority': i['priority'], 'parent': None,
                       'children': {'nodes': []}, 'team': {'key': 'MST'}, 'assignee': i['assignee']}, 'comment': None}
        if body is not None:
            c = self.comment(issue, body)
            n['comment'] = {'id': c['id'] + issue[-4:], 'body': body, 'createdAt': at,
                            'user': {'id': author[0], 'name': author[1]}}
        self.notes.append(n)
        return n

    def labels_of(self, issue):
        return sorted(l['name'] for l in self.labels if l['id'] in self.issues[issue]['labelIds'])

    def state_of(self, issue):
        return next(s['type'] for s in self.states if s['id'] == self.issues[issue]['stateId'])


class LinearBoardFlow(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name) / 'repo'
        (self.repo / '.mstack/secrets').mkdir(parents=True)
        key = self.repo / '.mstack/secrets/linear-api-key'
        key.write_text('k'); key.chmod(0o600)
        (self.repo / '.mstack/stack.json').write_text(json.dumps({'project': 'repo', 'preset': 'solo', 'visibility': 'local',
            'taskboard': {'table': 'repo', 'backend': 'linear', 'workers': ['claude-desktop'],
                          'link': {'provider': 'linear', 'mode': 'full', 'workspace': 'y', 'team': 'MST',
                                   'credential_file': '.mstack/secrets/linear-api-key'}}}))
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), *a], check=True, capture_output=True)
        git('init', '-q'); (self.repo / 'README').write_text('x'); git('add', 'README')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'base')
        self.fake = FakeLinear()
        p = patch.object(cli, 'STATE', Path(temp.name) / 'state.json'); p.start(); self.addCleanup(p.stop)
        p = patch.object(cli, 'LINEAR_BOARD', lambda path, settings, **kw:
                         linear_board.LinearBoard(path, settings, http=lambda key: self.fake.post, **kw))
        p.start(); self.addCleanup(p.stop)
        self.sql = []                                       # never the real Postgres issue table
        p = patch.object(cli, 'psql', self.sql.append); p.start(); self.addCleanup(p.stop)
        self.cli('table', '--project', str(self.repo))

    def cli(self, *argv, stdin=''):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(sys, 'stdin', io.StringIO(stdin)):
            self.assertEqual(cli.main(list(argv), cli.anyboard.Board(call=None)), 0)
        return json.loads(out.getvalue())

    def test_plan_approve_dispatch_review_accept(self):
        task = self.cli('plan', '--project', 'repo', '--title', 'Add rate limit', '--kind', 'FEAT',
                        '--agent', 'claude-desktop', '--plan', '-', stdin='1. do it')['task']
        self.assertEqual(self.fake.state_of(task), 'unstarted')
        self.assertEqual(self.fake.labels, [])                              # no labels created in the team
        first = self.fake.issues[task]['comments'][0]['body']
        self.assertTrue(first.startswith('🤖❓') and '(agent: claude-desktop)' in first)
        self.assertEqual(self.fake.issues[task]['assignee']['id'], ME)
        self.fake.comment(task, ':+1:')                                     # owner approves in Linear
        self.assertEqual(self.cli('poll')[0]['now'], 'Todo')
        spec = self.cli('dispatch', '--project', 'repo')['started'][0]['handoff']
        self.assertEqual(self.fake.state_of(task), 'started')
        branch = subprocess.run(['git', '-C', spec['cwd'], 'branch', '--show-current'], capture_output=True,
                                text=True).stdout.strip()
        self.assertEqual(branch, 'me/mst-1-x')                              # Linear's own branch name
        self.cli('done', '--task', task, '--size', 'small', '--summary', 'added')
        self.assertEqual(self.cli('status', '--project', 'repo')['tasks'][0]['status'], 'In Review')
        ask = self.fake.issues[task]['comments'][-1]
        ask['reactionData'] = [{'emoji': '👍', 'userIds': [ME]}]           # owner reacts on the result
        self.assertEqual(self.cli('poll')[0]['now'], 'Done')
        self.assertEqual(self.fake.state_of(task), 'completed')
        self.assertEqual(self.fake.labels, [])

    def test_session_note_reaches_the_issue(self):
        task = self.cli('plan', '--project', 'repo', '--title', 'T', '--plan', '-', stdin='p')['task']
        self.cli('note', '--task', task, '--direction', 'out', '--agent', 'claude', 'scope changed')
        self.assertIn('scope changed', self.fake.issues[task]['comments'][-1]['body'])

    def test_untouched_history_is_never_dispatched(self):
        self.fake.n += 1
        old = str(uuid.UUID(int=999))
        self.fake.issues[old] = {'id': old, 'identifier': 'MST-99', 'title': 'Old', 'description': '', 'url': 'u',
                                 'branchName': 'me/mst-99', 'priority': 3, 'createdAt': '2025', 'updatedAt': '2025',
                                 'stateId': 's-unstarted', 'comments': [], 'assignee': {'id': ME}, 'creator': {'id': ME}}
        row = [t for t in self.cli('status', '--project', 'repo')['tasks'] if t['task'] == old][0]
        self.assertEqual(row['status'], 'Backlog')                          # Linear "Todo" but never managed
        self.assertEqual(self.cli('dispatch', '--project', 'repo')['started'], [])

    def old_issue(self, n=500, state='s-unstarted', description='Users see a 500 on refresh'):
        iid = str(uuid.UUID(int=n))
        self.fake.issues[iid] = {'id': iid, 'identifier': 'MST-%d' % n, 'title': 'Old %d' % n, 'description': description,
                                 'url': 'u', 'branchName': 'me/mst-%d' % n, 'priority': 3, 'createdAt': '2025',
                                 'updatedAt': '2025', 'stateId': state, 'comments': [],
                                 'assignee': {'id': ME}, 'creator': {'id': ME}}
        return iid

    def auto(self):
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['auto'] = True
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))

    def tick(self):
        with patch.object(cli, 'LINEAR_EVERY', 0):
            return self.cli('tick')

    def test_slash_plan_trigger_propose_approve_dispatch(self):
        self.auto()
        old = self.old_issue()
        self.assertEqual(self.tick()['needs_orchestrator'], [])            # untouched history: nothing
        self.fake.comment(old, '/plan keep it small')
        need = self.tick()['needs_orchestrator']
        self.assertEqual([(n['kind'], n['issue'], n['notes']) for n in need], [('plan', 'MST-500', 'keep it small')])
        self.assertEqual(self.tick()['needs_orchestrator'], [])            # raised once
        self.cli('propose', '--project', 'repo', '--task', 'MST-500', '--agent', 'claude-desktop', '--plan', '-',
                 stdin='1. reproduce\n2. fix')
        self.assertEqual(self.fake.issues[old]['description'], 'Users see a 500 on refresh')   # never overwritten
        self.fake.comment(old, '👍')
        tick = self.tick()
        self.assertEqual([v['now'] for v in tick['verdicts']], ['Todo'])
        spec = [n for n in tick['needs_orchestrator'] if n['kind'] == 'handoff'][0]
        self.assertIn('1. reproduce', spec['prompt'])                       # the proposed plan reaches the worker
        self.assertIn('Users see a 500', spec['prompt'])

    def test_comments_on_work_in_progress_are_forwarded_once(self):
        self.auto()
        task = self.cli('plan', '--project', 'repo', '--title', 'T', '--agent', 'claude-desktop', '--plan', '-',
                        stdin='p')['task']
        self.fake.comment(task, 'lgtm')
        self.tick()
        self.cli('ack', '--task', task, '--session', 'local_w1')
        self.fake.comment(task, 'Also handle the empty cart case')
        need = [n for n in self.tick()['needs_orchestrator'] if n['kind'] == 'forward']
        self.assertEqual([(n['session'], n['text']) for n in need], [('local_w1', 'Also handle the empty cart case')])
        self.assertEqual([n for n in self.tick()['needs_orchestrator'] if n['kind'] == 'forward'], [])

    def test_closing_the_issue_stops_its_worker(self):
        self.auto()
        task = self.cli('plan', '--project', 'repo', '--title', 'T', '--agent', 'claude-desktop', '--plan', '-',
                        stdin='p')['task']
        self.fake.comment(task, 'lgtm')
        self.tick()
        self.cli('ack', '--task', task, '--session', 'local_w2')
        self.fake.issues[task]['stateId'] = 's-canceled'                     # you cancel it in Linear
        need = [n for n in self.tick()['needs_orchestrator'] if n['kind'] == 'stop']
        self.assertEqual([(n['session'], n['now']) for n in need], [('local_w2', 'Canceled')])
        self.assertIn('Stopped', self.fake.issues[task]['comments'][-1]['body'])
        self.assertEqual([n for n in self.tick()['needs_orchestrator'] if n['kind'] == 'stop'], [])

    def test_sub_issue(self):
        parent = self.cli('plan', '--project', 'repo', '--title', 'Epic', '--plan', '-', stdin='p')['task']
        child = self.cli('plan', '--project', 'repo', '--title', 'Part', '--parent', 'MST-1', '--plan', '-',
                         stdin='p')['task']
        self.assertEqual(self.fake.parent_of[child], parent)

    def test_linear_is_polled_at_most_every_30s(self):
        self.auto()
        calls = []
        with patch.object(cli, 'linear_signals', lambda *a: calls.append(1) or []):
            self.cli('tick'); self.cli('tick')
        self.assertEqual(len(calls), 1)

    def scoped(self, **orchestrators):
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text())
        cfg['taskboard']['orchestrators'] = orchestrators
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))

    def test_focus_scope_sees_only_its_roots_and_their_sub_issues(self):
        root = self.cli('plan', '--project', 'repo', '--title', 'Root', '--plan', '-', stdin='p')['task']
        child = self.cli('plan', '--project', 'repo', '--title', 'Child', '--parent', 'MST-1', '--plan', '-', stdin='p')['task']
        other = self.cli('plan', '--project', 'repo', '--title', 'Other', '--plan', '-', stdin='p')['task']
        self.scoped(**{'customer-api': {'apps': ['*'], 'focus': ['MST-1']}})
        seen = {t['task'] for t in self.cli('status', '--project', 'repo', '--scope', 'customer-api')['tasks']}
        self.assertEqual(seen, {root, child})
        self.assertEqual(len(self.cli('status', '--project', 'repo')['tasks']), 3)      # no scope: everything
        self.fake.comment(other, '/plan')                                               # outside focus: ignored
        with patch.object(cli, 'LINEAR_EVERY', 0):
            need = self.cli('tick', '--project', 'repo', '--scope', 'customer-api')['needs_orchestrator']
        self.assertEqual([n for n in need if n['kind'] == 'plan'], [])

    def test_adopted_session_gets_comments_forwarded(self):
        old = self.old_issue(n=600, state='s-started')
        self.scoped(**{'customer-api': {'apps': ['*'], 'focus': ['MST-600']}})
        self.auto()
        out = self.cli('adopt', '--project', 'repo', '--scope', 'customer-api', '--task', 'MST-600',
                       '--session', 'local_owner_session', '--tree', '/w/iro')
        self.assertEqual((out['issue'], out['status']), ('MST-600', 'In Progress'))
        self.assertIn('Tracked by the customer-api orchestrator', self.fake.issues[old]['comments'][-1]['body'])
        self.fake.comment(old, 'Please also check the ARM runners')
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9):
            need = self.cli('tick', '--project', 'repo', '--scope', 'customer-api')['needs_orchestrator']
        self.assertEqual([(n['kind'], n['session']) for n in need], [('forward', 'local_owner_session')])
        # A session's note by issue name lands on the same issue.
        self.cli('note', '--task', 'MST-600', 'ARM runner fixed')
        self.assertIn('ARM runner fixed', self.fake.issues[old]['comments'][-1]['body'])

    def test_exclude_leaves_another_scopes_tree_out(self):
        root = self.cli('plan', '--project', 'repo', '--title', 'Portal', '--plan', '-', stdin='p')['task']
        child = self.cli('plan', '--project', 'repo', '--title', 'Portal part', '--parent', 'MST-1', '--plan', '-', stdin='p')['task']
        other = self.cli('plan', '--project', 'repo', '--title', 'API', '--plan', '-', stdin='p')['task']
        self.scoped(**{'api': {'apps': ['*'], 'exclude': ['MST-1']}, 'portal': {'apps': ['*'], 'focus': ['MST-1']}})
        seen = lambda scope: {t['task'] for t in self.cli('status', '--project', 'repo', '--scope', scope)['tasks']}
        self.assertEqual(seen('api'), {other})                  # and any new issue lands here, not nowhere
        self.assertEqual(seen('portal'), {root, child})

    def test_mirror_writes_every_issue_with_focus_flags(self):
        self.cli('plan', '--project', 'repo', '--title', 'Root', '--plan', '-', stdin='p')
        self.cli('plan', '--project', 'repo', '--title', 'Child', '--parent', 'MST-1', '--plan', '-', stdin='p')
        self.old_issue(n=700, state='s-completed')
        self.scoped(**{'customer-api': {'apps': ['*'], 'focus': ['MST-1']}})
        sql = []
        out = cli.mirror('repo', run_sql=sql.append)
        self.assertEqual((out['rows'], out['focus']), (3, 2))
        rows = json.loads(sql[0].split('$m', 1)[1].split('$', 1)[1].rsplit('$m', 1)[0])
        flags = {r['identifier']: (r['focus'], r['scopes']) for r in rows}
        self.assertEqual(flags, {'MST-1': (True, 'customer-api'), 'MST-2': (True, 'customer-api'), 'MST-700': (False, '')})
        self.assertIn('ON CONFLICT (board, identifier)', sql[0])

    def test_adopting_a_backlog_issue_never_dispatches_a_second_worker(self):
        self.auto()
        self.old_issue(n=800, state='s-backlog')
        out = self.cli('adopt', '--project', 'repo', '--task', 'MST-800', '--session', 'local_existing')
        self.assertEqual(out['status'], 'Awaiting Approval')                   # not started in Linear: a plan, never Todo
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9):
            tick = self.cli('tick', '--project', 'repo')
        self.assertEqual((tick['started'], [n for n in tick['needs_orchestrator'] if n['kind'] == 'handoff']), ([], []))

    def test_history_is_not_raised_for_planning(self):
        self.cli('plan', '--project', 'repo', '--title', 'T', '--plan', '-', stdin='p')
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['auto'] = True
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        tick = self.cli('tick')
        self.assertEqual([n for n in tick['needs_orchestrator'] if n['kind'] == 'plan'], [])


    def test_private_board_never_writes_to_linear(self):
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['private'] = True
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        self.auto()
        old = self.old_issue()
        self.fake.comment(old, '/plan from a teammate')                    # Linear comments are not verdicts
        self.assertEqual(self.tick()['needs_orchestrator'], [])
        self.cli('owner', '--project', 'repo', '--task', 'MST-500', '/plan keep it small')
        need = self.tick()['needs_orchestrator']
        self.assertEqual([(n['kind'], n['notes']) for n in need], [('plan', 'keep it small')])
        self.cli('propose', '--project', 'repo', '--task', 'MST-500', '--agent', 'claude-desktop', '--plan', '-',
                 stdin='1. fix')
        self.cli('owner', '--project', 'repo', '--task', 'MST-500', '👍')
        tick = self.tick()
        self.assertEqual([v['now'] for v in tick['verdicts']], ['Todo'])
        self.assertTrue([n for n in tick['needs_orchestrator'] if n['kind'] == 'handoff'])
        self.cli('ack', '--task', old, '--session', 'local_w1')
        self.cli('done', '--task', old, '--size', 'small', '--summary', 'fixed')
        thread = self.cli('thread', '--project', 'repo', '--task', 'MST-500')
        self.assertEqual(thread['status'], 'In Review')
        self.assertTrue(any('finished' in m['text'] for m in thread['messages']))
        # Linear saw no comment, only the status field (MST-60): a finished worker is still In Progress there.
        self.assertEqual([c['body'] for c in self.fake.issues[old]['comments']], ['/plan from a teammate'])
        self.assertEqual(self.fake.state_of(old), 'started')
        self.assertEqual(oct((self.repo / '.mstack/journal.json').stat().st_mode & 0o777), '0o600')
        out = io.StringIO()
        with contextlib.redirect_stderr(out), contextlib.redirect_stdout(io.StringIO()), \
                patch.object(sys, 'stdin', io.StringIO('p')):       # never the runner's own stdin
            self.assertEqual(cli.main(['plan', '--project', 'repo', '--title', 'New', '--plan', '-'],
                                      cli.anyboard.Board(call=None)), 1)
        self.assertIn('private board', out.getvalue())

    # ---- MST-60: Linear triggers ----
    def test_new_issue_assigned_to_the_owner_starts_orchestration_once(self):
        self.auto()
        old = self.old_issue(n=950)
        self.fake.notify('issueAssignedToYou', old, at='2000-01-01T00:00:00Z')      # before the first read: history
        self.assertEqual(self.tick()['needs_orchestrator'], [])                     # first read: baseline only
        self.assertEqual(self.tick()['needs_orchestrator'], [])
        new = self.old_issue(n=951)
        self.fake.notify('issueAssignedToYou', new)
        tick = self.tick()
        need = tick['needs_orchestrator']
        self.assertEqual([(n['kind'], n['issue']) for n in need], [('new_issue', 'MST-951')])
        self.assertIn('board propose', need[0]['do'])                               # complete: plan, never start
        self.assertIn('Nothing starts unless', need[0]['do'])
        self.assertEqual((need[0]['triage']['priority'], need[0]['triage']['missing']), ('Medium', []))
        thin = self.old_issue(n=952, description='fix it')
        self.fake.issues[thin]['priority'] = 0
        self.fake.notify('issueAssignedToYou', thin)
        gate = self.tick()['needs_orchestrator'][0]                                  # triage gate (owner, 2026-10-30)
        self.assertEqual(gate['triage']['missing'], ['priority', 'scope/description'])
        self.assertIn('do not plan or start it yet', gate['do'])
        self.assertEqual(self.tick()['needs_orchestrator'], [])                     # deduped per assignment
        self.assertEqual(self.cli('status', '--project', 'repo')['tasks'][-1]['status'], 'Backlog')   # nothing started
        self.fake.notify('issueAssignedToYou', new, assignee='someone-else')       # reassigned away: nothing
        self.assertEqual(self.tick()['needs_orchestrator'], [])

    def test_mention_goes_to_the_live_worker_else_the_scope_orchestrator(self):
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['private'] = True
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        self.scoped(**{'api': {'apps': ['*'], 'exclude': ['MST-961']}, 'portal': {'apps': ['*'], 'focus': ['MST-961']}})
        self.auto()
        busy, idle = self.old_issue(n=960, state='s-started'), self.old_issue(n=961)
        self.cli('adopt', '--project', 'repo', '--scope', 'api', '--task', 'MST-960', '--session', 'local_w')
        tick = lambda scope: self.cli('tick', '--project', 'repo', '--scope', scope)['needs_orchestrator']
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9):
            tick('api')                                                             # baseline
            self.fake.notify('issueCommentMention', busy, body='@me can you check the ETA?')
            self.fake.notify('issueCommentMention', idle, body='@me portal needs this')
            self.fake.notify('issueCommentMention', idle, body='note to self', author=(ME, 'Me'))   # own: ignored
            api = [n for n in tick('api') if n['kind'] == 'mention']
            portal = [n for n in tick('portal') if n['kind'] == 'mention']
            self.assertEqual(tick('api') + tick('portal'), [])                      # deduped per comment
        self.assertEqual([(n['issue'], n['session'], n['author']) for n in api], [('MST-960', 'local_w', 'Product Owner')])
        self.assertIn('not an owner instruction', api[0]['do'])
        self.assertEqual([(n['issue'], n['session'], n['text']) for n in portal], [('MST-961', None, '@me portal needs this')])
        self.assertEqual(self.fake.state_of(idle), 'unstarted')                     # a mention starts nothing

    def test_related_sessions_are_listed_but_never_workers(self):
        old = self.old_issue(n=900, state='s-completed')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-900', '--session', 'local_main')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-900', '--session', 'local_old', '--related', 'obsolete')
        row = [r for r in self.cli('status', '--project', 'repo')['tasks'] if r['task'] == old][0]
        self.assertEqual((row['session'], row['related']), ('local_main', [{'session': 'local_old', 'note': 'obsolete'}]))
        self.assertEqual(len(self.fake.issues[old]['comments']), 1)        # only the worker's adoption

    def test_handover_briefs_a_fresh_orchestrator(self):
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['private'] = True
        cfg['taskboard']['orchestrators'] = {'api': {'apps': ['*']}}
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        waiting = self.old_issue(n=501)
        self.cli('owner', '--project', 'repo', '--task', 'MST-501', '/plan')
        self.cli('propose', '--project', 'repo', '--scope', 'api', '--task', 'MST-501', '--plan', '-', stdin='1. fix it')
        self.old_issue(n=502, state='s-started')
        self.cli('adopt', '--project', 'repo', '--scope', 'api', '--task', 'MST-502', '--session', 'local_w')
        self.old_issue(n=503, state='s-completed')                         # untouched history: left out
        out = self.cli('handover', '--project', 'repo', '--scope', 'api')
        self.assertEqual(out['waiting_on_owner'], ['MST-501'])
        self.assertEqual([r['issue'] for r in out['issues']], ['MST-501', 'MST-502'])
        self.assertFalse(out['watcher_running'])
        for text in ('api orchestrator', 'PRIVATE', "worker `local_w`", '1. fix it', 'start `watch --project repo --scope api`'):
            self.assertIn(text, out['prompt'])

    def test_notes_link_docs_instead_of_carrying_them(self):
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text())
        cfg['taskboard']['docs_url'] = 'https://github.com/o/r/blob/main/'
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        old = self.old_issue(n=950, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-950', '--session', 'local_x')
        self.cli('note', '--task', 'MST-950', 'Design written', '--doc', 'docs/design/011-HUB.md')
        self.assertIn('[docs/design/011-HUB.md](https://github.com/o/r/blob/main/docs/design/011-HUB.md)',
                      self.fake.issues[old]['comments'][-1]['body'])

    # ---- sparks MST-25..33 ----
    def test_verdicts_approval_with_notes_and_hedges(self):
        import board
        self.assertEqual(board.verdict_of('Approve'), 'approved')
        # MST-60: a reply with content is never judged by wording; the orchestrator reads it (`board verdict`).
        self.assertEqual(board.verdict_of('Approve. Use the CN region first.'), 'feedback')
        self.assertEqual(board.verdict_of('ok but change the schema'), 'feedback')
        self.assertEqual(board.verdict_of('approve? not sure'), 'feedback')
        task = self.cli('plan', '--project', 'repo', '--title', 'T', '--plan', '-', stdin='p')['task']
        self.fake.comment(task, '👍'); self.fake.comment(task, 'Also add a test for refunds')
        row = self.cli('poll')[0]
        self.assertEqual((row['verdict'], row.get('now'), 'board verdict' in row['action']), ('feedback', None, True))
        out = self.cli('verdict', '--task', task, 'approve', '--why', 'approved, with a test added')
        self.assertEqual((out['now'], 'refunds' in out['notes']), ('Todo', True))
        self.assertIn('refunds', self.cli('dispatch', '--project', 'repo')['started'][0]['handoff']['prompt'])

    def test_adopted_worker_is_resumed_not_stuck_in_todo(self):                                # MST-26
        self.auto()
        old = self.old_issue(n=810, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-810', '--session', 'local_existing')
        self.cli('propose', '--project', 'repo', '--task', 'MST-810', '--plan', '-', stdin='1. next step')
        self.fake.comment(old, '👍')
        need = self.tick()['needs_orchestrator']
        resume = [n for n in need if n['kind'] == 'resume']
        self.assertEqual([(n['session'], '1. next step' in n['prompt']) for n in resume], [('local_existing', True)])
        self.assertEqual(self.fake.state_of(old), 'started')
        self.cli('ack', '--task', 'MST-810', '--session', 'local_existing')
        self.assertEqual([n for n in self.tick()['needs_orchestrator'] if n['kind'] == 'resume'], [])

    def test_done_works_by_issue_name_without_a_worktree(self):                                # MST-28
        old = self.old_issue(n=820, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-820', '--session', 'local_x')
        out = self.cli('done', '--task', 'MST-820', '--size', 'small', '--summary', 'inventory written')
        self.assertEqual(out['status'], 'In Review')
        self.assertIn('no mstack worktree recorded', self.fake.issues[old]['comments'][-1]['body'])

    def refused(self, *argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(list(argv), cli.anyboard.Board(call=None)), 1)
        return err.getvalue()

    def test_done_needs_a_doc_and_a_consolidated_description(self):                      # docs rule by size
        old = self.old_issue(n=830, state='s-started', description='long draft ' * 100)
        self.cli('adopt', '--project', 'repo', '--task', 'MST-830', '--session', 'local_x')
        self.assertIn('pass `--doc <path>`', self.refused('done', '--task', 'MST-830'))       # medium by default
        self.assertIn('not found', self.refused('done', '--task', 'MST-830', '--doc', 'docs/x.md'))
        (self.repo / 'docs').mkdir(); (self.repo / 'docs/x.md').write_text('# x')
        msg = self.refused('done', '--task', 'MST-830', '--doc', 'docs/x.md')
        self.assertIn('1099 characters', msg); self.assertIn('does not link `docs/x.md`', msg)
        self.fake.issues[old]['description'] = 'Short brief. Doc: [docs/x.md](https://h/docs/x.md)'
        out = self.cli('done', '--task', 'MST-830', '--doc', 'docs/x.md', '--summary', 'ok')
        self.assertEqual((out['status'], out['size'], out['forced']), ('In Review', 'medium', False))

    def test_size_from_propose_and_forced_done(self):
        self.old_issue(n=840, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-840', '--session', 'local_x')
        self.cli('propose', '--project', 'repo', '--task', 'MST-840', '--size', 'small', '--plan', '-', stdin='1. tiny')
        self.assertEqual(self.cli('done', '--task', 'MST-840', '--summary', 'ok')['size'], 'small')
        old = self.old_issue(n=850, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-850', '--session', 'local_y')
        self.assertIn('--force', self.refused('done', '--task', 'MST-850', '--size', 'big'))
        self.assertTrue(self.cli('done', '--task', 'MST-850', '--size', 'big', '--force')['forced'])
        self.assertIn('Forced past the docs check', self.fake.issues[old]['comments'][-1]['body'])

    def test_private_board_needs_the_doc_but_not_the_description(self):
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['private'] = True
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        self.old_issue(n=860, state='s-started', description='long draft ' * 100)
        self.cli('adopt', '--project', 'repo', '--task', 'MST-860', '--session', 'local_x')
        self.assertIn('--doc', self.refused('done', '--task', 'MST-860'))
        (self.repo / 'docs').mkdir(); (self.repo / 'docs/p.md').write_text('# p')
        self.assertEqual(self.cli('done', '--task', 'MST-860', '--doc', 'docs/p.md')['status'], 'In Review')

    def test_inhand_stops_the_watcher_raising_the_same_request(self):                          # MST-30
        self.auto()
        old = self.old_issue(n=830)
        self.fake.comment(old, '/plan please')
        self.cli('inhand', '--project', 'repo', '--task', 'MST-830')
        self.assertEqual([n for n in self.tick()['needs_orchestrator'] if n['kind'] == 'plan'], [])

    def test_tree_shows_existing_sub_issues(self):                                             # MST-23/27
        self.cli('plan', '--project', 'repo', '--title', 'Root', '--plan', '-', stdin='p')
        self.cli('plan', '--project', 'repo', '--title', 'Child', '--parent', 'MST-1', '--plan', '-', stdin='p')
        tree = self.cli('tree', '--project', 'repo', '--task', 'MST-1')['tree']
        self.assertEqual([(n['issue'], n['depth']) for n in tree], [('MST-1', 0), ('MST-2', 1)])

    def test_only_a_scope_dispatches_when_there_are_sub_orchestrators(self):                   # MST-33
        self.scoped(**{'api': {'apps': ['*']}})
        out = io.StringIO()
        with contextlib.redirect_stderr(out), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['dispatch', '--project', 'repo'], cli.anyboard.Board(call=None)), 1)
        self.assertIn('only a scope dispatches', out.getvalue())
        self.assertIn('started', self.cli('dispatch', '--project', 'repo', '--scope', 'api'))


    # ---- MST-47: after-merge follow-up ----
    def docs_url(self, private=False):
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text())
        cfg['taskboard']['docs_url'] = 'https://h/blob/main/'
        cfg['taskboard']['private'] = private
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))

    def git(self, *a):
        return subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t', *a],
                              check=True, capture_output=True, text=True).stdout.strip()

    def merged_branch(self, branch, doc='docs/m.md', push=True):
        """A branch with a doc commit, merged --no-ff into main (and pushed to a bare origin)."""
        origin = self.repo.parent / 'origin.git'
        if not origin.exists():
            subprocess.run(['git', 'init', '-q', '--bare', str(origin)], check=True)
            self.git('branch', '-M', 'main'); self.git('remote', 'add', 'origin', str(origin))
            self.git('push', '-q', 'origin', 'main'); self.git('remote', 'set-head', 'origin', 'main')
        self.git('checkout', '-q', '-b', branch)
        (self.repo / 'docs').mkdir(exist_ok=True); (self.repo / doc).write_text('# doc ' + branch)
        self.git('add', doc); self.git('commit', '-q', '-m', 'work on ' + branch)
        self.git('checkout', '-q', 'main'); self.git('merge', '-q', '--no-ff', '-m', 'Merge ' + branch, branch)
        if push:
            self.git('push', '-q', 'origin', 'main')
        return self.git('rev-parse', 'HEAD')

    def test_merged_adds_docs_as_resources_and_closes(self):
        self.docs_url()
        old = self.old_issue(n=870, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-870', '--session', 'local_x')
        sha = self.merged_branch('me/mst-870')
        out = self.cli('merged', '--task', 'MST-870', '--doc', 'docs/m.md')
        self.assertEqual((out['commit'], out['status'], out['resources_added'], out['warnings']),
                         (sha, 'Done', ['docs/m.md'], []))
        self.assertEqual(self.fake.attachments[old], [{'url': 'https://h/blob/main/docs/m.md', 'title': 'docs/m.md'}])
        self.assertTrue(self.fake.issues[old]['comments'][-1]['body'].startswith('🤖 Merged as'))
        self.assertEqual(self.fake.state_of(old), 'completed')
        self.assertEqual(self.cli('status', '--project', 'repo')['tasks'][0]['status'], 'Done')
        again = self.cli('merged', '--task', 'MST-870', '--commit', sha, '--doc', 'docs/m.md')
        self.assertEqual((again['commit'], again['resources_added']), (sha, []))   # already a Resource: skipped
        self.assertEqual(len(self.fake.attachments[old]), 1)

    def test_merged_refuses_until_pushed_and_verify_keeps_review(self):
        self.docs_url()
        old = self.old_issue(n=880, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-880', '--session', 'local_x')
        self.merged_branch('me/mst-879')                                       # sets up origin
        self.merged_branch('me/mst-880', doc='docs/n.md', push=False)
        before = len(self.fake.issues[old]['comments'])
        self.assertIn('not on the pushed origin/main', self.refused('merged', '--task', 'MST-880'))
        self.assertEqual(len(self.fake.issues[old]['comments']), before)
        self.git('push', '-q', 'origin', 'main')
        self.assertIn('not in', self.refused('merged', '--task', 'MST-880', '--doc', 'docs/none.md'))
        out = self.cli('merged', '--task', 'MST-880', '--doc', 'docs/m.md', '--verify', 'run it on {{mstack:CLIENT_REPO}}')
        self.assertEqual(out['status'], 'In Review')
        self.assertIn('docs not updated by the branch: docs/m.md', out['warnings'][0])
        self.assertIn('Still to verify: run it on {{mstack:CLIENT_REPO}}', self.fake.issues[old]['comments'][-1]['body'])
        self.assertEqual(self.fake.state_of(old), 'started')

    def test_status_and_tick_flag_merged_issues_that_are_not_done(self):
        self.auto()
        old = self.old_issue(n=890, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-890', '--session', 'local_x')
        self.fake.comment(old, '🤖 **claude** finished on branch `me/mst-890`')     # managed, In Review
        self.old_issue(n=891, state='s-started')                               # branch never created
        self.merged_branch('me/mst-890')
        self.git('branch', 'me/mst-891')                                       # empty branch: not flagged
        status = self.cli('status', '--project', 'repo')
        self.assertEqual(status['merged_not_done'], ['MST-890'])
        need = [n for n in self.tick()['needs_orchestrator'] if n['kind'] == 'merged']
        self.assertEqual([(n['issue'], n['branch']) for n in need], [('MST-890', 'me/mst-890')])
        self.assertEqual([n for n in self.tick()['needs_orchestrator'] if n['kind'] == 'merged'], [])   # once
        self.cli('merged', '--task', 'MST-890')
        self.assertNotIn('merged_not_done', self.cli('status', '--project', 'repo'))

    def test_note_and_done_add_docs_as_resources(self):
        self.docs_url()
        old = self.old_issue(n=900, state='s-started', description='Brief. Doc: docs/r.md')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-900', '--session', 'local_x')
        (self.repo / 'docs').mkdir(); (self.repo / 'docs/r.md').write_text('# r')
        self.assertEqual(self.cli('note', '--task', 'MST-900', 'Draft', '--doc', 'docs/r.md')['resources_added'], ['docs/r.md'])
        self.assertEqual(self.cli('done', '--task', 'MST-900', '--doc', 'docs/r.md')['resources_added'], [])
        self.assertEqual([a['url'] for a in self.fake.attachments[old]], ['https://h/blob/main/docs/r.md'])

    def test_private_board_merged_stays_local(self):
        self.docs_url(private=True)
        old = self.old_issue(n=910, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-910', '--session', 'local_x')
        self.merged_branch('me/mst-910')
        out = self.cli('merged', '--task', 'MST-910', '--doc', 'docs/m.md')
        self.assertEqual((out['status'], out['resources_added']), ('Done', []))
        self.assertEqual((self.fake.attachments, self.fake.issues[old]['comments'], self.fake.state_of(old)),
                         ({}, [], 'completed'))                                   # the status field only
        self.assertEqual(self.cli('status', '--project', 'repo')['tasks'][0]['status'], 'Done')

    def test_private_status_follows_the_stages_and_landing_branch(self):                      # MST-60
        self.docs_url(private=True)
        self.fake.states.insert(3, {'id': 's-review', 'type': 'started', 'name': 'In Review', 'position': 2.5})
        self.scoped(api={'apps': ['*'], 'never_done': True, 'landing': 'dev-sb'})
        old = self.old_issue(n=920)
        self.cli('owner', '--project', 'repo', '--task', 'MST-920', '/plan')
        self.cli('propose', '--project', 'repo', '--scope', 'api', '--task', 'MST-920', '--plan', '-', stdin='1. fix')
        self.assertEqual(self.fake.state_of(old), 'unstarted')                      # waiting for the owner: unchanged
        self.cli('owner', '--project', 'repo', '--task', 'MST-920', 'OK for read-only prod counts')
        self.assertEqual([r.get('now') for r in self.cli('poll')], [None])          # a side OK approves nothing
        self.cli('owner', '--project', 'repo', '--task', 'MST-920', '👍')
        self.cli('poll')
        self.assertEqual(self.fake.state_of(old), 'started')                        # approved → In Progress
        self.cli('adopt', '--project', 'repo', '--scope', 'api', '--task', 'MST-920', '--session', 'local_x')
        self.cli('done', '--task', 'MST-920', '--size', 'small', '--summary', 'ok')
        self.assertEqual(self.fake.issues[old]['stateId'], 's-started')              # finished, not landed
        self.merged_branch('me/mst-919')                                          # sets origin/main up
        self.git('checkout', '-q', '-b', 'dev-sb'); self.git('checkout', '-q', '-b', 'me/mst-920')
        (self.repo / 'docs/m.md').write_text('# landed'); self.git('commit', '-qam', 'work')
        self.git('checkout', '-q', 'dev-sb'); self.git('merge', '-q', '--no-ff', '-m', 'land', 'me/mst-920')
        self.git('push', '-q', 'origin', 'dev-sb'); self.git('checkout', '-q', 'main')
        out = self.cli('merged', '--task', 'MST-920', '--doc', 'docs/m.md')
        self.assertEqual((out['branch'], self.fake.issues[old]['stateId']), ('dev-sb', 's-started'))   # landed, never Done
        self.cli('merged', '--task', 'MST-920', '--verify', 'on Preview')
        self.assertEqual(self.fake.issues[old]['stateId'], 's-review')               # on Preview → In Review
        self.assertEqual(self.fake.issues[old]['comments'], [])

    def test_watcher_flags_a_linear_status_that_lags_the_board_once(self):                    # MST-58
        self.auto()
        old = self.old_issue(n=940)
        self.cli('adopt', '--project', 'repo', '--task', 'MST-940', '--session', 'local_x', '--stage', 'building')
        self.assertEqual(self.fake.state_of(old), 'started')
        self.fake.issues[old]['stateId'] = 's-unstarted'                              # someone moved it back in Linear
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9):
            lag = [n for n in self.cli('tick')['needs_orchestrator'] if n['kind'] == 'status_lag']
            self.assertEqual([(n['issue'], n['phase'], n['linear']) for n in lag], [('MST-940', 'In Progress', 'Unstarted')])
            self.assertEqual([n for n in self.cli('tick')['needs_orchestrator'] if n['kind'] == 'status_lag'], [])

    def test_adopt_keeps_the_real_stage(self):                                               # customer-api, MST-60
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['private'] = True
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        self.auto()
        self.fake.states.insert(3, {'id': 's-review', 'type': 'started', 'name': 'In Review', 'position': 2.5})
        draft, live, stuck = self.old_issue(n=139), self.old_issue(n=125, state='s-review'), self.old_issue(n=127)
        out = self.cli('adopt', '--project', 'repo', '--task', 'MST-139', '--session', 'a', '--stage', 'planning')
        self.assertEqual((out['status'], self.fake.state_of(draft)), ('Awaiting Approval', 'unstarted'))
        self.assertEqual(self.cli('adopt', '--project', 'repo', '--task', 'MST-125', '--session', 'b')['status'], 'In Review')
        self.assertEqual(self.fake.issues[live]['stateId'], 's-review')                # never pulled back to In Progress
        self.cli('adopt', '--project', 'repo', '--task', 'MST-127', '--session', 'c', '--stage', 'blocked',
                 '--reason', 'waiting for the iOS build')
        self.assertEqual(self.fake.state_of(stuck), 'unstarted')
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9):
            need = self.cli('tick')['needs_orchestrator']
        self.assertEqual([n for n in need if n['kind'] in ('status_lag', 'handoff', 'resume')], [])   # no false lags
        self.assertIn('waiting for the iOS build', self.cli('thread', '--project', 'repo', '--task', 'MST-127')['messages'][-1]['text'])

    def test_explicit_status_wins_and_the_watcher_never_rewrites_it(self):           # {{mstack:CLIENT_REPO}}, 14:20 UTC hotfix
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['private'] = True
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        self.auto()
        self.fake.states.insert(3, {'id': 's-review', 'type': 'started', 'name': 'In Review', 'position': 2.5})
        ids = {n: self.old_issue(n=n, state='s-started') for n in (125, 126, 139, 153)}
        for n in ids:
            self.cli('adopt', '--project', 'repo', '--task', 'MST-%d' % n, '--session', 's%d' % n)
        # 153: approved and queued on the board (Todo), but deliberately delayed.
        self.cli('propose', '--project', 'repo', '--task', 'MST-153', '--plan', '-', stdin='1. later')
        self.cli('owner', '--project', 'repo', '--task', 'MST-153', '👍'); self.cli('poll')
        for n, status in ((153, 'Todo'), (139, 'Backlog'), (126, 'In Progress'), (125, 'In Review')):
            self.cli('note', '--task', 'MST-%d' % n, '--status', status, 'real stage')
        want = {125: 's-review', 126: 's-started', 139: 's-backlog', 153: 's-unstarted'}
        got = lambda: {n: self.fake.issues[i]['stateId'] for n, i in ids.items()}
        self.assertEqual(got(), want)                                                  # exactly what was asked
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9):
            for _ in range(3):                                                         # minutes of watcher ticks
                tick = self.cli('tick')
                self.assertEqual([n for n in tick['needs_orchestrator'] if n['kind'] in ('resume', 'handoff', 'status_lag')], [])
        self.assertEqual(got(), want)                                                  # nothing overwritten
        self.assertEqual(tick['started'], [])                                          # held: never handed back

    def test_lag_check_from_the_live_false_flags(self):                                      # hub events 26-29
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['private'] = True
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        self.auto()
        self.fake.states.insert(3, {'id': 's-review', 'type': 'started', 'name': 'In Review', 'position': 2.5})
        adopt = lambda n, *extra: self.cli('adopt', '--project', 'repo', '--task', 'MST-%d' % n, '--session', 's%d' % n, *extra)
        # 26: approved, deliberately delayed by the owner; board Todo, Linear Todo.
        delayed = self.old_issue(n=153)
        self.cli('owner', '--project', 'repo', '--task', 'MST-153', '/plan')
        self.cli('propose', '--project', 'repo', '--task', 'MST-153', '--plan', '-', stdin='1. fix')
        self.cli('owner', '--project', 'repo', '--task', 'MST-153', '👍')
        self.cli('poll')
        self.fake.issues[delayed]['stateId'] = 's-unstarted'
        # 27: phase In Progress written by the old adopt (no stage stamp); Linear Backlog, a draft plan.
        draft = self.old_issue(n=139, state='s-backlog')
        adopt(139)
        self.fake.issues[draft]['stateId'] = 's-backlog'
        with cli.state() as st:
            st['runs'][draft].pop('stage')
        # 28/29: building on the board, already live on Preview in Linear: never pulled back.
        live = self.old_issue(n=126, state='s-review')
        adopt(126, '--stage', 'building')
        self.assertEqual(self.fake.issues[live]['stateId'], 's-review')               # the push never goes backwards
        # A real lag, and one held on purpose.
        lagging, held = self.old_issue(n=170), self.old_issue(n=171)
        adopt(170, '--stage', 'building'); adopt(171, '--stage', 'building')
        self.fake.issues[lagging]['stateId'] = self.fake.issues[held]['stateId'] = 's-unstarted'
        self.cli('note', '--task', 'MST-171', '--hold', 'owner: after the iOS release', 'delayed')
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9), \
                patch.object(cli, 'cmd_dispatch', lambda *a: {'started': []}):
            lags = [n for n in self.cli('tick')['needs_orchestrator'] if n['kind'] == 'status_lag']
            self.assertEqual([(n['issue'], n['linear'], n['want']) for n in lags], [('MST-170', 'Unstarted', 'Started')])
            self.assertIn('--push-status "Linear Unstarted → Started"', lags[0]['do'])    # want and do agree
            self.cli('note', '--task', 'MST-170', '--push-status', 'status sync')
            self.assertEqual(self.fake.state_of(lagging), 'started')
            self.assertEqual([n for n in self.cli('tick')['needs_orchestrator'] if n['kind'] == 'status_lag'], [])
        self.assertEqual((self.fake.state_of(delayed), self.fake.state_of(draft), self.fake.state_of(held)),
                         ('unstarted', 'backlog', 'unstarted'))

    def test_only_a_send_back_moves_linear_backwards(self):
        self.fake.states.insert(3, {'id': 's-review', 'type': 'started', 'name': 'In Review', 'position': 2.5})
        task = self.cli('plan', '--project', 'repo', '--title', 'T', '--agent', 'claude-desktop', '--plan', '-', stdin='p')['task']
        self.fake.comment(task, '👍'); self.cli('poll'); self.cli('dispatch', '--project', 'repo')
        self.cli('done', '--task', task, '--size', 'small', '--summary', 'x')
        self.assertEqual(self.fake.issues[task]['stateId'], 's-review')
        self.cli('adopt', '--project', 'repo', '--task', task, '--session', 'x', '--stage', 'building')   # not a verdict: stays
        self.assertEqual(self.fake.issues[task]['stateId'], 's-review')
        self.cli('note', '--task', task, '--status', 'In Progress', 'back on it')         # explicit: exactly that
        self.assertEqual(self.fake.issues[task]['stateId'], 's-started')
        self.cli('done', '--task', task, '--size', 'small', '--summary', 'y')
        self.fake.comment(task, 'rename it'); self.cli('poll')
        self.cli('verdict', '--task', task, 'changes')                                  # sent back: may go back
        self.assertEqual(self.fake.state_of(task), 'unstarted')

    def test_team_without_in_review_maps_to_its_nearest_state(self):                          # MST-53
        old = self.old_issue(n=930, state='s-started')
        self.cli('adopt', '--project', 'repo', '--task', 'MST-930', '--session', 'local_x')
        self.cli('done', '--task', 'MST-930', '--size', 'small', '--summary', 'ok')
        self.assertEqual(self.fake.state_of(old), 'started')
        self.assertEqual(json.loads(cli.STATE.read_text())['linear_state_map'], {'MST': {'In Review': 'Started'}})

    def test_adopt_without_a_stage_never_moves_linear(self):                    # customer-api 14:38 UTC, IRO-156..160
        cfg = json.loads((self.repo / '.mstack/stack.json').read_text()); cfg['taskboard']['private'] = True
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))
        self.auto()
        planning = {n: self.old_issue(n=n, state=state) for n, state in ((156, 's-backlog'), (157, 's-unstarted'), (160, 's-unstarted'))}
        for n in planning:
            out = self.cli('adopt', '--project', 'repo', '--task', 'MST-%d' % n, '--session', 's%d' % n)
            self.assertEqual((out['status'], out.get('linear_status')), ('Awaiting Approval', None))
        self.assertEqual({n: self.fake.state_of(i) for n, i in planning.items()},
                         {156: 'backlog', 157: 'unstarted', 160: 'unstarted'})
        forced = self.old_issue(n=158, state='s-started')                        # forced to In Progress before the fix
        self.cli('adopt', '--project', 'repo', '--task', 'MST-158', '--session', 's158')
        self.cli('note', '--task', 'MST-158', '--status', 'Todo', 'planning only')  # In Progress → Todo, exactly
        self.assertEqual(self.fake.state_of(forced), 'unstarted')
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9):
            tick = self.cli('tick')
        self.assertEqual([n for n in tick['needs_orchestrator'] if n['kind'] in ('resume', 'handoff', 'status_lag')], [])
        self.assertEqual(self.fake.state_of(forced), 'unstarted')


class WorkspaceFlow(unittest.TestCase):
    """A project that is a folder of repos (no git at the root)."""
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / '{{mstack:CLIENT_C_FOLDER}}'
        (self.root / '.mstack/secrets').mkdir(parents=True)
        key = self.root / '.mstack/secrets/linear-api-key'
        key.write_text('k'); key.chmod(0o600)
        for name in ('app', 'api'):
            repo = self.root / name
            repo.mkdir()
            git = lambda *a: subprocess.run(['git', '-C', str(repo), *a], check=True, capture_output=True)
            git('init', '-q', '-b', 'main'); (repo / 'README').write_text(name); git('add', 'README')
            git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'base')
        (self.root / '.mstack/stack.json').write_text(json.dumps({'project': '{{mstack:CLIENT_C_FOLDER}}', 'preset': 'solo',
            'taskboard': {'table': '{{mstack:CLIENT_C_FOLDER}}', 'backend': 'linear', 'workers': ['claude-desktop'],
                          'repos': {'app': {'path': 'app', 'base': 'main'}, 'api': {'path': 'api', 'base': 'main'}},
                          'link': {'provider': 'linear', 'mode': 'full', 'workspace': 'y', 'team': 'MST',
                                   'credential_file': '.mstack/secrets/linear-api-key'}}}))
        self.fake = FakeLinear()
        p = patch.object(cli, 'STATE', Path(temp.name) / 'state.json'); p.start(); self.addCleanup(p.stop)
        p = patch.object(cli, 'psql', lambda sql: None); p.start(); self.addCleanup(p.stop)
        p = patch.object(cli, 'LINEAR_BOARD', lambda path, settings, **kw:
                         linear_board.LinearBoard(path, settings, http=lambda key: self.fake.post, **kw))
        p.start(); self.addCleanup(p.stop)
        self.cli('table', '--project', str(self.root))

    cli = LinearBoardFlow.cli
    old_issue = LinearBoardFlow.old_issue

    def test_task_gets_a_worktree_per_repo_it_touches(self):
        old = self.old_issue(n=60)
        self.cli('propose', '--project', '{{mstack:CLIENT_C_FOLDER}}', '--task', 'MST-60', '--repos', 'app', '--plan', '-', stdin='p')
        self.fake.comment(old, '👍')
        self.cli('poll')
        spec = self.cli('dispatch', '--project', '{{mstack:CLIENT_C_FOLDER}}')['started'][0]['handoff']
        tree = Path(spec['cwd'])
        self.assertEqual(tree, self.root / '.mstack/worktrees/mst-60')
        branch = lambda d: subprocess.run(['git', '-C', str(d), 'branch', '--show-current'], capture_output=True,
                                          text=True).stdout.strip()
        self.assertEqual(branch(tree / 'app'), 'me/mst-60')
        self.assertFalse((tree / 'api').exists())
        self.assertIn('## Workspace', spec['prompt'])
        self.assertEqual(spec['title'], 'MST-60: Old 60')
        self.cli('worktree', '--task', 'MST-60', '--repo', 'api')       # the worker finds it needs the API too
        self.assertEqual(branch(tree / 'api'), 'me/mst-60')
        for name in ('app', 'api'):
            (tree / name / 'x').write_text('x')
            subprocess.run(['git', '-C', str(tree / name), 'add', 'x'], check=True)
            subprocess.run(['git', '-C', str(tree / name), '-c', 'user.name=t', '-c', 'user.email=t@t',
                            'commit', '-q', '-m', 'x'], check=True)
        self.cli('done', '--task', old, '--size', 'small', '--summary', 'both')
        self.assertIn('api 1 commit(s); app 1 commit(s)', self.fake.issues[old]['comments'][-1]['body'])
        self.assertEqual(branch(self.root / 'app'), 'main')               # the owner's checkout is untouched

if __name__ == '__main__':
    unittest.main()
