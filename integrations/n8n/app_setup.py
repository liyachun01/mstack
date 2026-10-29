"""One-shot, separately approved app setup on macOS OrbStack, never Ubuntu Docker.

Prepare takes private baseline/backups before definitions change. Activate checks
that exact approved delta, refuses collisions/reruns, and never starts PG/runners.
Operational artifacts are private; subprocess error text is never printed.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path('/home/developer/workspace/mstack')
IMAGE = 'n8nio/n8n:2.41.6@sha256:87e0bab2c93192e8dd885ff7b0697c22a1bd97489568a8c67cc140fd7dbb342d'
PG_IMAGE = 'pgvector/pgvector:0.8.6-pg18-trixie@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff'
APP = 'mcp-stack-n8n-1'
PG = 'mcp-stack-postgres-1'
NETWORKS = {'mcp-stack-n8n-db', 'mcp-stack-n8n-broker', 'mcp-stack-n8n-local'}
NEW_KEYS = ('n8n_encryption_key', 'n8n_runner_token')
COMPOSE = ['macctl', 'run', 'docker', 'compose', '--project-directory', '.', '-p',
           'mcp-stack', '-f', 'infra/n8n/compose.yaml']


class SetupFailure(RuntimeError):
    """Fixed safe stage label only, not potentially credential-bearing stderr."""


def require(condition, stage):
    if not condition:
        raise SetupFailure(stage)


def private_write(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(data)


def record(path, value):
    private_write(path, json.dumps(value, indent=2) + '\n')


def command(args, stage, logs=None, input=None, timeout=30, accepted=(0,)):
    try:
        result = subprocess.run(args, cwd=ROOT, input=input, text=True,
                                capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as failure:
        if logs is not None:
            # Preserve progress privately, including when Python returns bytes
            # despite text=True. Do not print vendor output or retry the command.
            def decoded(value):
                return value.decode(errors='replace') if isinstance(value, bytes) else (value or '')
            private_write(logs / (stage + '.log'),
                          decoded(failure.stdout) + decoded(failure.stderr))
        raise SetupFailure(stage + '-timeout-or-exec') from None
    except OSError:
        raise SetupFailure(stage + '-timeout-or-exec') from None
    if logs is not None:
        private_write(logs / (stage + '.log'), result.stdout + result.stderr)
    require(result.returncode in accepted, stage)
    return result.stdout


def docker(args, stage, **kwargs):
    return command(['macctl', 'run', 'docker', *args], stage, **kwargs)


def snapshots():
    ids = docker(['ps', '-aq'], 'container-inventory').split()
    template = ('{"id":{{json .Id}},"name":{{json .Name}},"status":{{json .State.Status}},'
                '"started":{{json .State.StartedAt}},"restarts":{{json .RestartCount}},'
                '"image":{{json .Config.Image}},"ports":{{json .NetworkSettings.Ports}},'
                '"networks":{{json .NetworkSettings.Networks}}}')
    rows = docker(['inspect', *ids, '--format', template], 'container-snapshots')
    return {r['name']: r for r in map(json.loads, rows.splitlines())}


def metadata():
    sql = """SELECT json_build_object('name',datname,'owner',pg_get_userbyid(datdba),'acl',datacl)
FROM pg_database ORDER BY datname;
SELECT json_build_object('name',rolname,'super',rolsuper,'createdb',rolcreatedb,
'createrole',rolcreaterole,'login',rolcanlogin,'replication',rolreplication,'bypass',rolbypassrls)
FROM pg_roles ORDER BY rolname;
"""
    return docker(['exec', '-i', PG, 'psql', '-X', '-q', '-U', 'postgres', '-d',
                   'postgres', '-At', '-v', 'ON_ERROR_STOP=1'], 'database-metadata', input=sql)


def file_fingerprint(path):
    return {'mode': path.lstat().st_mode, 'hash': hashlib.sha256(path.read_bytes()).hexdigest()}


def protected_files():
    paths = [ROOT / 'compose.yaml', ROOT / 'infra/mise.toml']
    paths += [p for p in (ROOT / 'infra').rglob('*') if p.is_file()
              and 'state' not in p.parts and p.suffix in ('.yaml', '.yml', '.toml', '.json')
              and p != ROOT / 'infra/postgres/compose.yaml']
    paths += [p for p in (ROOT / '.secrets').iterdir() if p.name not in NEW_KEYS]
    return {str(p): file_fingerprint(p) for p in paths if p.is_file()}


def home_manifest():
    # Reuse the existing inert hash/mode/link helper, never boot DeepSeek.
    sys.path.insert(0, str(ROOT / 'integrations/deepseek'))
    from web_smoke import private_home_manifest
    home = Path('/home/developer/.dsh')
    return {'root_mode': home.stat().st_mode, 'entries': private_home_manifest(home)}


def verify_domain():
    require(Path.cwd().resolve() == ROOT, 'repository-domain')
    require(not any(k in os.environ for k in ('DOCKER_HOST', 'DOCKER_CONTEXT')), 'docker-env-override')
    require(command(['macctl', 'run', 'uname', '-s'], 'macos-domain').strip() == 'Darwin', 'macos-domain')
    require(docker(['context', 'show'], 'docker-context').strip() == 'orbstack', 'docker-context')
    require(docker(['info', '--format', '{{.Name}} {{.OperatingSystem}} {{.Architecture}}'],
                   'docker-engine').strip() == 'orbstack OrbStack aarch64', 'docker-engine')
    require(command(['macctl', 'run', 'pwd'], 'macos-cwd').strip() ==
            '/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack', 'macos-cwd')
    docker(['compose', 'version', '--short'], 'compose-version')
    require(not (ROOT / '.env').exists(), 'unexpected-project-env')


def assert_absent_targets(rows):
    require('/' + APP not in rows, 'app-container-collision')
    names = set(docker(['network', 'ls', '--format', '{{.Name}}'], 'network-inventory').split())
    require(not names.intersection(NETWORKS), 'network-collision')
    volumes = docker(['volume', 'ls', '--format', '{{.Name}}'], 'volume-inventory').split()
    require('mcp-stack-n8n-data' not in volumes, 'volume-collision')
    require(all(not os.path.lexists(ROOT / '.secrets' / name) for name in NEW_KEYS), 'key-collision')
    command(['macctl', 'run', 'sh', '-c',
             'command -v lsof >/dev/null || exit 2; '
             'lsof -tiTCP:5678 -sTCP:LISTEN >/dev/null; r=$?; '
             'if [ "$r" = 1 ]; then exit 0; else exit 3; fi'], 'port-5678-preflight')
    require(not any(binding.get('HostPort') == '5678' for row in rows.values()
                    for bindings in (row['ports'] or {}).values() for binding in (bindings or [])),
            'retained-container-port-collision')


def prepare():
    verify_domain()
    rows = snapshots()
    assert_absent_targets(rows)
    require(rows['/' + PG]['image'] == PG_IMAGE and rows['/' + PG]['status'] == 'running', 'pg-image-state')
    require(docker(['inspect', PG, '--format', '{{.State.Health.Status}}'], 'pg-health').strip() == 'healthy', 'pg-health')
    sql = """SELECT current_setting('server_version_num')::int = 180006
AND pg_get_userbyid((SELECT datdba FROM pg_database WHERE datname='n8n')) = 'n8n'
AND EXISTS (SELECT FROM pg_roles WHERE rolname='n8n' AND rolcanlogin AND NOT rolsuper
AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication AND NOT rolbypassrls)
AND NOT has_database_privilege('n8n','basic_memory','CONNECT')
AND NOT has_database_privilege('basic_memory','n8n','CONNECT');
"""
    require(docker(['exec', '-i', PG, 'psql', '-X', '-q', '-U', 'postgres', '-d',
                    'postgres', '-At', '-v', 'ON_ERROR_STOP=1'], 'pg-login-scope', input=sql).strip() == 't', 'pg-login-scope')
    secret_dir = ROOT / '.secrets'
    require(not secret_dir.is_symlink() and stat.S_IMODE(secret_dir.stat().st_mode) == 0o700, 'secret-directory')
    password = secret_dir / 'n8n_password'
    require(password.is_file() and not password.is_symlink() and
            stat.S_IMODE(password.stat().st_mode) == 0o600 and
            re.fullmatch('[a-f0-9]{64}\\n?', password.read_text()) is not None, 'db-password-private-format')
    proposal = (ROOT / 'docs/N8N-APP-SETUP-PROPOSAL.md').read_text().split('```yaml\n', 1)[1].split('\n```', 1)[0]
    require((ROOT / 'infra/n8n/compose.yaml').read_text().strip() == proposal.strip(), 'approved-compose-contract')
    backup = Path(tempfile.mkdtemp(prefix='n8n-app-before-20261004-', dir=ROOT / 'backups'))
    for source, name in [(ROOT / 'infra/postgres/compose.yaml', 'original-postgres-compose.yaml'),
                         (ROOT / '.gitignore', 'original-gitignore')]:
        private_write(backup / name, source.read_text())
    baseline = {'containers': rows, 'database_metadata': metadata(), 'protected_files': protected_files(),
                'home': home_manifest(), 'compose_hash': file_fingerprint(ROOT / 'infra/n8n/compose.yaml')['hash']}
    record(backup / 'baseline.json', baseline)
    print(json.dumps({'prepared': True, 'backup': str(backup), 'retained_container_count': len(rows)}), flush=True)


def expected_postgres(original):
    old = '    networks:\n      - memory\n'
    require(original.count(old) == 1, 'original-pg-network-contract')
    result = original.replace(old, '    networks:\n      memory: {}\n      n8n_db:\n        aliases: [n8n-postgres]\n')
    return result.replace('networks:\n  memory:\n    name: mcp-stack-memory\n',
                          'networks:\n  memory:\n    name: mcp-stack-memory\n  n8n_db:\n    external: true\n    name: mcp-stack-n8n-db\n')


def compare_containers(before, after):
    require(set(after) == set(before) | {'/' + APP}, 'container-identity-set-changed')
    for name, original in before.items():
        current = copy.deepcopy(after[name])
        if name == '/' + PG and 'mcp-stack-n8n-db' not in original['networks']:
            require(set(current['networks']) == set(original['networks']) | {'mcp-stack-n8n-db'}, 'pg-network-delta')
            require('n8n-postgres' in current['networks']['mcp-stack-n8n-db']['Aliases'], 'pg-database-alias')
            del current['networks']['mcp-stack-n8n-db']
        require(original == current, 'existing-container-changed')


def compare_host_restart(before, after):
    """Accept only the declared external restart and already approved PG attach."""
    require(set(before) == set(after), 'restart-container-set-drift')
    for name, original in before.items():
        current = copy.deepcopy(after[name])
        if name == '/' + PG:
            extra = current['networks'].pop('mcp-stack-n8n-db', None)
            require(extra is not None and 'n8n-postgres' in extra['Aliases'], 'restart-pg-alias')
        if original['status'] == 'running':
            current['started'] = original['started']
            require(set(current['networks']) == set(original['networks']), 'restart-network-set-drift')
            for network, old in original['networks'].items():
                for field in ('NetworkID', 'Aliases', 'DNSNames'):
                    require(current['networks'][network].get(field) == old.get(field), 'restart-network-identity-drift')
                current['networks'][network] = old
        require(current == original, 'restart-unexpected-container-drift')


def pull_once(run):
    """Stream private progress to disk while keeping one bounded pull client."""
    path = run / 'pull-app.log'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as output:
        try:
            with subprocess.Popen(COMPOSE + ['pull', 'n8n'], cwd=ROOT,
                                  stdout=output, stderr=subprocess.STDOUT) as process:
                try:
                    code = process.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    raise SetupFailure('pull-app-timeout-no-retry') from None
        except OSError:
            raise SetupFailure('pull-app-exec-no-retry') from None
    require(code == 0, 'pull-app-failed-no-retry')


def retry_after_host_restart(backup):
    require(backup == ROOT / 'backups/n8n-app-before-20261004-vy_phq7l'
            and not backup.is_symlink(), 'approved-partial-backup-path')
    require((backup / 'activation-attempt.json').is_file(), 'original-attempt-required')
    verify_domain()
    require(json.loads(docker(['info', '--format', '{{json .RegistryConfig.Mirrors}}'],
                              'post-restart-mirrors')) in (None, []), 'host-mirrors-not-cleared')
    original = json.loads((backup / 'baseline.json').read_text())
    rows = snapshots()
    compare_host_restart(original['containers'], rows)
    require(metadata() == original['database_metadata'] and
            protected_files() == original['protected_files'] and home_manifest() == original['home'],
            'retry-protected-baseline-drift')
    require((ROOT / 'infra/postgres/compose.yaml').read_text() ==
            expected_postgres((backup / 'original-postgres-compose.yaml').read_text()), 'retry-pg-definition-drift')
    require((ROOT / '.gitignore').read_text() == (backup / 'original-gitignore').read_text() +
            'infra/n8n/state/\n', 'retry-ignore-drift')
    require(file_fingerprint(ROOT / 'infra/n8n/compose.yaml')['hash'] == original['compose_hash'], 'retry-compose-drift')
    require(docker(['inspect', PG, '--format', '{{.State.Health.Status}}'], 'retry-pg-health').strip() == 'healthy', 'retry-pg-health')
    names = set(docker(['network', 'ls', '--format', '{{.Name}}'], 'retry-networks').split())
    require(names.intersection(NETWORKS) == {'mcp-stack-n8n-db'}, 'retry-network-collision')
    net = json.loads(docker(['network', 'inspect', 'mcp-stack-n8n-db'], 'retry-db-network'))[0]
    require(net['Internal'] and net['Driver'] == 'bridge' and
            net['Labels'].get('com.mcp-stack.owner') == 'n8n' and
            set(net['Containers']) == {rows['/' + PG]['id']}, 'retry-db-network-scope')
    require('mcp-stack-n8n-data' not in docker(['volume', 'ls', '--format', '{{.Name}}'], 'retry-volumes').split(), 'retry-volume-collision')
    require('/' + APP not in rows, 'retry-app-collision')
    command(['macctl', 'run', 'sh', '-c', 'command -v lsof >/dev/null || exit 2; '
             'lsof -tiTCP:5678 -sTCP:LISTEN >/dev/null; r=$?; '
             'if [ "$r" = 1 ]; then exit 0; else exit 3; fi'], 'retry-port-5678')
    require(not any(b.get('HostPort') == '5678' for row in rows.values()
                    for values in (row['ports'] or {}).values() for b in (values or [])), 'retry-retained-port')
    secret_dir = ROOT / '.secrets'
    require(not secret_dir.is_symlink() and stat.S_IMODE(secret_dir.stat().st_mode) == 0o700, 'retry-secret-directory')
    keys = {}
    for name in (*NEW_KEYS, 'n8n_password'):
        path = secret_dir / name
        require(path.is_file() and not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) == 0o600
                and re.fullmatch('[a-f0-9]{64}\\n?', path.read_text()) is not None, 'retry-private-key')
        keys[str(path)] = file_fingerprint(path)
    state_base = ROOT / 'infra/n8n/state'
    require(state_base.is_dir() and not state_base.is_symlink() and
            stat.S_IMODE(state_base.stat().st_mode) == 0o700, 'retry-private-state')
    run = Path(tempfile.mkdtemp(prefix='retry-after-host-restart-', dir=state_base))
    baseline = {**original, 'containers': rows, 'retained_keys': keys,
                'external_change': 'user updated Docker settings and restarted macOS engine'}
    record(run / 'baseline.json', baseline)
    # An exclusive marker makes this particular retry approval single-use.
    record(backup / 'retry-after-host-restart.json', {'private_state': str(run), 'one_shot': True})
    print(json.dumps({'retrying_once': True, 'private_state': str(run), 'retained_container_count': len(rows)}), flush=True)
    command(COMPOSE + ['config', '--quiet'], 'compose-validation', logs=run)
    pull_once(run)
    image = json.loads(docker(['image', 'inspect', IMAGE], 'retry-pinned-image'))[0]
    require(image['Architecture'] == 'arm64' and image['Os'] == 'linux' and
            'n8nio/n8n@' + IMAGE.split('@', 1)[1] in image['RepoDigests'] and
            image['Config']['User'] == 'node' and
            image['Config']['Labels'].get('org.opencontainers.image.version') == '2.41.6', 'retry-image-contract')
    require(snapshots() == rows, 'retry-pre-create-container-drift')
    print('Pinned image verified; creating only the n8n app once, with pull disabled.', flush=True)
    command(COMPOSE + ['up', '-d', '--no-deps', '--pull', 'never', 'n8n'], 'start-app', logs=run, timeout=120)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        status = docker(['inspect', APP, '--format', '{{.State.Status}} {{.RestartCount}} {{.State.Health.Status}}'], 'retry-app-readiness').strip()
        require(status.startswith('running 0 '), 'retry-app-exited-or-restarted')
        if status.endswith(' healthy'):
            break
        time.sleep(2)
    else:
        raise SetupFailure('retry-readiness-timeout')
    result = qualify(baseline, run)
    record(run / 'qualification.json', result)
    print(json.dumps(result | {'private_state': str(run)}), flush=True)


def activate(backup):
    require(backup.parent == ROOT / 'backups' and backup.name.startswith('n8n-app-before-20261004-')
            and not backup.is_symlink(), 'backup-path')
    baseline = json.loads((backup / 'baseline.json').read_text())
    verify_domain()
    require(snapshots() == baseline['containers'] and metadata() == baseline['database_metadata'], 'pre-start-baseline-drift')
    assert_absent_targets(baseline['containers'])
    require(protected_files() == baseline['protected_files'] and home_manifest() == baseline['home'], 'protected-baseline-drift')
    require((ROOT / 'infra/postgres/compose.yaml').read_text() ==
            expected_postgres((backup / 'original-postgres-compose.yaml').read_text()), 'approved-pg-definition-delta')
    require((ROOT / '.gitignore').read_text() == (backup / 'original-gitignore').read_text() +
            'infra/n8n/state/\n', 'approved-ignore-delta')
    require(file_fingerprint(ROOT / 'infra/n8n/compose.yaml')['hash'] == baseline['compose_hash'], 'compose-drift')
    command(['git', 'check-ignore', 'infra/n8n/state/check', '.secrets/n8n_encryption_key'], 'ignore-private-artifacts')
    state_base = ROOT / 'infra/n8n/state'
    state_base.mkdir(mode=0o700, exist_ok=True)
    require(not state_base.is_symlink(), 'state-symlink')
    run = state_base / backup.name.removeprefix('n8n-app-before-')
    run.mkdir(mode=0o700)
    record(backup / 'activation-attempt.json', {'state': str(run), 'one_shot': True})
    print(json.dumps({'activating': True, 'private_state': str(run)}), flush=True)
    for name in NEW_KEYS:
        private_write(ROOT / '.secrets' / name, secrets.token_hex(32))
    command(COMPOSE + ['config', '--quiet'], 'compose-validation', logs=run)
    docker(['network', 'create', '--driver', 'bridge', '--internal', '--label',
            'com.mcp-stack.owner=n8n', 'mcp-stack-n8n-db'], 'create-db-network', logs=run)
    docker(['network', 'connect', '--alias', 'n8n-postgres', 'mcp-stack-n8n-db', PG],
           'attach-pg-network', logs=run)
    print('Pulling only the approved official n8n app image on macOS OrbStack.', flush=True)
    command(COMPOSE + ['pull', 'n8n'], 'pull-app', logs=run, timeout=600)
    command(COMPOSE + ['up', '-d', '--no-deps', 'n8n'], 'start-app', logs=run, timeout=120)
    print('App created once; checking bounded readiness, without restarting it.', flush=True)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        status = docker(['inspect', APP, '--format', '{{.State.Status}} {{.RestartCount}} {{.State.Health.Status}}'], 'app-readiness-state').strip()
        require(status.startswith('running 0 '), 'app-exited-or-restarted')
        if status.endswith(' healthy'):
            break
        time.sleep(2)
    else:
        raise SetupFailure('readiness-timeout')
    evidence = qualify(baseline, run)
    record(run / 'qualification.json', evidence)
    print(json.dumps(evidence), flush=True)


def qualify(baseline, run):
    # Full inspect stays in memory, never serialize Config.Env/credentials.
    app = json.loads(docker(['inspect', APP], 'app-private-inspect'))[0]
    require(app['Config']['Image'] == IMAGE and app['Config']['User'] == 'node', 'app-image-user')
    hc = app['HostConfig']
    require(hc['ReadonlyRootfs'] and not hc['Privileged'] and hc['Memory'] == 1073741824
            and hc['NanoCpus'] == 1000000000 and hc['PidsLimit'] == 256, 'app-security-resource-contract')
    require('ALL' in hc['CapDrop'] and 'no-new-privileges:true' in hc['SecurityOpt'], 'app-capabilities-contract')
    require(app['NetworkSettings']['Ports']['5678/tcp'] == [{'HostIp': '127.0.0.1', 'HostPort': '5678'}]
            and not app['NetworkSettings']['Ports'].get('5679/tcp')
            and set(app['NetworkSettings']['Networks']) == NETWORKS, 'app-network-port-contract')
    persistent_mounts = [m for m in app['Mounts'] if m['Type'] != 'tmpfs']
    if baseline.get('secret_volume'):
        require(len(persistent_mounts) == 2 and all(m['Type'] == 'volume' for m in persistent_mounts)
                and any(m.get('Name') == 'mcp-stack-n8n-data' and m['Destination'] == '/home/node/.n8n' and m['RW']
                        for m in persistent_mounts)
                and any(m.get('Name') == 'mcp-stack-n8n-secrets' and m['Destination'] == '/run/secrets' and not m['RW']
                        for m in persistent_mounts), 'app-secret-volume-contract')
    else:
        require(any(m.get('Name') == 'mcp-stack-n8n-data' and m['Destination'] == '/home/node/.n8n'
                for m in persistent_mounts) and
            {m['Destination'] for m in persistent_mounts} ==
            {'/home/node/.n8n', '/run/secrets/n8n_password', '/run/secrets/n8n_encryption_key',
             '/run/secrets/n8n_runner_token'} and
            all(not m['RW'] for m in persistent_mounts if m['Type'] == 'bind'), 'app-mount-contract')
    env = dict(x.split('=', 1) for x in app['Config']['Env'])
    require(env.get('N8N_RUNNERS_MODE') == 'external' and
            env.get('N8N_AI_ASSISTANT_BASE_URL') == '' and
            all(k not in env for k in ('DB_POSTGRESDB_PASSWORD', 'N8N_ENCRYPTION_KEY', 'N8N_RUNNERS_AUTH_TOKEN')),
            'app-secret-runner-contract')
    images = json.loads(docker(['image', 'inspect', app['Image']], 'app-image-inspect'))[0]
    require('n8nio/n8n@' + IMAGE.split('@', 1)[1] in images['RepoDigests'] and
            images['Config']['Labels'].get('org.opencontainers.image.version') == '2.41.6', 'app-image-digest-version')
    for suffix in ('/healthz/readiness', '/', '/setup'):
        value = command(host_http_arguments('http://127.0.0.1:5678' + suffix),
                        'host-http-' + ('root' if suffix == '/' else suffix.strip('/').replace('/', '-')))
        require(value == '200', 'host-http-response')
    html = command(['macctl', 'run', 'curl', '--noproxy', '*', '--fail', '--silent', '--show-error',
                    '--max-time', '5', 'http://127.0.0.1:5678/'], 'editor-shell-content')
    require('n8n' in html.lower(), 'editor-shell-content')
    assets = re.findall(r'<script[^>]+src="([^"\s]+)"', html)
    entries = [a for a in assets if re.fullmatch(r'(?:/|\./)?assets/index-[\w-]+\.js', a)]
    require(len(entries) == 1, 'editor-entry-asset-path')
    asset_url = 'http://127.0.0.1:5678/' + entries[0].removeprefix('./').lstrip('/')
    asset_http = command(host_http_arguments(asset_url), 'editor-entry-asset-http')
    require(asset_http == '200', 'editor-entry-asset-http')
    script = """const fs=require('fs');const paths=['n8n_password','n8n_encryption_key','n8n_runner_token'];
if(process.getuid()===0)process.exit(1);
const secretsReadable=paths.every(n=>/^[a-f0-9]{64}\\n?$/.test(fs.readFileSync('/run/secrets/'+n,'utf8')));
const mode=fs.statSync('/home/node/.n8n/config').mode&0o777;
if(!secretsReadable||mode!==0o600)process.exit(1);
console.log(JSON.stringify({nonRoot:true,secretsReadable:true,settingsMode:'0600'}));"""
    permissions = json.loads(docker(['exec', APP, 'node', '-e', script], 'app-private-permissions', logs=run))
    count = docker(['exec', PG, 'psql', '-X', '-q', '-U', 'postgres', '-d', 'n8n', '-At', '-c',
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"], 'n8n-migration-table-count').strip()
    require(count.isdigit() and int(count) > 0, 'n8n-migrations-absent')
    compare_containers(baseline['containers'], snapshots())
    require(metadata() == baseline['database_metadata'] and protected_files() == baseline['protected_files']
            and home_manifest() == baseline['home'], 'preservation-drift')
    require(all(file_fingerprint(Path(path)) == fingerprint
                for path, fingerprint in baseline.get('retained_keys', {}).items()), 'retained-key-drift')
    stats = docker(['stats', '--no-stream', '--format', '{{json .Name}} {{json .CPUPerc}} {{json .MemUsage}}',
                    APP, PG], 'app-pg-resource-sample', logs=run)
    return {'qualified': True, 'app': APP, 'version': '2.41.6', 'ui': 'http://127.0.0.1:5678/',
            'host_readiness_root_setup_http': 200, 'editor_entry_asset_http': 200, 'image_digest_verified': True,
            'security_and_volume_verified': True, **permissions,
            'n8n_public_table_count': int(count), 'retained_container_count': len(baseline['containers']),
            'existing_containers_unchanged_from_this_attempt_baseline': True,
            'pg_added_network_already_present_in_retry_baseline': 'mcp-stack-n8n-db' in baseline['containers']['/' + PG]['networks'],
            'existing_db_role_metadata_protected_files_home_unchanged': True,
            'runner_installed': False, 'owner_account_created': False,
            'workflow_or_model_execution': False, 'resource_sample': stats.strip()}


def host_http_arguments(url):
    # macctl rewrites standalone absolute arguments. /dev/null must be interpreted
    # by the macOS shell, not translated to the Ubuntu filesystem mirror.
    require(url.startswith('http://127.0.0.1:5678/'), 'host-http-url-scope')
    return ['macctl', 'run', 'sh', '-c',
            'curl --noproxy "*" --silent --show-error --output /dev/null '
            '--write-out "%{http_code}" --max-time 10 "$1"', 'sh', url]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-app-2.41.6', dest='approved', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--backup-directory', type=Path)
    parser.add_argument('--verify-only', action='store_true', help='Read-only runtime requalification; never pull/start/reconfigure.')
    parser.add_argument('--approved-retry-after-host-restart', action='store_true')
    parser.add_argument('--approved-secret-repair', action='store_true')
    parser.add_argument('--approved-cache-repair', action='store_true')
    args = parser.parse_args()
    require(args.approved, 'explicit-approval-flag-required')
    require(args.prepare != (args.backup_directory is not None), 'choose-prepare-or-activate')
    require(not (args.prepare and args.verify_only), 'prepare-is-not-verification')
    require(not (args.approved_retry_after_host_restart and (args.prepare or args.verify_only)), 'retry-mode-exclusive')
    require(not (args.approved_secret_repair and (args.verify_only or args.approved_retry_after_host_restart)), 'repair-mode-exclusive')
    require(not (args.approved_cache_repair and (args.verify_only or args.approved_retry_after_host_restart or args.approved_secret_repair)), 'cache-mode-exclusive')
    if args.approved_cache_repair:
        sys.path.insert(0, str(ROOT / 'integrations/n8n'))
        import cache_repair
        if args.prepare:
            cache_repair.prepare()
        else:
            cache_repair.activate(args.backup_directory.absolute())
    elif args.approved_secret_repair:
        sys.path.insert(0, str(ROOT / 'integrations/n8n'))
        import secret_repair
        if args.prepare:
            secret_repair.prepare()
        else:
            secret_repair.activate(args.backup_directory.absolute())
    elif args.approved_retry_after_host_restart:
        retry_after_host_restart(args.backup_directory.absolute())
    elif args.prepare:
        prepare()
    elif args.verify_only:
        backup = args.backup_directory.absolute()
        require(backup.parent == ROOT / 'backups' and not backup.is_symlink(), 'backup-path')
        baseline = json.loads((backup / 'baseline.json').read_text())
        verify_domain()
        state_base = ROOT / 'infra/n8n/state'
        require(state_base.is_dir() and not state_base.is_symlink(), 'existing-private-state-required')
        run = Path(tempfile.mkdtemp(prefix='verify-', dir=state_base))
        result = qualify(baseline, run)
        record(run / 'qualification.json', result)
        print(json.dumps(result | {'private_state': str(run)}), flush=True)
    else:
        activate(args.backup_directory.absolute())


if __name__ == '__main__':
    # Keep the repair module's exception/function identity identical to this CLI.
    sys.modules.setdefault('app_setup', sys.modules[__name__])
    try:
        main()
    except SetupFailure as error:
        print(json.dumps({'qualified': False, 'failed_stage': str(error),
                          'automatic_retry_or_cleanup': False}), flush=True)
        sys.exit(1)
    except Exception:
        print(json.dumps({'qualified': False, 'failed_stage': 'unexpected-error-private-details-suppressed',
                          'automatic_retry_or_cleanup': False}), flush=True)
        sys.exit(1)
