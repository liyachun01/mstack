"""Explicit offline maintenance: rebind existing 3.13.15 venvs to mise, without reinstalling packages.

No process is stopped and no interpreter/store is removed by this helper. Stdio MCP
consumers must be stopped/reconnected by their owning application, not daemonized.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HOME = Path('/home/developer')
VERSION = '3.13.15'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def old_roots(home=HOME):
    return tuple(home / '.local/share/uv/python' / name for name in (
        'cpython-3.13-linux-aarch64-gnu', 'cpython-3.13.15-linux-aarch64-gnu'))


def package_signature(env):
    """Identity, declared file hashes and source identity; do not import packages."""
    result = {}
    for folder in sorted((env / 'lib/python3.13/site-packages').glob('*.dist-info')):
        for name in ('METADATA', 'RECORD', 'direct_url.json', 'entry_points.txt'):
            path = folder / name
            if path.is_file():
                result[str(path.relative_to(env))] = sha(path.read_bytes())
    return result


def discover(home=HOME):
    roots = (home / '.local/share/uv/tools', home / '.cache/uv')
    olds = old_roots(home)
    target = home / '.local/share/mise/installs/python' / VERSION / 'bin/python3.13'
    environments = []
    for base in roots:
        if not base.exists():
            continue
        for cfg in sorted(base.rglob('pyvenv.cfg')):
            if cfg.is_symlink() or not cfg.resolve().is_relative_to(base.resolve()):
                raise ValueError('Unexpected symlinked environment configuration')
            before = cfg.read_text()
            fields = dict(line.split(' = ', 1) for line in before.splitlines() if ' = ' in line)
            if fields.get('home') not in {str(path / 'bin') for path in olds}:
                continue
            if fields.get('version_info') != VERSION or fields.get('implementation') != 'CPython':
                raise ValueError('Refusing different Python version/implementation: ' + str(cfg))
            env = cfg.parent
            if (env / 'bin').is_symlink():
                raise ValueError('Unexpected symlinked environment bin directory')
            links = []
            for link in sorted((env / 'bin').glob('python*')):
                if link.is_symlink():
                    original = os.readlink(link)
                    if original in {str(path / 'bin/python3.13') for path in olds}:
                        links.append({'path': str(link), 'before': original, 'after': str(target)})
            if len(links) != 1:
                raise ValueError('Expected one interpreter link: ' + str(env))
            # Hardcoded interpreter shebangs would require a separate reviewed migration.
            for path in (env / 'bin').iterdir():
                if path.is_file() and not path.is_symlink() and path.stat().st_size < 1_000_000:
                    with path.open('rb') as stream:
                        first = stream.read(512).split(b'\n', 1)[0]
                    if first.startswith(b'#!') and any(str(old).encode() in first for old in olds):
                        raise ValueError('Unexpected direct legacy shebang: ' + str(path))
            after = before.replace('home = ' + fields['home'], 'home = ' + str(target.parent), 1)
            environments.append({'env': str(env), 'cfg': str(cfg), 'before': before, 'after': after,
                                 'mode': stat.S_IMODE(cfg.stat().st_mode), 'links': links,
                                 'package_signature': package_signature(env)})
    return {'version': VERSION, 'home': str(home), 'target': str(target), 'environments': environments}


def live_consumers(home=HOME, proc=Path('/proc')):
    result = []
    visible = 0
    for directory in proc.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            exe = os.readlink(directory / 'exe')
            visible += 1
            if any(exe.startswith(str(old) + '/') for old in old_roots(home)):
                result.append({'pid': int(directory.name), 'executable': exe})
        except (OSError, ProcessLookupError):
            continue
    return result, visible


def verified_target(target):
    result = subprocess.run([str(target), '-I', '-c',
                             'import json,sys;print(json.dumps([list(sys.version_info[:3]),sys.base_prefix]))'],
                            capture_output=True, text=True, check=True,
                            env={'PATH': '/usr/bin:/bin', 'HOME': str(HOME), 'PYTHONDONTWRITEBYTECODE': '1'})
    version, prefix = json.loads(result.stdout)
    if version != [3, 13, 15] or Path(prefix).resolve() != target.parent.parent.resolve():
        raise ValueError('Replacement is not the exact verified mise Python')


def atomic_text(path, text, mode):
    fd, tmp = tempfile.mkstemp(prefix='.mise-rebind-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_link(path, target):
    temp = path.with_name(path.name + '.mise-rebind-' + str(os.getpid()))
    try:
        temp.symlink_to(target)
        os.replace(temp, path)
    finally:
        if temp.is_symlink():
            temp.unlink()


def check_state(plan, applied):
    failures = []
    for env in plan['environments']:
        key = 'after' if applied else 'before'
        if Path(env['cfg']).read_text() != env[key]:
            failures.append('config changed: ' + env['cfg'])
        for link in env['links']:
            if not Path(link['path']).is_symlink() or os.readlink(link['path']) != link[key]:
                failures.append('link changed: ' + link['path'])
        if package_signature(Path(env['env'])) != env['package_signature']:
            failures.append('package identity changed: ' + env['env'])
    if failures:
        raise ValueError('; '.join(failures[:5]))


def verify_environments(plan):
    """Check actual venv/base-prefix selection, stdlib TLS and native extension ABI offline."""
    target_prefix = Path(plan['target']).parent.parent.resolve()
    code = ('import json,sys,ssl,sqlite3,ctypes;'
            'print(json.dumps([list(sys.version_info[:3]),sys.prefix,sys.base_prefix]))')
    for env in plan['environments']:
        result = subprocess.run([str(Path(env['env']) / 'bin/python'), '-I', '-c', code],
                                capture_output=True, text=True, check=True,
                                env={'PATH': '/usr/bin:/bin', 'HOME': plan['home'],
                                     'PYTHONDONTWRITEBYTECODE': '1'}, timeout=20)
        version, prefix, base = json.loads(result.stdout)
        if (version != [3, 13, 15] or Path(prefix).resolve() != Path(env['env']).resolve()
                or Path(base).resolve() != target_prefix):
            raise ValueError('Venv interpreter did not select the mise base: ' + env['env'])


def apply(plan, manifest):
    consumers, visible = live_consumers(Path(plan['home']))
    if visible < 5:
        raise ValueError('Host process visibility required; run this maintenance command outside the sandbox')
    if consumers:
        raise ValueError('Legacy Python consumers still running: ' + ','.join(str(x['pid']) for x in consumers))
    verified_target(Path(plan['target']))
    check_state(plan, applied=False)
    if manifest.exists():
        raise ValueError('Manifest exists; inspect or roll back rather than repeating')
    manifest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest.parent.chmod(0o700)
    plan['phase'] = 'prepared'
    atomic_text(manifest, json.dumps(plan, indent=2) + '\n', 0o600)
    try:
        for env in plan['environments']:
            for link in env['links']:
                atomic_link(Path(link['path']), link['after'])
            atomic_text(Path(env['cfg']), env['after'], env['mode'])
        check_state(plan, applied=True)
    except BaseException:
        # Every mutation is reversible even if interrupted before its manifest update.
        rollback(plan)
        raise
    plan['phase'] = 'complete'
    atomic_text(manifest, json.dumps(plan, indent=2) + '\n', 0o600)


def rollback(plan):
    # Refuse to overwrite unrelated subsequent changes, including partially applied state.
    for env in plan['environments']:
        if Path(env['cfg']).read_text() not in (env['before'], env['after']):
            raise ValueError('Configuration drift blocks rollback')
        for link in env['links']:
            if not Path(link['path']).is_symlink() or os.readlink(link['path']) not in (link['before'], link['after']):
                raise ValueError('Link drift blocks rollback')
        if package_signature(Path(env['env'])) != env['package_signature']:
            raise ValueError('Package identity drift blocks rollback')
    for env in reversed(plan['environments']):
        atomic_text(Path(env['cfg']), env['before'], env['mode'])
        for link in env['links']:
            atomic_link(Path(link['path']), link['before'])
    check_state(plan, applied=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'apply', 'verify', 'rollback'))
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    if args.action in ('verify', 'rollback'):
        if not args.manifest:
            parser.error('--manifest is required')
        plan = json.loads(args.manifest.read_text())
        if args.action == 'rollback':
            rollback(plan)
            plan['phase'] = 'rolled-back'
            atomic_text(args.manifest, json.dumps(plan, indent=2) + '\n', 0o600)
        else:
            check_state(plan, applied=True)
            verified_target(Path(plan['target']))
            verify_environments(plan)
    else:
        plan = discover()
        verified_target(Path(plan['target']))
        if args.action == 'apply':
            if not args.manifest:
                parser.error('--manifest is required')
            private = ROOT / 'infra/maintenance/orb-devbox-mise/.secrets'
            if not args.manifest.resolve().is_relative_to(private.resolve()):
                parser.error('Manifest must be under the repo private maintenance directory')
            apply(plan, args.manifest)
    consumers, visible = live_consumers()
    print(json.dumps({'action': args.action, 'environments': len(plan['environments']),
                      'package_identity_count': sum(len(x['package_signature']) for x in plan['environments']),
                      'target': plan['target'], 'legacy_process_count': len(consumers),
                      'visible_process_count': visible, 'packages_reinstalled': 0, 'stores_removed': 0,
                      'global_mcp_configuration_changed': False}))


if __name__ == '__main__':
    main()
