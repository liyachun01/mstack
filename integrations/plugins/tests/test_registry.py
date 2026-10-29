import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import registry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)

    def add(self, name, **manifest):
        folder = self.project/'.mstack/plugins'/name
        folder.mkdir(parents=True)
        (folder/'plugin.json').write_text(json.dumps({'name': name, 'version': '0.1.0', **manifest}))

    def test_builtins_cover_every_joint(self):
        joints = {m['joint'] for m in registry.discover().values()}
        self.assertEqual(joints, set(registry.SCHEMA['properties']['joint']['enum']))

    def test_project_plugin_drops_in_and_renders(self):
        self.add('my-agent', joint='agent', status='implemented', transport='argv',
                 command=['{python}', '{plugin_dir}/run.py', '--cwd={cwd}', '{brief}'])
        plugin = registry.joint('agent', self.project)['my-agent']
        argv = registry.render(plugin, brief='do it', cwd='/w')
        self.assertEqual(argv[1:], [plugin['dir'] + '/run.py', '--cwd=/w', 'do it'])
        self.assertTrue(registry.available(plugin))

    def test_cannot_shadow_builtin(self):
        self.add('codex', joint='agent', status='implemented', transport='argv', command=['x'])
        with self.assertRaises(ValueError):
            registry.discover(self.project)

    def test_invalid_manifests_rejected(self):
        self.add('bad', joint='agent', status='implemented', transport='argv')   # argv needs command
        with self.assertRaises(ValueError):
            registry.discover(self.project)

    def test_missing_project_key_makes_plugin_unavailable(self):
        gateway = registry.discover()['agentgateway']
        self.assertFalse(registry.available(gateway, self.project))
        key = self.project / '.mstack/secrets/agentgateway-key'
        key.parent.mkdir(parents=True)
        key.write_text('k')
        self.assertTrue(registry.available(gateway, self.project))

    def test_pending_or_missing_binaries_are_unavailable(self):
        self.assertFalse(registry.available(registry.discover()['headroom']))
        self.add('ghost', joint='agent', status='implemented', transport='argv', command=['ghost-cli'],
                 requires={'binaries': ['definitely-not-installed-xyz']})
        self.assertFalse(registry.available(registry.joint('agent', self.project)['ghost']))


if __name__ == '__main__':
    unittest.main()
