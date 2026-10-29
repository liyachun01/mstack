import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'entrypoint.py'
SPEC = importlib.util.spec_from_file_location('toolchain_entrypoint', SOURCE)
entrypoint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entrypoint)


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cwd = self.root / 'caller project'
        self.cwd.mkdir()
        self.binary = self.root / 'installed-tool'
        self.binary.write_text('# synthetic executable\n')
        self.records = {}
        self.calls = []
        run_patch = patch.object(entrypoint.subprocess, 'run', side_effect=self.resolve)
        self.run = run_patch.start()
        self.addCleanup(run_patch.stop)

    def resolve(self, command, **kwargs):
        self.calls.append((command, kwargs))
        value = json.dumps(self.records) if 'ls' in command else str(self.binary)
        return subprocess.CompletedProcess(command, 0, value, '')

    def plan(self, alias, arguments=()):
        return entrypoint.command_plan(alias, list(arguments), self.cwd,
                                       {'PATH': '/old/fnm/bin:/usr/bin',
                                        'MISE_INSTALL_MISSING_TOOLS': '1',
                                        'MISE_CONFIG_FILE': '/old/global.toml',
                                        'PRIVATE_VALUE': 'synthetic-private'})

    def test_common_alias_uses_baseline_and_never_installs(self):
        command, env = self.plan('fdfind', ['two words', '$HOME; echo ignored'])
        self.assertEqual(command[1:5], ['-C', str(entrypoint.BASELINE), 'exec', '--no-deps'])
        self.assertEqual(command[-2:], ['two words', '$HOME; echo ignored'])
        self.assertIn(str(self.cwd), command)
        self.assertEqual(self.calls[0][0][-2:], ['which', 'fd'])
        self.assertEqual(env['MISE_INSTALL_MISSING_TOOLS'], '0')
        self.assertEqual(env['MISE_NOT_FOUND_AUTO_INSTALL'], '0')
        self.assertEqual(env['MISE_GLOBAL_CONFIG_FILE'], str(entrypoint.BASELINE / 'mise.toml'))
        self.assertNotIn('MISE_CONFIG_FILE', env)
        self.assertEqual(env['PRIVATE_VALUE'], 'synthetic-private')
        for _, kwargs in self.calls:
            self.assertNotIn('shell', kwargs)
            self.assertEqual(kwargs['env']['MISE_INSTALL_MISSING_TOOLS'], '0')

    def test_project_node_overrides_cli_default_without_changing_cwd(self):
        self.records = {'node': [{'version': '24.21.0', 'installed': True}]}
        command, _ = self.plan('node', ['-e', 'console.log("literal $HOME;")'])
        self.assertIn('node@24.21.0', command)
        self.assertEqual(self.calls[0][0][1:3], ['-C', str(self.cwd)])
        self.assertEqual(self.calls[1][0][-4:], ['which', 'node', '--tool', 'node@24.21.0'])
        self.assertEqual(command[-2:], ['-e', 'console.log("literal $HOME;")'])
        self.assertIn(str(entrypoint.NODE_CLI), command)

    def test_empty_project_uses_node_cli_fallback(self):
        command, _ = self.plan('npm', ['--version'])
        self.assertIn(str(entrypoint.NODE_CLI), command)
        self.assertFalse(any(arg.startswith('node@') for arg in command))
        self.assertEqual(self.calls[1][0][-2:], ['which', 'npm'])

    def test_explicit_project_pnpm_is_honored(self):
        for tool in ('pnpm', 'npm:pnpm'):
            with self.subTest(tool=tool):
                self.records = {'node': [{'version': '24.21.0', 'installed': True}],
                                tool: [{'version': '10.30.3', 'installed': True}]}
                command, _ = self.plan('pnpm')
                self.assertIn('node@24.21.0', command)
                self.assertIn(tool + '@10.30.3', command)
                self.assertEqual(self.calls[-1][0][-2:], ['--tool', tool + '@10.30.3'])

    def test_declared_missing_project_versions_fail_without_fallback(self):
        for alias, records in (
            ('node', {'node': [{'version': '99.0.0', 'installed': False}]}),
            ('pnpm', {'pnpm': [{'version': '99.0.0', 'installed': False}]}),
        ):
            with self.subTest(alias=alias):
                self.records = records
                self.calls.clear()
                with self.assertRaisesRegex(ValueError, 'missing; no fallback'):
                    self.plan(alias)
                self.assertEqual(len(self.calls), 1)

    def test_dsh_and_vendor_commands_keep_their_own_scopes(self):
        for alias, scope in (('dsh', entrypoint.DEEPSEEK), ('ve', entrypoint.NODE_CLI),
                             ('vefaas', entrypoint.NODE_CLI), ('ve-tos-cli', entrypoint.NODE_CLI)):
            with self.subTest(alias=alias):
                self.calls.clear()
                command, _ = self.plan(alias, ['--version'])
                self.assertEqual(command[2], str(scope))
                self.assertEqual(len(self.calls), 1)

    def test_uv_defaults_to_mise_python_scope_and_preserves_arguments(self):
        for alias in ('uv', 'uvx'):
            with self.subTest(alias=alias):
                self.calls.clear()
                command, env = self.plan(alias, ['--version'])
                self.assertEqual(command[2], str(entrypoint.PYTHON_SCOPE))
                self.assertEqual(command[-1], '--version')
                self.assertEqual(env['UV_PYTHON'], str(self.binary))
                self.assertIn(str(self.cwd), command)
                self.assertEqual(self.calls[-1][0][-2:], ['which', 'python'])

    def test_uv_honors_installed_project_python(self):
        self.records = {'python': [{'version': '3.12.12', 'installed': True}]}
        command, env = self.plan('uv')
        self.assertIn('python@3.12.12', command)
        self.assertEqual(env['UV_PYTHON'], str(self.binary))
        self.assertEqual(self.calls[-1][0][-4:],
                         ['which', 'python', '--tool', 'python@3.12.12'])

    def test_uv_missing_declared_python_fails_without_fallback(self):
        self.records = {'python': [{'version': '99.0.0', 'installed': False}]}
        with self.assertRaisesRegex(ValueError, 'Python is missing; no fallback'):
            self.plan('uv')
        self.assertEqual(len(self.calls), 1)

    def test_uv_keeps_explicit_user_python_override(self):
        for override in ('/caller/python', ''):
            with self.subTest(override=override):
                self.calls.clear()
                _, env = entrypoint.command_plan('uvx', [], self.cwd, {'UV_PYTHON': override})
                self.assertEqual(env['UV_PYTHON'], override)
                self.assertEqual(len(self.calls), 2)
                self.assertEqual(self.calls[-1][0][-2:], ['which', 'uvx'])

    def test_unknown_alias_and_recursive_executable_fail(self):
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            self.plan('unknown-command')
        self.assertFalse(self.calls)
        with patch.object(entrypoint, 'SCRIPT', self.binary):
            with self.assertRaisesRegex(ValueError, 'no system/PATH fallback'):
                self.plan('gh')

    def test_resolution_errors_do_not_print_private_diagnostics(self):
        self.run.side_effect = subprocess.CalledProcessError(
            1, ['mise'], stderr='PRIVATE_CREDENTIAL_IN_TEMPLATE')
        with self.assertRaises(ValueError) as raised:
            self.plan('node')
        self.assertNotIn('PRIVATE_CREDENTIAL', str(raised.exception))

    def test_internal_child_restores_cwd_and_passes_literal_arguments(self):
        with patch.object(entrypoint.os, 'chdir') as change, \
             patch.object(entrypoint.os, 'execvpe') as execute, \
             patch.dict(entrypoint.os.environ, {'PATH': '/mise/bin', 'X': 'preserved'}, clear=True):
            entrypoint.child_exec([str(self.cwd), str(self.binary), 'relative.js', '$(never-run)'])
        change.assert_called_once_with(str(self.cwd))
        executable, argv, env = execute.call_args.args
        self.assertEqual(executable, str(self.binary))
        self.assertEqual(argv, [str(self.binary), 'relative.js', '$(never-run)'])
        self.assertEqual(env, {'PATH': '/mise/bin', 'X': 'preserved', 'PWD': str(self.cwd)})

    def test_child_flag_from_a_command_alias_is_an_ordinary_argument(self):
        with patch.object(entrypoint.os, 'execvpe') as execute, \
             patch.object(entrypoint, 'child_exec') as child:
            entrypoint.main(['/synthetic/bin/node', '--child', 'relative.js'])
        child.assert_not_called()
        self.assertEqual(execute.call_args.args[1][-2:], ['--child', 'relative.js'])


if __name__ == '__main__':
    unittest.main()
