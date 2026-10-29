import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cli
import visibility


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout


class LocalVisibilityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)/'team'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        (self.repo/'AGENTS.md').write_text('# team rules\n')
        (self.repo/'.gitignore').write_text('node_modules/\n')

    def init(self, project=None, local=True, preset='solo'):
        args = argparse.Namespace(path=project or self.repo, name='team', preset=preset,
                                  model=None, context=[], local=local)
        with contextlib.redirect_stdout(io.StringIO()):
            return cli.initialize(args)

    def untracked(self):
        return git(self.repo, 'status', '--porcelain', '--untracked-files=all').splitlines()

    def test_local_init_leaves_team_files_and_status_clean(self):
        self.init()
        self.assertEqual((self.repo/'AGENTS.md').read_text(), '# team rules\n')
        self.assertEqual((self.repo/'.gitignore').read_text(), 'node_modules/\n')
        self.assertIn('.agents/skills/mstack/SKILL.md', (self.repo/'CLAUDE.local.md').read_text())
        self.assertEqual(self.untracked(), ['?? .gitignore', '?? AGENTS.md'])
        self.assertEqual(cli.resolve(self.repo)['visibility'], 'local')
        self.assertEqual(visibility.status(self.repo), {'git': True, 'tracked': [], 'unignored': []})

    def test_subdirectory_project_gets_prefixed_rules(self):
        sub = self.repo/'services/api'
        sub.mkdir(parents=True)
        self.init(sub)
        exclude = (self.repo/'.git/info/exclude').read_text()
        self.assertIn('/services/api/.mstack/', exclude)
        self.assertEqual(self.untracked(), ['?? .gitignore', '?? AGENTS.md'])

    def test_toggle_back_to_shared_removes_only_managed_block(self):
        exclude = self.repo/'.git/info/exclude'
        exclude.write_text('*.swp\n')
        self.init()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.set_visibility(self.repo, 'shared'), 0)
        self.assertEqual(exclude.read_text(), '*.swp\n')
        self.assertNotIn('visibility', json.loads((self.repo/'.mstack/stack.json').read_text()))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.set_visibility(self.repo, 'local'), 0)
            self.assertEqual(cli.set_visibility(self.repo, 'local'), 0)
        self.assertEqual(exclude.read_text().count(visibility.BEGIN), 1)

    def test_already_committed_files_block_doctor_and_are_never_untracked(self):
        self.init(local=False)
        git(self.repo, 'add', '.mstack/stack.json')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.set_visibility(self.repo, 'local'), 2)
        self.assertIn('.mstack/stack.json', git(self.repo, 'ls-files'))
        blockers = cli.doctor(self.repo, report=True)['blockers']
        self.assertTrue(any('git rm --cached' in b for b in blockers))

    def test_protected_repo_needs_explicit_owner_opt_in(self):
        repo = self.repo.parent / '{{mstack:CLIENT_REPO}}'
        repo.mkdir()
        git(repo, 'init', '-q')
        args = argparse.Namespace(path=repo, name='{{mstack:CLIENT_REPO}}', preset='solo', model=None, context=[], local=True)
        with self.assertRaises(ValueError):
            cli.initialize(args)
        args.allow_protected = True
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.initialize(args), 0)
        self.assertEqual(cli.resolve(repo)['visibility'], 'local')

    def test_team_tracked_mcp_json_is_left_to_the_team(self):
        (self.repo/'.mcp.json').write_text('{"mcpServers": {}}')
        git(self.repo, 'add', '.mcp.json')
        self.init()
        self.assertNotIn('/.mcp.json', (self.repo/'.git/info/exclude').read_text())
        self.assertEqual(visibility.status(self.repo), {'git': True, 'tracked': [], 'unignored': []})

    def test_skills_are_linked_and_stay_out_of_git(self):
        self.init()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.install_skills(['--project', str(self.repo)]), 0)
        self.assertTrue((self.repo / '.claude/skills/mstack-orchestrator/SKILL.md').is_file())
        self.assertTrue((self.repo / '.agents/skills/mstack-worker').is_symlink())
        self.assertEqual(self.untracked(), ['?? .gitignore', '?? AGENTS.md'])

    def test_shared_init_keeps_existing_behaviour(self):
        self.init(local=False)
        self.assertIn('.agents/skills/mstack/SKILL.md', (self.repo/'AGENTS.md').read_text())
        self.assertFalse((self.repo/'CLAUDE.local.md').exists())
        self.assertNotIn(visibility.BEGIN, (self.repo/'.git/info/exclude').read_text())


class ProjectProvidedToolTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)/'team'
        (self.project/'.mstack').mkdir(parents=True)

    def configure(self, tools, preset='daily'):
        (self.project/'.mstack/stack.json').write_text(json.dumps(
            {'project': 'team', 'preset': preset, 'tools': tools}))

    def test_project_tools_need_no_mstack_binding(self):
        self.configure({'graphify': {'source': 'project'},
                        'headroom': {'source': 'project', 'server': 'team-headroom'}})
        resolved = cli.resolve(self.project)
        self.assertEqual(resolved['project_tools'], {'graphify': 'graphify', 'headroom': 'team-headroom'})
        blockers = cli.doctor(self.project, report=True)['blockers']
        self.assertFalse([b for b in blockers if b.startswith(('graphify', 'headroom'))])
        self.assertTrue([b for b in blockers if b.startswith('anytype')])

    def test_project_tool_rejects_mstack_connection_fields(self):
        self.configure({'graphify': {'source': 'project', 'url': 'http://127.0.0.1:1/mcp'}})
        with self.assertRaises(ValueError):
            cli.resolve(self.project)
        self.configure({'graphify': {'server': 'graphify'}})
        with self.assertRaises(ValueError):
            cli.resolve(self.project)

    def test_launch_keeps_project_servers_and_disables_strays(self):
        self.configure({'graphify': {'source': 'project', 'server': 'team-graph'}}, preset='solo')
        existing = [{'name': 'team-graph', 'enabled': False}, {'name': 'stray', 'enabled': True}]
        with patch.object(cli, 'doctor', return_value={'ready': True}), \
                patch.object(cli.subprocess, 'check_output', return_value=json.dumps(existing)), \
                patch.object(cli.subprocess, 'call', return_value=0) as call:
            self.assertEqual(cli.launch(self.project), 0)
        argv = call.call_args[0][0]
        self.assertIn('mcp_servers.team-graph.enabled=true', argv)
        self.assertIn('mcp_servers.stray.enabled=false', argv)
        self.assertFalse(any(a.startswith('mcp_servers.project_graphify') for a in argv))

    def test_launch_refuses_when_project_server_is_missing(self):
        self.configure({'graphify': {'source': 'project'}}, preset='solo')
        with patch.object(cli, 'doctor', return_value={'ready': True}), \
                patch.object(cli.subprocess, 'check_output', return_value='[]'), \
                patch.object(cli.subprocess, 'call') as call:
            with self.assertRaises(ValueError):
                cli.launch(self.project)
        call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
