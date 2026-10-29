"""One-time, explicitly authorized Paradev (Superset 2.0.0) removal; Mac and Linux.

Run `python3 retire.py --apply <receipt-dir>` on each host after `paradev hosts
remove` has deregistered orb-devbox. Mirrors ../superset-retirement/retire_mac.py.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time


HOME = Path.home()
MAC = sys.platform == 'darwin'
PLATFORM = 'macos' if MAC else 'linux'
APP = Path('/Applications/Superset.app')
STATE = HOME / '.superset'
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
]
if MAC:
    OWNED += ['Library/Application Support/Superset', 'Library/Logs/Superset',
              'Library/Caches/com.superset.desktop',
              'Library/Caches/com.superset.desktop.ShipIt',
              'Library/Caches/@supersetdesktop-updater',
              'Library/Preferences/com.superset.desktop.plist',
              'Library/HTTPStorages/com.superset.desktop']
else:
    OWNED += ['superset']  # headless CLI installed by `hosts add`
ACP_LINK = HOME / '.node_modules'  # orb-devbox adapter link, see infra/paradev
PROTECTED = ['.codex/config.toml', '.codex/auth.json', '.claude.json',
             '.claude/.credentials.json', '.zprofile', '.local/bin/mise']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def owned_command(command):
    return isinstance(command, str) and (
        '$SUPERSET_HOME_DIR/hooks/' in command or str(STATE / 'hooks') + '/' in command)


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
    raw = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,args='], text=True)
    rows = {}
    for line in raw.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3:
            rows[int(parts[0])] = (int(parts[1]), parts[2])
    return rows


def process_tree(rows):
    markers = [str(APP) + '/', str(STATE) + '/', str(HOME / 'superset') + '/']
    owned = {pid for pid, (_, command) in rows.items() if any(m in command for m in markers)}
    while True:
        expanded = owned | {pid for pid, (parent, _) in rows.items() if parent in owned}
        if expanded == owned:
            return owned
        owned = expanded


def atomic_write(path, original, new):
    assert path.read_bytes() == original, 'Concurrent configuration change: ' + str(path)
    stage = path.with_name(path.name + '.paradev-retirement-tmp')
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


def planned_edits():
    edits = []
    for rel in JSON_PATHS:
        path = HOME / rel
        if not path.exists():
            continue
        raw = path.read_bytes()
        clean, count = strip_hooks(json.loads(raw), root=rel.startswith('.mastracode/'))
        if count:
            assert 'superset' not in json.dumps(clean).lower(), rel
            edits.append((path, raw, (json.dumps(clean, indent=2) + '\n').encode(), count))
    muse = HOME / '.config/muse/settings.json'
    if muse.exists():
        raw = muse.read_bytes()
        data = json.loads(raw)
        if data.get('managed_hooks_path') == str(STATE / 'hooks/muse/hooks.json'):
            del data['managed_hooks_path']
            data['managed_hooks_env_vars'] = [v for v in data.get('managed_hooks_env_vars', [])
                                            if not v.startswith('SUPERSET_')]
            if not data['managed_hooks_env_vars']:
                del data['managed_hooks_env_vars']
            edits.append((muse, raw, (json.dumps(data, indent=2) + '\n').encode(), 1))
    grok = HOME / '.grok/config.toml'
    if grok.exists():
        raw = grok.read_bytes()
        pattern = (rb'(?m)^# >>> superset-managed-grok-compat v1 \(do not edit\) >>>\n.*?'
                   rb'^# <<< superset-managed-grok-compat v1 <<<\n?')
        clean, count = re.subn(pattern, b'', raw, flags=re.S)
        if count:
            assert b'superset' not in clean.lower()
            edits.append((grok, raw, clean, count))
    zshrc = HOME / '.zshrc'
    if not MAC and zshrc.exists():
        raw = zshrc.read_bytes()
        line = b'export PATH="' + str(HOME / 'superset/bin').encode() + b':$PATH"\n'
        if raw.count(line) == 1:
            edits.append((zshrc, raw, raw.replace(line, b''), 1))
    return edits


def main():
    assert sys.argv[1] == '--apply'
    receipt_dir = Path(sys.argv[2])
    assert receipt_dir.is_dir() and receipt_dir.name == 'paradev-retirement'
    receipt = receipt_dir / (PLATFORM + '.json')
    assert not receipt.exists(), 'Do not replay completed retirement'
    assert STATE.is_dir() and not STATE.is_symlink()
    assert not (STATE / 'projects').exists() and not (STATE / 'worktrees').exists()
    baseline = {rel: digest(HOME / rel) for rel in PROTECTED}
    edits = planned_edits()
    for rel in OWNED:
        path = HOME / rel
        assert not path.is_symlink(), rel
        if path.is_file() and not rel.startswith('Library/'):
            assert b'superset' in path.read_bytes().lower(), rel
    # Stop only identity-checked Paradev processes; this script is not one of them.
    rows = processes()
    owned = process_tree(rows)
    assert os.getpid() not in owned
    for pid in sorted(owned):
        if processes().get(pid) == rows[pid]:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and process_tree(processes()):
        time.sleep(0.3)
    assert not process_tree(processes()), 'Paradev still running; no removal attempted'
    changed = []
    try:
        for path, raw, clean, count in edits:
            atomic_write(path, raw, clean)
            changed.append((path, raw, clean, count))
    except Exception:
        for path, raw, clean, count in reversed(changed):
            if path.read_bytes() == clean:
                atomic_write(path, clean, raw)
        raise
    removed = []
    targets = [STATE, *[HOME / rel for rel in OWNED]] + ([APP] if MAC else [])
    for path in targets:
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(str(path))
    if ACP_LINK.is_symlink() and 'infra/paradev' in os.readlink(ACP_LINK):
        ACP_LINK.unlink()
        removed.append(str(ACP_LINK))
    for path, raw, clean, count in changed:
        if path.suffix == '.json' and json.loads(clean) == {}:
            path.unlink()
            removed.append(str(path))
    after = {rel: digest(HOME / rel) for rel in PROTECTED}
    assert baseline == after, 'Protected file changed during cleanup'
    result = {
        'date': '2026-10-27', 'platform': PLATFORM, 'product': 'Paradev (Superset 2.0.0)',
        'removed_paths': removed, 'stopped_pids': sorted(owned),
        'configuration_cleanup': [{'path': str(p), 'removed_hooks_or_blocks': n,
                                   'before_sha256': hashlib.sha256(raw).hexdigest(),
                                   'after_sha256': digest(p)} for p, raw, clean, n in changed],
        'protected_files_unchanged': list(baseline),
        'paradev_processes_remaining': len(process_tree(processes())),
    }
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in result.items()}))


if __name__ == '__main__':
    main()
