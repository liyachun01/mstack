import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import hashlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from headroom_session import configure, valid_call


class HeadroomBoundaryTests(unittest.TestCase):
    def test_only_three_tools_and_exact_arguments(self):
        self.assertTrue(valid_call('headroom_compress', {'content': 'hello'}))
        self.assertTrue(valid_call('headroom_retrieve', {'hash': 'abc123'}))
        self.assertTrue(valid_call('headroom_stats', {}))
        for name, args in [('headroom_read', {'path': '/runtime/registry.json'}),
                           ('headroom_stats', {'tenant': 'project-b'}),
                           ('headroom_compress', {'content': 'hello', 'project_path': '/other'}),
                           ('headroom_compress', {'content': 42}),
                           ('headroom_compress', {'content': 'a' * (8 * 1024 * 1024 + 1)}),
                           ('headroom_retrieve', {'hash': '../other'})]:
            self.assertFalse(valid_call(name, args))

    def test_tenant_storage_paths_ignore_inherited_overrides(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, clear=False):
            root = Path(temp); folder = root/'tenants/project-a'; folder.mkdir(parents=True)
            (folder/'tenant.json').write_text(json.dumps({'version': 1, 'tenant': 'project-a'}))
            (root/'registry.json').write_text(json.dumps({'version': 1, 'tenants': {
                'project-a': {'enabled': True, 'token_sha256': hashlib.sha256(('a'*64).encode()).hexdigest()}}}))
            os.environ['HEADROOM_CCR_SQLITE_PATH'] = '/outside/ccr.db'
            os.environ['HEADROOM_SAVINGS_PATH'] = '/outside/stats.json'
            before = os.umask(0o077)
            try:
                tenant, actual = configure(root, {'tenant': 'project-a', 'token': 'a'*64})
                self.assertEqual(actual, folder)
                self.assertEqual(tenant, 'project-a')
                self.assertEqual(os.environ['HEADROOM_CCR_SQLITE_PATH'], str(folder/'workspace/ccr_store.db'))
                self.assertNotIn('HEADROOM_SAVINGS_PATH', os.environ)
                (folder/'workspace').rmdir(); (folder/'workspace').symlink_to(root)
                with self.assertRaises(ValueError): configure(root, {'tenant': 'project-a', 'token': 'a'*64})
            finally:
                os.umask(before)
