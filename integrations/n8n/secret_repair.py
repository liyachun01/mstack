"""Approved n8n-only secret-volume repair; no downloads or host chmod/chown."""
import copy
import json
import re
import stat
import tempfile
import time
from pathlib import Path

import app_setup as setup

VOLUME = 'mcp-stack-n8n-secrets'
INIT = 'mcp-stack-n8n-secret-init'
COMPOSE_PATH = setup.ROOT / 'infra/n8n/compose.yaml'
RETRY = setup.ROOT / 'infra/n8n/state/retry-after-host-restart-i5fht3la'
KEYS = ('n8n_password', *setup.NEW_KEYS)

INITIALIZER = r"""const fs=require('fs');
try {
  if(process.getuid()!==0 || fs.readdirSync('/target').length!==0) throw 0;
  const rows=fs.readFileSync('/etc/passwd','utf8').split('\n');
  const row=rows.find(r=>r.startsWith('node:')).split(':');
  const uid=Number(row[2]),gid=Number(row[3]);
  if(!Number.isInteger(uid)||!Number.isInteger(gid)||uid<=0||gid<=0) throw 0;
  const names=['n8n_password','n8n_encryption_key','n8n_runner_token'];
  const values=JSON.parse(fs.readFileSync(0,'utf8'));
  if(Object.keys(values).sort().join()!=[...names].sort().join()
     ||!names.every(n=>typeof values[n]==='string'&&/^[a-f0-9]{64}\n?$/.test(values[n]))) throw 0;
  fs.chmodSync('/target',0o700);
  for(const n of names){
    const p='/target/'+n;
    const fd=fs.openSync(p,'wx',0o600);
    try{fs.writeFileSync(fd,values[n]);fs.fchmodSync(fd,0o600);}finally{fs.closeSync(fd);}
    if(fs.readFileSync(p,'utf8')!==values[n]) throw 0;
    fs.chownSync(p,uid,gid);
  }
  fs.chownSync('/target',uid,gid);
  console.log(JSON.stringify({initialized:true,files:3,uid,gid,directoryMode:'0700',fileMode:'0600'}));
} catch { console.error('secret-volume-initialization-failed');process.exit(1); }
"""

CONTENT_CHECK = r"""const fs=require('fs');
try{
  const names=['n8n_password','n8n_encryption_key','n8n_runner_token'];
  const values=JSON.parse(fs.readFileSync(0,'utf8'));
  const d=fs.statSync('/run/secrets');
  if(process.getuid()===0||d.uid!==process.getuid()||(d.mode&0o777)!==0o700)throw 0;
  for(const n of names){const p='/run/secrets/'+n;const s=fs.statSync(p);
    if(s.uid!==process.getuid()||(s.mode&0o777)!==0o600||fs.readFileSync(p,'utf8')!==values[n])throw 0;}
  console.log(JSON.stringify({nonRoot:true,sourceEquivalent:true,directoryMode:'0700',fileMode:'0600'}));
}catch{console.error('secret-volume-verification-failed');process.exit(1);}
"""


def original_definition():
    return (setup.ROOT / 'docs/N8N-APP-SETUP-PROPOSAL.md').read_text().split('```yaml\n', 1)[1].split('\n```', 1)[0].strip() + '\n'


def repaired_definition(original):
    setup.require(original == original_definition(), 'repair-original-contract')
    result = original.replace('    volumes: ["n8n_data:/home/node/.n8n"]\n',
                              '    volumes: ["n8n_data:/home/node/.n8n", "n8n_secrets:/run/secrets:ro"]\n')
    result = result.replace('    secrets: [n8n_password, n8n_encryption_key, n8n_runner_token]\n', '')
    result = result.replace('  n8n_data: {name: mcp-stack-n8n-data}\n',
                            '  n8n_data: {name: mcp-stack-n8n-data}\n  n8n_secrets: {external: true, name: mcp-stack-n8n-secrets}\n')
    return result.split('\nsecrets:\n', 1)[0] + '\n'


def source_keys():
    directory = setup.ROOT / '.secrets'
    setup.require(not directory.is_symlink() and stat.S_IMODE(directory.stat().st_mode) == 0o700, 'repair-private-directory')
    values = {}
    for name in KEYS:
        path = directory / name
        setup.require(not path.is_symlink() and path.is_file() and
                      stat.S_IMODE(path.stat().st_mode) == 0o600, 'repair-private-key-mode')
        values[name] = path.read_text()
        setup.require(re.fullmatch('[a-f0-9]{64}\\n?', values[name]) is not None, 'repair-private-key-format')
    return values


def init_arguments():
    return ['run', '--rm', '-i', '--name', INIT, '--pull', 'never', '--network', 'none',
            '--read-only', '--user', '0:0', '--cap-drop', 'ALL', '--cap-add', 'CHOWN',
            '--security-opt', 'no-new-privileges:true', '--cpus', '0.5', '--memory', '128m',
            '--pids-limit', '64', '--mount', 'type=volume,src=' + VOLUME + ',dst=/target',
            '--entrypoint', 'node', setup.IMAGE, '-e', INITIALIZER]


def prepare():
    setup.verify_domain()
    old = json.loads((RETRY / 'baseline.json').read_text())
    rows = setup.snapshots()
    setup.compare_containers(old['containers'], rows)
    setup.require(setup.metadata() == old['database_metadata'] and
                  setup.protected_files() == old['protected_files'] and setup.home_manifest() == old['home'], 'repair-original-preservation')
    source_keys()
    setup.require(all(setup.file_fingerprint(Path(p)) == h for p, h in old['retained_keys'].items()), 'repair-original-keys')
    app = json.loads(setup.docker(['inspect', setup.APP], 'repair-existing-app'))[0]
    setup.require(app['Config']['Image'] == setup.IMAGE and app['Config']['User'] == 'node' and
                  app['State']['Status'] in ('restarting', 'exited') and app['State']['ExitCode'] == 1,
                  'repair-target-is-not-failed-app')
    setup.require({m['Destination'] for m in app['Mounts'] if m['Type'] == 'bind'} ==
                  {'/run/secrets/' + n for n in KEYS} and
                  any(m.get('Name') == 'mcp-stack-n8n-data' for m in app['Mounts']), 'repair-original-mounts')
    setup.require(COMPOSE_PATH.read_text() == original_definition(), 'repair-original-compose')
    image = json.loads(setup.docker(['image', 'inspect', setup.IMAGE], 'repair-image'))[0]
    setup.require(image['Architecture'] == 'arm64' and image['Config']['User'] == 'node' and
                  'n8nio/n8n@' + setup.IMAGE.split('@', 1)[1] in image['RepoDigests'], 'repair-image-contract')
    setup.require(VOLUME not in setup.docker(['volume', 'ls', '--format', '{{.Name}}'], 'repair-volumes').split()
                  and '/' + INIT not in rows, 'repair-name-collision')
    backup = Path(tempfile.mkdtemp(prefix='n8n-secret-before-20261004-', dir=setup.ROOT / 'backups'))
    baseline = {**old, 'containers': {k: v for k, v in rows.items() if k != '/' + setup.APP},
                'old_app_id': app['Id'], 'secret_volume': True}
    setup.private_write(backup / 'original-compose.yaml', COMPOSE_PATH.read_text())
    setup.record(backup / 'baseline.json', baseline)
    print(json.dumps({'repair_prepared': True, 'backup': str(backup)}), flush=True)


def activate(backup):
    setup.require(backup.parent == setup.ROOT / 'backups' and
                  backup.name.startswith('n8n-secret-before-20261004-') and not backup.is_symlink(), 'repair-backup-path')
    baseline = json.loads((backup / 'baseline.json').read_text())
    setup.verify_domain()
    rows = setup.snapshots()
    setup.compare_containers(baseline['containers'], rows)
    setup.require(rows['/' + setup.APP]['id'] == baseline['old_app_id'], 'repair-app-identity-drift')
    setup.require(COMPOSE_PATH.read_text() == repaired_definition((backup / 'original-compose.yaml').read_text()), 'repair-approved-compose-delta')
    protected = setup.protected_files()
    expected = copy.deepcopy(baseline['protected_files'])
    expected[str(COMPOSE_PATH)] = setup.file_fingerprint(COMPOSE_PATH)
    setup.require(protected == expected and setup.metadata() == baseline['database_metadata']
                  and setup.home_manifest() == baseline['home'], 'repair-pre-start-preservation')
    values = source_keys()
    setup.require(all(setup.file_fingerprint(Path(p)) == h for p, h in baseline['retained_keys'].items()), 'repair-key-drift')
    setup.require(VOLUME not in setup.docker(['volume', 'ls', '--format', '{{.Name}}'], 'repair-new-volume-collision').split(), 'repair-new-volume-collision')
    setup.require('/' + INIT not in rows, 'repair-initializer-collision')
    baseline['protected_files'] = protected
    state = setup.ROOT / 'infra/n8n/state'
    setup.require(state.is_dir() and not state.is_symlink() and stat.S_IMODE(state.stat().st_mode) == 0o700, 'repair-private-state')
    run = Path(tempfile.mkdtemp(prefix='secret-repair-', dir=state))
    setup.record(backup / 'activation-attempt.json', {'private_state': str(run), 'one_shot': True})
    setup.record(run / 'baseline.json', baseline)
    print(json.dumps({'repairing_once': True, 'private_state': str(run)}), flush=True)
    setup.command(setup.COMPOSE + ['config', '--quiet'], 'compose-validation', logs=run)
    setup.docker(['stop', '--time', '30', setup.APP], 'stop-failing-n8n', logs=run, timeout=40)
    setup.docker(['volume', 'create', '--label', 'com.mcp-stack.owner=n8n', VOLUME], 'create-secret-volume', logs=run)
    initialized = json.loads(setup.docker(init_arguments(), 'initialize-secret-volume', logs=run,
                                         input=json.dumps(values), timeout=60))
    setup.require(initialized['initialized'] and initialized['files'] == 3, 'repair-volume-initialization')
    setup.record(run / 'initializer-evidence.json', initialized)
    setup.require('/' + INIT not in setup.snapshots(), 'repair-initializer-not-removed')
    print('Secret volume initialized; temporary helper removed. Recreating only n8n, no pull.', flush=True)
    setup.command(setup.COMPOSE + ['up', '-d', '--no-deps', '--pull', 'never', '--force-recreate', 'n8n'],
                  'recreate-n8n', logs=run, timeout=120)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        status = setup.docker(['inspect', setup.APP, '--format', '{{.State.Status}} {{.RestartCount}} {{.State.Health.Status}}'], 'repair-readiness').strip()
        setup.require(status.startswith('running 0 '), 'repair-app-exited-or-restarted')
        if status.endswith(' healthy'):
            break
        time.sleep(2)
    else:
        raise setup.SetupFailure('repair-readiness-timeout')
    equivalent = json.loads(setup.docker(['exec', '-i', setup.APP, 'node', '-e', CONTENT_CHECK],
                                        'secret-volume-content-permissions', logs=run,
                                        input=json.dumps(values)))
    result = setup.qualify(baseline, run) | {'secret_volume': VOLUME, **equivalent,
                                           'temporary_initializer_removed': True}
    setup.record(run / 'qualification.json', result)
    print(json.dumps(result | {'private_state': str(run)}), flush=True)
