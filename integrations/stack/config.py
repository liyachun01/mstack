"""Authoritative project intent and shared catalog -> compatibility gateway registry."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

if __package__:
    from . import project_state
else:
    import project_state

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integrations'))
from gateway import projects as gateway

CONNECTORS=set(gateway.TOOLS)
CONTEXT={'graphify','codegraph','ai-memory','basic-memory'}
NON_BOUNDARY=('enabled','purpose','source','server')


def read(path):
    return json.loads(path.read_text())


def validate(value,name):
    schema=read(ROOT/'integrations/stack/schemas'/name)
    Draft202012Validator.check_schema(schema)
    error=best_match(Draft202012Validator(schema).iter_errors(value))
    if error:
        location='.'.join(map(str,error.absolute_path)) or '<root>'
        raise ValueError(f'{name}: {location}: invalid field ({error.validator})')


def endpoint(value):
    if not value:return
    url=urlsplit(value)
    if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Endpoint requires http(s), with no embedded credentials, query or fragment')


def credential(root,ref,exists=False):
    if not ref:return None
    path=root/ref
    if not ref.startswith('.secrets/') or '..' in Path(ref).parts or not path.resolve().is_relative_to((root/'.secrets').resolve()):
        raise ValueError('Credential reference must stay within repository .secrets')
    if path.is_symlink():raise ValueError('Credential reference cannot be a symlink')
    if path.exists() and (not path.is_file() or path.stat().st_mode&0o077):
        raise ValueError('Credential file must be private (0600 or stricter)')
    if exists and not path.is_file():raise ValueError('Referenced private credential is missing')
    return path


def project_config(project):
    cfg=read(project/'.mstack/stack.json')
    if not isinstance(cfg,dict):raise ValueError('Project config must be an object')
    if cfg.get('version')==2:
        allowed={'version','project','preset','model','context','jobs'}
        if set(cfg)-allowed:raise ValueError('Unknown legacy project config field')
        cfg={**cfg,'version':3}
    validate(cfg,'project.schema.json')
    for tool in ('anytype','windmill'):
        options=cfg.get(tool,{})
        endpoint(options.get('api_url',''))
        for key in ('credential_file','mcp_credential_file'):
            project_state.credential(project,options.get(key,''))
    project_state.credential(project,cfg.get('taskboard',{}).get('link',{}).get('credential_file',''))
    return {'version':3,'preset':'daily',**cfg}


def selections(cfg,root=ROOT):
    presets=read(root/'infra/stack/presets.json')['presets']
    preset=presets[cfg['preset']]
    selected={tool:{'enabled':True} for tool in preset['tools']+cfg.get('context',[])}
    if cfg.get('jobs',preset['jobs'])=='windmill':selected['windmill']={'enabled':True}
    for tool,options in cfg.get('tools',{}).items():selected[tool]={**selected.get(tool,{}),**options}
    for options in selected.values():
        endpoint(options.get('url',''))
        credential(root,options.get('credential_file',''))
        for key,value in options.get('input',{}).items():
            if key.endswith('_file'):credential(root,value)
    if selected.get('codex',{}).get('enabled') is False:raise ValueError('Codex harness cannot be disabled; choose its model route')
    for tool,options in selected.items():
        if options.get('source')=='project':
            if tool=='codex':raise ValueError('Codex is the harness, not a project-provided tool')
            if set(options)-set(NON_BOUNDARY):raise ValueError(tool+': a project-provided tool takes no mstack connection, URL or credential')
        elif 'server' in options:raise ValueError(tool+': server names a project-provided MCP server; set source: project')
    return selected


def project_provided(selected):
    """Tools the repository provides itself, mapped to their project MCP server names."""
    return {tool:options.get('server',tool) for tool,options in selected.items()
            if options.get('source')=='project' and options.get('enabled',True)}


def validate_catalog(catalog,root):
    validate(catalog,'connections.schema.json')
    for conn in catalog['connections'].values():
        endpoint(conn['mcp_url']);endpoint(conn['input'].get('api_url',''))
        for key,value in conn['input'].items():
            if key.endswith('_file'):credential(root,value)


def connection_selection(tool,options,catalog,root):
    name=options.get('connection')
    if name not in catalog['connections']:raise ValueError('Unknown shared connection reference for '+tool)
    conn=copy.deepcopy(catalog['connections'][name])
    if conn['tool']!=tool:raise ValueError('Connection provider does not match selected tool')
    if 'url' in options:conn['mcp_url']=options['url']
    conn['input'].update(options.get('input',{}))
    for key in ['credential_file','auth_type']:
        if key in options:conn['input'][key]=options[key]
    endpoint(conn['mcp_url']);endpoint(conn['input'].get('api_url',''))
    for key,value in conn['input'].items():
        if key.endswith('_file'):credential(root,value)
    space=options.get('space',{})
    ids={k:options[k] for k in ['space_id','docs_collection_id','tasks_collection_id'] if k in options}
    if ids:
        if space:raise ValueError('Use Anytype space or top-level IDs, not both')
        space={**conn['space'],**ids}
    if conn!=catalog['connections'][name]:
        suffix=hashlib.sha256(json.dumps(conn,sort_keys=True).encode()).hexdigest()[:12]
        name='override-'+tool+'-'+suffix
    selection={'connection':name,'enabled':options.get('enabled',True),'access':options.get('access','read-only'),
               'purpose':options.get('purpose',''),'space':space}
    return name,conn,selection


def load_index(root):
    path=root/'infra/stack/project-index.json'
    value=read(path) if path.exists() else {'version':1,'projects':{}}
    validate(value,'index.schema.json')
    return value


def registry(root=ROOT,extra=None,index=None):
    catalog=read(root/'infra/stack/connections.json');validate_catalog(catalog,root)
    index=copy.deepcopy(index or load_index(root))
    if extra:
        project=extra.resolve();cfg=project_config(project);slug=cfg['project']
        if slug in index['projects'] and (root/index['projects'][slug]).resolve()!=project:
            raise ValueError('Project slug already belongs to a different directory')
        index['projects'][slug]=str(project.relative_to(root)) if project.is_relative_to(root) else str(project)
    result={'$schema':'../../integrations/gateway/schemas/projects.schema.json','version':1,'description':'Generated from project stack.json files and infra/stack/connections.json; do not edit this snapshot.',
            'connections':copy.deepcopy(catalog['connections']),'projects':{}}
    for slug,path in index['projects'].items():
        project=(root/path).resolve()
        if '{{mstack:CLIENT_REPO}}' in project.parts:raise ValueError('Protected {{mstack:CLIENT_REPO}} cannot be registered')
        cfg=project_config(project)
        if cfg['project']!=slug:raise ValueError('Indexed config has a different project ID')
        tools={}
        for tool,opts in selections(cfg,root).items():
            if not opts.get('connection'):continue
            if tool not in CONNECTORS:raise ValueError('Named connections currently support Slack/Linear/Figma/Notion/Anytype')
            if opts.get('transport','agentgateway')!='agentgateway':raise ValueError('Named connectors currently use agentgateway; preserve qualified direct tools through bindings')
            name,conn,selection=connection_selection(tool,opts,catalog,root)
            result['connections'][name]=conn;tools[tool]=selection
        if tools:
            result['projects'][slug]={'input':cfg.get('input',{'repo':str(project)}),'harnesses':cfg.get('harnesses',['codex']),
                                      'tool_transport':'agentgateway','tools':tools}
    if result['projects']:gateway.validate_document(result,'projects.schema.json')
    return result,index


def binding_document(root,reg):
    bindings=read(root/'infra/agentgateway/projects.bindings.json')
    # Preserve retired evidence on disk; omitted selections are not gateway targets.
    result=copy.deepcopy(bindings)
    result['projects']={p:{t:v for t,v in tools.items() if t in reg['projects'][p]['tools']}
                        for p,tools in bindings['projects'].items() if p in reg['projects']}
    for p,cfg in reg['projects'].items():
        for t in cfg['tools']:result['projects'].setdefault(p,{}).setdefault(t,{'status':'pending'})
    return result


def resolved_connections(project,root=ROOT):
    reg,_=registry(root,project)
    if not reg['projects']:return {}
    entries=gateway.resolve(reg,binding_document(root,reg),root)
    return entries.get(project_config(project)['project'],{})


def direct_fingerprint(options,root=ROOT):
    boundary={k:v for k,v in options.items() if k not in NON_BOUNDARY}
    if options.get('credential_file'):
        path=credential(root,options['credential_file'])
        if path.exists():boundary['credential_fingerprint']=hashlib.sha256(path.read_bytes()).hexdigest()
    return gateway.digest(boundary)


def direct_server(options,binding):
    server=copy.deepcopy(binding.get('mcp',{}))
    if options.get('url'):
        server.pop('command',None);server.pop('args',None)
        server['url']=options['url'];server['enabled']=True
        if binding.get('tools'):server['enabled_tools']=binding['tools']
    return server
