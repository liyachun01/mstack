"""Explicit, locked reconciliation of project intent; no background provisioner."""
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from contextlib import contextmanager

import config as intent
import project_state
from config import gateway

ROOT=intent.ROOT


def digest(value):return gateway.digest(value)


def atomic(path,value,mode=0o600):
    encoded=json.dumps(value,indent=2)+'\n'
    if path.exists() and path.read_text()==encoded:
        if path.stat().st_mode&0o777!=mode:os.chmod(path,mode)
        return False
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as handle:
            handle.write(encoded);handle.flush();os.fsync(handle.fileno())
        os.chmod(name,mode);os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def runtime_config(root=ROOT):
    path=root/'infra/agentgateway/state/projects/runtime/config.yaml'
    if not path.exists():return None
    # The native gateway uses YAML 1.2: 'off' is a string, not YAML 1.1 False.
    import yaml
    class Loader(yaml.SafeLoader):pass
    Loader.yaml_implicit_resolvers=copy.deepcopy(Loader.yaml_implicit_resolvers)
    for key,values in Loader.yaml_implicit_resolvers.items():
        Loader.yaml_implicit_resolvers[key]=[(tag,regex) for tag,regex in values if tag!='tag:yaml.org,2002:bool']
    Loader.add_implicit_resolver('tag:yaml.org,2002:bool',re.compile(r'^(?:true|false|True|False|TRUE|FALSE)$'),list('tTfF'))
    return yaml.load(path.read_text(),Loader=Loader)


def changed_paths(old,new,path=''):
    if isinstance(old,dict) and isinstance(new,dict):
        result=[]
        for key in sorted(set(old)|set(new)):
            child=(path+'.' if path else '')+str(key)
            result.extend([child] if key not in old or key not in new else changed_paths(old[key],new[key],child))
        return result
    if isinstance(old,list) and isinstance(new,list):
        if len(old)!=len(new):return [path]
        return [p for i,(a,b) in enumerate(zip(old,new)) for p in changed_paths(a,b,path+'.'+str(i))]
    return [] if old==new else [path]


def owner_settings(root=ROOT):
    path=root/'infra/stack/gateway.json'
    value=intent.read(path) if path.exists() else {'version':1}
    intent.validate(value,'gateway.schema.json')
    forbidden={'api_key','token','password','secret','client_secret','Authorization','authorization','Cookie','cookie','keyHash','htpasswd','backendAuth','apiKey','basicAuth'}
    def check(value):
        if isinstance(value,dict):
            if set(value)&forbidden:raise ValueError('Owner additions cannot embed authentication; keep credentials in file-backed managed connections')
            for child in value.values():check(child)
        elif isinstance(value,list):
            for child in value:check(child)
    check(value)
    if set(value.get('gateways',{}))&{'projects','viewer'}:raise ValueError('Owner gateway additions cannot replace managed project/UI listeners')
    for route in value.get('routes',[]):
        if not route.get('name') or route['name'] in ('health','not-found','viewer','viewer-not-found'):
            raise ValueError('Owner route needs a non-managed name')
        if not route.get('gateways') or set(route['gateways'])-set(value.get('gateways',{})):
            raise ValueError('Owner routes must select their separately declared owner gateways')
    return value


def overlay(base,owner):
    result=copy.deepcopy(base)
    result['config'].update(owner.get('config',{}))
    for name,cfg in owner.get('gateways',{}).items():
        if name in result['gateways']:raise ValueError('Owner gateway name collides with generated gateway')
        result['gateways'][name]=cfg
    names={r['name'] for r in result['routes']}
    for route in owner.get('routes',[]):
        if route['name'] in names:raise ValueError('Owner route name collides with generated project route')
        result['routes'].append(copy.deepcopy(route));names.add(route['name'])
    return result


def prepare(project,root=ROOT,generate=False):
    project=project.resolve();cfg=intent.project_config(project)
    reg,index=intent.registry(root,project)
    binding=intent.binding_document(root,reg)
    resolved=gateway.resolve(reg,binding,root) if reg['projects'] else {}
    hashes={};missing=[]
    for slug,value in reg['projects'].items():
        for caller in value['harnesses']:
            ref=f'.secrets/agentgateway/projects/{slug}/{caller}-token'
            path=intent.credential(root,ref)
            if generate:hashes[(slug,caller)]=gateway.private_key(path)
            elif path.exists():
                value=path.read_text().strip()
                if not re.fullmatch(r'[0-9a-f]{64}',value):raise ValueError('Existing project token format is invalid; preserved')
                hashes[(slug,caller)]=hashlib.sha256(value.encode()).hexdigest()
            else:
                missing.append(ref);hashes[(slug,caller)]=hashlib.sha256(('pending:'+slug+'/'+caller).encode()).hexdigest()
    ui=intent.read(root/'infra/agentgateway/projects/ui.json')
    gateway.validate_document(ui,'ui.schema.json')
    if generate:
        if root!=ROOT:raise ValueError('Runtime credential generation is only supported in the actual stack repository')
        gateway.ui_login()
    desired=gateway.gateway_config(resolved,hashes,root,ui=ui['enabled'],writable=ui['mode']=='read-write')
    desired=overlay(desired,owner_settings(root))
    entries=resolved.get(cfg['project'],{})
    pending={tool:gateway.blockers(entry,root) for tool,entry in entries.items() if entry['enabled']}
    pending={tool:problems for tool,problems in pending.items() if problems}
    local={'project':cfg['project'],'config':cfg,'bindings':project_state.bindings(project),
           'connections':{t:{k:v for k,v in e.items() if k!='binding'} for t,e in entries.items()},
           'direct_boundaries':{t:intent.direct_fingerprint(o,root) for t,o in intent.selections(cfg,root).items() if not o.get('connection')}}
    for entry in entries.values():
        # Scope identity is stable, but updated qualification evidence also changes local launch readiness.
        local['connections'][entry['tool']]['binding']=entry['binding']
    current=runtime_config(root)
    state_path=root/'infra/stack/state/reconcile.json'
    state=intent.read(state_path) if state_path.exists() else {}
    live_hash=digest(current) if current is not None else None
    expected=state.get('runtime_hash')
    drift=current is not None and ((expected is not None and live_hash!=expected) or (expected is None and current!=desired))
    artifact=project/project_state.RELATIVE
    existing=project_state.read(project)['launch']
    return {'config':cfg,'registry':reg,'index':index,'desired':desired,'current':current,'state':state,
            'drift':drift,'missing_credentials':missing,'pending':pending,
            'local_hash':digest(local),'local_change':existing.get('intent_fingerprint')!=digest(local),
            'runtime_change':current!=desired,'changes':changed_paths(current or {},desired),
            'artifact':artifact,'entries':entries}


def plan(project,root=ROOT):
    p=prepare(project,root)
    return {'project':p['config']['project'],'reconciliation':{
        'gateway_change':p['runtime_change'],'project_launch_change':p['local_change'],
        'owner_ui_drift':p['drift'],'changed_fields':p['changes'],
        'missing_credential_files':p['missing_credentials'],'pending_connections':p['pending'],
        'ready':not p['pending'] and not p['missing_credentials'],
        'note':'Read-only plan. Apply preserves unrelated projects; pending providers remain closed.'},
        'remote_calls':0,'services_started':0}


@contextmanager
def lock(root):
    directory=root/'infra/stack/state';directory.mkdir(mode=0o700,exist_ok=True)
    os.chmod(directory,0o700)
    with (directory/'reconcile.lock').open('a') as handle:
        os.chmod(handle.name,0o600)
        fcntl.flock(handle,fcntl.LOCK_EX)
        yield


def recreate(root=ROOT):
    # Existing macOS engine only; neither install nor pull. Resolve current cwd on the Mac.
    command=['macctl','run','docker','compose','-p','mstack','--project-directory','.',
             '-f','infra/agentgateway/compose.yaml','-f','infra/agentgateway/projects/compose.yaml',
             'up','-d','--no-deps','--pull','never','--force-recreate','agentgateway']
    inspected=subprocess.run(['macctl','run','docker','inspect','mcp-stack-agentgateway-1',
        '--format','{{index .Config.Labels "com.docker.compose.project"}}/{{index .Config.Labels "com.docker.compose.service"}}'],cwd=root,capture_output=True,text=True)
    if inspected.returncode or inspected.stdout.strip()!='mstack/agentgateway':
        raise RuntimeError('Existing mcp-stack agentgateway is missing; stack apply does not install services')
    result=subprocess.run(command,cwd=root,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('Targeted agentgateway recreation failed; no other services were targeted')
    expected=digest(runtime_config(root))
    checked=subprocess.run(['macctl','run','python3','integrations/stack/verify_runtime.py',expected],cwd=root,capture_output=True,text=True)
    if checked.returncode:raise RuntimeError('Gateway runtime verification failed after recreation')


def launch_artifact(project,p,root):
    cfg=p['config'];slug=cfg['project'];servers={};credentials={}
    if p['entries']:
        url='http://host.orb.internal:58080/mcp/projects/'+slug
        if 'codex' in cfg.get('harnesses',['codex']):
            allowed=[tool+'_'+name for tool,entry in p['entries'].items() if entry['enabled'] and not gateway.blockers(entry,root) for name in entry['binding'].get('tools',[])]
            servers['project_gateway']={'url':url,'bearer_token_env_var':'STACK_GATEWAY_TOKEN','enabled':True,'enabled_tools':allowed}
            credentials['STACK_GATEWAY_TOKEN']=f'.secrets/agentgateway/projects/{slug}/codex-token'
    return {'version':1,'project':slug,'intent_fingerprint':p['local_hash'],
            'harnesses':cfg.get('harnesses',['codex']),'codex':{'mcp_servers':servers,'credential_files':credentials},
            'claude':{'status':'connection manifest only; Desktop registration is not performed',
                      'url':'http://127.0.0.1:58080/mcp/projects/'+slug if p['entries'] else None,
                      'credential_file':f'.secrets/agentgateway/projects/{slug}/claude-token' if p['entries'] and 'claude' in cfg.get('harnesses',['codex']) else None},
            'pending_connections':p['pending'],'global_config_changed':False}


def apply(project,root=ROOT,drift='stop',restart=recreate):
    with lock(root):
        p=prepare(project,root)
        if p['drift'] and drift!='restore':
            raise ValueError('Owner UI drift detected. Run stack adopt for non-project UI additions, or stack apply --drift restore to restore reviewed config. See stack plan.')
        if p['missing_credentials']:
            p=prepare(project,root,generate=True)
        else:
            # Reuse keys; regenerate only the hashed UI login file when requested settings changed.
            if root==ROOT:gateway.ui_login()
        current=p['current'];desired=p['desired']
        changed=current!=desired
        runtime=root/'infra/agentgateway/state/projects/runtime/config.yaml'
        candidate=root/'infra/agentgateway/state/projects/config.json'
        if changed:
            if runtime_config(root)!=current:raise ValueError('Owner runtime changed during apply; review a fresh stack plan')
            atomic(candidate,desired,0o644)
            gateway.apply_candidate(candidate,runtime)
            try:restart(root)
            except Exception:
                if current is not None:
                    atomic(candidate,current,0o644);gateway.apply_candidate(candidate,runtime)
                    try:restart(root)
                    except Exception:raise RuntimeError('Gateway apply and rollback restart failed; previous config file restored. Inspect only agentgateway.')
                raise RuntimeError('Gateway apply failed; previous configuration restored')
        # Compatibility snapshot is derived, never a second source of project strategy.
        atomic(root/'infra/agentgateway/projects.json',p['registry'],0o644)
        atomic(root/'infra/stack/project-index.json',p['index'],0o644)
        artifact=launch_artifact(project,p,root)
        if p['local_change']:
            with project_state.edit(project) as state:state['launch']=artifact
        live=runtime_config(root)
        state={'version':1,'runtime_hash':digest(live),'desired_hash':digest(desired)}
        state_path=root/'infra/stack/state/reconcile.json'
        if p['state']!=state:atomic(state_path,state)
        return {'project':p['config']['project'],'applied':True,'gateway_changed':changed,
                'project_launch_changed':p['local_change'],'ready':not p['pending'],
                'pending_connections':p['pending'],'harness_settings':str(p['artifact']),
                'services_recreated':['agentgateway'] if changed else [],'global_config_changed':False,
                'provider_logins':0,'model_calls':0}


def adopt(project,root=ROOT):
    """Adopt owner logging and separate non-project listeners/routes into intent."""
    with lock(root):
        p=prepare(project,root);live=p['current']
        if live is None:raise ValueError('No active owner configuration to adopt')
        base=copy.deepcopy(p['desired'])
        prior=owner_settings(root)
        for key in prior.get('gateways',{}):base['gateways'].pop(key,None)
        old_names={r['name'] for r in prior.get('routes',[])}
        base['routes']=[r for r in base['routes'] if r['name'] not in old_names]
        base['config']['logging']=gateway.gateway_config({}, {}, ui=True)['config']['logging']
        adopted={'version':1,'config':{'logging':live['config'].get('logging',{})},
                 'gateways':{k:v for k,v in live['gateways'].items() if k not in base['gateways']},
                 'routes':[r for r in live['routes'] if r.get('name') not in {r['name'] for r in base['routes']}]}
        # Managed auth/project scopes stay config-derived. They cannot be inferred from arbitrary UI backends.
        combined=overlay(base,adopted)
        if combined!=live:raise ValueError('UI changed managed project/auth settings. Express those changes in project config and qualify changed scopes; use --drift restore after reviewing the plan.')
        path=root/'infra/stack/gateway.json'
        previous=path.read_bytes() if path.exists() else None
        atomic(path,adopted,0o644)
        try:owner_settings(root)
        except Exception:
            if previous is None:path.unlink()
            else:path.write_bytes(previous)
            raise
        atomic(root/'infra/stack/state/reconcile.json',{'version':1,'runtime_hash':digest(live),'desired_hash':digest(live)})
        return {'adopted':True,'config_file':str(path),'services_recreated':[],'provider_scopes_changed':False}
