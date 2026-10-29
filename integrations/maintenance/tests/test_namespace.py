import copy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('migration',Path(__file__).resolve().parents[1]/'namespace_mstack.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MigrationChecks(unittest.TestCase):
    def setUp(self):
        self.old={'Image':'pinned','Mounts':[{'Type':'volume','Name':'original','Source':'/vol','Destination':'/data','RW':True}],
                  'Config':{'Env':['KEY=secret','MODE=worker'],'Labels':{'com.docker.compose.project':'mcp-stack','io.mstack.runtime':'shared-tenants'}},
                  'HostConfig':{'Privileged':False,'PortBindings':{'80/tcp':[{'HostIp':'127.0.0.1','HostPort':'58090'}]}},
                  'NetworkSettings':{'Networks':{'network':{'Aliases':['service','container']}}}}
    def test_namespace_and_generated_identity_are_allowed(self):
        new=copy.deepcopy(self.old);new['Config']['Labels']['com.docker.compose.project']='mstack'
        new['Id']='new';new['Config']['Env'].reverse()
        self.assertEqual(m.compare(self.old,new),[])
    def test_default_dns_empty_list_and_null_are_equivalent(self):
        new=copy.deepcopy(self.old)
        for key in ['Dns','DnsSearch','DnsOptions']:
            self.old['HostConfig'][key]=[];new['HostConfig'][key]=None
        self.assertEqual(m.compare(self.old,new),[])
        new['HostConfig']['Dns']=['8.8.8.8']
        self.assertIn('HostConfig.Dns',m.compare(self.old,new))

    def test_volume_credential_and_port_changes_are_rejected(self):
        for field in ['volume','credential','port','privileged','alias']:
            new=copy.deepcopy(self.old)
            if field=='volume':new['Mounts'][0]['Name']='empty-new-volume'
            if field=='credential':new['Config']['Env'][0]='KEY=other'
            if field=='port':new['HostConfig']['PortBindings']['80/tcp'][0]['HostIp']='0.0.0.0'
            if field=='privileged':new['HostConfig']['Privileged']=True
            if field=='alias':new['NetworkSettings']['Networks']['network']['Aliases']=['different']
            self.assertTrue(m.compare(self.old,new),field)
    def test_exact_service_allowlist_excludes_other_projects(self):
        self.assertEqual(set(m.SPECS),{'postgres','windmill-server','windmill-worker','whodb','garage','opencodex','agentgateway','ai-memory','graphify','anytype-mcp','headroom'})
        for service in m.SPECS:
            self.assertEqual(m.compose(service)[:3],['compose','-p','mstack'])

if __name__=='__main__':unittest.main()
