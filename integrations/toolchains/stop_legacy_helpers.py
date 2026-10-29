"""Explicit one-time drain of identified Codex MCP/language-server trees.

Requires the owning Codex PID, exact PID/start/executable rechecks and a private
receipt. Never stops the owning Codex process, containers or unrelated services.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import time

import inventory

ROOT = Path(__file__).resolve().parents[2]
HOME = Path('/home/developer')
ALLOWED = {'uv', 'uvx', 'python', 'python3', 'python3.13', 'node', 'mise'}


def snapshot():
    rows = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        row = inventory.process_record(path)
        if row is None:
            continue
        try:
            tail = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            row['parent'] = int(tail[1])
            row['uid'] = path.stat().st_uid
            rows[row['pid']] = row
        except (OSError, ValueError):
            continue
    return rows


def legacy(row):
    executable = row['executable']
    return (executable.startswith(str(HOME / '.local/share/fnm') + '/')
            or executable.startswith(str(HOME / '.local/share/uv/python') + '/')
            or executable == str(HOME / '.local/bin/uv') + ' (deleted)')


def unchanged(row):
    current = inventory.process_record(Path('/proc') / str(row['pid']))
    return current is not None and all(current[key] == row[key]
                                       for key in ('pid', 'start_ticks', 'executable'))


def plan(owner):
    rows = snapshot()
    if owner not in rows or Path(rows[owner]['executable']).name != 'codex':
        raise ValueError('Expected the inspected owning native Codex process')
    if not Path('/proc/1').is_dir():
        raise ValueError('Full host process visibility is required')
    roots = set()
    for row in rows.values():
        if not legacy(row):
            continue
        branch = row
        seen = set()
        while branch['parent'] in rows and branch['parent'] != owner:
            if branch['pid'] in seen:
                raise ValueError('Unexpected process ancestry')
            seen.add(branch['pid'])
            branch = rows[branch['parent']]
        if branch['parent'] != owner:
            raise ValueError('Legacy consumer outside the inspected owner; nothing stopped')
        roots.add(branch['pid'])
    targets = set(roots)
    while True:
        expanded = targets | {pid for pid, row in rows.items() if row['parent'] in targets}
        if expanded == targets:
            break
        targets = expanded
    selected = [rows[pid] for pid in sorted(targets)]
    if any(row['uid'] != os.getuid() or Path(row['executable'].removesuffix(' (deleted)')).name not in ALLOWED
           for row in selected):
        raise ValueError('Unexpected non-helper descendant; nothing stopped')
    if not any(row.get('identifier') in {'headroom', 'serena'} for row in selected):
        raise ValueError('No recognizable MCP helper tree')
    return {'owner': rows[owner], 'roots': sorted(roots), 'processes': selected, 'phase': 'planned'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-pid', type=int, required=True)
    parser.add_argument('--stop', action='store_true')
    args = parser.parse_args()
    state = plan(args.owner_pid)
    if args.stop:
        private = Path((ROOT / 'infra/maintenance/orb-devbox-mise/current-path.txt').read_text().strip())
        receipt = private / 'drain/stopped-processes.json'
        if receipt.exists():
            raise ValueError('Stop receipt exists; inspect before repeating')
        receipt.parent.mkdir(mode=0o700, exist_ok=True)
        def save():
            receipt.write_text(json.dumps(state, indent=2) + '\n')
            receipt.chmod(0o600)
        save()
        if not unchanged(state['owner']) or not all(unchanged(row) for row in state['processes']):
            raise ValueError('Process identities changed before stopping; nothing stopped')
        # Parent first prevents new children; exact child rechecks handle their exit races.
        ordered = sorted(state['processes'], key=lambda row: row['pid'] not in state['roots'])
        state['term_sent'] = []
        for row in ordered:
            if unchanged(row):
                try:
                    os.kill(row['pid'], signal.SIGTERM)
                    state['term_sent'].append(row['pid'])
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + 5
        while any(unchanged(row) for row in ordered) and time.monotonic() < deadline:
            time.sleep(0.1)
        state['remaining'] = [row['pid'] for row in ordered if unchanged(row)]
        state['phase'] = 'stopped' if not state['remaining'] else 'graceful-stop-incomplete'
        state['owner_unchanged'] = unchanged(state['owner'])
        save()
        if state['remaining']:
            raise ValueError('Helpers did not all exit; inspect private receipt before proceeding')
    print(json.dumps({'phase': state['phase'], 'helper_roots': len(state['roots']),
                      'helper_processes': len(state['processes']), 'owner_stopped': False,
                      'containers_changed': 0}))


if __name__ == '__main__':
    main()
