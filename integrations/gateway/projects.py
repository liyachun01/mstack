"""Render authenticated project routes. Blank/unqualified upstreams stay closed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
from urllib.parse import urlparse
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT/'infra/agentgateway/projects.json'
BINDINGS = ROOT/'infra/agentgateway/projects.bindings.json'
TOOLS = {'slack', 'linear', 'figma', 'notion', 'anytype'}
CALLERS = ('codex', 'claude')


def validate_document(value, schema_name):
    schema = read(ROOT/'integrations/gateway/schemas'/schema_name)
    Draft202012Validator.check_schema(schema)
    error = best_match(Draft202012Validator(schema).iter_errors(value))
    if error:
        location = '.'.join(str(k) for k in error.absolute_path) or '<root>'
        # Never echo an invalid value: it could be an accidentally pasted token.
        raise ValueError(f'{schema_name}: {location}: invalid field ({error.validator})')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def resolve(registry, bindings, root=ROOT):
    validate_document(registry, 'projects.schema.json')
    validate_document(bindings, 'bindings.schema.json')
    if registry.get('version') != 1 or bindings.get('version') != 1:
        raise ValueError('Expected registry/bindings version 1')
    for project, tools in bindings['projects'].items():
        if project not in registry['projects'] or set(tools)-set(registry['projects'][project]['tools']):
            raise ValueError('Binding references an unknown project/tool')
    result = {}
    anytype_spaces = set()
    for project, cfg in registry['projects'].items():
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', project):
            raise ValueError('Invalid project slug')
        result[project] = {}
        for tool, selection in cfg['tools'].items():
            if tool not in TOOLS:
                raise ValueError('Unsupported connection tool')
            conn = registry['connections'][selection['connection']]
            if conn['tool'] != tool:
                raise ValueError('Connection tool does not match selection')
            space = selection.get('space') or conn['space']
            if tool == 'anytype' and selection.get('enabled', True) and space.get('space_id'):
                if space['space_id'] in anytype_spaces:
                    raise ValueError('Anytype Space shared by multiple enabled projects; use separate project Spaces')
                anytype_spaces.add(space['space_id'])
            identity = {'project': project, 'tool': tool, 'connection': selection['connection'],
                        'input': conn['input'], 'space': space, 'mcp_url': conn['mcp_url'],
                        'access': selection.get('access', 'read-only')}
            credential=conn['input'].get('credential_file','')
            if credential and (root/credential).is_file():
                identity['credential_fingerprint']=hashlib.sha256((root/credential).read_bytes()).hexdigest()
            binding = bindings.get('projects', {}).get(project, {}).get(tool, {})
            result[project][tool] = {**identity, 'scope_fingerprint': digest(identity),
                                    'binding': binding, 'enabled': selection.get('enabled', True),
                                    'purpose': selection.get('purpose', '')}
    return result


def blockers(entry, root=ROOT):
    tool, inp, space, b = entry['tool'], entry['input'], entry['space'], entry['binding']
    problems = []
    if not entry.get('enabled', True):
        problems.append('tool disabled in this project')
    if b.get('access') != entry.get('access', 'read-only'):
        problems.append('requested access mode not qualified')
    required = {'slack': ('workspace_id',), 'linear': ('workspace_id',),
                'figma': ('account',), 'notion': ('workspace_id',), 'anytype': ()}[tool]
    if any(not inp.get(k) for k in required):
        problems.append('account/workspace input blank')
    if not inp.get('credential_file'):
        problems.append('credential binding blank')
    elif not (root/inp['credential_file']).is_file():
        problems.append('credential file missing')
    scope_ok = {'slack': bool(space.get('channel_ids')),
                'linear': bool(space.get('project_ids')),
                'figma': bool(space.get('file_keys')),
                'notion': bool(space.get('page_ids') or space.get('data_source_ids')),
                'anytype': bool(space.get('space_id') and space.get('docs_collection_id')
                                and space.get('tasks_collection_id'))}[tool]
    if not scope_ok:
        problems.append('destination space blank')
    if b.get('status') != 'qualified':
        problems.append('live scope qualification pending')
    if b.get('scope_fingerprint') != entry['scope_fingerprint']:
        problems.append('binding does not match current scope')
    if b.get('scope_enforcement') not in ('upstream-credential', 'scoped-adapter'):
        problems.append('upstream resource restriction not qualified')
    url = urlparse(b.get('mcp_url', ''))
    if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
        problems.append('qualified MCP endpoint missing/invalid')
    names = b.get('tools', [])
    if not names or any(not re.fullmatch(r'[A-Za-z0-9_-]+', n) for n in names):
        problems.append('qualified tool allowlist missing/invalid')
    evidence = b.get('evidence_file', '')
    if not evidence or not (root/evidence).is_file():
        problems.append('scope evidence file missing')
    else:
        proof = read(root/evidence)
        if any(proof.get(k) != entry[k] for k in ('project', 'tool', 'scope_fingerprint')) or not all(
                proof.get(k) is True for k in ('passed', 'allowed_read', 'out_of_scope_denied', 'no_unauthorized_dispatch')):
            problems.append('scope evidence incomplete/stale')
    return problems


def gateway_config(resolved, hashes, root=ROOT, ui=None, writable=False):
    config = {'config': {'adminAddr':'off', 'statsAddr':'off', 'readinessAddr':'off',
                         'enableIpv6':False, 'workerThreads':1, 'storage':{'mode':'readOnly'},
                         'logging':{'level':'warn', 'filter':'false'}},
              'gateways': {'projects': {'port':4000, 'apiKey':{'mode':'strict', 'keys':[
                  {'keyHash':'sha256:'+value, 'metadata':{'project':p, 'caller':c}}
                  for (p,c),value in hashes.items()]}}}, 'routes': []}
    routes = config['routes']
    routes.append({'name':'health', 'gateways':['projects'],
                   'matches':[{'path':{'exact':'/healthz'}}],
                   'policies':{'directResponse':{'status':200}}})
    for project, tools in resolved.items():
        targets, rules = [], []
        for tool, entry in tools.items():
            if blockers(entry, root):
                continue
            binding = entry['binding']
            target = {'name':tool, 'mcp':{'host':binding['mcp_url']}}
            # An adapter must hold its provider credential itself. For a natively
            # resource-restricted upstream, mount a private credential explicitly.
            if binding.get('backend_key_mount'):
                mount = binding['backend_key_mount']
                if not re.fullmatch(r'/run/secrets/[a-z0-9-]+', mount):
                    raise ValueError('Invalid backend key mount')
                target['policies'] = {'backendAuth':{'key':{'value':{'file':mount},
                    'location':{'header':{'name':'authorization','prefix':'Bearer '}}}}}
            elif binding['scope_enforcement'] == 'upstream-credential':
                raise ValueError('Resource-restricted upstream needs its private backend key mount')
            targets.append(target)
            rules.append('mcp.tool.target == '+json.dumps(tool)+' && mcp.tool.name in '+json.dumps(binding['tools']))
        policy = {'authorization':{'rules':['apiKey.project == '+json.dumps(project)]}}
        route = {'name':project, 'gateways':['projects'],
                 'matches':[{'path':{'exact':'/mcp/projects/'+project}}], 'policies':policy}
        if targets:
            policy['mcpAuthorization'] = {'rules': rules}
            route['backends'] = [{'mcp':{'targets':targets, 'statefulMode':'stateful',
                               'prefixMode':'always', 'failureMode':'failClosed', 'dnsRebindingProtection':True}}]
        else:
            policy['directResponse'] = {'status':503, 'body':'Project connections not configured'}
        routes.append(route)
    routes.append({'name':'not-found', 'gateways':['projects'],
                   'policies':{'directResponse':{'status':404}}})
    if ui:
        config['config']['storage']['mode'] = 'file' if writable else 'readOnly'
        config['gateways']['viewer'] = {'port':4001, 'basicAuth':{
            'mode':'strict', 'realm':'mcp-stack owner',
            'htpasswd':{'file':'/config/ui.htpasswd'}}}
        routes.extend([
            {'name':'viewer', 'gateways':['viewer'], 'matches':[
                {'path':{'exact':'/'}}, {'path':{'pathPrefix':'/ui'}},
                {'path':{'pathPrefix':'/api'}}], 'backends':[{'internal':'forward'}]},
            {'name':'viewer-not-found','gateways':['viewer'],
             'policies':{'directResponse':{'status':404}}}])
    return config


def apply_candidate(candidate, runtime):
    """Explicit local apply; render by itself never overwrites existing UI edits."""
    runtime.parent.mkdir(mode=0o770, exist_ok=True)
    os.chmod(runtime.parent,0o770)
    os.chown(runtime.parent,-1,501)
    if runtime.exists():
        old=runtime.read_bytes()
        backup=runtime.parent/('config.before-'+hashlib.sha256(old).hexdigest()+'.yaml')
        if not backup.exists():
            backup.write_bytes(old);os.chmod(backup,0o600)
    import tempfile
    fd,name=tempfile.mkstemp(prefix='.config-',dir=runtime.parent)
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(candidate.read_bytes());handle.flush();os.fsync(handle.fileno())
        os.chown(name,-1,501);os.chmod(name,0o660)
        os.replace(name,runtime)
    finally:
        if os.path.exists(name):os.unlink(name)


def seed_runtime(candidate, runtime):
    if runtime.exists():
        return False
    apply_candidate(candidate, runtime)
    return True

def ui_login():
    settings = read(ROOT/'infra/agentgateway/projects/ui.json')
    validate_document(settings, 'ui.schema.json')
    if not settings['enabled']:
        return None
    import bcrypt
    path = ROOT/settings['password_file']
    private_key(path)
    password = path.read_text().strip().encode()
    state = ROOT/'infra/agentgateway/state/projects'
    state.mkdir(mode=0o700, exist_ok=True)
    cache = state/'ui-htpasswd'
    prefix = settings['username']+':'
    if cache.exists():
        prior = cache.read_text().strip()
        if prior.startswith(prefix) and bcrypt.checkpw(password, prior.split(':',1)[1].encode()):
            if cache.stat().st_mode&0o777!=0o644:os.chmod(cache,0o644)
            return prior+'\n'
    entry = prefix+bcrypt.hashpw(password,bcrypt.gensalt(rounds=12)).decode()+'\n'
    cache.write_text(entry); os.chmod(cache,0o644)
    return entry


def private_key(path):
    if '..' in path.parts or not path.parent.resolve().is_relative_to((ROOT/'.secrets').resolve()):
        raise ValueError('Credential must stay under this repository private secrets directory')
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Project key must be a private regular file')
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(path.parent, 0o700)
    if not path.exists():
        fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_hex(32)+'\n')
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError('Project key must be a private regular file')
    value = path.read_text().strip()
    if not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('Invalid project key format; existing key preserved')
    return hashlib.sha256(value.encode()).hexdigest()


def load_registry():
    if (ROOT/'infra/stack/connections.json').exists():
        sys.path.insert(0,str(ROOT/'integrations'))
        from stack.config import registry
        return registry(ROOT)[0]
    return read(REGISTRY)

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['validate', 'plan', 'render', 'apply'])
    p.add_argument('--project', help='Limit plan output to one slug; render preserves all projects')
    args = p.parse_args(argv)
    registry = load_registry()
    if (ROOT/'infra/stack/connections.json').exists():
        from stack.config import binding_document
        bindings=binding_document(ROOT,registry)
    else:
        bindings=read(BINDINGS)
    resolved = resolve(registry,bindings) if registry['projects'] else {}
    validate_document(read(ROOT/'infra/agentgateway/projects/ui.json'), 'ui.schema.json')
    if args.project and args.action != 'plan':
        raise ValueError('Use render without --project to preserve simultaneous routes')
    if args.project:
        if args.project not in resolved:
            raise ValueError('Unknown project slug')
        resolved = {args.project: resolved[args.project]}
    if args.action == 'validate':
        print(json.dumps({'valid':True, 'projects':list(resolved), 'remote_calls':0,
                          'note':'Schema and references valid; live qualification remains separate'}))
        return 0
    if args.action == 'plan':
        print(json.dumps({'projects':{project:{tool:{
            'connection':e['connection'], 'space':e['space'],
            'enabled':e['enabled'], 'access':e['access'], 'purpose':e['purpose'],
            'scope_fingerprint':e['scope_fingerprint'], 'ready':not blockers(e),
            'blockers':blockers(e)} for tool,e in tools.items()}
            for project,tools in resolved.items()}, 'remote_calls':0}, indent=2))
        return 0
    state = ROOT/'infra/agentgateway/state/projects'
    runtime = state/'runtime/config.yaml'
    if args.action == 'apply':
        apply_candidate(state/'config.json',runtime)
        print(json.dumps({'applied':str(runtime),'services_started':0,
                          'note':'Owner runtime updated from last rendered candidate; prior UI config backed up'}))
        return 0
    hashes = {(project,caller):private_key(ROOT/'.secrets/agentgateway/projects'/project/(caller+'-token'))
              for project in resolved for caller in registry['projects'][project].get('harnesses', CALLERS)}
    settings=read(ROOT/'infra/agentgateway/projects/ui.json')
    config = gateway_config(resolved, hashes, ui=ui_login(), writable=settings['mode']=='read-write')
    state.mkdir(mode=0o700, exist_ok=True)
    os.chmod(state, 0o700)
    path = state/'config.json'
    if path.exists():
        backup = state/('config.before-'+digest(read(path))+'.json')
        if not backup.exists():
            backup.write_bytes(path.read_bytes()); os.chmod(backup, 0o600)
    temp = state/'config.next.json'
    temp.write_text(json.dumps(config, indent=2)+'\n'); os.chmod(temp, 0o644)
    temp.replace(path)
    seeded = seed_runtime(path,runtime)
    print(json.dumps({'rendered':str(path), 'projects':list(resolved),
                      'runtime_seeded':seeded,'existing_ui_edits_preserved':not seeded,
                      'secret_values_printed':False, 'services_started':0,
                      'live_connections':sum(not blockers(e) for ts in resolved.values() for e in ts.values())}, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as error:
        print('connections: '+str(error), file=sys.stderr)
        raise SystemExit(1)
