import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import config
import reconcile


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in ['presets.json','models.json','connections.json']:
            reconcile.atomic(self.root/'infra/stack'/name,config.read(config.ROOT/'infra/stack'/name),0o644)
        ui=config.read(config.ROOT/'infra/agentgateway/projects/ui.json')
        reconcile.atomic(self.root/'infra/agentgateway/projects/ui.json',ui,0o644)
        bindings={'version':1,'projects':{slug:{'slack':{'status':'pending'}} for slug in ('project-a','project-b')}}
        reconcile.atomic(self.root/'infra/agentgateway/projects.bindings.json',bindings,0o644)
        self.projects={}
        for slug in ['project-a','project-b']:
            project=self.root/'examples'/slug;self.projects[slug]=project
            cfg={'version':3,'project':slug,'preset':'solo','harnesses':['codex','claude'],
                 'tools':{'slack':{'connection':'slack-shared','space':{},'access':'read-only'}}}
            reconcile.atomic(project/'.mstack/stack.json',cfg,0o644)
            reconcile.atomic(project/'.mstack/state.json',{'version':1,'project':slug,'bindings':{}},0o644)
            for caller in ['codex','claude']:
                path=self.root/'.secrets/agentgateway/projects'/slug/(caller+'-token')
                path.parent.mkdir(parents=True,exist_ok=True);path.write_text(('a' if slug=='project-a' else 'b')*64);path.chmod(0o600)
        reconcile.atomic(self.root/'infra/stack/project-index.json',{'version':1,'projects':{p:'examples/'+p for p in self.projects}},0o644)
        desired=reconcile.prepare(self.projects['project-a'],self.root)['desired']
        reconcile.atomic(self.root/'infra/agentgateway/state/projects/runtime/config.yaml',desired)
        self.restart=Mock()

    def edit(self,slug,mutate):
        path=self.projects[slug]/'.mstack/stack.json';value=config.read(path);mutate(value);reconcile.atomic(path,value,0o644)

    def apply(self,slug='project-a',**kwargs):
        return reconcile.apply(self.projects[slug],self.root,restart=self.restart,**kwargs)

    def test_repeat_apply_no_restart_or_artifact_rewrite(self):
        first=self.apply();path=self.projects['project-a']/'.mstack/state.json';stamp=path.stat().st_mtime_ns
        files=[self.root/'infra/agentgateway/projects.json',self.root/'infra/stack/project-index.json',self.root/'infra/stack/state/reconcile.json']
        stamps=[p.stat().st_mtime_ns for p in files]
        second=self.apply()
        self.assertEqual(stamps,[p.stat().st_mtime_ns for p in files])
        self.assertFalse(first['gateway_changed']);self.assertFalse(second['project_launch_changed'])
        self.assertEqual(path.stat().st_mtime_ns,stamp);self.restart.assert_not_called()
        self.assertFalse(first['ready']);self.assertIn('slack',first['pending_connections'])

    def test_project_config_updates_route_preserving_other_project(self):
        self.apply();before=reconcile.runtime_config(self.root)
        self.edit('project-a',lambda c:c.update(harnesses=['codex']))
        plan=reconcile.plan(self.projects['project-a'],self.root)
        self.assertTrue(plan['reconciliation']['gateway_change']);self.assertFalse(plan['reconciliation']['owner_ui_drift'])
        self.apply();self.restart.assert_called_once()
        after=reconcile.runtime_config(self.root)
        self.assertEqual([r for r in before['routes'] if r['name']=='project-b'],[r for r in after['routes'] if r['name']=='project-b'])
        hashes=after['gateways']['projects']['apiKey']['keys']
        self.assertEqual(sum(k['metadata']['project']=='project-b' for k in hashes),2)
        self.assertEqual(sum(k['metadata']['project']=='project-a' for k in hashes),1)
        self.assertTrue(list((self.root/'infra/agentgateway/state/projects/runtime').glob('config.before-*.yaml')))

    def test_drift_stops_and_restore_is_explicit(self):
        self.apply();live=reconcile.runtime_config(self.root);original=copy.deepcopy(live)
        live['config']['logging']['level']='info'
        reconcile.atomic(self.root/'infra/agentgateway/state/projects/runtime/config.yaml',live)
        with self.assertRaisesRegex(ValueError,'drift'):self.apply()
        self.restart.assert_not_called()
        self.apply(drift='restore');self.assertEqual(reconcile.runtime_config(self.root),original)

    def test_adopt_owner_settings_then_apply_is_noop(self):
        self.apply();live=reconcile.runtime_config(self.root);live['config']['logging']['level']='info'
        live['gateways']['owner-extra']={'port':4002}
        live['routes'].append({'name':'owner-extra','gateways':['owner-extra'],'policies':{'directResponse':{'status':204}}})
        reconcile.atomic(self.root/'infra/agentgateway/state/projects/runtime/config.yaml',live)
        result=reconcile.adopt(self.projects['project-a'],self.root);self.assertTrue(result['adopted'])
        self.assertEqual(reconcile.prepare(self.projects['project-a'],self.root)['desired'],live)
        self.assertFalse(self.apply()['gateway_changed']);self.restart.assert_not_called()

    def test_adopt_cannot_infer_provider_scopes_from_ui_route(self):
        self.apply();live=reconcile.runtime_config(self.root)
        next(r for r in live['routes'] if r['name']=='project-a')['policies'].pop('authorization')
        reconcile.atomic(self.root/'infra/agentgateway/state/projects/runtime/config.yaml',live)
        with self.assertRaisesRegex(ValueError,'managed'):reconcile.adopt(self.projects['project-a'],self.root)
        self.assertFalse((self.root/'infra/stack/gateway.json').exists())

    def test_url_credentials_typos_and_path_escape_rejected_without_leak(self):
        for option in [{'url':'https://user:SECRET@example.test/mcp'}, {'url':'https://example.test/mcp?token=SECRET'},
                       {'credential_file':'.secrets/../escape'}, {'api_key':'SECRET'}, {'input':{'api_key':'SECRET'}}, {'enabled':'false'}]:
            with self.subTest(option=option):
                self.edit('project-a',lambda c:c['tools'].update(slack={'connection':'slack-shared',**option}))
                with self.assertRaises((ValueError,KeyError)) as error:reconcile.plan(self.projects['project-a'],self.root)
                self.assertNotIn('SECRET',str(error.exception))

    def test_disabled_context_does_not_require_or_emit_tool(self):
        self.edit('project-a',lambda c:c.update(context=['codegraph'],tools={'codegraph':{'enabled':False}}))
        cfg=config.project_config(self.projects['project-a']);self.assertFalse(config.selections(cfg,self.root)['codegraph']['enabled'])
        self.assertNotIn('project-a',config.registry(self.root)[0]['projects'])
        self.assertIn('project-b',config.registry(self.root)[0]['projects'])

    def test_mismatched_project_identity_is_rejected(self):
        self.edit('project-a',lambda c:c.update(project='different'))
        with self.assertRaises(ValueError):reconcile.plan(self.projects['project-a'],self.root)

    def test_yaml_off_roundtrips_as_string(self):
        path=self.root/'infra/agentgateway/state/projects/runtime/config.yaml'
        path.write_text('config:\n  adminAddr: off\n  enableIpv6: false\n')
        value=reconcile.runtime_config(self.root)
        self.assertEqual(value['config']['adminAddr'],'off');self.assertIs(value['config']['enableIpv6'],False)

    def test_failed_restart_restores_original_and_keeps_binding_state(self):
        self.apply();original=reconcile.runtime_config(self.root)
        binding=(self.root/'infra/agentgateway/projects.bindings.json').read_bytes()
        self.edit('project-a',lambda c:c.update(harnesses=['codex']))
        self.restart.side_effect=[RuntimeError('synthetic failure'),None]
        with self.assertRaisesRegex(RuntimeError,'restored'):self.apply()
        self.assertEqual(reconcile.runtime_config(self.root),original)
        self.assertEqual((self.root/'infra/agentgateway/projects.bindings.json').read_bytes(),binding)
        self.assertEqual(self.restart.call_count,2)

    def test_scope_override_and_url_change_are_project_local(self):
        before=config.registry(self.root)[0]
        self.edit('project-a',lambda c:c['tools']['slack'].update(space={'channel_ids':['channel-a']},url='https://example.test/mcp'))
        after=config.registry(self.root)[0]
        self.assertEqual(before['projects']['project-b'],after['projects']['project-b'])
        selection=after['projects']['project-a']['tools']['slack']
        self.assertEqual(selection['space']['channel_ids'],['channel-a'])
        self.assertEqual(after['connections'][selection['connection']]['mcp_url'],'https://example.test/mcp')
        self.assertTrue(reconcile.prepare(self.projects['project-a'],self.root)['pending']['slack'])

    def test_direct_url_and_secret_options_resolve_without_inline_token(self):
        options={'url':'https://example.test/mcp','credential_file':'.secrets/provider'}
        server=config.direct_server(options,{'mcp':{'command':'old-command','args':['old']},'tools':['read_symbol']})
        self.assertEqual(server['url'],options['url']);self.assertNotIn('command',server)
        self.assertEqual(server['enabled_tools'],['read_symbol'])
        self.assertNotIn('credential_file',server)

    def test_literal_secret_in_direct_input_is_rejected(self):
        self.edit('project-a',lambda c:c['tools'].update(codegraph={'input':{'api_key':'SECRET'}}))
        with self.assertRaises(ValueError) as error:reconcile.plan(self.projects['project-a'],self.root)
        self.assertNotIn('SECRET',str(error.exception))

    def test_secret_rotation_invalidates_scope_identity(self):
        path=self.root/'.secrets/provider';path.write_text('synthetic-key-a');path.chmod(0o600)
        self.edit('project-a',lambda c:c['tools']['slack'].update(credential_file='.secrets/provider'))
        first=reconcile.prepare(self.projects['project-a'],self.root)['entries']['slack']['scope_fingerprint']
        path.write_text('synthetic-key-b')
        second=reconcile.prepare(self.projects['project-a'],self.root)['entries']['slack']['scope_fingerprint']
        self.assertNotEqual(first,second)


if __name__=='__main__':unittest.main()
