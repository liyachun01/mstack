import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import board
import cli
import linear


class FakeBoard(board.Board):
    """In-memory channel: objects with properties/body and one discussion each."""
    def __init__(self):
        self.objects, self.threads, self.n = {}, {}, 0

    def _id(self):
        self.n += 1
        return 'bafy%024d' % self.n

    def ensure_type(self):
        return 'agent_task'

    def ensure_table(self, project, known=None):
        if known and known.get('collection'):
            return known
        return {'collection': 'coll-' + project, 'widget': 'w-' + project}

    def tidy_views(self, collection):
        pass

    def add(self, collection, tasks):
        for t in tasks:
            self.objects[t]['member_of'] = collection

    def move(self, task, type_key):
        self.objects[task]['type'] = type_key

    def create(self, project, title, plan, agent='codex', priority='Medium', labels=(), collection=None,
               app=None, kind=None):
        task = self._id()
        self.objects[task] = {'type': 'agent_task', 'member_of': collection, 'name': board.titled(title, app, kind),
                              'task_app': app, 'task_kind': kind, 'body': '## Plan\n' + plan, 'task_project': project,
                              'task_status': 'Awaiting Approval', 'task_agent': agent, 'task_source': 'anytype',
                              'task_priority': priority, 'task_labels': list(labels), 'agent_run_count': 0}
        return task

    def call(self, method, path, body=None):  # used by linear.sync for pulled issues
        task = self._id()
        self.objects[task] = dict(body['properties'], name=body['name'], body=body['markdown'], type=body['type'])
        return {'id': task}

    def tasks(self, table, kind='collections'):
        if kind == 'queries':   # legacy layout: everything of the project
            return [{'id': t, **o} for t, o in self.objects.items() if o['task_project'] == table.split('-', 1)[1]]
        return [{'id': t, **o} for t, o in self.objects.items() if o.get('member_of') == table]

    def get(self, task):
        return dict(self.objects[task])

    def body(self, task):
        return self.objects[task]['body']

    def set(self, task, **props):
        self.objects[task].update(props)

    def say(self, task, text, ask=False, reply_to=None):
        self.owner(task, (board.ASK if ask else board.MARK) + ' ' + text)

    def owner(self, task, text, reactions=None):
        thread = self.threads.setdefault(task, [])
        thread.append({'id': 'm%d' % len(thread), 'order': '%04d' % len(thread), 'text': text,
                       'reactions': reactions or {}})
        return thread[-1]

    def messages(self, task):
        return self.threads.get(task, [])


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name) / 'market'
        (self.repo / '.mstack').mkdir(parents=True)
        self.configure()
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), *a], check=True, capture_output=True)
        git('init', '-q')
        (self.repo / 'README.md').write_text('market\n')
        git('add', 'README.md')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'base')
        patcher = patch.object(cli, 'STATE', Path(temp.name) / 'state.json')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.b = FakeBoard()
        self.spawned = []
        spawner = patch.object(cli, 'spawn', side_effect=lambda argv, log: self.spawned.append(argv) or 999999)
        spawner.start()
        self.addCleanup(spawner.stop)
        self.run_cli('table', '--project', str(self.repo))

    def configure(self, joints=None, **taskboard):
        cfg = {'project': 'market', 'preset': 'solo', 'visibility': 'local',
               'taskboard': {'table': 'market', 'workers': ['echo'], **taskboard}}
        if joints:
            cfg['joints'] = joints
        (self.repo / '.mstack/stack.json').write_text(json.dumps(cfg))

    def run_cli(self, *argv, stdin=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(sys, 'stdin', io.StringIO(stdin or '')):
            self.assertEqual(cli.main(list(argv), self.b), 0)
        return json.loads(out.getvalue())

    def plan(self, title='Add cart'):
        return self.run_cli('plan', '--project', 'market', '--title', title, '--plan', '-',
                            '--agent', 'echo', stdin='1. model\n2. tests')['task']

    def test_reaction_approves_plan_and_reply_feedback_waits_for_replan(self):
        a, b = self.plan('A'), self.plan('B')
        self.b.threads[a][-1]['reactions'] = {'👍': 1}
        self.b.owner(b, 'Please also handle discounts')
        rows = {r['task']: r for r in self.run_cli('poll', '--project', 'market')}
        self.assertEqual((rows[a]['verdict'], rows[a]['now']), ('approved', 'Todo'))
        self.assertEqual(rows[b]['verdict'], 'feedback')
        self.assertEqual(self.b.objects[b]['task_status'], 'Awaiting Approval')
        self.run_cli('ask', '--task', b, 'Revised: discounts included')
        self.assertEqual(self.run_cli('poll'), [])      # new ask resets: earlier reply no longer counts
        self.b.owner(b, '👍')
        self.assertEqual(self.run_cli('poll')[0]['now'], 'Todo')

    def test_thumbs_down_drops_and_agent_notes_are_not_verdicts(self):
        a = self.plan()
        self.run_cli('note', '--task', a, 'please react when you can')
        self.assertEqual(self.run_cli('poll'), [])
        self.b.threads[a][0]['reactions'] = {'👎': 1}
        self.assertEqual(self.run_cli('poll')[0]['now'], 'Canceled')

    def test_parallel_workers_get_separate_worktrees_then_review_loop(self):
        tasks = [self.plan('Catalog'), self.plan('Checkout')]
        for t in tasks:
            self.b.owner(t, 'lgtm')
        self.run_cli('poll')
        started = self.run_cli('dispatch', '--project', 'market')['started']
        self.assertEqual(len(started), 2)
        self.assertTrue(all(argv[2] == 'work' for argv in self.spawned))   # replayed in-process below
        for t in tasks:
            short = t[-8:]
            tree = self.repo / '.mstack/worktrees' / short
            self.assertEqual((tree / '.mstack/cache/current-task').read_text(), t)
            result = self.run_cli('work', '--task', t, '--table', 'market', '--runner', 'echo', '--tree', str(tree))
            self.assertEqual((result['exit'], result['commits']), (0, 1))
            self.assertEqual(self.b.objects[t]['task_status'], 'In Review')
            self.assertIn('task/' + short, subprocess.run(['git', '-C', str(self.repo), 'branch'],
                                                          capture_output=True, text=True).stdout)
        self.assertNotIn('work-notes', subprocess.run(['git', '-C', str(self.repo), 'ls-files'],
                                                      capture_output=True, text=True).stdout)
        self.b.owner(tasks[0], 'Rename the module please')
        self.b.threads[tasks[1]][-1]['reactions'] = {'✅': 1}
        rows = {r['task']: r['now'] for r in self.run_cli('poll')}
        self.assertEqual(rows, {tasks[0]: 'Todo', tasks[1]: 'Done'})

    def test_max_parallel_and_human_tasks(self):
        self.configure(max_parallel=1)
        a, h = self.plan('A'), self.plan('Human')
        self.b.objects[h]['task_agent'] = 'human'
        for t in (a, h):
            self.b.owner(t, '👍')
        self.run_cli('poll')
        started = self.run_cli('dispatch', '--project', 'market')['started']
        self.assertEqual([s['task'] for s in started], [a])

    def linear_post(self, issue, org='{{mstack:CLIENT_ORG_A_SHORT}}', calls=None):
        def post(query, variables):
            if calls is not None:
                calls.append(variables)
            if 'organization' in query:
                return {'organization': {'urlKey': org, 'name': 'x'}, 'viewer': {'id': 'me'}}
            if 'issues(' in query:
                return {'issues': {'nodes': [issue]}}
            if 'teams(' in query:
                return {'teams': {'nodes': [{'id': 'team', 'labels': {'nodes': []},
                                             'states': {'nodes': [{'id': 's-done', 'type': 'completed', 'position': 1}]}}]}}
            if 'issue(id' in query:
                return {'issue': {'id': 'lin2', 'identifier': variables['id'], 'title': 't', 'url': 'u', 'priority': 3,
                                  'updatedAt': '2026-10-28T01:00:00Z', 'state': {'type': 'backlog'}}}
            if 'issueLabelCreate' in query:
                return {'issueLabelCreate': {'issueLabel': {'id': 'label-1'}}}
            if 'issueUpdate' in query:
                return {'issueUpdate': {'issue': {'updatedAt': '2026-10-28T03:00:00Z'}}}
            return {'issueCreate': {'issue': {'id': 'lin2', 'identifier': 'MKT-2', 'url': 'u',
                                              'updatedAt': '2026-10-28T01:00:00Z'}}}
        return post

    ISSUE = {'id': 'lin1', 'identifier': 'MKT-1', 'title': 'Pulled', 'url': 'https://linear.app/x/MKT-1',
             'priority': 2, 'updatedAt': '2026-10-28T00:00:00Z', 'state': {'type': 'started'},
             'labels': {'nodes': []}}
    LINK = {'workspace': '{{mstack:CLIENT_ORG_A_SHORT}}', 'team': 'MKT'}

    def test_linear_pull_waits_in_backlog_and_push_creates(self):
        local = self.plan('Local only')
        self.b.objects[local]['task_status'] = 'Todo'
        calls = []
        pulled = linear.sync(self.b, 'market', 'coll-market', {**self.LINK, 'mode': 'pull'},
                             self.linear_post(self.ISSUE, calls=calls))
        self.assertEqual((pulled['pulled'], pulled['workspace']), (['MKT-1'], '{{mstack:CLIENT_ORG_A_SHORT}}'))
        mirrored = [o for o in self.b.objects.values() if o.get('linear_identifier') == 'MKT-1'][0]
        self.assertEqual(mirrored['task_status'], 'Backlog')          # "started" in Linear still waits here
        self.assertIn({'team': {'key': {'eq': 'MKT'}}}, calls[1]['filter']['and'])
        full = linear.sync(self.b, 'market', 'coll-market', {**self.LINK, 'mode': 'full'},
                           self.linear_post({**self.ISSUE, 'state': {'type': 'completed'},
                                             'updatedAt': '2026-10-28T02:00:00Z'}))
        self.assertEqual((full['pulled'], full['pushed']), ([], ['MKT-2']))
        self.assertEqual(mirrored['task_status'], 'Done')             # endings carry over
        self.assertEqual(self.b.objects[local]['linear_identifier'], 'MKT-2')

    def test_linear_retries_network_errors_but_not_api_errors(self):
        import urllib.error
        tries = []
        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): pass
        def flaky(req, timeout):
            tries.append(1)
            if len(tries) < 3:
                raise urllib.error.URLError(TimeoutError('handshake timed out'))
            return Resp(b'{"data": {"ok": 1}}')
        self.assertEqual(linear.http('k', pause=0, opener=flaky)('q', {}), {'ok': 1})
        self.assertEqual(len(tries), 3)
        def denied(req, timeout):
            tries.append(1)
            raise urllib.error.HTTPError('u', 401, 'no', {}, io.BytesIO())
        tries.clear()
        with self.assertRaises(urllib.error.HTTPError):
            linear.http('k', pause=0, opener=denied)('q', {})
        self.assertEqual(len(tries), 1)

    def test_linear_label_scope_push_labels_issue_and_syncs_status_back(self):
        t = self.plan('Pushed one')
        self.b.objects[t].update(task_status='Todo', task_labels=['agents'])
        calls = []
        link = {**self.LINK, 'mode': 'full', 'scope': 'label', 'label': 'agents'}
        out = linear.sync(self.b, 'market', 'coll-market', link, self.linear_post(self.ISSUE, calls=calls))
        self.assertEqual(out['pushed'], ['MKT-2'])
        self.assertIn({'input': {'name': 'agents', 'teamId': 'team'}}, calls)          # label created once
        created = [c for c in calls if 'input' in c and 'labelIds' in c['input']][0]
        self.assertEqual(created['input']['labelIds'], ['label-1'])
        self.b.objects[t]['task_status'] = 'Done'
        out = linear.sync(self.b, 'market', 'coll-market', link, self.linear_post(self.ISSUE))
        self.assertEqual(out['updated_in_linear'], ['MKT-2'])                          # found by direct lookup

    def test_one_table_two_app_links(self):
        api_task = self.plan('Rate limit login')
        self.b.objects[api_task].update(task_app='API', task_kind='FEAT', task_status='Todo',
                                         name='[API][FEAT] Rate limit login')
        web_task = self.plan('Fix footer')
        self.b.objects[web_task].update(task_app='WEB', task_status='Todo', name='[WEB] Fix footer')
        bug = {**self.ISSUE, 'identifier': 'IRO-7', 'title': 'Crash on refresh',
               'labels': {'nodes': [{'name': 'Bug'}]}}
        calls = []
        api = linear.sync(self.b, 'market', 'coll-market', {**self.LINK, 'mode': 'full'},
                          self.linear_post(bug, calls=calls), app='API', others=['API', 'WEB'])
        pulled = [o for o in self.b.objects.values() if o.get('linear_identifier') == 'IRO-7'][0]
        self.assertEqual((pulled['name'], pulled['task_app'], pulled['task_kind'], pulled['task_status']),
                         ('[API][BUG] Crash on refresh', 'API', 'BUG', 'Backlog'))
        self.assertEqual(api['pushed'], ['MKT-2'])                                   # only the API task
        self.assertEqual(self.b.objects[api_task]['linear_identifier'], 'MKT-2')
        self.assertNotIn('linear_identifier', self.b.objects[web_task])
        created = [c for c in calls if 'input' in c and 'teamId' in c['input'] and 'title' in c['input']][0]
        self.assertEqual(created['input']['title'], 'Rate limit login')             # prefix stays on the board
        table_wide = linear.sync(self.b, 'market', 'coll-market', {**self.LINK, 'mode': 'push'},
                                 self.linear_post(self.ISSUE), app=None, others=['API', 'WEB'])
        self.assertEqual(table_wide['pushed'], [])                                   # app tasks belong to app links

    def test_sync_runs_every_link_with_its_own_key(self):
        keys = self.repo / '.mstack/secrets'
        keys.mkdir(parents=True, exist_ok=True)
        apps = {}
        for code in ('API', 'WEB'):
            (keys / ('linear-api-key-' + code.lower())).write_text('k-' + code)
            (keys / ('linear-api-key-' + code.lower())).chmod(0o600)
            apps[code] = {'path': 'apps/' + code.lower(), 'link': {
                'provider': 'linear', 'mode': 'pull', **self.LINK,
                'credential_file': '.mstack/secrets/linear-api-key-' + code.lower()}}
        self.configure(apps=apps)
        seen = []
        def fake(b, name, table, link, post, app=None, others=()):
            seen.append((app, sorted(others), link['credential_file']))
            return {'pulled': [], 'pushed': [], 'updated_in_anytype': [], 'updated_in_linear': []}
        with patch.object(linear, 'sync', fake), patch.object(linear, 'http', lambda key: key):
            out = self.run_cli('sync', '--project', 'market')
        self.assertEqual(seen, [('API', ['API', 'WEB'], '.mstack/secrets/linear-api-key-api'),
                                ('WEB', ['API', 'WEB'], '.mstack/secrets/linear-api-key-web')])
        self.assertEqual(sorted(out['links']), ['API', 'WEB'])

    def test_linear_pull_follows_pages_for_full_history(self):
        pages = {None: (['H-1', 'H-2'], 'c1'), 'c1': (['H-3'], None)}
        def post(query, variables):
            if 'organization' in query:
                return {'organization': {'urlKey': '{{mstack:CLIENT_ORG_A_SHORT}}', 'name': 'x'}, 'viewer': {'id': 'me'}}
            ids, nxt = pages[variables['after']]
            return {'issues': {'nodes': [{**self.ISSUE, 'identifier': i, 'title': i} for i in ids],
                               'pageInfo': {'hasNextPage': nxt is not None, 'endCursor': nxt}}}
        out = linear.sync(self.b, 'market', 'coll-market', {**self.LINK, 'mode': 'pull'}, post)
        self.assertEqual(out['pulled'], ['H-1', 'H-2', 'H-3'])

    def test_linear_refuses_a_key_from_another_workspace(self):
        with self.assertRaises(ValueError):
            linear.sync(self.b, 'market', 'coll-market', {**self.LINK, 'mode': 'pull'},
                        self.linear_post(self.ISSUE, org='someone-else'))
        self.assertFalse([o for o in self.b.objects.values() if o.get('linear_identifier')])

    def test_tick_raises_imported_issues_for_planning_once(self):
        self.configure(auto=True, link={'provider': 'linear', 'mode': 'pull', **self.LINK,
                                        'credential_file': '.mstack/secrets/linear-api-key'})
        self.assertIn('key file missing', self.tick()['waiting'][0])
        linear.sync(self.b, 'market', 'coll-market', {**self.LINK, 'mode': 'pull'}, self.linear_post(self.ISSUE))
        need = self.tick()['needs_orchestrator']
        self.assertEqual([(n['kind'], n['linear']) for n in need], [('plan', 'MKT-1')])
        self.assertEqual(self.tick()['needs_orchestrator'], [])
        self.assertEqual(self.tick()['started'], [])                  # never dispatched from Backlog

    def test_one_shared_type_one_collection_per_project_and_legacy_migrates(self):
        a = self.plan()
        self.assertEqual((self.b.objects[a]['type'], self.b.objects[a]['member_of']), ('agent_task', 'coll-market'))
        other = self.b.create('elsewhere', 'Other project', 'x', collection='coll-elsewhere')
        self.assertNotIn(other, [t['id'] for t in self.b.tasks('coll-market')])
        # An earlier per-project-type layout is re-typed in place and its objects removed.
        self.b.objects[a].update(type='task_market', member_of=None)
        data = json.loads(cli.STATE.read_text())
        data['tables']['market'] = {'query': 'query-market', 'type': 'task_market', 'widget': 'w1',
                                    'path': str(self.repo)}
        cli.STATE.write_text(json.dumps(data))
        deleted = []
        self.b.call = lambda method, path, body=None: deleted.append(path)
        self.assertEqual(self.run_cli('table', '--project', str(self.repo))['moved'], [a])
        self.assertEqual((self.b.objects[a]['type'], self.b.objects[a]['member_of']), ('agent_task', 'coll-market'))
        self.assertEqual(deleted, ['objects/query-market', 'widgets/w1', 'types/task_market'])

    def test_project_agent_plugin_is_used_without_code_changes(self):
        folder = self.repo / '.mstack/plugins/scribe'
        folder.mkdir(parents=True)
        (folder / 'plugin.json').write_text(json.dumps({
            'name': 'scribe', 'version': '0.1.0', 'joint': 'agent', 'status': 'implemented', 'transport': 'argv',
            'command': ['{python}', '{plugin_dir}/scribe.py']}))
        (folder / 'scribe.py').write_text(
            'import subprocess\nopen("SCRIBE.md", "w").write("hi")\n'
            'subprocess.run(["git", "add", "SCRIBE.md"], check=True)\n'
            'subprocess.run(["git", "-c", "user.name=s", "-c", "user.email=s@s", "commit", "-q", "-m", "scribe"], check=True)\n')
        self.configure(workers=['scribe'])
        a = self.plan()
        self.b.objects[a]['task_agent'] = 'scribe'
        self.b.owner(a, '👍')
        self.run_cli('poll')
        self.assertEqual(self.run_cli('dispatch', '--project', 'market')['started'][0]['runner'], 'scribe')
        tree = self.repo / '.mstack/worktrees' / a[-8:]
        result = self.run_cli('work', '--task', a, '--table', 'market', '--runner', 'scribe', '--tree', str(tree))
        self.assertEqual((result['exit'], result['commits']), (0, 1))

    def register_headroom(self):
        sys.path.insert(0, str(Path(cli.__file__).resolve().parents[1] / 'stack'))
        import project_state
        with project_state.edit(self.repo) as st:
            st['tenants']['headroom'] = {'tenant': 'market', 'container': 'mstack-headroom'}

    def approved(self, agent):
        a = self.plan()
        self.b.objects[a]['task_agent'] = agent
        self.b.owner(a, '👍')
        self.run_cli('poll')
        return a

    def test_codex_run_gets_project_mcp_servers_per_run(self):
        self.configure(workers=['codex'], joints={'compress': 'headroom'})
        self.register_headroom()
        a = self.approved('codex')
        with patch.object(cli.registry.shutil, 'which', return_value='/bin/codex'):
            row = self.run_cli('dispatch', '--project', 'market')['started'][0]
        self.assertEqual((row['tools'], row['skipped_tools']), (['mstack_headroom'], []))
        tree = self.repo / '.mstack/worktrees' / a[-8:]
        self.assertIn('mstack_headroom: pass large JSON', (tree / '.mstack/cache/brief.md').read_text())
        run = json.loads(cli.STATE.read_text())['runs'][a]
        argv = cli.runners.command('codex', 'brief', tree, self.repo, run['mcp'])
        self.assertIn('mcp_servers.mstack_headroom.command="python3"', argv)
        launch = [x for x in argv if x.startswith('mcp_servers.mstack_headroom.args=')][0]
        self.assertIn('"--project", "%s", "--tool", "headroom"' % self.repo.resolve(), launch)
        self.assertFalse((tree / '.mcp.json').exists())

    def test_claude_desktop_gets_untracked_mcp_json_in_local_mode(self):
        self.configure(workers=['claude-desktop'], joints={'compress': 'headroom'})
        self.register_headroom()
        a = self.approved('claude-desktop')
        row = self.run_cli('dispatch', '--project', 'market')['started'][0]
        tree = Path(row['handoff']['cwd'])
        servers = json.loads((tree / '.mcp.json').read_text())['mcpServers']
        self.assertEqual(list(servers), ['mstack_headroom'])
        settings = json.loads((tree / '.claude/settings.local.json').read_text())
        self.assertEqual(settings['enabledMcpjsonServers'], ['mstack_headroom'])
        self.assertIn('mstack_headroom', row['handoff']['prompt'])
        status = subprocess.run(['git', '-C', str(tree), 'status', '--porcelain', '--untracked-files=all'],
                                capture_output=True, text=True).stdout
        self.assertNotIn('.mcp.json', status)

    def test_tools_are_skipped_with_reasons_not_forced(self):
        self.configure(workers=['claude-desktop'], joints={'compress': 'headroom'})
        a = self.approved('claude-desktop')            # tenant not registered
        row = self.run_cli('dispatch', '--project', 'market')['started'][0]
        self.assertEqual(row['tools'], [])
        self.assertIn('not available', row['skipped_tools'][0])
        self.assertFalse((Path(row['handoff']['cwd']) / '.mcp.json').exists())

    def test_team_owned_mcp_json_is_never_edited(self):
        (self.repo / '.mcp.json').write_text('{"mcpServers": {}}')
        subprocess.run(['git', '-C', str(self.repo), 'add', '-f', '.mcp.json'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t',
                        'commit', '-q', '-m', 'team mcp'], check=True)
        self.configure(workers=['claude-desktop'], joints={'compress': 'headroom'})
        self.register_headroom()
        self.approved('claude-desktop')
        row = self.run_cli('dispatch', '--project', 'market')['started'][0]
        self.assertIn('tracks its own .mcp.json', row['skipped_tools'][0])
        self.assertEqual((Path(row['handoff']['cwd']) / '.mcp.json').read_text(), '{"mcpServers": {}}')

    def test_brief_carries_approved_revisions(self):
        a = self.plan()
        self.b.owner(a, 'add US-CA please')
        self.run_cli('ask', '--task', a, 'Revised: AU, NZ and US-CA')
        self.b.owner(a, '👍')
        self.run_cli('poll')
        self.run_cli('dispatch', '--project', 'market')
        brief = (self.repo / '.mstack/worktrees' / a[-8:] / '.mstack/cache/brief.md').read_text()
        self.assertIn('- Revised: AU, NZ and US-CA\n', brief)
        self.assertNotIn('React 👍', brief.split('Owner notes:')[0])

    def tick(self):
        return self.run_cli('tick')

    def test_tick_ignores_tables_that_did_not_opt_in(self):
        a = self.plan()
        self.b.owner(a, '👍')
        self.assertEqual(self.tick()['tables'], [])
        self.assertEqual(self.b.objects[a]['task_status'], 'Awaiting Approval')

    def test_tick_turns_an_approval_into_a_running_worker_once(self):
        self.configure(auto=True)
        a = self.plan()
        self.b.owner(a, ':+1:')
        first = self.tick()
        self.assertEqual([v['now'] for v in first['verdicts']], ['Todo'])
        self.assertEqual([r['task'] for r in first['started']], [a])
        self.assertEqual(self.b.objects[a]['task_status'], 'In Progress')
        second = self.tick()
        self.assertEqual((second['verdicts'], second['started'], second['needs_orchestrator']), ([], [], []))
        self.assertEqual(len(self.spawned), 1)

    def test_tick_offers_handoffs_until_acknowledged(self):
        self.configure(auto=True, workers=['claude-desktop'])
        a = self.approved('claude-desktop')
        need = self.tick()['needs_orchestrator']
        self.assertEqual([(n['kind'], n['task'], n['via']) for n in need], [('handoff', a, 'start_session')])
        self.assertEqual(len(self.tick()['needs_orchestrator']), 1)      # still not started: offered again
        self.run_cli('ack', '--task', a, '--session', 'local_abc')
        self.assertEqual(json.loads(cli.STATE.read_text())['sessions_seen']['local_abc']['state'], 'active')
        self.assertEqual(self.tick()['needs_orchestrator'], [])
        self.assertEqual(self.tick()['started'], [])                    # busy, never re-dispatched

    def test_tick_surfaces_plan_feedback_once(self):
        self.configure(auto=True)
        a = self.plan()
        self.b.owner(a, 'split this into two tasks')
        need = self.tick()['needs_orchestrator']
        self.assertEqual([(n['kind'], n['feedback']) for n in need], [('replan', 'split this into two tasks')])
        self.assertEqual(self.tick()['needs_orchestrator'], [])

    def test_watch_reloads_itself_when_mstack_changes(self):
        class Reloaded(Exception):
            pass
        def execv(exe, argv):
            raise Reloaded(argv)
        with patch.object(cli, 'code_fingerprint', side_effect=['old', 'new']), \
                patch.object(cli.os, 'execv', execv), patch.object(cli.subprocess, 'run') as run, \
                patch.object(cli, 'ARGV', ['watch', '--interval', '0']):
            with self.assertRaises(Reloaded) as raised:
                cli.main(['watch', '--interval', '0'], self.b)
        self.assertEqual(raised.exception.args[0][2:], ['watch', '--interval', '0'])
        run.assert_not_called()                        # no --project: nothing to sync first

    def test_watch_called_in_process_never_reexecs(self):
        with patch.object(cli, 'code_fingerprint', side_effect=['old', 'new', 'newer']), \
                patch.object(cli.os, 'execv', side_effect=AssertionError('re-exec from a test')):
            self.assertEqual(cli.main(['watch', '--interval', '0', '--max-ticks', '1'], self.b), 0)

    def test_spark_files_a_backlog_issue_on_mstacks_board(self):
        import spark
        posted = []
        class Link:
            def team(self): return {'id': 'team-mst'}
            def me(self): return 'me'
            def state_id(self, status): return 's-' + status
            def post(self, query, v):
                posted.append(v['input'])
                return {'issueCreate': {'issue': {'id': 'x', 'identifier': 'MST-99'}}}
        with patch.dict(spark.os.environ, {'CLAUDE_CODE_HOST_SESSION_ID': 'local_api'}):
            out = spark.file_spark('{{mstack:CLIENT_REPO}}', 'Orchestrators forget their role', 'details', ['docs/a.md'], Link())
        self.assertEqual(out['issue'], 'MST-99')
        made = posted[0]
        self.assertEqual((made['title'], made['stateId'], made['assigneeId']),
                         ('[SPARK] Orchestrators forget their role', 's-Backlog', 'me'))
        self.assertIn('**From:** {{mstack:CLIENT_REPO}}, session `local_api`', made['description'])
        self.assertIn('`docs/a.md`', made['description'])

    def test_watch_exits_only_with_work(self):
        self.configure(auto=True, workers=['claude-desktop'])
        with patch.object(cli.time, 'sleep'), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.run_cli('watch', '--max-ticks', '2', '--interval', '0'),
                             {'stopped': 'max ticks reached'})
            a = self.approved('claude-desktop')
            result = self.run_cli('watch', '--interval', '0')
        self.assertEqual(result['needs_orchestrator'][0]['task'], a)

    def test_linear_outage_never_breaks_tick_and_sync_is_rate_limited(self):
        self.configure(auto=True, link={'provider': 'linear', 'mode': 'pull', **self.LINK,
                                        'credential_file': '.mstack/secrets/linear-api-key'})
        key = self.repo / '.mstack/secrets/linear-api-key'
        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text('lin_test')
        key.chmod(0o644)
        self.assertIn('Private project credential', self.tick()['skipped_tables']['market'])
        key.chmod(0o600)
        calls = []
        def down(args, b):
            calls.append(1)
            raise RuntimeError('handshake timed out')
        with patch.object(cli, 'cmd_sync', down):
            first = self.tick()
            second = self.tick()
        self.assertIn('handshake', first['sync_errors']['market'])
        self.assertNotIn('sync_errors', second)            # not retried until SYNC_EVERY passes
        self.assertEqual(len(calls), 1)

    def test_second_watcher_refuses_to_start(self):
        held = open(cli.STATE.with_name('watch.all.lock'), 'w')
        cli.fcntl.flock(held, cli.fcntl.LOCK_EX | cli.fcntl.LOCK_NB)
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['watch', '--max-ticks', '1'], self.b), 1)
        self.assertIn('already running', err.getvalue())
        held.close()

    def test_dependent_task_waits_then_starts_with_blocker_branches(self):
        blocker, dependent = self.approved('echo'), self.approved('echo')
        self.b.objects[dependent]['task_blocked_by'] = [blocker]
        started = self.run_cli('dispatch', '--project', 'market', '--runner', 'echo')['started']
        self.assertEqual([r['task'] for r in started], [blocker])          # dependent waits
        tree = self.repo / '.mstack/worktrees' / blocker[-8:]
        self.run_cli('work', '--task', blocker, '--table', 'market', '--runner', 'echo', '--tree', str(tree))
        self.b.objects[blocker]['task_status'] = 'Done'
        started = self.run_cli('dispatch', '--project', 'market', '--runner', 'echo')['started']
        self.assertEqual([r['task'] for r in started], [dependent])
        log = subprocess.run(['git', '-C', str(self.repo / '.mstack/worktrees' / dependent[-8:]), 'log', '--oneline'],
                             capture_output=True, text=True).stdout
        self.assertIn('echo worker', log)                                   # blocker's commit is in
        self.assertNotIn('echo worker', subprocess.run(['git', '-C', str(self.repo), 'log', '--oneline', 'master'],
                                                       capture_output=True, text=True).stdout)

    def test_naming_convention_and_app_folder(self):
        self.configure(apps={'API': {'path': 'apps/api'}}, workers=['claude-desktop'])
        (self.repo / 'apps/api').mkdir(parents=True)
        (self.repo / 'apps/api/main.py').write_text('x')
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t',
                        'commit', '-q', '-m', 'api'], check=True)
        a = self.run_cli('plan', '--project', 'market', '--title', 'Login fails on retry', '--plan', '-',
                         '--app', 'API', '--kind', 'BUG', '--agent', 'claude-desktop', stdin='fix it')['task']
        self.assertEqual((self.b.objects[a]['name'], self.b.objects[a]['task_app'], self.b.objects[a]['task_kind']),
                         ('[API][BUG] Login fails on retry', 'API', 'BUG'))
        for bad in (['--app', 'WEB'], ['--kind', 'WISH']):
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(['plan', '--project', 'market', '--title', 'x', '--plan', '-', *bad],
                                          self.b), 1)
        self.b.owner(a, '👍')
        self.run_cli('poll')
        spec = self.run_cli('dispatch', '--project', 'market')['started'][0]['handoff']
        self.assertTrue(spec['cwd'].endswith('/apps/api'))
        self.assertIn('belongs to app [API]', spec['prompt'])

    def test_private_table_does_not_sync(self):
        self.assertEqual(self.run_cli('sync', '--project', 'market')['link'], 'private')


    def test_desktop_handoff_gets_launch_spec_and_reports_with_done(self):
        self.configure(workers=['claude-desktop', 'echo'], max_parallel=1)
        a, b = self.plan('Desk A'), self.plan('Desk B')
        for t in (a, b):
            self.b.objects[t]['task_agent'] = 'claude-desktop'
            self.b.owner(t, '👍')
        self.run_cli('poll')
        started = self.run_cli('dispatch', '--project', 'market')['started']
        self.assertEqual(self.spawned, [])                       # nothing launched from the shell
        spec = started[0]['handoff']
        tree = Path(spec['cwd'])
        self.assertEqual((spec['host'], spec['via']), ('claude-desktop', 'start_session'))
        self.assertIn('done --task ' + a, spec['prompt'])
        self.assertEqual((tree / '.mstack/cache/current-task').read_text(), a)
        self.assertTrue((tree / '.mstack/cache/brief.md').is_file())
        # A handed-off task stays busy until it reports, so max_parallel holds.
        self.assertEqual(self.run_cli('dispatch', '--project', 'market')['started'], [])
        (tree / 'feature.txt').write_text('x')
        subprocess.run(['git', '-C', str(tree), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(tree), '-c', 'user.name=t', '-c', 'user.email=t@t',
                        'commit', '-q', '-m', 'desk'], check=True)
        self.assertEqual(self.run_cli('done', '--task', a, '--size', 'small', '--summary', 'Added feature')['commits'], 1)
        self.assertEqual(self.b.objects[a]['task_status'], 'In Review')
        self.assertTrue(self.b.threads[a][-1]['text'].startswith(board.ASK))
        self.assertEqual(self.run_cli('dispatch', '--project', 'market')['started'][0]['task'], b)

    def test_owner_opened_desktop_gets_instructions(self):
        self.configure(workers=['codex-desktop'])
        a = self.plan()
        self.b.objects[a]['task_agent'] = 'codex-desktop'
        self.b.owner(a, 'go ahead')
        self.run_cli('poll')
        spec = self.run_cli('dispatch', '--project', 'market')['started'][0]['handoff']
        self.assertEqual(spec['via'], 'owner')
        self.assertIn('.mstack/cache/brief.md', spec['instructions'])

    def test_done_requires_dispatch(self):
        a = self.plan()
        out = io.StringIO()
        with contextlib.redirect_stderr(out), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['done', '--task', a], self.b), 1)
        self.assertIn('has no worker on the board', out.getvalue())

    # ---- CLI workers: DeepSeek Harness (`dsh`) through a fake binary, like `echo` (MST-57) ----------------------
    def fake_dsh(self, **env):
        """Put a fake `dsh` first on PATH; returns the file its argv lines go to."""
        bin_dir = self.repo.parent / 'bin'
        bin_dir.mkdir(exist_ok=True)
        fake = bin_dir / 'dsh'
        fake.write_text('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, Path(__file__).with_name('fake_dsh.py')))
        fake.chmod(0o755)
        argv_log = self.repo.parent / 'dsh-argv.jsonl'
        values = {'PATH': '%s:%s' % (bin_dir, os.environ['PATH']), 'FAKE_DSH_ARGV': str(argv_log), **env}
        patcher = patch.dict(os.environ, values)
        patcher.start()
        self.addCleanup(patcher.stop)
        return argv_log

    def dsh_task(self, **env):
        argv_log = self.fake_dsh(**env)
        self.configure(workers=['dsh'], joints={'compress': 'headroom'})
        self.register_headroom()
        a = self.approved('dsh')
        row = self.run_cli('dispatch', '--project', 'market')['started'][0]
        self.assertEqual((row['runner'], row['tools']), ('dsh', ['mstack_headroom']))
        return a, self.repo / '.mstack/worktrees' / a[-8:], argv_log

    def work(self, a, tree, *extra):
        return self.run_cli('work', '--task', a, '--table', 'market', '--runner', 'dsh', '--tree', str(tree), *extra)

    def calls(self, argv_log):
        return [json.loads(line) for line in argv_log.read_text().splitlines()]

    def test_dsh_worker_records_session_then_resumes_with_a_forwarded_comment(self):
        a, tree, argv_log = self.dsh_task()
        result = self.work(a, tree)
        session = result['session']
        self.assertTrue(session.startswith('fake-'))
        self.assertEqual((result['exit'], result['commits'], result['turns']), (0, 1, 1))
        self.assertIn('Fake dsh finished: Task:', self.b.threads[a][-1]['text'])     # summary from the final event
        self.assertEqual(self.b.objects[a]['task_status'], 'In Review')
        run = json.loads(cli.STATE.read_text())['runs'][a]
        self.assertEqual((run['session'], run['native_session'], run['live']), ('dsh:' + session, session, False))
        first = self.calls(argv_log)[0]
        self.assertEqual((first[:2], first[-2]), (['--profile', 'headless'], '--json'))   # argv[0] is not logged
        self.assertNotIn('--session-id', first)
        patch_file = Path(first[first.index('--patch') + 1])
        self.assertEqual(patch_file.parent, tree / '.mstack/cache')
        self.assertIn('"serverName": "mstack_headroom"', patch_file.read_text())
        self.assertTrue(Path(run['log']).with_suffix('.stream.log').read_text().count('"type": "session"'))
        # The owner comments after the run ended: queued, and a resumed turn is spawned at once.
        self.spawned.clear()
        delivered = self.run_cli('forward', '--task', a, 'Rename the module please')['delivered']
        self.assertIn('resumed dsh session ' + session, delivered)
        self.assertEqual(self.spawned[0][-1], '--resume')
        result = self.work(a, tree, '--resume')
        last = self.calls(argv_log)[-1]
        self.assertEqual(last[last.index('--session-id') + 1], session)
        self.assertIn('Rename the module please', last[-1])
        self.assertEqual((result['session'], result['commits']), (session, 2))
        self.assertNotIn('queued', json.loads(cli.STATE.read_text())['runs'][a])

    def test_dsh_comment_during_a_turn_becomes_the_next_turn_of_the_same_session(self):
        a, tree, argv_log = self.dsh_task(FAKE_DSH_QUEUE=str(cli.STATE))
        result = self.work(a, tree)
        self.assertEqual(result['turns'], 2)
        second = self.calls(argv_log)[1]
        self.assertEqual(second[second.index('--session-id') + 1], result['session'])
        self.assertIn('Also add a test please', second[-1])
        asks = [m for m in self.b.threads[a] if m['text'].startswith(board.ASK)]
        self.assertEqual(len(asks), 2)                           # the plan ask and one review ask, not two

    def test_dsh_worker_that_reported_done_itself_is_not_reported_twice(self):
        a, tree, _ = self.dsh_task(FAKE_DSH_DONE=str(cli.STATE))
        before = len(self.b.threads[a])
        result = self.work(a, tree)
        self.assertEqual(result['finish'], 'skipped: the worker already reported done')
        self.assertEqual(len(self.b.threads[a]), before)

    def test_back_from_review_dispatch_resumes_the_dsh_session(self):
        a, tree, _ = self.dsh_task()
        session = self.work(a, tree)['session']
        self.b.owner(a, 'Please rename the module')
        self.assertEqual(self.run_cli('poll')[0]['now'], 'Todo')
        self.spawned.clear()
        self.run_cli('dispatch', '--project', 'market')
        self.assertEqual(self.spawned[0][-1], '--resume')
        self.assertEqual(json.loads(cli.STATE.read_text())['runs'][a]['native_session'], session)

    def sleeper(self, task):
        """A process that looks like `cli.py work --task <task>` (what stop_cli checks), in its own group."""
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', str(Path(cli.__file__)),
                                 'work', '--task', task], start_new_session=True)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        return proc

    def test_board_stop_and_hub_delivery_for_cli_workers(self):
        a, tree, _ = self.dsh_task()
        self.work(a, tree)
        proc = self.sleeper(a)
        with cli.state() as s:
            s['runs'][a].update(pid=proc.pid, live=True)
        # While it runs, a forwarded comment waits for the next turn; nothing new is spawned.
        self.spawned.clear()
        left, done = cli.deliver_to_cli([{'kind': 'forward', 'table': 'market', 'task': a, 'text': 'one more thing'},
                                         {'kind': 'plan', 'table': 'market', 'task': 'other'}], self.b)
        self.assertEqual([i['kind'] for i in left], ['plan'])
        self.assertIn('queued for the running dsh worker', done[0]['result'])
        self.assertIn('Your comment went to the CLI worker', self.b.threads[a][-1]['text'])
        self.assertEqual(self.spawned, [])
        # A pid that is not this task's worker is never signalled.
        other = self.sleeper('someone-else')
        with cli.state() as s:
            s['runs'][a].update(pid=other.pid, live=True)
        self.assertIn('no longer this worker', cli.stop_cli(a))
        self.assertIsNone(other.poll())
        with cli.state() as s:
            s['runs'][a].update(pid=proc.pid, live=True)
            del s['runs'][a]['stopped']
        # The owner closed the issue: the hub stops the process group.
        left, done = cli.deliver_to_cli([{'kind': 'stop', 'table': 'market', 'task': a, 'now': 'Canceled'}], self.b)
        self.assertEqual(left, [])
        self.assertIn('stopped dsh worker (pid %d)' % proc.pid, done[0]['result'])
        self.assertEqual(proc.wait(timeout=10), -15)
        run = json.loads(cli.STATE.read_text())['runs'][a]
        self.assertTrue(run['stopped'])
        self.assertEqual(run['queued'], [])
        self.assertIn('not delivered', self.run_cli('forward', '--task', a, 'too late')['delivered'])
        self.assertIn('was not running', self.run_cli('stop', '--task', a)['stopped'])
        self.assertIn('Worker stopped', self.b.threads[a][-1]['text'])

    def test_stop_refuses_desktop_workers(self):
        self.configure(workers=['claude-desktop'])
        a = self.approved('claude-desktop')
        self.run_cli('dispatch', '--project', 'market')
        with self.assertRaises(ValueError):
            cli.stop_cli(a)


class BridgeRetryTests(unittest.TestCase):
    def test_429_is_retried_other_errors_are_not(self):
        from types import SimpleNamespace as NS
        replies = [NS(returncode=1, stderr='HTTP 429 rate_limit_exceeded', stdout=''),
                   NS(returncode=1, stderr='HTTP 429 rate_limit_exceeded', stdout=''),
                   NS(returncode=0, stderr='', stdout='{"body": {"ok": 1}}')]
        waits = []
        self.assertEqual(board.macctl('GET', 'x', runner=lambda *a, **k: replies.pop(0), sleep=waits.append), {'ok': 1})
        self.assertEqual(waits, [1, 2])
        with self.assertRaises(RuntimeError):
            board.macctl('GET', 'x', runner=lambda *a, **k: NS(returncode=1, stderr='HTTP 400 bad', stdout=''),
                         sleep=waits.append)


class DecideTests(unittest.TestCase):
    def test_owner_words(self):
        ask = {'id': 'a', 'order': '1', 'text': board.ASK + ' plan', 'reactions': {}}
        for text, verdict in [('LGTM!', 'approved'), ('👍', 'approved'), ('ok', 'approved'),
                              ('ok but use sqlite', 'feedback')]:
            self.assertEqual(board.decide([ask, {'order': '2', 'text': text}])[0], verdict)
        self.assertEqual(board.decide([ask])[0], 'pending')

    def test_several_comments_are_judged_one_by_one(self):
        ask = {'id': 'a', 'order': '1', 'text': board.ASK + ' plan', 'reactions': {}}
        for texts, verdict in [(['approve 👍', '👍'], 'approved'), (['lgtm', ':+1:'], 'approved'),
                               (['👍👍'], 'approved'), (['approve 👍', 'but use sqlite'], 'feedback'),
                               (['👎'], 'rejected'), (['ok', 'actually split it'], 'feedback')]:
            msgs = [ask] + [{'order': str(i + 2), 'text': t} for i, t in enumerate(texts)]
            self.assertEqual(board.decide(msgs)[0], verdict, texts)

    def test_titles_get_the_app_prefix_even_with_their_own_brackets(self):
        self.assertEqual(board.titled('[clientapp-api] Slow import', 'API', 'BUG'), '[API][BUG] [clientapp-api] Slow import')
        self.assertEqual(board.titled('[API][BUG] Slow import', 'API', 'BUG'), '[API][BUG] Slow import')
        self.assertEqual(board.titled('Plain', None, None), 'Plain')

    def test_anytype_shortcodes(self):
        ask = {'id': 'a', 'order': '1', 'text': board.ASK + ' result', 'reactions': {}}
        for text, verdict in [(':+1:', 'approved'), (':white_check_mark:', 'approved'),
                              (':-1:', 'rejected'), (':+1: but rename it', 'feedback')]:
            self.assertEqual(board.decide([ask, {'order': '2', 'text': text}])[0], verdict)


if __name__ == '__main__':
    unittest.main()
