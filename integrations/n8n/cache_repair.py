"""Approved single tmpfs addition and n8n-only recreation, without downloads."""
import copy
import json
import stat
import tempfile
import time
from pathlib import Path

import app_setup as setup
import secret_repair as secrets

PREVIOUS = setup.ROOT / 'infra/n8n/state/secret-repair-vzhjpu59'
CACHE_OPTIONS = 'size=64m,uid=1000,gid=1000,mode=0700'


def original_definition():
    return secrets.repaired_definition(secrets.original_definition())


def repaired_definition(original):
    setup.require(original == original_definition(), 'cache-original-contract')
    return original.replace('    tmpfs: ["/tmp:size=128m,mode=1777"]\n',
                            '    tmpfs: ["/tmp:size=128m,mode=1777", "/home/node/.cache:' + CACHE_OPTIONS + '"]\n')


def unchanged(baseline, permit_compose_delta=False):
    rows = setup.snapshots()
    setup.compare_containers(baseline['containers'], rows)
    protected = setup.protected_files()
    expected = copy.deepcopy(baseline['protected_files'])
    if permit_compose_delta:
        expected[str(secrets.COMPOSE_PATH)] = setup.file_fingerprint(secrets.COMPOSE_PATH)
    setup.require(protected == expected and setup.metadata() == baseline['database_metadata']
                  and setup.home_manifest() == baseline['home'], 'cache-preservation-drift')
    secrets.source_keys()
    setup.require(all(setup.file_fingerprint(Path(p)) == h for p, h in baseline['retained_keys'].items()), 'cache-key-drift')
    return rows, protected


def prepare():
    setup.verify_domain()
    previous = json.loads((PREVIOUS / 'baseline.json').read_text())
    rows, protected = unchanged(previous)
    app = json.loads(setup.docker(['inspect', setup.APP], 'cache-failed-app'))[0]
    setup.require(app['Config']['Image'] == setup.IMAGE and app['Config']['User'] == 'node'
                  and app['HostConfig']['ReadonlyRootfs'] and app['RestartCount'] > 0
                  and app['State'].get('Health', {}).get('Status') != 'healthy', 'cache-target-not-failed-app')
    setup.require('/home/node/.cache' not in app['HostConfig']['Tmpfs'] and
                  any(m.get('Name') == secrets.VOLUME and not m['RW'] for m in app['Mounts']), 'cache-original-mounts')
    setup.require(secrets.COMPOSE_PATH.read_text() == original_definition(), 'cache-original-compose')
    setup.require(not any(b.get('HostPort') == '5678' for name, row in rows.items() if name != '/' + setup.APP
                          for bindings in (row['ports'] or {}).values() for b in (bindings or [])), 'cache-other-container-port')
    setup.require(setup.docker(['inspect', setup.PG, '--format', '{{.State.Health.Status}}'], 'cache-pg-health').strip() == 'healthy', 'cache-pg-health')
    backup = Path(tempfile.mkdtemp(prefix='n8n-cache-before-20261004-', dir=setup.ROOT / 'backups'))
    baseline = {**previous, 'old_app_id': app['Id'], 'cache_tmpfs': True, 'protected_files': protected}
    setup.private_write(backup / 'original-compose.yaml', secrets.COMPOSE_PATH.read_text())
    setup.record(backup / 'baseline.json', baseline)
    print(json.dumps({'cache_prepared': True, 'backup': str(backup)}), flush=True)


def activate(backup):
    setup.require(backup.parent == setup.ROOT / 'backups' and
                  backup.name.startswith('n8n-cache-before-20261004-') and not backup.is_symlink(), 'cache-backup-path')
    setup.verify_domain()
    baseline = json.loads((backup / 'baseline.json').read_text())
    rows, protected = unchanged(baseline, permit_compose_delta=True)
    setup.require(rows['/' + setup.APP]['id'] == baseline['old_app_id'], 'cache-app-identity-drift')
    setup.require(secrets.COMPOSE_PATH.read_text() == repaired_definition((backup / 'original-compose.yaml').read_text()), 'cache-approved-compose-delta')
    state = setup.ROOT / 'infra/n8n/state'
    setup.require(state.is_dir() and not state.is_symlink() and stat.S_IMODE(state.stat().st_mode) == 0o700, 'cache-private-state')
    run = Path(tempfile.mkdtemp(prefix='cache-repair-', dir=state))
    setup.record(backup / 'activation-attempt.json', {'private_state': str(run), 'one_shot': True})
    baseline['protected_files'] = protected
    setup.record(run / 'baseline.json', baseline)
    print(json.dumps({'cache_repairing_once': True, 'private_state': str(run)}), flush=True)
    setup.command(setup.COMPOSE + ['config', '--quiet'], 'compose-validation', logs=run)
    setup.docker(['stop', '--time', '30', setup.APP], 'stop-failing-n8n', logs=run, timeout=40)
    setup.command(['macctl', 'run', 'sh', '-c', 'command -v lsof >/dev/null || exit 2; '
                   'lsof -tiTCP:5678 -sTCP:LISTEN >/dev/null; r=$?; '
                   'if [ "$r" = 1 ]; then exit 0; else exit 3; fi'], 'cache-port-free-after-stop')
    setup.command(setup.COMPOSE + ['up', '-d', '--no-deps', '--pull', 'never', '--force-recreate', 'n8n'],
                  'recreate-n8n', logs=run, timeout=120)
    print('Only n8n recreated; checking readiness without retries/restarts.', flush=True)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        status = setup.docker(['inspect', setup.APP, '--format', '{{.State.Status}} {{.RestartCount}} {{.State.Health.Status}}'], 'cache-readiness').strip()
        setup.require(status.startswith('running 0 '), 'cache-app-exited-or-restarted')
        if status.endswith(' healthy'):
            break
        time.sleep(2)
    else:
        raise setup.SetupFailure('cache-readiness-timeout')
    equivalent = json.loads(setup.docker(['exec', '-i', setup.APP, 'node', '-e', secrets.CONTENT_CHECK],
                                        'secret-volume-content-permissions', logs=run,
                                        input=json.dumps(secrets.source_keys())))
    app = json.loads(setup.docker(['inspect', setup.APP], 'cache-runtime-inspect'))[0]
    setup.require(app['HostConfig']['Tmpfs'] == {'/tmp': 'size=128m,mode=1777', '/home/node/.cache': CACHE_OPTIONS}, 'cache-tmpfs-options')
    script = """const fs=require('fs');const d=fs.statSync('/home/node/.cache');
const v=fs.statfsSync('/home/node/.cache');
if(d.uid!==process.getuid()||d.gid!==process.getgid()||(d.mode&0o777)!==0o700||v.type!==0x01021994||v.bsize*v.blocks!==67108864)process.exit(1);
console.log(JSON.stringify({cacheOwner:process.getuid(),cacheMode:'0700',cacheFilesystem:'tmpfs',cacheLimitBytes:v.bsize*v.blocks,cacheUsedBytes:v.bsize*(v.blocks-v.bfree),compiledIndexPresent:fs.existsSync('/home/node/.cache/n8n/public/index.html')}));"""
    cache = json.loads(setup.docker(['exec', setup.APP, 'node', '-e', script], 'cache-volume-stat', logs=run))
    setup.require(cache['compiledIndexPresent'], 'cache-index-absent')
    result = setup.qualify(baseline, run) | equivalent | cache
    setup.record(run / 'qualification.json', result)
    print(json.dumps(result | {'private_state': str(run)}), flush=True)
