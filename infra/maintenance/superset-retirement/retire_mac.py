"""One-time, explicitly authorized Superset retirement; not a startup helper."""
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import time


HOME = Path.home()
APP = Path('/Applications/Superset.app')
STATE = HOME / '.superset'
RECOVERED = HOME / 'Developer/recovered-from-superset-20261026'
JSON_PATHS = [
    '.claude/settings.json', '.codex/hooks.json', '.cursor/hooks.json',
    '.gemini/settings.json', '.factory/settings.json',
    '.config/devin/config.json', '.mastracode/hooks.json',
]
SKILLS = ['standup', 'page', '10x', 'feedback', 'plugins', 'integrations',
          'setup', 'computer', 'panes', 'orchestrate', 'browser',
          'contribute', 'doctor', 'automate']
OWNED = [
    '.claude/skills/superset',
    *['.agents/skills/superset-' + name for name in SKILLS],
    '.config/amp/plugins/superset-lifecycle.ts',
    '.pi/agent/extensions/superset-hooks.ts',
    '.omp/agent/extensions/superset-hooks.ts',
    '.grok/hooks/superset-notify.json',
    'Library/Application Support/Superset',
    'Library/Caches/com.superset.desktop',
    'Library/Caches/com.superset.desktop.ShipIt',
    'Library/Caches/@supersetdesktop-updater',
    'Library/Preferences/com.superset.desktop.plist',
    'Library/HTTPStorages/com.superset.desktop',
    'Library/Logs/Superset',
]
PROTECTED = [
    '.codex/config.toml', '.codex/auth.json', '.claude.json',
    '.claude/.credentials.json', '.zshrc', '.zprofile',
    '.paseo/config.json', '.paseo/daemon-keypair.json',
    'Library/Application Support/Paseo/desktop-settings.json',
    '/Applications/Paseo.app/Contents/Info.plist',
    '/Applications/T3 Code (Beta).app/Contents/Info.plist',
    '/Applications/Claude.app/Contents/Info.plist',
    '/Applications/magpie.app/Contents/Info.plist',
    '.local/bin/mise',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def owned_command(command):
    return isinstance(command, str) and (
        '$SUPERSET_HOME_DIR/hooks/' in command or
        str(STATE / 'hooks') + '/' in command
    )


def strip_hooks(data, root=False):
    result = copy.deepcopy(data)
    events = result if root else result.get('hooks', {})
    removed = 0
    for event, groups in list(events.items()):
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for group in groups:
            if owned_command(group.get('command')):
                removed += 1
                continue
            if isinstance(group.get('hooks'), list):
                kept = [h for h in group['hooks'] if not owned_command(h.get('command'))]
                removed += len(group['hooks']) - len(kept)
                if len(kept) != len(group['hooks']):
                    if not kept:
                        continue
                    group['hooks'] = kept
            kept_groups.append(group)
        if kept_groups:
            events[event] = kept_groups
        elif groups:
            del events[event]
    if not root and not events and 'hooks' in result:
        del result['hooks']
    return result, removed


def processes():
    raw = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,comm=,args='], text=True)
    rows = {}
    for line in raw.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3:
            rows[int(parts[0])] = (int(parts[1]), parts[2])
    return rows


def process_tree(rows):
    owned = {pid for pid, (_, command) in rows.items()
             if str(APP) + '/' in command or str(STATE) + '/' in command}
    while True:
        expanded = owned | {pid for pid, (parent, _) in rows.items() if parent in owned}
        if expanded == owned:
            return owned
        owned = expanded


def atomic_write(path, original, new):
    assert path.read_bytes() == original, 'Concurrent configuration change: ' + str(path)
    stage = path.with_name(path.name + '.superset-retirement-tmp')
    assert not stage.exists()
    try:
        fd = os.open(stage, os.O_CREAT | os.O_EXCL | os.O_WRONLY, path.stat().st_mode & 0o777)
        with os.fdopen(fd, 'wb') as f:
            f.write(new)
            f.flush()
            os.fsync(f.fileno())
        os.replace(stage, path)
    finally:
        if stage.exists():
            stage.unlink()


def git(path, *args):
    return subprocess.check_output(
        ['/usr/bin/git', '-c', 'core.fsmonitor=false', '-C', str(path), *args],
        env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}, stderr=subprocess.PIPE, text=True,
    ).strip()


def main():
    assert sys.platform == 'darwin' and sys.argv[1] == '--apply'
    receipt_dir = Path(sys.argv[2])
    assert receipt_dir.is_dir() and receipt_dir.name == 'superset-retirement'
    assert not (receipt_dir / 'mac.json').exists(), 'Do not replay completed retirement'
    info = plistlib.loads((APP / 'Contents/Info.plist').read_bytes())
    assert info['CFBundleIdentifier'] == 'com.superset.desktop'
    assert info['CFBundleShortVersionString'] == '1.40.0'
    assert STATE.is_dir() and not STATE.is_symlink() and not RECOVERED.exists()
    assert json.loads((STATE / 'plugins/mcp-ledger.json').read_text())['files'] == {}
    baseline = {rel: digest(HOME / rel) for rel in PROTECTED}
    edits = []
    for rel in JSON_PATHS:
        path = HOME / rel
        if not path.exists():
            continue
        raw = path.read_bytes()
        data = json.loads(raw)
        clean, count = strip_hooks(data, root=rel.startswith('.mastracode/'))
        assert count > 0 and 'superset' not in json.dumps(clean).lower(), rel
        edits.append((path, raw, (json.dumps(clean, indent=2) + '\n').encode(), count))
    muse = HOME / '.config/muse/settings.json'
    raw = muse.read_bytes()
    data = json.loads(raw)
    assert data['managed_hooks_path'] == str(STATE / 'hooks/muse/hooks.json')
    del data['managed_hooks_path']
    data['managed_hooks_env_vars'] = [v for v in data['managed_hooks_env_vars']
                                    if not v.startswith('SUPERSET_')]
    if not data['managed_hooks_env_vars']:
        del data['managed_hooks_env_vars']
    edits.append((muse, raw, (json.dumps(data, indent=2) + '\n').encode(), 1))
    grok = HOME / '.grok/config.toml'
    raw = grok.read_bytes()
    pattern = rb'(?m)^# >>> superset-managed-grok-compat v1 \(do not edit\) >>>\n.*?^# <<< superset-managed-grok-compat v1 <<<\n?'
    clean, count = re.subn(pattern, b'', raw, flags=re.S)
    assert count == 1 and b'superset' not in clean.lower()
    edits.append((grok, raw, clean, 1))
    for rel in OWNED:
        path = HOME / rel
        assert not path.is_symlink(), rel
        if path.exists() and path.is_file() and not rel.startswith('Library/'):
            assert b'superset' in path.read_bytes().lower(), rel
    repos = [STATE / 'projects/supertest',
             *sorted((STATE / 'worktrees/supertest').iterdir())]
    assert len(repos) == 3
    heads = {str(p.relative_to(STATE)): git(p, 'rev-parse', 'HEAD') for p in repos}
    for p in repos:
        assert git(p, 'status', '--porcelain=v1', '--untracked-files=all') == ''
        assert git(p, 'ls-files') == ''
    # Stop only identity-checked Superset processes. No foreground app control.
    rows = processes()
    owned = process_tree(rows)
    assert os.getpid() not in owned
    for pid in sorted(owned):
        current = processes()
        if current.get(pid) == rows[pid]:
            os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline and process_tree(processes()):
        time.sleep(0.2)
    assert not process_tree(processes()), 'Superset still running; no removal attempted'
    # Keep all repository bytes; repair only Git's cross-directory metadata.
    RECOVERED.mkdir(mode=0o700)
    for name in ['projects', 'worktrees']:
        shutil.move(str(STATE / name), str(RECOVERED / name))
    root = RECOVERED / 'projects/supertest'
    worktrees = sorted((RECOVERED / 'worktrees/supertest').iterdir())
    git(root, 'worktree', 'repair', *[str(p) for p in worktrees])
    for rel, head in heads.items():
        p = RECOVERED / rel
        assert git(p, 'rev-parse', 'HEAD') == head
        assert git(p, 'status', '--porcelain=v1', '--untracked-files=all') == ''
    changed = []
    try:
        for path, raw, clean, count in edits:
            atomic_write(path, raw, clean)
            changed.append((path, raw, clean, count))
            assert path.read_bytes() == clean
    except Exception:
        for path, raw, clean, count in reversed(changed):
            if path.read_bytes() == clean:
                atomic_write(path, clean, raw)
        raise
    removed = []
    for path in [APP, STATE, *[HOME / rel for rel in OWNED]]:
        if not path.exists():
            continue
        assert not path.is_symlink(), str(path)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(str(path))
    # Remove empty hook-only JSON files; keep metadata/non-hook settings.
    for path, raw, clean, count in changed:
        if path.suffix == '.json' and json.loads(clean) == {}:
            path.unlink()
            removed.append(str(path))
    after = {rel: digest(HOME / rel) for rel in PROTECTED}
    assert baseline == after, 'Protected file changed during cleanup'
    assert not process_tree(processes())
    assert all(not Path(p).exists() for p in removed)
    result = {
        'date': '2026-10-26', 'platform': 'macOS', 'product': 'Superset',
        'removed_version': info['CFBundleShortVersionString'],
        'removed_paths': removed, 'stopped_pids': sorted(owned),
        'configuration_cleanup': [{'path': str(p), 'removed_hooks_or_blocks': n,
                                   'before_sha256': hashlib.sha256(raw).hexdigest(),
                                   'after_sha256': digest(p)} for p, raw, clean, n in changed],
        'protected_files_unchanged': list(baseline),
        'project_preservation': {'path': str(RECOVERED), 'repository_count': 1,
                                 'worktree_count': 2, 'heads': heads,
                                 'clean_and_repaired': True},
        'superset_processes_remaining': 0,
        'app_credentials_or_runtime_backups_retained': False,
        'cloud_account_or_subscription_changed': False,
    }
    (receipt_dir / 'mac.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
