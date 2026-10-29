import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cli


class StackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)/'notes'

    def init(self, preset='project', context=None):
        args = argparse.Namespace(path=self.project, name='notes', preset=preset,
                                  model=None, context=context or [])
        with contextlib.redirect_stdout(io.StringIO()):
            return cli.initialize(args)

    def test_new_project_has_no_borrowed_binding(self):
        self.init()
        config = cli.resolve(self.project)
        self.assertEqual(config['tools'], ['codex', 'anytype'])
        self.assertEqual(config['bindings']['tools'], {})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.doctor(self.project), 2)
        self.assertFalse((self.project/'.secrets').exists())
        for retired in ('mcpstack.config.json','stack.bindings.json','stack.tenants.json','stack.runtime.json'):
            self.assertFalse((self.project/'infra'/retired).exists())

    def test_reinit_preserves_existing_files(self):
        self.init()
        p = self.project/'.mstack/stack.json'
        before = p.read_bytes()
        with self.assertRaises(ValueError):
            self.init('events')
        self.assertEqual(before, p.read_bytes())

    def test_context_is_explicit_and_unqualified(self):
        self.init('research', ['codegraph'])
        self.assertIn('codegraph', cli.resolve(self.project)['tools'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.doctor(self.project), 2)
        self.assertNotIn('graphify', cli.resolve(self.project)['tools'])

    def test_cross_project_binding_rejected(self):
        self.init()
        p = self.project/'.mstack/state.json'
        state = json.loads(p.read_text());state['project'] = 'clock'
        p.write_text(json.dumps(state))
        with self.assertRaises(ValueError):
            cli.resolve(self.project)

    def test_local_model_cannot_silently_fallback(self):
        self.init('knowledge')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.launch(self.project, inspect=True), 2)

    def test_removed_proxy_routes_cannot_launch_or_inherit_magpie(self):
        self.init('solo')
        config = self.project / '.mstack/stack.json'
        for route in ('local', 'deepseek'):
            with self.subTest(route=route):
                config.write_text(json.dumps({'project':'notes','preset':'solo','model':route}))
                resolved = cli.resolve(self.project)
                self.assertNotIn('opencodex', resolved['tools'])
                self.assertIsNone(resolved['model_route']['provider'])
                self.assertNotIn('endpoint', resolved['model_route'])
                self.assertNotIn('token_file', resolved['model_route'])
                with patch.object(cli.subprocess, 'call') as call, patch.object(cli.subprocess, 'check_output') as check:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(cli.launch(self.project, inspect=True), 2)
                    call.assert_not_called(); check.assert_not_called()

    def test_removed_opencodex_tool_is_rejected(self):
        self.init('solo')
        (self.project/'.mstack/stack.json').write_text(json.dumps({
            'project':'notes','preset':'solo','tools':{'opencodex':{'enabled':True}}}))
        with self.assertRaises(ValueError):
            cli.resolve(self.project)

    def test_solo_needs_no_pkm_service(self):
        self.init('solo')
        self.assertEqual(cli.resolve(self.project)['tools'], ['codex'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.doctor(self.project), 0)

    def test_unknown_field_fails(self):
        self.init()
        p = self.project/'.mstack/stack.json'
        state = json.loads(p.read_text());state['api_key'] = 'not-a-real-key'
        p.write_text(json.dumps(state))
        with self.assertRaises(ValueError):
            cli.resolve(self.project)

    def test_daily_default_selects_shared_workflow_without_borrowing_grants(self):
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(['init', str(self.project), '--name', 'notes'])
        self.assertEqual(cli.resolve(self.project)['preset'], 'daily')
        self.assertEqual(json.loads((self.project/'.mstack/stack.json').read_text()), {'project':'notes'})
        self.assertEqual(cli.resolve(self.project)['tools'], ['codex','headroom','graphify','anytype','windmill'])
        self.assertFalse(cli.doctor(self.project, report=True)['ready'])
        self.assertEqual(cli.resolve(self.project)['bindings']['tools'], {})
        self.assertFalse((self.project/'.secrets').exists())
        self.assertTrue((self.project / '.agents/skills/mstack/SKILL.md').is_file())

    def test_compact_config_overrides_and_unknown_version(self):
        self.init('daily')
        p = self.project/'.mstack/stack.json'
        p.write_text(json.dumps({'project':'notes','tools':{'graphify':{'enabled':False}}}))
        self.assertNotIn('graphify', cli.resolve(self.project)['tools'])
        self.assertIn('headroom', cli.resolve(self.project)['tools'])
        p.write_text(json.dumps({'project':'notes','version':99}))
        with self.assertRaises(ValueError): cli.resolve(self.project)

    def test_automate_does_not_require_storage_or_documents(self):
        self.init('automate')
        self.assertEqual(cli.resolve(self.project)['tools'], ['codex', 'windmill'])
        self.assertFalse(cli.doctor(self.project, report=True)['ready'])

    def test_unknown_gstack_workflow_rejected(self):
        self.init('build')
        p = self.project / '.mstack/stack.json'
        cfg = json.loads(p.read_text()); cfg['workflow'] = {'gstack': ['invented']}
        p.write_text(json.dumps(cfg))
        with self.assertRaises(ValueError):
            cli.resolve(self.project)

    def test_external_direct_plan_does_not_require_unrelated_gateway_registry(self):
        self.init('daily')
        with patch.object(cli.reconcile, 'plan', side_effect=AssertionError('Unrelated gateway consulted')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(cli.main(['plan', '--project', str(self.project)]), 0)
        self.assertFalse(json.loads(out.getvalue())['reconciliation']['global_registry_consulted'])

    def test_project_metadata_is_self_contained_and_git_safe(self):
        self.init('solo')
        self.assertFalse((self.project/'infra').exists())
        subprocess.run(['git','-C',str(self.project),'init','-q'],check=True)
        for name in ('state.json','.lock','secrets/key','cache/browser','evidence/result.json'):
            result=subprocess.run(['git','-C',str(self.project),'check-ignore','-q','.mstack/'+name])
            self.assertEqual(result.returncode,0,name)
        for name in ('stack.json','.gitignore'):
            result=subprocess.run(['git','-C',str(self.project),'check-ignore','-q','.mstack/'+name])
            self.assertEqual(result.returncode,1,name)
        self.assertIn('.mstack/stack.json',(self.project/'AGENTS.md').read_text())

    def test_init_does_not_mask_legacy_intent(self):
        (self.project/'infra').mkdir(parents=True)
        old=self.project/'infra/stack.json';old.write_text('{"project":"notes","preset":"solo"}')
        with self.assertRaises(ValueError):self.init('daily')
        self.assertFalse((self.project/'.mstack').exists())
        self.assertTrue(old.exists())

    def test_direct_apply_does_not_consult_gateway(self):
        self.init('solo')
        with patch.object(cli.reconcile,'apply',side_effect=AssertionError('Gateway consulted')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(['apply','--project',str(self.project)]),0)

    def test_proof_rejects_skill_only_graph_engine(self):
        self.init('proof')
        p = self.project/'.mstack/state.json'
        binding = json.loads(p.read_text())
        evidence = self.project/'observed.json'; evidence.write_text('{}')
        binding['bindings']['graphify'] = {'status': 'qualified', 'interface': 'skill',
                                        'evidence_file': 'observed.json'}
        p.write_text(json.dumps(binding))
        blockers = cli.doctor(self.project, report=True)['blockers']
        self.assertTrue(any('graphify: needs a harness capability or shared container tenant' in s for s in blockers))


if __name__ == '__main__':
    unittest.main()
