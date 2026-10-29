"""Offline setup/definition contracts; no Docker, credential reads or network."""
import copy
import inspect
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app_setup as setup
import secret_repair as repair
import cache_repair as cache


class SetupContracts(unittest.TestCase):
    def test_restart_comparison_preserves_stopped_and_accepts_declared_delta(self):
        before = {'/' + setup.PG: {'id': 'pg', 'status': 'running', 'started': 'before',
                                  'networks': {'memory': {'NetworkID': 'net', 'Aliases': ['pg'], 'IP': 'old'}}},
                  '/stopped': {'id': 'retained', 'status': 'exited', 'started': 'original', 'networks': {}}}
        after = copy.deepcopy(before)
        after['/' + setup.PG]['started'] = 'after-user-restart'
        after['/' + setup.PG]['networks']['memory']['IP'] = 'new'
        after['/' + setup.PG]['networks']['mcp-stack-n8n-db'] = {'Aliases': ['n8n-postgres']}
        setup.compare_host_restart(before, after)
        after['/stopped']['status'] = 'running'
        with self.assertRaisesRegex(setup.SetupFailure, 'unexpected-container-drift'):
            setup.compare_host_restart(before, after)

    def test_post_retry_comparison_requires_existing_pg_network_unchanged(self):
        before = {'/' + setup.PG: {'networks': {'mcp-stack-n8n-db': {'Aliases': ['n8n-postgres']}}}}
        after = copy.deepcopy(before)
        after['/' + setup.APP] = {}
        setup.compare_containers(before, after)
        after['/' + setup.PG]['networks'] = {}
        with self.assertRaisesRegex(setup.SetupFailure, 'existing-container-changed'):
            setup.compare_containers(before, after)

    def test_retry_never_recreates_keys_network_or_restarts_pg(self):
        source = inspect.getsource(setup.retry_after_host_restart)
        for forbidden in ('secrets.token_hex', "'network', 'create'", "'network', 'connect'", "'restart'", "'prepare'"):
            self.assertNotIn(forbidden, source)
        self.assertIn("'--pull', 'never', 'n8n'", source)
        self.assertIn("'retry-after-host-restart.json'", source)

    def test_timeout_retains_private_progress_without_retry(self):
        failure = subprocess.TimeoutExpired(['synthetic'], 1,
                                            output=b'private progress', stderr=b'private error')
        with patch.object(setup.subprocess, 'run', side_effect=failure) as run, \
                patch.object(setup, 'private_write') as write:
            with self.assertRaisesRegex(setup.SetupFailure, '^pull-app-timeout-or-exec$'):
                setup.command(['synthetic'], 'pull-app', logs=Path('/synthetic'), timeout=1)
            run.assert_called_once()
            write.assert_called_once_with(Path('/synthetic/pull-app.log'),
                                          'private progressprivate error')

    def test_compose_equals_approved_inert_proposal(self):
        expected = (setup.ROOT / 'docs/N8N-APP-SETUP-PROPOSAL.md').read_text().split('```yaml\n', 1)[1].split('\n```', 1)[0]
        actual = (setup.ROOT / 'infra/n8n/compose.yaml').read_text().strip()
        self.assertIn(actual, (expected.strip(), repair.repaired_definition(expected.strip() + '\n').strip(),
                               cache.repaired_definition(cache.original_definition()).strip()))

    def test_cache_delta_changes_only_one_tmpfs_entry(self):
        before = yaml.safe_load(cache.original_definition())
        after = yaml.safe_load(cache.repaired_definition(cache.original_definition()))
        expected = copy.deepcopy(before)
        expected['services']['n8n']['tmpfs'].append('/home/node/.cache:' + cache.CACHE_OPTIONS)
        self.assertEqual(after, expected)

    def test_cache_repair_never_initializes_volume_or_downloads(self):
        source = inspect.getsource(cache.activate)
        for forbidden in ('pull_once', 'init_arguments', "'volume', 'create'", 'token_hex', "'restart'"):
            self.assertNotIn(forbidden, source)
        self.assertIn("'--pull', 'never', '--force-recreate', 'n8n'", source)
        self.assertIn("'activation-attempt.json'", source)

    def test_cache_mode_rejects_combined_repair(self):
        with patch.object(sys, 'argv', ['setup', '--approved-app-2.41.6', '--approved-cache-repair',
                                       '--approved-secret-repair', '--backup-directory', '/invalid']), \
                patch.object(setup, 'command') as command:
            with self.assertRaisesRegex(setup.SetupFailure, 'cache-mode-exclusive'):
                setup.main()
            command.assert_not_called()

    def test_one_official_app_no_runner_or_host_runtime(self):
        data = yaml.safe_load((setup.ROOT / 'infra/n8n/compose.yaml').read_text())
        self.assertEqual(set(data['services']), {'n8n'})
        app = data['services']['n8n']
        self.assertEqual(app['image'], setup.IMAGE)
        self.assertEqual(app['ports'], ['127.0.0.1:5678:5678'])
        self.assertTrue(app['read_only'])
        self.assertEqual(app['environment']['N8N_RUNNERS_MODE'], 'external')
        self.assertEqual(app['environment']['DB_POSTGRESDB_DATABASE'], 'n8n')
        self.assertFalse(any('sock' in m for m in app['volumes']))
        if 'secrets' in data:
            self.assertEqual(set(data['secrets']), {'n8n_password', 'n8n_encryption_key', 'n8n_runner_token'})
        else:
            self.assertEqual(data['volumes']['n8n_secrets'], {'external': True, 'name': repair.VOLUME})
            self.assertIn('n8n_secrets:/run/secrets:ro', app['volumes'])

    def test_secret_repair_changes_only_secret_delivery(self):
        before = yaml.safe_load(repair.original_definition())
        after = yaml.safe_load(repair.repaired_definition(repair.original_definition()))
        expected = copy.deepcopy(before)
        del expected['secrets']
        del expected['services']['n8n']['secrets']
        expected['services']['n8n']['volumes'].append('n8n_secrets:/run/secrets:ro')
        expected['volumes']['n8n_secrets'] = {'external': True, 'name': repair.VOLUME}
        self.assertEqual(after, expected)

    def test_initializer_is_offline_pinned_and_has_only_chown(self):
        args = repair.init_arguments()
        for flag, value in [('--pull', 'never'), ('--network', 'none'), ('--user', '0:0'),
                            ('--cap-drop', 'ALL'), ('--cap-add', 'CHOWN')]:
            self.assertEqual(args[args.index(flag) + 1], value)
        self.assertIn(setup.IMAGE, args)
        for forbidden in ['--privileged', '--env', '--env-file', '--publish']:
            self.assertNotIn(forbidden, args)
        self.assertNotIn('bind', args[args.index('--mount') + 1])

    def test_repair_has_no_download_or_key_regeneration(self):
        source = inspect.getsource(repair.activate)
        self.assertNotIn('pull_once', source)
        self.assertNotIn('token_hex', source)
        self.assertIn("'--pull', 'never', '--force-recreate', 'n8n'", source)
        self.assertIn('input=json.dumps(values)', source)

    def test_secret_repair_mode_cannot_double_as_retry(self):
        with patch.object(sys, 'argv', ['setup', '--approved-app-2.41.6', '--approved-secret-repair',
                                       '--approved-retry-after-host-restart', '--backup-directory', '/invalid']), \
                patch.object(setup, 'command') as command:
            with self.assertRaisesRegex(setup.SetupFailure, 'repair-mode-exclusive'):
                setup.main()
            command.assert_not_called()

    def test_missing_approval_never_calls_macctl(self):
        with patch.object(sys, 'argv', ['setup', '--prepare']), patch.object(setup, 'command') as command:
            with self.assertRaisesRegex(setup.SetupFailure, 'approval'):
                setup.main()
            command.assert_not_called()

    def test_prepare_and_activate_are_mutually_exclusive(self):
        with patch.object(sys, 'argv', ['setup', '--approved-app-2.41.6', '--prepare',
                                       '--backup-directory', '/invalid']), patch.object(setup, 'command') as command:
            with self.assertRaisesRegex(setup.SetupFailure, 'choose-prepare'):
                setup.main()
            command.assert_not_called()

    def test_pg_expected_delta_rejects_an_unknown_original(self):
        with self.assertRaisesRegex(setup.SetupFailure, 'network-contract'):
            setup.expected_postgres('services: {}\n')

    def test_pg_pin_uses_numeric_version_not_distribution_string(self):
        source = inspect.getsource(setup.prepare)
        self.assertIn("current_setting('server_version_num')::int = 180006", source)
        self.assertNotIn("current_setting('server_version') = '18.6'", source)

    def test_only_new_app_and_pg_alias_are_allowed(self):
        before = {'/' + setup.PG: {'id': 'pg', 'started': 'original',
                                  'networks': {'memory': {'Aliases': ['postgres']}}}}
        after = copy.deepcopy(before)
        after['/' + setup.APP] = {'id': 'new-app'}
        after['/' + setup.PG]['networks']['mcp-stack-n8n-db'] = {'Aliases': ['n8n-postgres']}
        setup.compare_containers(before, after)
        after['/' + setup.PG]['started'] = 'restarted'
        with self.assertRaisesRegex(setup.SetupFailure, 'existing-container-changed'):
            setup.compare_containers(before, after)

    def test_unknown_extra_container_fails_preservation(self):
        with self.assertRaisesRegex(setup.SetupFailure, 'identity-set'):
            setup.compare_containers({}, {'/' + setup.APP: {}, '/unexpected': {}})

    def test_mac_host_http_keeps_absolute_output_path_inside_shell(self):
        args = setup.host_http_arguments('http://127.0.0.1:5678/setup')
        self.assertEqual(args[:4], ['macctl', 'run', 'sh', '-c'])
        self.assertNotIn('/dev/null', args)
        self.assertIn('--output /dev/null', args[4])
        self.assertEqual(args[-1], 'http://127.0.0.1:5678/setup')
        with self.assertRaisesRegex(setup.SetupFailure, 'url-scope'):
            setup.host_http_arguments('http://example.com/')


if __name__ == '__main__':
    unittest.main()
