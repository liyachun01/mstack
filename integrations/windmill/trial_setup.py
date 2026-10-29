"""One-shot, separately approved isolated trial. No harness/model/workflow jobs."""
import argparse
import json
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'infra/windmill/state'
ENV = STATE / 'trial.env'
PASSWORD = ROOT / '.secrets/windmill_trial_password'
PROJECT = 'mcp-stack-windmill-trial'
NAMES = {PROJECT + '-' + x for x in ('db', 'server', 'worker')}
VOLUMES = {PROJECT + '-' + x for x in ('postgres-data', 'worker-cache', 'worker-logs')}
IMAGES = [
    'postgres:18.6-alpine@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873',
    'ghcr.io/windmill-labs/windmill:1.823.1@sha256:20932690bab6b1820bba7a4b5934998ec69fa3f82c0ddd9a500114e53ef51f50',
]
COMPOSE = ['docker', 'compose', '-p', PROJECT, '--env-file', 'infra/windmill/state/trial.env',
           '-f', 'infra/windmill/compose.trial.yaml']
# Deliberately exclude Config.Env and all application/private credential data.
FORMAT = ('{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},'
          '"status":{{json .State.Status}},"started":{{json .State.StartedAt}},'
          '"restarts":{{json .RestartCount}},"ports":{{json .HostConfig.PortBindings}},'
          '"mounts":{{json .Mounts}},"networks":{{json .NetworkSettings.Networks}}}')


class TrialFailure(RuntimeError):
    pass


def private_write(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(text)


def command(args, stage, logs, timeout=30, allowed=(0,)):
    try:
        result = subprocess.run(['macctl', 'run', *args], cwd=ROOT, text=True,
                                capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or b''
        errors = error.stderr or b''
        content = (output.decode(errors='replace') if isinstance(output, bytes) else output)
        content += errors.decode(errors='replace') if isinstance(errors, bytes) else errors
        private_write(logs / (stage + '.log'), content)
        raise TrialFailure(stage + ': timed out; no automatic retry') from None
    private_write(logs / (stage + '.log'), result.stdout + result.stderr)
    if result.returncode not in allowed:
        raise TrialFailure(stage + ': failed; inspect the private operation log')
    return result


def inventory(stage, logs):
    ids = command(['docker', 'ps', '-aq'], stage + '-ids', logs).stdout.split()
    if not ids:
        return {}
    result = command(['docker', 'inspect', '--format', FORMAT, *ids], stage, logs)
    data = [json.loads(x) for x in result.stdout.splitlines()]
    return {x['name'].lstrip('/'): x for x in data}


def compare(before, after):
    for name, data in before.items():
        # Docker's Mounts array has no stable ordering. Compare full mount
        # records canonically; still reject any mount or other metadata change.
        def canonical(record):
            if record is None:
                return None
            normalized = dict(record)
            if 'mounts' in normalized:
                normalized['mounts'] = sorted(normalized['mounts'],
                                              key=lambda mount: json.dumps(mount, sort_keys=True))
            return normalized
        if canonical(after.get(name)) != canonical(data):
            raise TrialFailure('existing-container-metadata-changed: ' + name)
    if set(after) - set(before) != NAMES:
        raise TrialFailure('unexpected-container-delta')


def approved_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-trusted-trial-1.823.1', dest='approved_trial', action='store_true')
    args = parser.parse_args()
    if not args.approved_trial:
        raise TrialFailure('Explicit scoped trial approval required before any action')


def main():
    approved_arguments()
    # This flag is an execution guard, not consent. The caller must have the user's
    # separate approval of the version, download, privileges, credentials and scope.
    if ENV.exists() or ENV.is_symlink() or PASSWORD.exists() or PASSWORD.is_symlink():
        raise TrialFailure('Trial credentials already exist; refuse one-shot rerun')
    for path in (STATE, PASSWORD.parent):
        if path.is_symlink():
            raise TrialFailure('Refuse symlinked private parent')
    if not PASSWORD.parent.is_dir() or PASSWORD.parent.stat().st_mode & 0o077:
        raise TrialFailure('Existing .secrets directory must already be private; do not chmod it')
    STATE.mkdir(mode=0o700, exist_ok=True)
    if STATE.stat().st_mode & 0o077:
        raise TrialFailure('Existing Windmill state directory is not private')
    operation = Path(tempfile.mkdtemp(prefix='install-', dir=STATE))
    print('Private operation directory: ' + str(operation), flush=True)
    context = command(['docker', 'context', 'show'], 'context', operation).stdout.strip()
    engine = command(['docker', 'info', '--format', '{{.Name}}|{{.OperatingSystem}}|{{.Architecture}}'],
                     'engine', operation).stdout.strip()
    if context != 'orbstack' or engine != 'orbstack|OrbStack|aarch64':
        raise TrialFailure('Wrong execution domain/engine; refuse deployment')
    # Host shell variables outrank Compose --env-file. Never let an inherited URL
    # silently redirect the trial to a shared/remote database. No values printed.
    command(['sh', '-c', 'if [ "${WM_TRIAL_DATABASE_URL+x}" = x ]; then exit 42; fi'],
            'env-shadow-check', operation)
    before = inventory('before', operation)
    if NAMES.intersection(before):
        raise TrialFailure('Trial container name collision')
    volumes = command(['docker', 'volume', 'ls', '--format', '{{.Name}}'], 'volumes', operation).stdout.splitlines()
    networks = command(['docker', 'network', 'ls', '--format', '{{.Name}}'], 'networks', operation).stdout.splitlines()
    if VOLUMES.intersection(volumes) or PROJECT in networks:
        raise TrialFailure('Trial storage/network already exists; refuse reuse')
    port = command(['sh', '-c', 'lsof -nP -iTCP:58090 -sTCP:LISTEN'], 'port', operation, allowed=(0, 1))
    if port.returncode == 0 or port.stderr:
        raise TrialFailure('Port 58090 occupied or inventory failed')

    for index, image in enumerate(IMAGES):
        present = command(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'],
                          'image-present-' + str(index), operation, allowed=(0, 1))
        if present.returncode:
            if not any(message in present.stderr.lower() for message in ('no such image', 'no such object')):
                raise TrialFailure('Image inventory failed; do not download as a fallback')
            print('Pulling only approved pinned image: ' + image, flush=True)
            command(['docker', 'pull', '--platform', 'linux/arm64', image],
                    'pull-' + str(index), operation, timeout=1200)
        else:
            print('Reusing cached approved image: ' + image, flush=True)

    password = secrets.token_hex(32)
    private_write(PASSWORD, password + '\n')
    private_write(ENV, 'WM_TRIAL_DATABASE_URL=postgres://windmill:' + password + '@db:5432/windmill\n')
    del password
    command([*COMPOSE, 'config', '--quiet'], 'definition', operation)

    print('Starting isolated Windmill PostgreSQL18.6 only; no shared database changes.', flush=True)
    command([*COMPOSE, 'up', '-d', '--no-deps', '--pull', 'never', 'db'], 'start-db', operation, timeout=120)
    for attempt in range(30):
        check = command(['docker', 'inspect', PROJECT + '-db', '--format', '{{.State.Health.Status}}'],
                        'db-health-' + str(attempt), operation).stdout.strip()
        if check == 'healthy':
            break
        time.sleep(2)
    else:
        raise TrialFailure('New trial PostgreSQL did not become healthy')
    print('Trial PostgreSQL healthy. Starting only the approved server and one non-privileged worker.', flush=True)
    command([*COMPOSE, 'up', '-d', '--no-deps', '--pull', 'never', 'server', 'worker'],
            'start-windmill', operation, timeout=120)
    for attempt in range(60):
        check = command(['docker', 'inspect', PROJECT + '-server', '--format', '{{.State.Health.Status}}'],
                        'server-health-' + str(attempt), operation).stdout.strip()
        if check == 'healthy':
            break
        time.sleep(2)
    else:
        raise TrialFailure('Windmill server did not become healthy')
    for endpoint in ('', 'api/version'):
        # macctl rewrites slash-prefixed standalone arguments. Keep /dev/null
        # inside the fixed host shell script; URLs/credentials are never dynamic input.
        script = ("curl --noproxy '*' --silent --show-error --max-time 10 "
                  "--output /dev/null --write-out '%{http_code}' http://127.0.0.1:58090/" + endpoint)
        result = command(['sh', '-c', script],
                         'http-' + ('root' if not endpoint else 'version'), operation)
        if result.stdout.strip() != '200':
            raise TrialFailure('Windmill HTTP endpoint not ready')
    after = inventory('after', operation)
    compare(before, after)
    if any(after[name]['status'] != 'running' or after[name]['restarts'] for name in NAMES):
        raise TrialFailure('New trial process not stable')
    report = {'url': 'http://127.0.0.1:58090/', 'windmill': '1.823.1', 'postgres': '18.6',
              'existing_container_metadata_unchanged': True, 'new_containers': sorted(NAMES),
              'http_root_and_version': 200, 'worker_process_running': True,
              'worker_job_execution_qualified': False, 'job_sandbox_enabled': False,
              'owner_login_performed': False, 'harness_or_memory_connected': False}
    private_write(operation / 'qualification.json', json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    print('Finished isolated trial foundation. No further component, login or job is started.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except TrialFailure as error:
        print('STOP: ' + str(error), flush=True)
        print('No automatic retry, permission change, shutdown, rollback or deletion. Preserve new trial data.', flush=True)
        raise SystemExit(1)
