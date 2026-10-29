"""memory.long joint conformance kit, run against every memory.long plugin.

Set MSTACK_LIVE_GRAPHIFY=<project path> to run it against that project's live Graphify tenant.
"""
import functools
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import registry

HERE = Path(__file__).resolve().parent


class MemoryLongContract:
    """Mix into a TestCase that sets self.query, self.module and self.scope."""
    QUESTION = 'cart subtotal'

    def test_results_cite_sources(self):
        hits = self.query(self.scope, self.QUESTION)
        self.assertTrue(hits)
        for hit in hits:
            self.assertIsInstance(hit['text'], str)
            self.assertRegex(hit['source'], r'^[\w./-]+:L\d+')
            self.assertGreater(hit['score'], 0)

    def test_k_limits_results_and_scores_descend(self):
        hits = self.query(self.scope, self.QUESTION, k=2)
        self.assertLessEqual(len(hits), 2)
        self.assertEqual([h['score'] for h in hits], sorted((h['score'] for h in hits), reverse=True))

    def test_sources_stay_inside_the_project(self):
        for hit in self.query(self.scope, self.QUESTION):
            self.assertFalse(hit['source'].startswith(('/', '..')))

    def test_empty_query_rejected_and_indexing_is_explicit(self):
        with self.assertRaises(ValueError):
            self.query(self.scope, ' ')
        with self.assertRaises(NotImplementedError):
            self.module.index(self.scope, ['market/'])


class GraphifyAdapterContract(MemoryLongContract, unittest.TestCase):
    def setUp(self):
        self.module = registry.load(registry.discover()['graphify'])
        argv = [sys.executable, str(HERE/'fake_graphify_mcp.py')]
        self.query = functools.partial(self.module.query, client=lambda _l: self.module.McpStdio(argv))
        self.scope = {'project': 'market', 'task': None, 'session': None, 'root': '/tmp/market'}

    def test_launches_the_projects_own_tenant(self):
        self.assertEqual(self.module.launcher(self.scope)[-4:], ['--project', '/tmp/market', '--tool', 'graphify'])


@unittest.skipUnless(os.environ.get('MSTACK_LIVE_GRAPHIFY'), 'live Graphify tenant not requested')
class LiveGraphifyContract(MemoryLongContract, unittest.TestCase):
    def setUp(self):
        self.module = registry.load(registry.discover()['graphify'])
        self.query = self.module.query
        root = os.environ['MSTACK_LIVE_GRAPHIFY']
        self.scope = {'project': Path(root).name, 'task': None, 'session': None, 'root': root}


if __name__ == '__main__':
    unittest.main()
