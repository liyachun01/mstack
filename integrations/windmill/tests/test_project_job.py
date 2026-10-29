import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import project_job as job

class ProjectJobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name);(self.project/'.mstack').mkdir();(self.project/'.mstack/secrets').mkdir()
        for name in ('api','mcp'):
            p=self.project/'.mstack/secrets'/name;p.write_text('synthetic');p.chmod(0o600)
        self.cfg={'project':'notes','windmill':{'api_url':'http://localhost:58090/api','workspace':'notes',
                 'script':'u/admin/reviewed_job','credential_file':'.mstack/secrets/api','mcp_credential_file':'.mstack/secrets/mcp'}}
        (self.project/'.mstack/stack.json').write_text(json.dumps(self.cfg))
        with job.project_state.edit(self.project) as state:
            state['bindings']['windmill']={'status':'qualified','connection_fingerprint':job.project_state.connection_fingerprint(self.project,'windmill')}
            state['runtime']['windmill']={'script_hash':'reviewed','source_sha256':hashlib.sha256(b'reviewed source').hexdigest()}

    def test_new_config_runs_only_reviewed_script_and_records_result(self):
        before=(self.project/'.mstack/stack.json').read_bytes()
        with patch.object(job,'request',side_effect=[{'hash':'reviewed','content':'reviewed source'},'job-one',{'success':True,'result':42}]) as call:
            result=job.run(self.project,{'value':2})
            self.assertEqual(result['result'],42)
            self.assertEqual(call.call_args_list[1].args[3],{'value':2})
        self.assertEqual(before,(self.project/'.mstack/stack.json').read_bytes())
        self.assertTrue((self.project/'.mstack/evidence/windmill-run.json').exists())

    def test_changed_script_or_connection_blocks_execution(self):
        with patch.object(job,'request',return_value={'hash':'changed','content':'changed'}) as call:
            with self.assertRaises(ValueError):job.run(self.project,{})
            self.assertEqual(call.call_count,1)
        (self.project/'.mstack/secrets/api').write_text('rotated')
        with patch.object(job,'request') as call:
            with self.assertRaises(ValueError):job.run(self.project,{})
            call.assert_not_called()

if __name__=='__main__':unittest.main()
