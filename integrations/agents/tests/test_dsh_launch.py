"""dsh worker launcher (MST-62). Synthetic key, DSH_HOME and a fake dsh; no node, no model call."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'dsh_launch.py'
SPEC = importlib.util.spec_from_file_location('dsh_launch_under_test', SOURCE)
launch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launch)

KEY = 'sk-synthetic0000000000000000'


class DshLaunchTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'infra/harnesses/deepseek/state/worker-home').mkdir(parents=True)
        (self.root / '.secrets').mkdir()
        self.key = self.root / '.secrets/deepseek-worker.key'
        self.key.write_text(KEY + '\n')
        self.key.chmod(0o600)
        self.fake = self.root / 'bin/dsh'
        self.fake.parent.mkdir()
        env = {'MSTACK_DSH_FAKE': str(self.fake), 'MSTACK_DSH_STATE_ROOT': str(self.root),
               'MSTACK_TASK': 'T-1', 'LINEAR_API_KEY': 'lin_api_secret'}
        patcher = patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_clean_environment_overlay_first_and_args_unchanged(self):
        argv, env = launch.build('headless', ['--patch', '/run.yml', '--json', 'do it'])
        self.assertEqual(argv, [str(self.fake), '--profile', 'headless', '--patch', str(launch.OVERLAY),
                                '--patch', '/run.yml', '--json', 'do it'])
        self.assertEqual(env['DSH_HOME'], str(self.root / 'infra/harnesses/deepseek/state/worker-home'))
        self.assertEqual((env['DSH_TELEMETRY_DISABLED'], env['DSH_TELEMETRY_MODE']), ('1', 'DISABLED'))
        self.assertEqual((env['DEEPSEEK_API_KEY'], env['MSTACK_TASK']), (KEY, 'T-1'))
        self.assertNotIn('LINEAR_API_KEY', env)
        self.assertTrue(env['PATH'].startswith(str(self.fake.parent) + ':'))

    def test_long_lived_profiles_use_the_same_settings(self):
        argv, env = launch.build('acp', [])
        self.assertEqual(argv[1:3], ['--profile', 'acp'])
        self.assertIn('DEEPSEEK_API_KEY', env)
        with self.assertRaises(ValueError):
            launch.build('web', [])

    def test_dry_run_prints_the_command_without_the_key(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(launch.main(['--dry-run', '--profile', 'headless', '--json', 'go']), 0)
        shown = json.loads(out.getvalue())
        self.assertEqual(shown['argv'][-2:], ['--json', 'go'])
        self.assertEqual(shown['env']['DEEPSEEK_API_KEY'], '<redacted>')
        self.assertNotIn(KEY, out.getvalue())

    def test_refuses_a_loose_or_missing_key_and_a_missing_home(self):
        self.key.chmod(0o644)
        with self.assertRaisesRegex(ValueError, '0600'):
            launch.build('headless', [])
        self.key.unlink()
        with self.assertRaisesRegex(ValueError, 'key absent'):
            launch.build('headless', [])
        self.key.write_text(KEY)
        self.key.chmod(0o600)
        (self.root / 'infra/harnesses/deepseek/state/worker-home').rmdir()
        with self.assertRaisesRegex(ValueError, 'DSH_HOME absent'):
            launch.build('headless', [])

    def test_state_root_is_the_main_checkout(self):
        with patch.dict(os.environ, {'MSTACK_DSH_STATE_ROOT': ''}):
            root = launch.state_root()
        self.assertTrue((root / '.git').is_dir())                 # never a worktree's `.git` file


if __name__ == '__main__':
    unittest.main()
