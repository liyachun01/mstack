import json
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import project_state

class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'.mstack').mkdir()
        (self.root/'.mstack/stack.json').write_text('{"project":"notes"}')

    def test_missing_state_has_no_borrowed_access_and_ignores_legacy(self):
        (self.root/'infra').mkdir()
        (self.root/'infra/stack.bindings.json').write_text('{"tools":{"anytype":{"status":"qualified"}}}')
        self.assertEqual(project_state.read(self.root)['bindings'],{})

    def test_atomic_updates_preserve_other_sections_and_intent(self):
        before=(self.root/'.mstack/stack.json').read_bytes()
        def update(section):
            with project_state.edit(self.root) as state:state[section]['observed']=True
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(update,project_state.SECTIONS))
        actual=project_state.read(self.root)
        self.assertTrue(all(actual[k]['observed'] for k in project_state.SECTIONS))
        self.assertEqual(before,(self.root/'.mstack/stack.json').read_bytes())
        self.assertEqual((self.root/project_state.RELATIVE).stat().st_mode&0o777,0o600)
        self.assertIn('/secrets/',(self.root/'.mstack/.gitignore').read_text())

    def test_foreign_identity_and_symlink_fail_closed(self):
        with project_state.edit(self.root):pass
        p=self.root/project_state.RELATIVE
        value=json.loads(p.read_text());value['project']='foreign';p.write_text(json.dumps(value))
        with self.assertRaises(ValueError):project_state.read(self.root)
        p.unlink();p.symlink_to(self.root/'.mstack/stack.json')
        with self.assertRaises(ValueError):project_state.read(self.root)
        with self.assertRaises(ValueError):
            with project_state.edit(self.root):pass

    def test_project_secrets_reject_other_locations_and_symlinked_folders(self):
        for ref in ('.secrets/key','.mstack/secrets/../../outside','/tmp/key'):
            with self.assertRaises(ValueError):project_state.credential(self.root,ref)
        outside=self.root/'outside';outside.mkdir()
        (self.root/'.mstack/secrets').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):project_state.credential(self.root,'.mstack/secrets/key')

    def test_credential_rotation_invalidates_connection_but_document_draft_does_not(self):
        (self.root/'.mstack/secrets').mkdir();key=self.root/'.mstack/secrets/key';key.write_text('synthetic-a');key.chmod(0o600)
        cfg={'project':'notes','anytype':{'space_id':'own-channel','api_url':'http://localhost:31009','credential_file':'.mstack/secrets/key'}}
        path=self.root/'.mstack/stack.json';path.write_text(json.dumps(cfg))
        original=project_state.connection_fingerprint(self.root,'anytype')
        cfg['anytype']['documents']={'brief':{'name':'Brief','local_draft':'docs/BRIEF.md'}};path.write_text(json.dumps(cfg))
        self.assertEqual(original,project_state.connection_fingerprint(self.root,'anytype'))
        key.write_text('synthetic-b')
        self.assertNotEqual(original,project_state.connection_fingerprint(self.root,'anytype'))

if __name__=='__main__':unittest.main()
