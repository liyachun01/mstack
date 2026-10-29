"""Offline checks only; no Docker, network, credentials or installations."""
import unittest
import copy
import inspect
import sys
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[3]
FILE = ROOT / 'infra/windmill/compose.trial.yaml'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import trial_setup as setup


class TrialDefinition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = yaml.safe_load(FILE.read_text())

    def test_standalone_three_service_project(self):
        self.assertEqual(self.data['name'], 'mcp-stack-windmill-trial')
        self.assertEqual(set(self.data['services']), {'db', 'server', 'worker'})
        self.assertEqual(self.data['networks'], {'default': {'name': 'mcp-stack-windmill-trial'}})

    def test_official_exact_digest_pins_and_arm64(self):
        images = {
            'db': 'postgres:18.6-alpine@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873',
            'server': 'ghcr.io/windmill-labs/windmill:1.823.1@sha256:20932690bab6b1820bba7a4b5934998ec69fa3f82c0ddd9a500114e53ef51f50',
            'worker': 'ghcr.io/windmill-labs/windmill:1.823.1@sha256:20932690bab6b1820bba7a4b5934998ec69fa3f82c0ddd9a500114e53ef51f50',
        }
        for name, service in self.data['services'].items():
            self.assertEqual(service['image'], images[name])
            self.assertEqual(service['platform'], 'linux/arm64')
            self.assertEqual(service['pull_policy'], 'never')

    def test_only_loopback_ui_and_no_database_publication(self):
        services = self.data['services']
        self.assertEqual(services['server']['ports'], ['127.0.0.1:58090:8000'])
        self.assertNotIn('ports', services['db'])
        self.assertNotIn('ports', services['worker'])

    def test_no_socket_privileged_mode_or_host_namespaces(self):
        for service in self.data['services'].values():
            self.assertFalse(service.get('privileged', False))
            self.assertNotIn('cap_add', service)
            self.assertEqual(service['security_opt'], ['no-new-privileges:true'])
            for name in ('pid', 'ipc', 'network_mode', 'devices', 'build'):
                self.assertNotIn(name, service)
            self.assertFalse(any('docker.sock' in mount for mount in service['volumes']))
        self.assertEqual(self.data['services']['worker']['cap_drop'], ['ALL'])

    def test_trial_job_isolation_tradeoff_is_explicit(self):
        worker = self.data['services']['worker']
        self.assertEqual(worker['environment']['NUM_WORKERS'], '1')
        self.assertEqual(worker['environment']['DISABLE_NSJAIL'], 'true')
        self.assertEqual(worker['environment']['ENABLE_UNSHARE_PID'], 'false')
        self.assertEqual(worker['environment']['FAVOR_UNSHARE_PID'], 'false')

    def test_only_new_named_storage_and_secret_original(self):
        for volume in self.data['volumes'].values():
            self.assertTrue(volume['name'].startswith('mcp-stack-windmill-trial-'))
            self.assertNotIn('external', volume)
        self.assertEqual(self.data['secrets'], {
            'windmill_trial_password': {'file': '../../.secrets/windmill_trial_password'}})
        db = self.data['services']['db']
        self.assertEqual(db['volumes'], ['postgres_data:/var/lib/postgresql'])
        self.assertNotIn('POSTGRES_PASSWORD', db['environment'])
        for name in ('server', 'worker'):
            service = self.data['services'][name]
            self.assertEqual(service['environment']['DATABASE_URL'],
                             '${WM_TRIAL_DATABASE_URL:?Use the approved isolated trial env file}')
            self.assertNotIn('secrets', service)

    def test_bounded_resources_and_logs(self):
        for name, service in self.data['services'].items():
            self.assertGreater(service['cpus'], 0)
            self.assertLessEqual(service['cpus'], 1)
            self.assertIn('mem_limit', service)
            self.assertLessEqual(service['pids_limit'], 512)
            self.assertEqual(service['logging']['options'], {'max-size': '5m', 'max-file': '2'})
            self.assertEqual(service['container_name'], 'mcp-stack-windmill-trial-' + name)

    def test_file_is_not_auto_selected_or_included_by_root(self):
        self.assertEqual(FILE.name, 'compose.trial.yaml')
        root = (ROOT / 'compose.yaml').read_text()
        self.assertNotIn('windmill', root.lower())
        self.assertNotIn('include:', FILE.read_text())

    def test_missing_approval_does_nothing(self):
        with patch.object(sys, 'argv', ['trial_setup']), patch.object(setup, 'command') as command, \
                patch.object(Path, 'mkdir') as mkdir:
            with self.assertRaisesRegex(setup.TrialFailure, 'Explicit scoped trial approval'):
                setup.main()
            command.assert_not_called()
            mkdir.assert_not_called()

    def test_exact_version_flag_parses_without_side_effects(self):
        with patch.object(sys, 'argv', ['trial_setup', '--approved-trusted-trial-1.823.1']):
            setup.approved_arguments()

    def test_existing_container_drift_is_reported_not_repaired(self):
        before = {'{{mstack:CLIENT_REPO}}': {'id': 'retained', 'status': 'running', 'restarts': 0}}
        after = copy.deepcopy(before)
        after.update({name: {} for name in setup.NAMES})
        setup.compare(before, after)
        after['{{mstack:CLIENT_REPO}}']['restarts'] = 1
        with self.assertRaisesRegex(setup.TrialFailure, 'existing-container-metadata-changed'):
            setup.compare(before, after)

    def test_mount_order_is_not_drift_but_mount_changes_are(self):
        before = {'{{mstack:CLIENT_REPO}}': {'mounts': [
            {'Source': '/one', 'Destination': '/a', 'RW': False},
            {'Source': '/two', 'Destination': '/b', 'RW': True},
        ]}}
        after = copy.deepcopy(before)
        after['{{mstack:CLIENT_REPO}}']['mounts'].reverse()
        after.update({name: {} for name in setup.NAMES})
        setup.compare(before, after)
        self.assertEqual(before['{{mstack:CLIENT_REPO}}']['mounts'][0]['Destination'], '/a')
        after['{{mstack:CLIENT_REPO}}']['mounts'][0]['RW'] = False
        with self.assertRaisesRegex(setup.TrialFailure, 'existing-container-metadata-changed'):
            setup.compare(before, after)

    def test_no_secret_dumps_auto_cleanup_or_original_assets(self):
        source = inspect.getsource(setup)
        self.assertNotIn('Config.Env', setup.FORMAT)
        self.assertNotIn('docker-compose.yml', source)
        for forbidden in ("'--privileged'", "'--remove-orphans'", "'down'", "'restart'", "'rm'", "'prune'"):
            self.assertNotIn(forbidden, source)
        self.assertIn("'--no-deps', '--pull', 'never'", source)
        self.assertIn('os.O_EXCL', source)
        self.assertIn('0o600', source)

    def test_null_output_path_stays_in_fixed_mac_shell(self):
        source = inspect.getsource(setup.main)
        self.assertIn('--output /dev/null', source)
        self.assertIn("command(['sh', '-c', script]", source)
        self.assertNotIn("'--output', '/dev/null'", source)


if __name__ == '__main__':
    unittest.main()
