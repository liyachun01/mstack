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
import project_state
import sync


class SyncTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)/'team'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        p = patch.object(sync, 'REGISTRY', Path(temp.name)/'projects.json'); p.start(); self.addCleanup(p.stop)
        p = patch.object(sync, 'BOARD_STATE', Path(temp.name)/'none.json'); p.start(); self.addCleanup(p.stop)
        with contextlib.redirect_stdout(io.StringIO()):
            cli.initialize(argparse.Namespace(path=self.repo, name='team', preset='solo', model=None, context=[], local=True))
            cli.install_skills(['--project', str(self.repo)])

    def sync(self, check=False):
        return sync.sync_project(self.repo, check)

    def test_new_project_is_registered_and_already_current(self):
        self.assertEqual(sync.projects(), [self.repo.resolve()])
        first = self.sync()
        self.assertEqual(first['changes'], [])
        self.assertEqual(project_state.read(self.repo)['runtime']['mstack_sync']['version'], sync.VERSION)

    def test_brings_an_old_project_up_to_date_and_is_idempotent(self):
        self.sync()
        (self.repo/'.claude/skills/mstack-models').unlink()                       # a skill shipped later
        (self.repo/'.agents/skills/mstack-gone').symlink_to(self.repo/'nowhere')    # a skill mstack dropped
        ignore = self.repo/'.mstack/.gitignore'
        ignore.write_text(ignore.read_text().replace('/journal.json\n', ''))       # an ignore rule added later
        check = self.sync(check=True)
        self.assertEqual(len(check['changes']), 3)
        self.assertFalse((self.repo/'.claude/skills/mstack-models').exists())      # --check writes nothing
        done = self.sync()
        self.assertEqual(sorted(done['changes']), sorted(check['changes']))
        self.assertTrue((self.repo/'.claude/skills/mstack-models/SKILL.md').is_file())
        self.assertFalse((self.repo/'.agents/skills/mstack-gone').is_symlink())
        self.assertIn('/journal.json', ignore.read_text())
        self.assertEqual(self.sync()['changes'], [])
        status = subprocess.run(['git', '-C', str(self.repo), 'status', '--porcelain', '--untracked-files=all'],
                                capture_output=True, text=True).stdout
        self.assertEqual(status, '')                                               # all of it stays out of git

    def test_generated_skill_follows_mstack_unless_edited_here(self):
        self.sync()
        skill = self.repo/'.agents/skills/mstack/SKILL.md'
        with patch.object(cli, 'skill_text', lambda: 'new template\n'):
            self.assertEqual(self.sync()['changes'], ['.agents/skills/mstack/SKILL.md: updated'])
            self.assertEqual(skill.read_text(), 'new template\n')
            skill.write_text('my own notes\n')
        with patch.object(cli, 'skill_text', lambda: 'newer template\n'):
            result = self.sync()
        self.assertEqual(skill.read_text(), 'my own notes\n')
        self.assertTrue(any('edited here' in n for n in result['notes']))

    def test_config_migrations_run_once_in_order(self):
        self.sync()
        def add_flag(config):
            config.setdefault('taskboard', {})['private'] = True
            return ['taskboard.private = true']
        with patch.object(sync, 'MIGRATIONS', sync.MIGRATIONS + [(2, 'private by default', add_flag)]), \
                patch.object(sync, 'VERSION', 2):
            changes = self.sync()['changes']
            self.assertEqual([c for c in changes if c.startswith('config:')], ['config: taskboard.private = true'])
            self.assertIn('.claude/settings.local.json: role-card hook added', changes)   # now it has a board
            self.assertTrue(json.loads((self.repo/'.mstack/stack.json').read_text())['taskboard']['private'])
            self.assertEqual(self.sync()['changes'], [])

    def test_doctor_reports_pending_updates(self):
        (self.repo/'.claude/skills/mstack-models').unlink()
        report = cli.doctor(self.repo, report=True)
        self.assertEqual(report['mstack_updates'], ['.claude/skills/mstack-models: linked'])


    def test_worker_worktrees_get_the_role_hook(self):
        config = json.loads((self.repo/'.mstack/stack.json').read_text())
        config['taskboard'] = {'table': 'team'}
        (self.repo/'.mstack/stack.json').write_text(json.dumps(config))
        tree = self.repo/'.claude/worktrees/iro-1'
        tree.mkdir(parents=True)
        sync.BOARD_STATE.write_text(json.dumps({'runs': {'t': {'tree': str(tree), 'issue': 'IRO-1'}}}))
        changes = self.sync()['changes']
        self.assertIn('.claude/worktrees/iro-1/.claude/settings.local.json: role-card hook added (worker IRO-1)', changes)
        self.assertIn('roles.py', (tree/'.claude/settings.local.json').read_text())
        self.assertEqual(self.sync()['changes'], [])

if __name__ == '__main__':
    unittest.main()
