import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('python_rebind', Path(__file__).parents[1] / 'python_rebind.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class RebindTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = self.home / '.local/share/uv/tools/headroom-ai'
        (self.env / 'bin').mkdir(parents=True)
        self.old = M.old_roots(self.home)[1]
        self.cfg = self.env / 'pyvenv.cfg'
        self.cfg.write_text('home = ' + str(self.old / 'bin') + '\nimplementation = CPython\n'
                            'version_info = 3.13.15\ninclude-system-site-packages = false\n')
        self.cfg.chmod(0o640)
        (self.env / 'bin/python').symlink_to(self.old / 'bin/python3.13')
        (self.env / 'bin/python3').symlink_to('python')
        self.metadata = self.env / 'lib/python3.13/site-packages/headroom_ai-0.34.0.dist-info/METADATA'
        self.metadata.parent.mkdir(parents=True)
        self.metadata.write_text('Name: headroom-ai\nVersion: 0.34.0\n')
        self.manifest = self.home / 'private/manifest.json'

    def perform(self, plan):
        with patch.object(M, 'live_consumers', return_value=([], 40)), patch.object(M, 'verified_target'):
            M.apply(plan, self.manifest)

    def test_round_trip_preserves_packages_relative_links_and_modes(self):
        plan = M.discover(self.home)
        original = self.cfg.read_text()
        metadata = self.metadata.read_bytes()
        self.perform(plan)
        M.check_state(plan, applied=True)
        self.assertEqual(os.readlink(self.env / 'bin/python'), plan['target'])
        self.assertEqual(os.readlink(self.env / 'bin/python3'), 'python')
        self.assertEqual(self.metadata.read_bytes(), metadata)
        self.assertEqual(self.cfg.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.manifest.stat().st_mode & 0o777, 0o600)
        M.rollback(json.loads(self.manifest.read_text()))
        self.assertEqual(self.cfg.read_text(), original)
        self.assertEqual(os.readlink(self.env / 'bin/python'), str(self.old / 'bin/python3.13'))

    def test_live_consumer_blocks_before_any_write(self):
        plan = M.discover(self.home)
        with patch.object(M, 'live_consumers', return_value=([{'pid': 42}], 40)):
            with self.assertRaisesRegex(ValueError, 'still running'):
                M.apply(plan, self.manifest)
        self.assertFalse(self.manifest.exists())

    def test_sandbox_visibility_blocks_apply(self):
        with patch.object(M, 'live_consumers', return_value=([], 2)):
            with self.assertRaisesRegex(ValueError, 'visibility'):
                M.apply(M.discover(self.home), self.manifest)

    def test_changed_package_blocks_apply_and_rollback(self):
        plan = M.discover(self.home)
        self.metadata.write_text('Name: headroom-ai\nVersion: altered\n')
        with self.assertRaisesRegex(ValueError, 'package identity changed'):
            self.perform(plan)
        with self.assertRaisesRegex(ValueError, 'Package identity drift'):
            M.rollback(plan)

    def test_other_interpreters_are_untouched(self):
        self.cfg.write_text('home = /usr/bin\nversion_info = 3.14.4\n')
        self.assertEqual(M.discover(self.home)['environments'], [])

    def test_wrong_version_fails_closed(self):
        self.cfg.write_text(self.cfg.read_text().replace('3.13.15\n', '3.13.14\n'))
        with self.assertRaisesRegex(ValueError, 'different Python version'):
            M.discover(self.home)

    def test_direct_legacy_shebang_fails_closed(self):
        script = self.env / 'bin/headroom'
        script.write_text('#!' + str(self.old / 'bin/python3.13') + '\nprint(1)\n')
        with self.assertRaisesRegex(ValueError, 'legacy shebang'):
            M.discover(self.home)

    def test_config_drift_blocks_rollback(self):
        plan = M.discover(self.home)
        self.perform(plan)
        self.cfg.write_text(self.cfg.read_text() + 'unexpected = value\n')
        with self.assertRaisesRegex(ValueError, 'drift'):
            M.rollback(plan)

    def test_interrupted_apply_restores_partially_changed_links(self):
        plan = M.discover(self.home)
        real_atomic = M.atomic_text
        def broken(path, value, mode):
            if path == self.cfg and 'mise' in value:
                raise OSError('injected write failure')
            return real_atomic(path, value, mode)
        with patch.object(M, 'atomic_text', side_effect=broken):
            with self.assertRaisesRegex(OSError, 'injected'):
                self.perform(plan)
        M.check_state(plan, applied=False)


if __name__ == '__main__':
    unittest.main()
