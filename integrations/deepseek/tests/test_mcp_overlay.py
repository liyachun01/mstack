"""Inert YAML/source contract checks. Never read keys, evaluate JS or connect."""

from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[3]
OVERLAY = ROOT / 'infra/harnesses/deepseek/mcp-stack.cordis.yml'


class InertLoader(yaml.SafeLoader):
    pass


InertLoader.add_constructor('tag:yaml.org,2002:js',
                           lambda loader, node: {'__jsExpr': loader.construct_scalar(node)})


class NativeOverlayTests(unittest.TestCase):
    def setUp(self):
        self.text = OVERLAY.read_text()
        self.rows = yaml.load(self.text, Loader=InertLoader)[0]['insert']

    def test_only_existing_official_plugin_and_scoped_routes(self):
        self.assertEqual(len(self.rows), 2)
        self.assertEqual({r['name'] for r in self.rows}, {'@deepseek-ai/dsh-mcp-client'})
        self.assertEqual({r['config']['url'] for r in self.rows}, {
            'http://127.0.0.1:58081/mcp/graphify',
            'http://127.0.0.1:58081/mcp/codegraph'})
        self.assertEqual({r['config']['transport'] for r in self.rows}, {'streamable-http'})
        self.assertNotRegex(self.text, r'\b(?:command|args|env|cwd):')

    def test_unique_valid_names(self):
        self.assertEqual(len({r['id'] for r in self.rows}), 2)
        self.assertEqual(len({r['config']['serverName'] for r in self.rows}), 2)
        for row in self.rows:
            self.assertRegex(row['config']['serverName'], r'^[A-Za-z0-9_-]{1,32}$')

    def test_header_expression_is_shared_and_never_contains_a_key(self):
        expressions = [r['config']['headers']['Authorization'] for r in self.rows]
        self.assertEqual(expressions[0], expressions[1])
        source = expressions[0]['__jsExpr']
        for marker in ('MCP_STACK_GATEWAY_KEY_FILE', 'process.cwd()',
                       '.secrets/agentgateway-client-key', 'lstatSync', 'isFile()',
                       '0o077', 'readFileSync', "return 'Bearer ' + key"):
            self.assertIn(marker, source)
        self.assertIsNone(re.search(r'[a-f0-9]{64}', self.text))

    def test_native_loopback_authority_without_host_or_origin_override(self):
        for row in self.rows:
            headers = row['config']['headers']
            self.assertEqual(set(headers), {'Authorization'})
            self.assertTrue(row['config']['url'].startswith('http://127.0.0.1:58081/'))
            self.assertNotIn('Host', headers)
            self.assertNotIn('Origin', headers)

    def test_initial_qualification_has_no_automatic_reconnect(self):
        for row in self.rows:
            config = row['config']
            self.assertIs(config['failOnStartupError'], True)
            self.assertEqual(config['toolCallTimeoutMs'], 10000)
            self.assertEqual(config['reconnect'], {'enabled': False})

    def test_no_other_components_or_profile_changes(self):
        for value in ('basic-memory', 'supabase', 'n8n', 'process.env.DSH_HOME',
                      'execSync', 'spawn', 'writeFile', 'unlink'):
            self.assertNotIn(value, self.text)
        self.assertEqual(set(yaml.load(self.text, Loader=InertLoader)[0]), {'insert'})

    def test_optional_vision_gate_is_a_disable_only_patch(self):
        patch = yaml.safe_load((OVERLAY.parent / 'no-vision.cordis.yml').read_text())
        self.assertEqual(patch, [{'id': 'vision-toolkit', 'disabled': True}])


if __name__ == '__main__':
    unittest.main()
