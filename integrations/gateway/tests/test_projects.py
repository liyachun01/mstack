import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from projects import read, resolve, gateway_config, blockers, digest, validate_document, private_key, apply_candidate, seed_runtime, ROOT


def qualified(entries, root):
    root.joinpath('credential').write_text('synthetic-only')
    for project, tools in entries.items():
        for tool, entry in tools.items():
            entry['input'] = {'workspace_id':'synthetic', 'credential_file':'credential'}
            entry['space'] = {'channel_ids':['channel-'+project[-1]]}
            entry['scope_fingerprint'] = digest({k:entry[k] for k in (
                'project','tool','connection','input','space','mcp_url','access')})
            proof = {k:entry[k] for k in ('project','tool','scope_fingerprint')}
            proof.update({k:True for k in ('passed','allowed_read','out_of_scope_denied','no_unauthorized_dispatch')})
            name = project+'-'+tool+'.json'
            root.joinpath(name).write_text(json.dumps(proof))
            entry['binding'] = {'status':'qualified', 'scope_fingerprint':entry['scope_fingerprint'],
                'access':entry['access'],
                'scope_enforcement':'scoped-adapter', 'mcp_url':'http://fixture:8000/'+project[-1]+'/mcp',
                'tools':['read_channel'], 'evidence_file':name}


class ProjectPolicyTests(unittest.TestCase):
    def setUp(self):
        self.registry = read(Path(__file__).with_name('policy_fixture.json'))
        self.bindings = {'version':1,'projects':{p:{t:{'status':'pending'} for t in row['tools']} for p,row in self.registry['projects'].items()}}

    def test_empty_inputs_never_enable_backend(self):
        r = resolve(self.registry,self.bindings)
        cfg = gateway_config(r,{('project-a','codex'):'a'*64})
        self.assertFalse(any('backends' in route for route in cfg['routes']))
        for route in cfg['routes'][1:-1]:
            self.assertEqual(route['policies']['directResponse']['status'],503)
            self.assertIn('apiKey.project',route['policies']['authorization']['rules'][0])

    def test_shared_scope_and_per_project_override(self):
        self.registry['connections']['slack-shared']['space'] = {'channel_ids':['shared']}
        r = resolve(self.registry,self.bindings)
        self.assertEqual(r['project-a']['slack']['space'],r['project-b']['slack']['space'])
        self.registry['projects']['project-b']['tools']['slack']['space'] = {'channel_ids':['private-b']}
        changed = resolve(self.registry,self.bindings)
        self.assertNotEqual(changed['project-b']['slack']['scope_fingerprint'],r['project-b']['slack']['scope_fingerprint'])
        self.assertEqual(changed['project-a']['slack']['scope_fingerprint'],r['project-a']['slack']['scope_fingerprint'])

    def test_stale_or_incomplete_scope_proof_denies(self):
        entries = resolve(self.registry,self.bindings)
        entries = {p:{'slack':ts['slack']} for p,ts in entries.items()}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); qualified(entries,root)
            entry=entries['project-a']['slack']
            self.assertEqual(blockers(entry,root),[])
            entry['binding']['scope_fingerprint']='stale'
            self.assertIn('binding does not match current scope',blockers(entry,root))
            entry['binding']['scope_fingerprint']=entry['scope_fingerprint']
            proof=root/entry['binding']['evidence_file']
            content=json.loads(proof.read_text());content['out_of_scope_denied']=False
            proof.write_text(json.dumps(content))
            self.assertIn('scope evidence incomplete/stale',blockers(entry,root))

    def test_connection_tool_mismatch_refused(self):
        self.registry['projects']['project-a']['tools']['slack']['connection']='linear-shared'
        with self.assertRaises(ValueError):resolve(self.registry,self.bindings)

    def test_wrong_types_and_typos_rejected(self):
        for mutate in [
            lambda r:r['connections']['slack-shared']['space'].update(channel_ids='all'),
            lambda r:r['projects']['project-a']['tools']['slack'].update(access='write-anything'),
            lambda r:r['projects']['project-a']['input'].update(reop='/typo'),
            lambda r:r['connections']['slack-shared']['input'].update(credential_file='../other-key'),
            lambda r:r['connections']['slack-shared']['input'].update(credential_file='.secrets/../other-key'),
            lambda r:r['connections']['slack-shared']['space'].update(channel_ids=['*']),
        ]:
            with self.subTest(mutate=mutate):
                r=copy.deepcopy(self.registry);mutate(r)
                with self.assertRaises(ValueError):resolve(r,self.bindings)

    def test_disabling_tool_or_changing_access_denies_qualified_binding(self):
        entries=resolve(self.registry,self.bindings)
        entries={'project-a':{'slack':entries['project-a']['slack']}}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);qualified(entries,root);entry=entries['project-a']['slack']
            self.assertFalse(blockers(entry,root))
            entry['enabled']=False
            self.assertIn('tool disabled in this project',blockers(entry,root))
            entry['enabled']=True;entry['access']='read-write'
            self.assertIn('requested access mode not qualified',blockers(entry,root))

    def test_ui_keeps_raw_admin_off_and_project_rules_separate(self):
        config=gateway_config(resolve(self.registry,self.bindings),{('project-a','codex'):'a'*64},ui='synthetic-hash')
        self.assertEqual(config['config']['adminAddr'],'off')
        self.assertEqual(config['config']['storage']['mode'],'readOnly')
        self.assertEqual(config['gateways']['viewer']['basicAuth']['mode'],'strict')
        self.assertIn('apiKey',config['gateways']['projects'])

    def test_owner_mode_and_render_preserves_saved_config(self):
        cfg=gateway_config(resolve(self.registry,self.bindings),{('project-a','codex'):'a'*64},ui='hash',writable=True)
        self.assertEqual(cfg['config']['storage']['mode'],'file')
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate.json';runtime=Path(tmp)/'runtime/config.yaml'
            candidate.write_text('first candidate')
            self.assertTrue(seed_runtime(candidate,runtime))
            runtime.write_text('owner saved changes')
            candidate.write_text('second candidate')
            self.assertFalse(seed_runtime(candidate,runtime))
            self.assertEqual(runtime.read_text(),'owner saved changes')
            apply_candidate(candidate,runtime)
            self.assertEqual(runtime.read_text(),'second candidate')
            backups=list(runtime.parent.glob('config.before-*.yaml'))
            self.assertEqual(len(backups),1)
            self.assertEqual(backups[0].read_text(),'owner saved changes')

    def test_unknown_binding_and_reused_anytype_space_rejected(self):
        bindings=copy.deepcopy(self.bindings);bindings['projects']['missing']={}
        with self.assertRaises(ValueError):resolve(self.registry,bindings)
        for project in ['project-a','project-b']:
            self.registry['connections']['anytype-'+project]['space']['space_id']='same-space'
        with self.assertRaises(ValueError):resolve(self.registry,self.bindings)

    def test_blank_ui_password_reference_and_external_key_path_rejected(self):
        ui=read(ROOT/'infra/agentgateway/projects/ui.json');ui['password_file']=''
        with self.assertRaises(ValueError):validate_document(ui,'ui.schema.json')
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);mode=folder.stat().st_mode
            with self.assertRaises(ValueError):private_key(folder/'outside'/'key')
            self.assertFalse((folder/'outside').exists())
            self.assertEqual(folder.stat().st_mode,mode)


if __name__ == '__main__':unittest.main()
