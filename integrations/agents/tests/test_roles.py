import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import roles


class RoleCardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)/'repo'
        (self.project/'.mstack').mkdir(parents=True)
        (self.project/'.mstack/stack.json').write_text(json.dumps({'project': 'repo', 'taskboard': {
            'table': 'repo', 'backend': 'linear', 'private': True,
            'link': {'workspace': '{{mstack:CLIENT_ORG_B}}', 'team': 'CAN'},
            'apps': {'API': {'link': {'workspace': '{{mstack:CLIENT_ORG_A_SHORT}}', 'team': 'IRO'}}},
            'orchestrators': {'customer-api': {'apps': ['API']}, 'staff-web': {'apps': ['*']}}}}))
        board = Path(temp.name)/'board.json'
        board.write_text(json.dumps({'tables': {'repo': {'path': str(self.project)}},
                                     'runs': {'t1': {'table': 'repo', 'scope': 'customer-api', 'session': 'local_w',
                                                     'issue': 'IRO-9', 'tree': '/w/iro-9'},
                                              't2': {'table': 'repo', 'scope': 'customer-api', 'session': 'local_sub',
                                                     'issue': 'IRO-10', 'parent': 'IRO-9'}},
                                     'related': {'t1': [{'session': 'local_old', 'note': 'obsolete'}]}}))
        p = patch.object(roles, 'BOARD_STATE', board); p.start(); self.addCleanup(p.stop)
        for session, role, scope in (('local_top', 'orchestrator', None), ('local_api', 'sub-orchestrator', 'customer-api')):
            argv = ['set', '--project', str(self.project), '--session', session, '--role', role]
            with patch('sys.stdout', io.StringIO()):
                roles.main(argv + (['--scope', scope] if scope else []))

    def test_orchestrator_assigns_to_sub_orchestrators_and_never_works(self):
        text = roles.card(self.project, 'local_top')
        self.assertIn('repo **orchestrator** (top level)', text)
        self.assertIn('You never work on an issue yourself', text)
        self.assertIn('**customer-api**: apps API ({{mstack:CLIENT_ORG_A_SHORT}}/IRO), session `local_api`', text)
        self.assertIn('**staff-web**: apps * ({{mstack:CLIENT_ORG_B}}/CAN), no session registered', text)

    def test_sub_orchestrator_card_knows_scope_private_mode_workers_and_its_orchestrator(self):
        text = roles.card(self.project, 'local_api')
        self.assertIn('**customer-api** sub-orchestrator', text)
        self.assertIn('You never work on an issue yourself', text)
        self.assertIn('Your orchestrator is `local_top`', text)
        self.assertIn('board owner --project repo --scope customer-api', text)
        self.assertIn('`local_w`', text)

    def test_worker_history_and_strangers(self):
        self.assertIn('**worker** for IRO-9', roles.card(self.project, 'local_w'))
        self.assertIn('history', roles.card(self.project, 'local_old'))
        self.assertIsNone(roles.card(self.project, 'local_someone_else'))

    def test_hook_adds_the_card_for_this_session_only(self):
        event = json.dumps({'hook_event_name': 'UserPromptSubmit', 'cwd': str(self.project/'apps/x')})
        out = io.StringIO()
        with patch.dict(os.environ, {'CLAUDE_CODE_HOST_SESSION_ID': 'local_api'}), \
                patch('sys.stdin', io.StringIO(event)), patch('sys.stdout', out):
            roles.hook()
        context = json.loads(out.getvalue())['hookSpecificOutput']['additionalContext']
        self.assertIn('customer-api', context)
        out = io.StringIO()
        with patch.dict(os.environ, {'CLAUDE_CODE_HOST_SESSION_ID': 'local_nobody'}), \
                patch('sys.stdin', io.StringIO(event)), patch('sys.stdout', out):
            roles.hook()
        self.assertEqual(out.getvalue(), '')

    def test_install_keeps_existing_settings_and_is_idempotent(self):
        settings = self.project/'.claude/settings.local.json'
        settings.parent.mkdir()
        settings.write_text(json.dumps({'permissions': {'allow': ['Bash(ls)']}}))
        self.assertEqual(roles.install(self.project), ['UserPromptSubmit', 'SessionStart'])
        self.assertEqual(roles.install(self.project), [])
        data = json.loads(settings.read_text())
        self.assertEqual(data['permissions'], {'allow': ['Bash(ls)']})
        self.assertEqual(len(data['hooks']['UserPromptSubmit']), 1)


    def test_worker_may_start_helpers_and_helpers_report_only_to_it(self):
        worker = roles.card(self.project, 'local_w')
        self.assertIn('You may start **helper** side sessions', worker)
        self.assertIn('--project %s --session <helper id> --role helper --task IRO-9 --worker local_w' % self.project, worker)
        argv = ['set', '--project', str(self.project), '--session', 'local_h', '--role', 'helper']
        with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
            self.assertEqual(roles.main(argv + ['--task', 'IRO-9', '--worker', 'local_api']), 1)   # not a worker
            self.assertEqual(roles.main(argv + ['--task', 'IRO-9', '--worker', 'local_w']), 0)
            self.assertEqual(roles.main(['set', '--project', str(self.project), '--session', 'local_h2', '--role',
                                         'helper', '--task', 'IRO-9', '--worker', 'local_w']), 0)
        helper = roles.card(self.project, 'local_h')
        self.assertIn('**helper** for IRO-9', helper)
        self.assertIn('Your worker is `local_w`', helper)
        self.assertIn('Never write to the issue or board', helper)
        self.assertIn('Your helpers: `local_h`, `local_h2`', roles.card(self.project, 'local_w'))

    def test_sub_issue_worker_is_linked_both_ways(self):
        self.assertIn('Your sub-issue workers (nested under you, they own their records): IRO-10 `local_sub`',
                      roles.card(self.project, 'local_w'))
        self.assertIn('This is a sub-issue of IRO-9 (worker `local_w`)', roles.card(self.project, 'local_sub'))

    def test_tree_shows_the_hierarchy(self):                                                    # MST-34
        text = roles.tree(self.project)
        self.assertIn('repo orchestrator `local_top`', text)
        self.assertIn('  - customer-api sub-orchestrator `local_api`', text)
        self.assertIn('    - IRO-9 worker `local_w`', text)
        self.assertIn('      - IRO-10 worker `local_sub`', text)

    def test_orchestrator_with_scopes_never_dispatches(self):                                   # MST-33
        self.assertIn('You never start worker sessions or run `dispatch`', roles.card(self.project, 'local_top'))

if __name__ == '__main__':
    unittest.main()
