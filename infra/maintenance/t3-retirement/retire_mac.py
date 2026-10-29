"""Completed one-time T3 retirement; never use as a startup or health check."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import signal
import sqlite3
import subprocess
import sys
import time


HOME = Path.home()
APP = Path('/Applications/T3 Code (Beta).app')
STATE = HOME / '.t3'
TARGETS = [APP, STATE, HOME / 'Library/Application Support/t3code-v2',
           HOME / 'Library/Preferences/com.t3tools.t3code.plist']
PROTECTED = [
    '.codex/config.toml', '.codex/auth.json', '.claude/settings.json',
    '.claude.json', '.claude/.credentials.json', '.zshrc', '.zprofile',
    '.paseo/config.json', '.paseo/daemon-keypair.json',
    'Library/Application Support/Paseo/desktop-settings.json',
    '/Applications/Paseo.app/Contents/Info.plist',
    '/Applications/Claude.app/Contents/Info.plist',
    '/Applications/magpie.app/Contents/Info.plist',
    '.local/bin/mise', '.local/bin/codex', '.local/bin/claude',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def processes():
    rows = {}
    raw = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,comm=,args='], text=True)
    for line in raw.splitlines():
        p = line.strip().split(None, 2)
        if len(p) == 3:
            rows[int(p[0])] = (int(p[1]), p[2])
    return rows


def owned_processes(rows):
    owned = {pid for pid, (_, cmd) in rows.items()
             if str(APP) + '/' in cmd or str(STATE) + '/' in cmd}
    while True:
        expanded = owned | {pid for pid, (parent, _) in rows.items() if parent in owned}
        if expanded == owned:
            return owned
        owned = expanded


def main():
    assert sys.platform == 'darwin' and sys.argv[1] == '--apply'
    receipt_dir = Path(sys.argv[2])
    assert receipt_dir.is_dir() and receipt_dir.name == 't3-retirement'
    assert not (receipt_dir / 'mac.json').exists(), 'Do not replay completed cleanup'
    info = plistlib.loads((APP / 'Contents/Info.plist').read_bytes())
    assert info['CFBundleIdentifier'] == 'com.t3tools.t3code'
    assert info['CFBundleShortVersionString'] == '0.1.2'
    assert all(p.exists() and not p.is_symlink() for p in TARGETS)
    baseline = {rel: digest(HOME / rel) for rel in PROTECTED}
    # Abort if worktree/scratch content appears after the read-only inventory.
    assert not list((STATE / 'worktrees').iterdir())
    scratch = list((STATE / 'scratch').rglob('*'))
    assert all(p.is_dir() and not p.is_symlink() for p in scratch)
    # Preserve all external project directories; inspect only path metadata.
    db = sqlite3.connect('file:' + str(STATE / 'userdata/statev2.sqlite') +
                         '?mode=ro&immutable=1', uri=True)
    project_paths = [Path(row[0]) for row in db.execute(
        'SELECT workspace_root FROM projection_projects') if row[0]]
    db.close()
    external = [p for p in project_paths if p != STATE and STATE not in p.parents]
    project_identity = {str(p): (p.stat().st_dev, p.stat().st_ino) if p.exists() else None
                        for p in external}
    rows = processes()
    owned = owned_processes(rows)
    assert os.getpid() not in owned
    for pid in sorted(owned):
        if processes().get(pid) == rows[pid]:
            os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 12
    while owned_processes(processes()) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert not owned_processes(processes()), 'T3 still running; nothing deleted'
    # No configuration outside these four observed, app-owned paths is edited.
    for path in TARGETS:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    assert all(not p.exists() for p in TARGETS)
    assert not owned_processes(processes())
    after = {rel: digest(HOME / rel) for rel in PROTECTED}
    assert baseline == after, 'A protected file changed during cleanup'
    for path, identity in project_identity.items():
        p = Path(path)
        assert ((p.stat().st_dev, p.stat().st_ino) if p.exists() else None) == identity
    result = {
        'date': '2026-10-26', 'product': 'T3 Code Beta', 'removed_version': '0.1.2',
        'platform': 'macOS', 'removed_paths': [str(p) for p in TARGETS],
        'removed_app_managed_codex_version': '0.156.1',
        'removed_t3_cli_wrapper': str(STATE / 'bin/t3'),
        'removed_state': ['T3 account tokens and secrets', 'T3 thread databases',
                          'app settings, attachments, logs and caches'],
        'stopped_pids': sorted(owned), 'remaining_t3_processes': 0,
        'worktrees_before_removal': 0, 'scratch_files_before_removal': 0,
        'external_project_paths_unchanged': list(project_identity),
        'protected_files_unchanged': list(baseline),
        'protected_file_hashes_after': after,
        'global_agent_configuration_edits': False,
        'app_state_or_credentials_backup_retained': False,
        'cloud_account_or_subscription_changed': False,
    }
    (receipt_dir / 'mac.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
