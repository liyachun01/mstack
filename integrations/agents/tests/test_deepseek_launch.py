"""Offline launcher migration checks. All files and credentials are synthetic."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'deepseek_launch.py'
SPEC = importlib.util.spec_from_file_location('deepseek_launch_under_test', SOURCE)
launch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launch)


class MiseLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mise = self.root / 'mise'
        self.mise.write_text('# synthetic mise executable\n')
        self.node_root = self.root / 'installs/node' / launch.NODE_VERSION
        self.node = self.node_root / 'bin/node'
        self.node.parent.mkdir(parents=True)
        self.node.write_text('# synthetic node executable\n')
        self.node.chmod(0o700)
        self.cli_prefix = self.root / 'installs/npm-deepseek-ai-dsh' / launch.HARNESS_VERSION
        self.cli_root = self.cli_prefix / 'lib/node_modules/@deepseek-ai/dsh'
        (self.cli_root / 'lib').mkdir(parents=True)
        self.metadata = self.cli_root / 'package.json'
        self.metadata.write_text(json.dumps({'name': '@deepseek-ai/dsh',
                                             'version': launch.HARNESS_VERSION}))
        (self.cli_root / 'lib/bin.js').write_text('// synthetic entrypoint\n')
        self.dsh_home = self.root / 'dsh-home'
        profile = self.dsh_home / 'profiles/web/package.json'
        profile.parent.mkdir(parents=True)
        profile.write_text('{}')
        patches = self.root / 'infra/harnesses/deepseek'
        patches.mkdir(parents=True)
        for name in ('mcp-stack.cordis.yml', 'no-vision.cordis.yml', 'harnessbot.cordis.yml'):
            (patches / name).write_text('# synthetic patch\n')
        for name, value in (('ROOT', self.root), ('MISE', self.mise), ('DSH_HOME', self.dsh_home)):
            context = patch.object(launch, name, value)
            context.start()
            self.addCleanup(context.stop)
        credential_patch = patch.object(launch, 'credential', return_value='sk-synthetic-offline')
        self.credential = credential_patch.start()
        self.addCleanup(credential_patch.stop)
        run_patch = patch.object(launch.subprocess, 'run', side_effect=self.resolve)
        self.run = run_patch.start()
        self.addCleanup(run_patch.stop)

    def resolve(self, command, **kwargs):
        roots = {f'node@{launch.NODE_VERSION}': self.node_root,
                 f'npm:@deepseek-ai/dsh@{launch.HARNESS_VERSION}': self.cli_prefix}
        return subprocess.CompletedProcess(command, 0, str(roots[command[-1]]) + '\n', '')

    def test_exact_pins_resolve_without_install_and_preserve_launch_contract(self):
        command, env = launch.command_and_env()
        self.assertEqual(command[:4], [str(self.node), str(self.cli_root / 'lib/bin.js'),
                                      '--profile', 'web'])
        self.assertEqual(command[-5:], ['--no-open', '--host', '127.0.0.1', '--port', '3080'])
        self.assertEqual(command.count('--patch'), 3)
        self.assertEqual(env['PATH'], str(self.node_root / 'bin') + ':/usr/bin:/bin')
        self.assertEqual(env['DSH_HOME'], str(self.dsh_home))
        self.assertEqual(env['DSH_TELEMETRY_DISABLED'], '1')
        self.assertEqual(env[launch.KEY_VAR], 'sk-synthetic-offline')
        self.assertNotIn('sk-synthetic-offline', ' '.join(command))
        self.assertNotIn('fnm', ' '.join(command) + env['PATH'])
        for call in self.run.call_args_list:
            args, kwargs = call
            self.assertEqual(args[0][1:4], ['-C', str(self.root / 'infra/harnesses/deepseek'),
                                           'where'])
            self.assertEqual(kwargs['env']['MISE_INSTALL_MISSING_TOOLS'], '0')
            self.assertEqual(kwargs['env']['MISE_NOT_FOUND_AUTO_INSTALL'], '0')
            self.assertEqual(kwargs['env']['MISE_GLOBAL_CONFIG_FILE'],
                             str(self.root / 'infra/harnesses/deepseek/mise.toml'))
            self.assertNotIn(launch.KEY_VAR, kwargs['env'])

    def test_missing_installation_fails_before_reading_credentials(self):
        self.run.side_effect = subprocess.CalledProcessError(1, ['mise', 'where'])
        with self.assertRaisesRegex(ValueError, 'install separately'):
            launch.command_and_env()
        self.credential.assert_not_called()

    def test_changed_package_version_fails_before_reading_credentials(self):
        self.metadata.write_text(json.dumps({'name': '@deepseek-ai/dsh', 'version': '99.0.0'}))
        with self.assertRaisesRegex(ValueError, 'version changed'):
            launch.command_and_env()
        self.credential.assert_not_called()

    def test_aube_package_layout_preserves_launch_contract(self):
        target = self.cli_prefix / 'node_modules/@deepseek-ai/dsh'
        target.parent.mkdir(parents=True)
        self.cli_root.rename(target)
        command, _ = launch.command_and_env()
        self.assertEqual(command[1], str(target / 'lib/bin.js'))

    def test_ambiguous_package_layout_fails_before_credentials(self):
        duplicate = self.cli_prefix / 'node_modules/@deepseek-ai/dsh'
        duplicate.mkdir(parents=True)
        (duplicate / 'package.json').write_text(self.metadata.read_text())
        with self.assertRaisesRegex(ValueError, 'one installed harness'):
            launch.command_and_env()
        self.credential.assert_not_called()

    def test_unpinned_or_relative_resolution_is_rejected(self):
        for path in (str(self.node_root.parent), 'relative/24.19.0'):
            with self.subTest(path=path):
                self.run.return_value = subprocess.CompletedProcess([], 0, path + '\n', '')
                self.run.side_effect = None
                with self.assertRaisesRegex(ValueError, 'exact-version'):
                    launch.command_and_env()
        self.credential.assert_not_called()

    def test_missing_profile_is_not_reinitialized(self):
        (self.dsh_home / 'profiles/web/package.json').unlink()
        with self.assertRaisesRegex(ValueError, 'refusing automatic profile'):
            launch.command_and_env()
        self.credential.assert_not_called()
        self.assertFalse((self.dsh_home / 'profiles/web/package.json').exists())


if __name__ == '__main__':
    unittest.main()
