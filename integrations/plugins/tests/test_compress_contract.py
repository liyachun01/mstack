"""compress joint conformance kit, run against every compress plugin.

`CompressContract` is the reusable part: a replacement plugin passes by giving it
its own compress/expand. The Headroom adapter is checked through real MCP stdio
against a stand-in server; set MSTACK_LIVE_HEADROOM=<project path> to run the same
kit against that project's live Headroom tenant.
"""
import functools
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import registry

HERE = Path(__file__).resolve().parent
TEXT = '\n'.join('line %d: GET /api/cart 200 in %d ms user=%d' % (i, 10 + i % 7, i % 13) for i in range(400))


class CompressContract:
    """Mix into a TestCase that sets self.compress, self.expand and self.scope."""

    def test_round_trip_returns_the_exact_original(self):
        out = self.compress(self.scope, TEXT)
        self.assertEqual(self.expand(self.scope, out['handle']), TEXT)

    def test_result_shape(self):
        out = self.compress(self.scope, TEXT)
        self.assertIsInstance(out['summary'], str)
        self.assertIsInstance(out['handle'], str)
        self.assertGreater(out['original_tokens'], 0)
        self.assertLessEqual(out['compressed_tokens'], out['original_tokens'])

    def test_budget_is_reported(self):
        out = self.compress(self.scope, TEXT, budget_tokens=1)
        self.assertTrue(out['over_budget'])

    def test_rejects_empty_text_and_foreign_handles(self):
        with self.assertRaises(ValueError):
            self.compress(self.scope, '')
        with self.assertRaises((ValueError, RuntimeError)):
            self.expand(self.scope, '../../etc/passwd')
        with self.assertRaises(RuntimeError):
            self.expand(self.scope, 'f' * 24)        # well-formed but never issued to this tenant


class HeadroomAdapterContract(CompressContract, unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        adapter = registry.load(registry.discover()['headroom'])
        store = Path(temp.name)/'store.json'
        argv = [sys.executable, str(HERE/'fake_headroom_mcp.py'), str(store)]
        client = lambda _launcher: adapter.McpStdio(argv)
        self.compress = functools.partial(adapter.compress, client=client)
        self.expand = functools.partial(adapter.expand, client=client)
        self.scope = {'project': 'market', 'task': None, 'session': None, 'root': temp.name}
        self.adapter = adapter

    def test_launches_the_projects_own_tenant(self):
        argv = self.adapter.launcher(self.scope)
        self.assertEqual(argv[-4:], ['--project', self.scope['root'], '--tool', 'headroom'])
        with self.assertRaises(ValueError):
            self.adapter.compress({'project': 'market'}, 'x')


@unittest.skipUnless(os.environ.get('MSTACK_LIVE_HEADROOM'), 'live Headroom tenant not requested')
class LiveHeadroomContract(CompressContract, unittest.TestCase):
    def setUp(self):
        adapter = registry.load(registry.discover()['headroom'])
        self.compress, self.expand = adapter.compress, adapter.expand
        root = os.environ['MSTACK_LIVE_HEADROOM']
        self.scope = {'project': Path(root).name, 'task': None, 'session': None, 'root': root}


if __name__ == '__main__':
    unittest.main()
