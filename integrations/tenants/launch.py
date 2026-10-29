"""Project stdio transport to an authenticated session in a shared tool container."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'stack'))
import project_state
import threading

COMMANDS = {
    'graphify': ['mstack-graphify', '/opt/venv/bin/python', '/integration/graphify_session.py'],
    'anytype': ['mstack-anytype-mcp', 'node', '/integration/anytype.mjs'],
    'headroom': ['mstack-headroom', 'python', '/integration/headroom_session.py'],
}


def launch(project, tool):
    project = project.resolve()
    cfg = project_state.tenants(project)
    slug = json.loads((project / '.mstack/stack.json').read_text())['project']
    if cfg.get('version') != 1 or cfg.get('project') != slug:
        raise ValueError('Tenant configuration belongs to another project')
    binding = cfg['tools'][tool]
    if binding['tenant'] != slug or binding['container'] != COMMANDS[tool][0]:
        raise ValueError('Tenant binding mismatch')
    key = project_state.credential(project,binding['credential_file'],exists=True)
    token = key.read_text().strip()
    if not re.fullmatch('[a-f0-9]{64}', token):
        raise ValueError('Invalid project credential')
    # Embedded shell prevents macctl from rewriting in-container absolute paths.
    import shlex
    cmd = 'exec ' + shlex.join(['docker', 'exec', '-i', *COMMANDS[tool]])
    child = subprocess.Popen(['macctl', 'run', 'sh', '-c', cmd], stdin=subprocess.PIPE)
    def stop(signum, _frame):
        child.terminate()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        child.stdin.write(json.dumps({'tenant': slug, 'token': token}).encode() + b'\n')
        child.stdin.flush()
        def forward():
            try:
                while chunk := os.read(0, 65536):
                    child.stdin.write(chunk)
                    child.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
            finally:
                child.stdin.close()
        threading.Thread(target=forward, daemon=True).start()
        return child.wait()
    finally:
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired: child.kill(); child.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--tool', choices=COMMANDS, required=True)
    args = parser.parse_args()
    try:
        raise SystemExit(launch(args.project, args.tool))
    except (KeyError, ValueError, OSError):
        print('mstack: missing or invalid project tenant binding', file=sys.stderr)
        raise SystemExit(1)
