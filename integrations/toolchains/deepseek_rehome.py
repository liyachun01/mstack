#!/usr/bin/python3
"""Rehome retained DeepSeek package bytes without upgrading or starting it.

Only ``apply`` changes the existing profile links. Source packages are never
deleted. Reports contain paths, package hashes and link metadata, not file data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path.home() / '.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/@deepseek-ai/dsh'
PROFILE = Path.home() / '.dsh'
DESTINATION = ROOT / 'infra/harnesses/deepseek/runtime/profile-packages/dsh'
PRIVATE_ROOT = ROOT / 'infra/maintenance/orb-devbox-mise/.secrets'
EXPECTED_PROFILE_LINKS = 430


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def tree_manifest(root: Path) -> dict:
    """Hash real files and link texts; refuse links escaping the copied tree."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Package root must be an existing real directory')
    entries = {}
    for base, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            path = Path(base) / name
            relative = str(path.relative_to(root))
            mode = stat.S_IMODE(path.lstat().st_mode)
            if path.is_symlink():
                target = os.readlink(path)
                if Path(target).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError('Package tree has an absolute or escaping symlink')
                entries[relative] = {'type': 'symlink', 'target': target, 'mode': mode}
            elif path.is_file():
                entries[relative] = {'type': 'file', 'size': path.stat().st_size,
                                     'sha256': digest(path), 'mode': mode}
            elif path.is_dir():
                entries[relative] = {'type': 'directory', 'mode': mode}
            else:
                raise ValueError('Package tree contains a special file')
    return entries


def profile_files(root: Path) -> dict:
    """Prove that configuration, credentials and other real files are unchanged."""
    result = {}
    for base, _, files in os.walk(root, followlinks=False):
        for name in files:
            path = Path(base) / name
            if not path.is_symlink() and path.is_file():
                result[str(path.relative_to(root))] = {
                    'sha256': digest(path), 'mode': stat.S_IMODE(path.stat().st_mode)}
    return result


def profile_links(profile: Path, source: Path, destination: Path) -> list[dict]:
    result = []
    for base, directories, files in os.walk(profile, followlinks=False):
        for name in sorted(directories + files):
            path = Path(base) / name
            if not path.is_symlink():
                continue
            target = os.readlink(path)
            try:
                suffix = Path(target).relative_to(source)
            except ValueError:
                if '/.local/share/fnm/' in target:
                    raise ValueError('Unexpected additional fnm link outside the retained package')
                continue
            result.append({'path': str(path), 'before': target,
                           'after': str(destination / suffix),
                           'resolved_before': path.exists()})
    return result


def atomic_link(path: Path, expected: str, replacement: str) -> None:
    if not path.is_symlink() or os.readlink(path) != expected:
        raise ValueError('Profile link changed since inspection; refusing overwrite')
    temporary = path.with_name(path.name + '.mcp-stack-rehome-' + uuid.uuid4().hex)
    try:
        temporary.symlink_to(replacement)
        os.replace(temporary, path)
    finally:
        if temporary.is_symlink():
            temporary.unlink()


def save_private(path: Path, value: dict) -> None:
    data = json.dumps(value, indent=2, sort_keys=True) + '\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(data)


def summary(state: dict) -> dict:
    entries = state['source_manifest']
    return {'phase': state['phase'], 'source': state['source'],
            'destination': state['destination'], 'profile_links': len(state['links']),
            'preexisting_broken_links': sum(not item['resolved_before'] for item in state['links']),
            'package_files': sum(item['type'] == 'file' for item in entries.values()),
            'package_symlinks': sum(item['type'] == 'symlink' for item in entries.values()),
            'package_bytes': sum(item.get('size', 0) for item in entries.values()),
            'profile_regular_files': len(state['profile_files']),
            'source_deleted': False, 'network_calls': 0, 'services_started': 0}


def plan() -> dict:
    if PROFILE.is_symlink() or not PROFILE.is_dir():
        raise ValueError('Existing DeepSeek home must be a real directory')
    metadata = json.loads((SOURCE / 'package.json').read_text())
    if (metadata.get('name'), metadata.get('version')) != ('@deepseek-ai/dsh', '0.2.0-rc.2'):
        raise ValueError('Retained package name/version changed')
    links = profile_links(PROFILE, SOURCE, DESTINATION)
    if len(links) != EXPECTED_PROFILE_LINKS:
        raise ValueError('Retained profile link inventory changed; inspect before applying')
    return {'phase': 'planned', 'source': str(SOURCE), 'destination': str(DESTINATION),
            'profile': str(PROFILE), 'links': links,
            'source_manifest': tree_manifest(SOURCE), 'profile_files': profile_files(PROFILE)}


def apply() -> dict:
    state = plan()
    if DESTINATION.exists() or DESTINATION.is_symlink():
        raise ValueError('Destination already exists; inspect the previous report rather than overwrite')
    PRIVATE_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(PRIVATE_ROOT, 0o700)
    state_dir = Path(tempfile.mkdtemp(prefix='deepseek-rehome-', dir=PRIVATE_ROOT))
    os.chmod(state_dir, 0o700)
    state['state_directory'] = str(state_dir)
    state['created_utc'] = datetime.now(timezone.utc).isoformat()
    state['phase'] = 'prepared'
    save_private(state_dir / 'manifest.json', state)
    DESTINATION.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # A sibling copy becomes visible only after its complete byte/mode/link check.
    temporary = Path(tempfile.mkdtemp(prefix='.dsh-copy-', dir=DESTINATION.parent))
    temporary.rmdir()
    changed = []
    try:
        shutil.copytree(SOURCE, temporary, symlinks=True, copy_function=shutil.copy2)
        if tree_manifest(temporary) != state['source_manifest']:
            raise ValueError('Package copy differs from the retained package')
        if tree_manifest(SOURCE) != state['source_manifest']:
            raise ValueError('Source package changed during copying')
        os.replace(temporary, DESTINATION)
        state['phase'] = 'copy-verified'
        save_private(state_dir / 'manifest.json', state)
        if profile_files(PROFILE) != state['profile_files']:
            raise ValueError('Profile real files changed before link cutover')
        for item in state['links']:
            if Path(item['after']).exists() != item['resolved_before']:
                raise ValueError('Relocation would change a profile link resolution result')
        for item in state['links']:
            atomic_link(Path(item['path']), item['before'], item['after'])
            changed.append(item)
        if profile_files(PROFILE) != state['profile_files']:
            raise ValueError('Profile real files changed during link cutover')
        if profile_links(PROFILE, SOURCE, DESTINATION):
            raise ValueError('Unexpected source link remains')
        for item in state['links']:
            path = Path(item['path'])
            if not path.is_symlink() or os.readlink(path) != item['after'] or path.exists() != item['resolved_before']:
                raise ValueError('Profile link verification failed')
        state['phase'] = 'complete'
        save_private(state_dir / 'manifest.json', state)
    except BaseException:
        for item in reversed(changed):
            atomic_link(Path(item['path']), item['after'], item['before'])
        state['phase'] = 'failed-links-restored'
        save_private(state_dir / 'manifest.json', state)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return state


def load_state(directory: str) -> dict:
    state_dir = Path(directory).absolute()
    if not state_dir.resolve().is_relative_to(PRIVATE_ROOT.resolve()):
        raise ValueError('Expected the private migration state directory')
    state = json.loads((state_dir / 'manifest.json').read_text())
    if (state['source'], state['destination'], state['profile']) != (str(SOURCE), str(DESTINATION), str(PROFILE)):
        raise ValueError('State targets differ from the exact approved locations')
    return state


def rollback(directory: str) -> dict:
    state = load_state(directory)
    if tree_manifest(SOURCE) != state['source_manifest']:
        raise ValueError('Restore the exact legacy source archive before link rollback')
    # Validate every link before changing any, so unrelated edits are preserved.
    for item in state['links']:
        path = Path(item['path'])
        if not path.is_symlink() or os.readlink(path) not in (item['before'], item['after']):
            raise ValueError('A migrated link was edited after cutover; refusing rollback')
    for item in state['links']:
        path = Path(item['path'])
        if os.readlink(path) == item['after']:
            atomic_link(path, item['after'], item['before'])
    state['phase'] = 'rolled-back-copy-retained'
    save_private(Path(directory) / 'manifest.json', state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'apply', 'report', 'rollback'])
    parser.add_argument('--state-dir')
    args = parser.parse_args()
    if args.action in ('report', 'rollback') and not args.state_dir:
        parser.error('--state-dir is required for report/rollback')
    if args.action == 'plan':
        state = plan()
    elif args.action == 'apply':
        state = apply()
    elif args.action == 'rollback':
        state = rollback(args.state_dir)
    else:
        state = load_state(args.state_dir)
    output = summary(state)
    if 'state_directory' in state:
        output['private_state_directory'] = state['state_directory']
    print(json.dumps(output, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f'DeepSeek retained-package rehome failed: {error}', file=sys.stderr)
        sys.exit(1)
