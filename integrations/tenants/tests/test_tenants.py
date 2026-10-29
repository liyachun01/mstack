import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry import authenticate, read_bootstrap, tenant_file
from manage import register, inspect_binding, service


class TenantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = {'version': 1, 'tenants': {
            name: {'enabled': True, 'token_sha256': hashlib.sha256(token.encode()).hexdigest()}
            for name, token in [('project-a', 'a'*64), ('project-b', 'b'*64)]}}

    def test_project_a_cannot_select_b_with_its_key(self):
        self.assertEqual(authenticate(self.registry, {'tenant': 'project-a', 'token': 'a'*64})[0], 'project-a')
        with self.assertRaises(ValueError): authenticate(self.registry, {'tenant': 'project-b', 'token': 'a'*64})

    def test_unknown_disabled_and_extra_fields_fail_closed(self):
        self.registry['tenants']['project-a']['enabled'] = False
        for value in [{'tenant': 'project-a', 'token': 'a'*64}, {'tenant': '../project-a', 'token': 'a'*64},
                      {'tenant': 'missing', 'token': 'a'*64}, {'tenant': 'project-b', 'token': 'b'*64, 'graph': '/etc/passwd'}]:
            with self.assertRaises(ValueError): authenticate(self.registry, value)

    def test_bootstrap_does_not_consume_following_mcp_message(self):
        reader, writer = os.pipe()
        try:
            os.write(writer, b'{"tenant":"project-a","token":"test"}\n{"jsonrpc":"2.0"}\n')
            self.assertEqual(read_bootstrap(reader)['tenant'], 'project-a')
            self.assertEqual(os.read(reader, 100), b'{"jsonrpc":"2.0"}\n')
        finally: os.close(reader); os.close(writer)

    def test_graph_symlink_cannot_escape_tenant(self):
        folder = self.root/'tenants/project-a'; folder.mkdir(parents=True)
        outside = self.root/'outside.json'; outside.write_text('{}')
        (folder/'graph.json').symlink_to(outside)
        with self.assertRaises(ValueError): tenant_file(self.root, 'project-a', 'graph.json')

    def project(self, slug):
        p = self.root/slug; (p/'.mstack').mkdir(parents=True)
        (p/'.mstack/stack.json').write_text(json.dumps({'project': slug}))
        graph = p/'graph.json'; graph.write_text('{"nodes":[],"edges":[]}')
        return p, graph

    def test_registration_reuses_service_and_preserves_project_credentials(self):
        a, graph_a = self.project('project-a'); b, graph_b = self.project('project-b')
        state = self.root/'runtime'
        register(a, 'graphify', graph_a, state); register(b, 'graphify', graph_b, state)
        self.assertEqual(inspect_binding(a, 'graphify', state)['container'], inspect_binding(b, 'graphify', state)['container'])
        key_a = (a/'.mstack/secrets/mstack-graphify-token').read_bytes()
        self.assertNotEqual(key_a, (b/'.mstack/secrets/mstack-graphify-token').read_bytes())
        with self.assertRaises(ValueError): register(a, 'graphify', graph_a, state)
        self.assertEqual(key_a, (a/'.mstack/secrets/mstack-graphify-token').read_bytes())
        (b/'.mstack/secrets/mstack-graphify-token').write_bytes(key_a)
        with self.assertRaises(ValueError): inspect_binding(b, 'graphify', state)

    def test_registered_index_drift_is_not_local_readiness(self):
        project, graph = self.project('project-a'); state = self.root/'runtime'
        register(project, 'graphify', graph, state)
        (state/'graphify/tenants/project-a/graph.json').write_text('{"nodes":[{"id":"changed"}]}')
        with self.assertRaises(ValueError): inspect_binding(project, 'graphify', state)

    def test_new_credentials_are_git_ignored_and_existing_rules_preserved(self):
        project, graph = self.project('project-a')
        subprocess.run(['git', '-C', str(project), 'init', '-q'], check=True)
        (project/'.gitignore').write_text('existing-private-file')
        register(project, 'graphify', graph, self.root/'runtime')
        for name in ['existing-private-file', '.mstack/secrets/mstack-graphify-token']:
            subprocess.run(['git', '-C', str(project), 'check-ignore', '-q', name], check=True)

    def test_anytype_registration_uses_unified_intent_and_detects_key_rotation(self):
        project,_=self.project('notes');state=self.root/'runtime'
        cfg={'project':'notes','anytype':{'space_id':'own-space','api_url':'http://localhost:31009','credential_file':'.mstack/secrets/anytype'}}
        (project/'.mstack/stack.json').write_text(json.dumps(cfg))
        (project/'.mstack/secrets').mkdir();key=project/'.mstack/secrets/anytype';key.write_text('synthetic-own-key');key.chmod(0o600)
        (project/'.mstack/anytype').mkdir();(project/'.mstack/anytype/openapi.json').write_text('{}')
        register(project,'anytype',state=state)
        self.assertEqual(inspect_binding(project,'anytype',state)['tenant'],'notes')
        generated=json.loads((project/'.mstack/state.json').read_text())
        self.assertEqual(generated['tenants']['anytype']['tenant'],'notes')
        self.assertEqual(json.loads((project/'.mstack/stack.json').read_text()),cfg)
        key.write_text('rotated')
        with self.assertRaises(ValueError):inspect_binding(project,'anytype',state)

    def test_service_creation_handles_docker_missing_object_case_and_denies_daemon_errors(self):
        with patch('manage.subprocess.run') as run:
            run.side_effect = [subprocess.CompletedProcess([], 1, '', 'error: no such object: mstack-headroom'),
                               subprocess.CompletedProcess([], 0, '', '')]
            self.assertEqual(service('start', 'headroom')['headroom']['action'], 'start')
            self.assertIn('--no-deps', run.call_args_list[1].args[0])
            self.assertEqual(run.call_args_list[1].args[0][-1], 'headroom')
        with patch('manage.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'Cannot connect to Docker')) as run:
            with self.assertRaises(ValueError): service('start', 'headroom')
            self.assertEqual(run.call_count, 1)


if __name__ == '__main__': unittest.main()
