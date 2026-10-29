"""Prepare or explicitly launch the existing project DeepSeek Web profile.

Default is a read-only check. No inference, plugin installation, global key
configuration or current-process stop. --launch requires a separate approved
idle Web lifecycle operation. Credentials never enter argv or output.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MISE = Path.home() / '.local/bin/mise'
NODE_VERSION = '24.19.0'
HARNESS_VERSION = '0.2.0-rc.2'
DSH_HOME = Path.home() / '.dsh'
KEY_VAR = 'MCP_STACK_HARNESSBOT_DEEPSEEK_KEY'


def installed_tool_root(tool, version):
    """Resolve an already-installed exact tool; never invoke mise install/exec."""
    if not MISE.is_file():
        raise ValueError('Existing mise executable absent; installation is not automatic')
    config_dir = ROOT / 'infra/harnesses/deepseek'
    env = {'HOME': str(Path.home()), 'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
           'MISE_GLOBAL_CONFIG_FILE': str(config_dir / 'mise.toml'),
           'MISE_INSTALL_MISSING_TOOLS': '0', 'MISE_NOT_FOUND_AUTO_INSTALL': '0'}
    try:
        result = subprocess.run(
            [str(MISE), '-C', str(config_dir),
             'where', f'{tool}@{version}'],
            env=env, stdin=subprocess.DEVNULL, check=True, capture_output=True,
            text=True, timeout=10)
    except subprocess.SubprocessError as exc:
        raise ValueError('Pinned mise tool absent or unresolved; install separately') from exc
    lines = result.stdout.strip().splitlines()
    if len(lines) != 1:
        raise ValueError('Unexpected mise installation path')
    root = Path(lines[0])
    if not root.is_absolute() or root.name != version or not root.is_dir():
        raise ValueError('Expected an existing exact-version mise installation')
    return root


def credential():
    source = ROOT / '.secrets/agents.csv'
    if source.is_symlink() or not source.is_file():
        raise ValueError('Expected the repository credential CSV as a regular file')
    with source.open(newline='') as f:
        matches = [r for r in csv.reader(f) if len(r) == 3 and r[1].strip() == 'harnessbot']
    if len(matches) != 1 or 'deepseek' not in matches[0][0].lower():
        raise ValueError('Expected exactly one DeepSeek harnessbot credential')
    key = matches[0][2].strip()
    if not key.startswith('sk-') or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError('Unexpected DeepSeek credential format')
    return key


def command_and_env():
    node_root = installed_tool_root('node', NODE_VERSION)
    node = node_root / 'bin/node'
    cli_prefix = installed_tool_root('npm:@deepseek-ai/dsh', HARNESS_VERSION)
    candidates = [cli_prefix / relative for relative in
                  ('node_modules/@deepseek-ai/dsh', 'lib/node_modules/@deepseek-ai/dsh')]
    installed = [path for path in candidates if (path / 'package.json').is_file()]
    if len(installed) != 1:
        raise ValueError('Expected one installed harness package in the mise prefix')
    cli_root = installed[0]
    if not cli_root.resolve().is_relative_to(cli_prefix.resolve()):
        raise ValueError('Installed harness package escapes its mise prefix')
    if not node.is_file() or not os.access(node, os.X_OK):
        raise ValueError('Pinned Node executable absent')
    metadata = json.loads((cli_root / 'package.json').read_text())
    if metadata['name'] != '@deepseek-ai/dsh' or metadata['version'] != HARNESS_VERSION:
        raise ValueError('Installed harness version changed; requalify before launch')
    if not (cli_root / 'lib/bin.js').is_file():
        raise ValueError('Installed harness entrypoint absent')
    profile = DSH_HOME / 'profiles/web/package.json'
    if not profile.is_file():
        raise ValueError('Existing Web profile absent; refusing automatic profile initialization')
    env = {'PATH': str(node_root / 'bin') + ':/usr/bin:/bin',
           'LANG': 'C.UTF-8', 'DSH_HOME': str(DSH_HOME),
           'DSH_TELEMETRY_DISABLED': '1', 'NODE_DISABLE_COMPILE_CACHE': '1',
           'MCP_STACK_GATEWAY_KEY_FILE': str(ROOT / '.secrets/agentgateway-client-key'),
           KEY_VAR: credential()}
    cmd = [str(node), str(cli_root / 'lib/bin.js'), '--profile', 'web']
    for name in ('mcp-stack.cordis.yml', 'no-vision.cordis.yml', 'harnessbot.cordis.yml'):
        path = ROOT / 'infra/harnesses/deepseek' / name
        if not path.is_file():
            raise ValueError('Required project patch absent')
        cmd.extend(['--patch', str(path)])
    cmd.extend(['--no-open', '--host', '127.0.0.1', '--port', '3080'])
    return cmd, env


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--launch', action='store_true')
    args = p.parse_args()
    cmd, env = command_and_env()
    if not args.launch:
        print(json.dumps({'status': 'prepared-not-activated', 'credential_alias': 'harnessbot',
                          'model': 'deepseek-flash', 'version': HARNESS_VERSION,
                          'key_in_argv': False, 'command': cmd,
                          'environment_names': sorted(env), 'model_requests': 0}, indent=2))
        return
    # A human-approved restart must first verify identity/idleness and stop only
    # the owned old Web process. This launcher never interrupts an existing host.
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1', 3080)) == 0:
            raise ValueError('Web already listening; refusing duplicate launch or automatic restart')
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1', 58081)) != 0:
            raise ValueError('Required existing loopback forwarder is unavailable')
    state = ROOT / 'infra/harnesses/deepseek/state'
    state.mkdir(mode=0o700, exist_ok=True)
    os.chmod(state, 0o700)
    log = state / 'harnessbot-web.log'
    with os.fdopen(os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
        process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=out, stderr=out,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
    # Log can contain the Web launch token; do not print or publish it.
    print(json.dumps({'started_pid': process.pid, 'log': str(log), 'credential_alias': 'harnessbot'}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError):
        print('DeepSeek project launch check failed; inspect the prepared configuration privately.', file=sys.stderr)
        sys.exit(1)
