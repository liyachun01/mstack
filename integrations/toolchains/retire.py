"""Retire verified duplicate Linux CLIs, preserving active stores and exact rollback."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HOME = Path('/home/developer')
# Git/Git LFS remain Ubuntu-owned for editor and minimal-PATH access.
PACKAGES = 'gh direnv fd-find fzf jq ripgrep shellcheck shfmt tmux'.split()


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    private = Path((ROOT / 'infra/maintenance/orb-devbox-mise/current-path.txt').read_text().strip())
    baseline = json.loads((private / 'baseline.json').read_text())
    for name in ('replacement-verification.json', 'consumer-verification.json'):
        report = json.loads((private / name).read_text())
        passed = report.get('passed') if isinstance(report, dict) else all(row['passed'] for row in report)
        if not passed:
            raise ValueError('Replacement/consumer verification must pass first')
    archive = Path(baseline['archive'])
    if digest(archive) != baseline['archive_sha256']:
        raise ValueError('Rollback archive checksum changed')
    state = private / 'retirement'
    state.mkdir(mode=0o700, exist_ok=True)
    receipt = state / 'manifest.json'
    if receipt.exists():
        raise ValueError('Retirement receipt exists; inspect before repeating')
    installed = {}
    for package in PACKAGES:
        result = subprocess.run(['/usr/bin/dpkg-query', '-W', '-f=${db:Status-Status}\t${Version}', package],
                                capture_output=True, text=True, check=True)
        status, version = result.stdout.split('\t')
        if status != 'installed':
            raise ValueError('Expected installed legacy package: ' + package)
        installed[package] = version
    debs = {}
    for path in Path('/var/cache/apt/archives').glob('*.deb'):
        result = subprocess.run(['/usr/bin/dpkg-deb', '-f', str(path), 'Package', 'Version'],
                                capture_output=True, text=True, check=True)
        fields = dict(line.split(': ', 1) for line in result.stdout.splitlines())
        package = fields['Package']
        if package in installed and fields['Version'] == installed[package]:
            debs[package] = path
    if set(debs) != set(PACKAGES):
        raise ValueError('Exact cached rollback packages are required')
    command = ['/usr/bin/apt-get', '--no-auto-remove', 'remove', *PACKAGES]
    simulation = subprocess.run([command[0], '-s', *command[1:]], capture_output=True, text=True, check=True)
    removals = [line.split()[1] for line in simulation.stdout.splitlines() if line.startswith('Remv ')]
    if set(removals) != set(PACKAGES) or any(line.startswith('Inst ') for line in simulation.stdout.splitlines()):
        raise ValueError('Unexpected apt transaction; nothing removed')
    # Check true procfs without argv/environment disclosure, before retiring Bun.
    spec = importlib.util.spec_from_file_location('inventory', ROOT / 'integrations/toolchains/inventory.py')
    inventory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory)
    processes, _ = inventory.process_inventory()
    if any(str(HOME / '.bun/bin') in row.get('executable', '') for row in processes):
        raise ValueError('Legacy Bun remains in use')
    bun_members = ['.bun/bin/bun', '.bun/bin/bunx', '.bun/_bun']
    with tarfile.open(archive) as tar:
        for relative in bun_members:
            member = tar.getmember(relative)
            path = HOME / relative
            if member.issym():
                if not path.is_symlink() or os.readlink(path) != member.linkname:
                    raise ValueError('Legacy Bun symlink changed')
            elif not path.is_file() or digest(path) != hashlib.sha256(tar.extractfile(member).read()).hexdigest():
                raise ValueError('Legacy Bun file changed since backup')
    if not args.apply:
        print(json.dumps({'ready': True, 'apt_packages': PACKAGES, 'legacy_bun_files': len(bun_members),
                          'fnm_and_uv_stores_retained': True, 'services_changed': 0}))
        return
    copied = []
    for package, source in debs.items():
        target = state / source.name
        shutil.copy2(source, target)
        target.chmod(0o600)
        if digest(source) != digest(target):
            raise ValueError('Rollback package copy checksum failed')
        copied.append({'package': package, 'version': installed[package], 'path': str(target), 'sha256': digest(target)})
    (state / 'apt-simulation.txt').write_text(simulation.stdout)
    (state / 'apt-simulation.txt').chmod(0o600)
    data = {'phase': 'prepared', 'rollback_debs': copied, 'bun_members': bun_members,
            'archive_sha256': baseline['archive_sha256'], 'fnm_and_uv_stores_retained': True,
            'services_changed': 0}
    receipt.write_text(json.dumps(data, indent=2) + '\n')
    receipt.chmod(0o600)
    env = {**os.environ, 'DEBIAN_FRONTEND': 'noninteractive', 'NEEDRESTART_MODE': 'l'}
    result = subprocess.run(['sudo', '-n', command[0], '-y', *command[1:]],
                            env=env, capture_output=True, text=True)
    for name, content in (('apt.stdout', result.stdout), ('apt.stderr', result.stderr)):
        path = state / name
        path.write_text(content)
        path.chmod(0o600)
    data['apt_exit_code'] = result.returncode
    if result.returncode:
        receipt.write_text(json.dumps(data, indent=2) + '\n')
        raise ValueError('Exact apt removal failed; inspect private log and prepared rollback')
    for relative in bun_members:
        (HOME / relative).unlink()
    data['phase'] = 'complete'
    receipt.write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'retired_apt_packages': len(PACKAGES), 'retired_standalone_bun_files': len(bun_members),
                      'exact_rollback_debs_verified': len(copied), 'fnm_and_uv_stores_retained': True,
                      'services_changed': 0}))


if __name__ == '__main__':
    main()
