"""Read native Codex configuration and skill discovery, without a turn/model call."""
import argparse,json,select,subprocess,time
from pathlib import Path


def inspect(project):
    process=subprocess.Popen(['codex','app-server','--stdio'],cwd=project,
                             stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    sequence=0;buffer=b''
    def request(method,params):
        nonlocal sequence,buffer
        sequence+=1
        process.stdin.write(json.dumps({'id':sequence,'method':method,'params':params}).encode()+b'\n');process.stdin.flush()
        end=time.monotonic()+25
        while time.monotonic()<end:
            if b'\n' not in buffer:
                if not select.select([process.stdout],[],[],max(0,end-time.monotonic()))[0]:break
                chunk=process.stdout.read1(65536)
                if not chunk:raise RuntimeError('Codex app server ended')
                buffer+=chunk
            while b'\n' in buffer:
                line,buffer=buffer.split(b'\n',1);row=json.loads(line)
                if row.get('id')==sequence:
                    if row.get('error'):raise RuntimeError(row['error'])
                    return row['result']
        raise TimeoutError(method)
    try:
        request('initialize',{'clientInfo':{'name':'mstack_discovery','version':'1'},'capabilities':{'experimentalApi':True}})
        process.stdin.write(b'{"method":"initialized"}\n');process.stdin.flush()
        config=request('config/read',{'cwd':str(project),'includeLayers':True})
        skills=request('skills/list',{'cwds':[str(project)],'forceReload':True})
        selected=[]
        for item in skills.get('data',[]):
            for skill in item.get('skills',[]):
                if skill.get('name')=='mstack':selected.append({k:skill.get(k) for k in ('name','path','scope','enabled')})
        servers=config.get('config',{}).get('mcp_servers',{})
        root=Path(__file__).resolve().parents[2]
        invocation=json.loads(subprocess.check_output([str(root/'mstack'),'run','--project',str(project),'--inspect'],cwd=project))
        layers=[{'name':l['name'],'disabledReason':l.get('disabledReason')} for l in config.get('layers',[]) if l['name']['type']=='project']
        evidence={'project':project.name,'cwd':str(project),'tool':'Codex app-server config/read + skills/list',
                  'project_mcp_servers':{k:{'command':v.get('command'),'args':v.get('args')} for k,v in servers.items() if k.startswith('project_')},
                  'project_skills':selected,'global_config_changed':False,'inference_calls':0,
                  'project_config_layers':layers,'explicit_mstack_invocation':invocation}
        resolved=json.loads(subprocess.check_output([str(root/'mstack'),'plan','--project',str(project)],cwd=project))
        required={'project_'+t for t in resolved['tools'] if t in ('graphify','headroom','windmill','anytype')}
        evidence['passed']=required<=set(invocation['enabled_mcp_servers']) and any(s['path']==str(project/'.agents/skills/mstack/SKILL.md') for s in selected)
        return evidence
    finally:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('project',type=Path);a=parser.parse_args();p=a.project.resolve()
    evidence=inspect(p);(p/'.mstack/evidence').mkdir(parents=True,exist_ok=True);(p/'.mstack/evidence/configuration.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence,indent=2))
