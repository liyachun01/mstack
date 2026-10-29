#!/usr/bin/python3
"""Global discovery entrypoints; versions and private state stay repo-owned."""
import os
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PLATFORM = 'macos' if sys.platform == 'darwin' else 'linux'
SCOPE = ROOT / 'infra/harnesses/agent-clis' / PLATFORM
name = Path(sys.argv[0]).name
if name not in {'claude', 'codex'}:
    raise SystemExit('Invoke through the claude or codex discovery link')

env = dict(os.environ)
env.pop('MISE_CONFIG_FILE', None)
env['MISE_CEILING_PATHS'] = str(SCOPE.parent)
env['MISE_GLOBAL_CONFIG_FILE'] = str(SCOPE.parent / 'empty-global.toml')
env['MISE_INSTALL_MISSING_TOOLS'] = '0'
env['MISE_NOT_FOUND_AUTO_INSTALL'] = '0'
mise = Path.home() / '.local/bin/mise'
resolved = subprocess.run([str(mise), '-C', str(SCOPE), 'which', name],
                          env=env, capture_output=True, text=True, timeout=30)
if resolved.returncode:
    sys.stderr.write('Pinned CLI unavailable; check the agent-clis mise profile.\n')
    raise SystemExit(resolved.returncode)
binary = resolved.stdout.strip()
if not Path(binary).is_file():
    raise SystemExit('mise did not resolve an installed executable')

# Subscription entrypoints do not inherit another harness's API routing.
for key in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL',
            'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_USE_BEDROCK',
            'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY',
            'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'CODEX_API_KEY'):
    env.pop(key, None)
env['BROWSER'] = str(ROOT / 'integrations/toolchains/open-edge')
network = SCOPE / 'network.json'
if network.is_file():
    for key, value in json.loads(network.read_text()).items():
        if key not in {'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY'}:
            raise SystemExit('Unexpected CLI network setting')
        env.setdefault(key, value)
if name == 'claude':
    env['CLAUDE_CONFIG_DIR'] = str(SCOPE.parent / 'state' / PLATFORM / 'claude')
    env['DISABLE_AUTOUPDATER'] = '1'
else:
    # Preserve the desktop/CLI history and credentials on this machine.
    env['CODEX_HOME'] = str(Path.home() / '.codex')
os.execve(binary, [binary, *sys.argv[1:]], env)
