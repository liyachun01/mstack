"""Explicit tenant registration and shared-container lifecycle; never auto-index."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'stack'))
import project_state
import tempfile

from registry import authenticate, tenant_file, SLUG

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'infra/services/state'
CONTAINERS = {'graphify': 'mstack-graphify', 'anytype': 'mstack-anytype-mcp', 'headroom': 'mstack-headroom'}
IMAGES = {'graphify': 'sha256:2474b94caadd0aba2d3a27aa7de2f97a3692ea2a77dca9a0c061b940492b68e9',
          'headroom': 'sha256:4dd47ac9644868cefb4921ce67bb5e6d882da44470c3acfbb721fe0fd54314d9',
          'anytype': 'sha256:bfd63423ea17c48d6986cf8218394e4daa44d3df6fbd0c78c04e04d09d82c146'}


def write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def save(path, value):
    write(path, (json.dumps(value, indent=2) + '\n').encode())


@contextmanager
def locked(state):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / '.registration.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def register(project, tool, graph=None, state=STATE):
    project = project.resolve()
    intent = json.loads((project / '.mstack/stack.json').read_text())
    slug = intent['project']
    if not SLUG.fullmatch(slug) or '{{mstack:CLIENT_REPO}}' in project.parts:
        raise ValueError('Invalid or protected project')
    payload = {}
    extra = {}
    if tool == 'graphify':
        if graph is None or graph.is_symlink() or not graph.is_file() or graph.stat().st_size > 64 * 1024 * 1024:
            raise ValueError('Supply an existing approved graph JSON, at most 64 MiB; no automatic indexing')
        content = graph.read_bytes()
        parsed = json.loads(content)
        if not isinstance(parsed, dict) or not isinstance(parsed.get('nodes'), list):
            raise ValueError('Expected a Graphify graph')
        payload['graph.json'] = content
        extra['index_sha256'] = hashlib.sha256(content).hexdigest()
        extra['index_source'] = str(graph.resolve())
    elif tool == 'headroom':
        payload['tenant.json'] = (json.dumps({'version': 1, 'tenant': slug}) + '\n').encode()
        extra['cache'] = 'separate native SQLite cache; MCP originals expire after 3600 seconds'
    elif tool == 'anytype':
        binding = project_state.anytype(project)
        key = project_state.credential(project,binding['credential_file'],exists=True)
        schema = project / '.mstack/anytype/openapi.json'
        if schema.is_symlink(): raise ValueError('Project schema must be a regular file')
        payload = {'anytype_api_key': key.read_bytes(), 'openapi.json': schema.read_bytes()}
        extra['space_id'] = binding['space_id']
    else:
        raise ValueError('Unsupported shared tool')
    with locked(state):
        regpath = state / tool / 'registry.json'
        registry = json.loads(regpath.read_text()) if regpath.exists() else {'version': 1, 'tenants': {}}
        config = project_state.tenants(project)
        if config['project'] != slug: raise ValueError('Tenant configuration belongs to another project')
        target = state / tool / 'tenants' / slug
        ref = '.mstack/secrets/mstack-' + tool + '-token'
        if slug in registry['tenants'] or tool in config['tools'] or target.exists() or (project / ref).exists():
            raise ValueError('Tenant already exists or has partial state; preserve it for reconciliation')
        if tool == 'anytype' and any(t.get('space_id') == extra['space_id'] for t in registry['tenants'].values()):
            raise ValueError('Anytype channel is already bound to another tenant')
        project_state.ignored(project)
        token = secrets.token_hex(32)
        for name, content in payload.items(): write(target / name, content)
        write(project / ref, (token + '\n').encode())
        registry['tenants'][slug] = {'enabled': True, 'project_root': str(project),
                                    'token_sha256': hashlib.sha256(token.encode()).hexdigest(), **extra}
        save(regpath, registry)
        config['tools'][tool] = {'tenant': slug, 'container': CONTAINERS[tool], 'credential_file': ref}
        with project_state.edit(project) as generated:generated['tenants']=config['tools']
    return {'project': slug, 'tool': tool, 'container': CONTAINERS[tool], 'status': 'registered; live qualification required',
            'indexing': False, 'services_started': False}


def inspect_binding(project, tool, state=STATE):
    cfg = project_state.tenants(project)
    slug = json.loads((project / '.mstack/stack.json').read_text())['project']
    binding = cfg['tools'][tool]
    if cfg['project'] != slug or binding['tenant'] != slug or binding['container'] != CONTAINERS[tool]:
        raise ValueError('Shared tenant binding mismatch')
    key = project_state.credential(project,binding['credential_file'],exists=True)
    registry = json.loads((state / tool / 'registry.json').read_text())
    _, entry = authenticate(registry, {'tenant': slug, 'token': key.read_text().strip()})
    if entry['project_root'] != str(project.resolve()):
        raise ValueError('Tenant is registered to another project directory')
    if tool == 'graphify':
        graph = tenant_file(state / tool, slug, 'graph.json')
        if hashlib.sha256(graph.read_bytes()).hexdigest() != entry['index_sha256']:
            raise ValueError('Registered graph changed; explicit requalification required')
    elif tool == 'headroom':
        marker = json.loads(tenant_file(state / tool, slug, 'tenant.json').read_text())
        if marker != {'version': 1, 'tenant': slug}:
            raise ValueError('Headroom tenant marker differs from project intent')
    else:
        stored=tenant_file(state / tool, slug, 'anytype_api_key')
        selected=project_state.anytype(project)
        credential=project_state.credential(project,selected['credential_file'],exists=True)
        if stored.read_bytes()!=credential.read_bytes():
            raise ValueError('Registered Anytype credential differs; reconcile explicitly')
        expected = selected['space_id']
        if entry['space_id'] != expected:
            raise ValueError('Registered Anytype channel differs from project intent')
    return {'tenant': slug, 'container': binding['container']}


def service(action, tool=None):
    results = {}
    for name in ([tool] if tool else CONTAINERS):
        container = CONTAINERS[name]
        found = subprocess.run(['macctl', 'run', 'docker', 'inspect', container], capture_output=True, text=True)
        missing = any(message in found.stderr.lower() for message in ('no such object', 'no such container'))
        if found.returncode and not missing:
            raise ValueError('Shared service inspection unavailable: ' + name)
        row = json.loads(found.stdout)[0] if found.returncode == 0 else None
        if row and (row['Image'] != IMAGES[name] or (row['Config'].get('Labels') or {}).get('io.mstack.runtime') != 'shared-tenants'):
            raise ValueError('Unexpected shared service identity: ' + name)
        if action == 'status':
            results[name] = {'container': container, 'status': row['State']['Status'] if row else 'absent'}
        elif action == 'start':
            if row:
                subprocess.run(['macctl', 'run', 'docker', 'start', row['Id']], check=True, stdout=subprocess.DEVNULL)
            else:
                service_name = 'anytype-mcp' if name == 'anytype' else name
                subprocess.run(['macctl', 'run', 'docker', 'compose', '-f', str(ROOT / 'infra/services/compose.yaml'),
                                'up', '-d', '--no-deps', '--no-build', '--pull', 'never', service_name], check=True)
            results[name] = {'container': container, 'action': 'start'}
        elif action == 'stop':
            if row: subprocess.run(['macctl', 'run', 'docker', 'stop', row['Id']], check=True, stdout=subprocess.DEVNULL)
            results[name] = {'container': container, 'action': 'stop; all tenants affected; data retained'}
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    tenant = sub.add_parser('tenant'); commands = tenant.add_subparsers(dest='action', required=True)
    add = commands.add_parser('add'); add.add_argument('--project', type=Path, required=True)
    add.add_argument('--tool', choices=CONTAINERS, required=True); add.add_argument('--graph', type=Path)
    commands.add_parser('list')
    services = sub.add_parser('services'); lifecycle = services.add_subparsers(dest='action', required=True)
    lifecycle.add_parser('status')
    for action in ['start', 'stop']:
        lifecycle.add_parser(action).add_argument('tool', choices=CONTAINERS)
    args = parser.parse_args(argv)
    try:
        if args.command == 'services': result = service(args.action, getattr(args, 'tool', None))
        elif args.action == 'add': result = register(args.project, args.tool, args.graph)
        else:
            result = {}
            for tool in CONTAINERS:
                file = STATE / tool / 'registry.json'
                registry = json.loads(file.read_text()) if file.exists() else {'tenants': {}}
                result[tool] = {slug: {'enabled': entry['enabled'], 'project_root': entry['project_root']}
                                for slug, entry in registry['tenants'].items()}
        print(json.dumps(result, indent=2)); return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError):
        print('mstack: tenant/service operation failed; existing state preserved for inspection', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
