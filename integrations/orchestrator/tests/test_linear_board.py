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
        self.issues, self.labels, self.n = {}, [], 0
        self.states = [{'id': 's-' + t, 'type': t, 'name': t.title(), 'position': i} for i, t in
                       enumerate(['backlog', 'unstarted', 'started', 'completed', 'canceled'])]

    def node(self, i):
        return {**i, 'labels': {'nodes': [l for l in self.labels if l['id'] in i.get('labelIds', [])]},
                'state': next(s for s in self.states if s['id'] == i['stateId']),
                'inverseRelations': {'nodes': i.get('blockedBy', [])}, 'comments': {'nodes': i['comments']}}

    def post(self, query, v):
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
        self.cli('done', '--task', task, '--summary', 'added')
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
        self.assertEqual(out['status'], 'In Progress')
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
        self.cli('done', '--task', old, '--summary', 'fixed')
        thread = self.cli('thread', '--project', 'repo', '--task', 'MST-500')
        self.assertEqual(thread['status'], 'In Review')
        self.assertTrue(any('finished' in m['text'] for m in thread['messages']))
        # Linear saw nothing: only the teammate's comment, and the original state.
        self.assertEqual([c['body'] for c in self.fake.issues[old]['comments']], ['/plan from a teammate'])
        self.assertEqual(self.fake.state_of(old), 'unstarted')
        self.assertEqual(oct((self.repo / '.mstack/journal.json').stat().st_mode & 0o777), '0o600')
        out = io.StringIO()
        with contextlib.redirect_stderr(out), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['plan', '--project', 'repo', '--title', 'New', '--plan', '-'],
                                      cli.anyboard.Board(call=None)), 1)
        self.assertIn('private board', out.getvalue())

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
        self.cli('worktree', '--task', 'MST-60', '--repo', 'api')       # the worker finds it needs the API too
        self.assertEqual(branch(tree / 'api'), 'me/mst-60')
        for name in ('app', 'api'):
            (tree / name / 'x').write_text('x')
            subprocess.run(['git', '-C', str(tree / name), 'add', 'x'], check=True)
            subprocess.run(['git', '-C', str(tree / name), '-c', 'user.name=t', '-c', 'user.email=t@t',
                            'commit', '-q', '-m', 'x'], check=True)
        self.cli('done', '--task', old, '--summary', 'both')
        self.assertIn('api 1 commit(s); app 1 commit(s)', self.fake.issues[old]['comments'][-1]['body'])
        self.assertEqual(branch(self.root / 'app'), 'main')               # the owner's checkout is untouched

if __name__ == '__main__':
    unittest.main()
