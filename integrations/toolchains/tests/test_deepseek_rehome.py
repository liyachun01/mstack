import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / 'deepseek_rehome.py'
SPEC = importlib.util.spec_from_file_location('deepseek_rehome', MODULE_PATH)
rehome = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rehome)


class RehomeTests(unittest.TestCase):
    def test_copy_preserves_working_and_preexisting_broken_links_and_real_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'legacy/dsh'
            source.mkdir(parents=True)
            (source / 'package.json').write_text(json.dumps(
                {'name': '@deepseek-ai/dsh', 'version': '0.2.0-rc.2'}))
            (source / 'module.js').write_bytes(b'exact retained module\n')
            (source / 'internal').symlink_to('module.js')
            profile = root / 'profile'
            profile.mkdir()
            secret = profile / 'existing-config.json'
            secret.write_bytes(b'private original config')
            secret.chmod(0o600)
            (profile / 'working').symlink_to(source / 'module.js')
            (profile / 'already-broken').symlink_to(source / 'missing.js')
            destination = root / 'runtime/dsh'
            private = root / '.secrets'
            with patch.multiple(rehome, SOURCE=source, PROFILE=profile,
                                DESTINATION=destination, PRIVATE_ROOT=private,
                                EXPECTED_PROFILE_LINKS=2):
                state = rehome.apply()
                self.assertEqual(state['phase'], 'complete')
                self.assertEqual(rehome.tree_manifest(source), rehome.tree_manifest(destination))
                self.assertEqual((profile / 'working').read_bytes(), b'exact retained module\n')
                self.assertFalse((profile / 'already-broken').exists())
                self.assertEqual(secret.read_bytes(), b'private original config')
                self.assertEqual(secret.stat().st_mode & 0o777, 0o600)
                restored = rehome.rollback(state['state_directory'])
                self.assertEqual(restored['phase'], 'rolled-back-copy-retained')
                self.assertEqual((profile / 'working').readlink(), source / 'module.js')
                self.assertTrue(destination.exists())

    def test_manifest_rejects_external_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'escape').symlink_to('/usr/bin/python3')
            with self.assertRaisesRegex(ValueError, 'escaping symlink'):
                rehome.tree_manifest(root)

    def test_atomic_link_refuses_unrelated_edit(self):
        with tempfile.TemporaryDirectory() as temporary:
            link = Path(temporary) / 'package'
            link.symlink_to('/original')
            with self.assertRaisesRegex(ValueError, 'changed since inspection'):
                rehome.atomic_link(link, '/previous-inventory', '/replacement')
            self.assertEqual(str(link.readlink()), '/original')

    def test_link_inventory_rejects_another_fnm_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / 'other').symlink_to('/home/example/.local/share/fnm/other-package')
            with self.assertRaisesRegex(ValueError, 'additional fnm link'):
                rehome.profile_links(profile, Path('/legacy/dsh'), Path('/destination'))


if __name__ == '__main__':
    unittest.main()
