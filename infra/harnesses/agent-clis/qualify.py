"""Save public setup evidence without credentials, account IDs or session text."""
from pathlib import Path
import base64
import datetime
import json
import subprocess
import sys

root = Path(sys.argv[1])
platform = 'macos' if sys.platform == 'darwin' else 'linux'
scope = root / 'infra/harnesses/agent-clis'
home = Path.home()
def run(name, *args):
    return subprocess.run([str(home / '.local/bin' / name), *args],
                          capture_output=True, text=True, timeout=20)
versions = {}
for name in ('codex', 'claude'):
    result = run(name, '--version')
    assert result.returncode == 0
    versions[name] = result.stdout.strip()
auth = json.loads(run('claude', 'auth', 'status').stdout)
assert auth.get('loggedIn') and auth.get('authMethod') == 'claude.ai'
codex_auth = run('codex', 'login', 'status')
assert codex_auth.returncode == 0 and 'ChatGPT' in codex_auth.stdout + codex_auth.stderr
before = scope / 'state' / platform / ('before-20261027-complete' if platform == 'macos' else 'before-20261027') / 'auth.json'
def identity(path):
    token = json.loads(path.read_text())['tokens']['id_token'].split('.')[1]
    claims = json.loads(base64.urlsafe_b64decode(token + '=' * (-len(token) % 4)))
    return claims['sub']
assert identity(before) == identity(home / '.codex/auth.json')
record = {
    'qualified_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'platform': platform, 'versions': versions,
    'claude_auth': {key: auth.get(key) for key in ('loggedIn', 'authMethod', 'apiProvider', 'subscriptionType')},
    'codex_auth': 'ChatGPT; Edge OAuth completed; same existing account',
    'codex_home_preserved': str(home / '.codex'),
    'model_prompt_sent': False,
}
if platform == 'macos':
    record['desktop_bundles_absent'] = all(not Path(p).exists() for p in ('/Applications/Claude.app', '/Applications/ChatGPT.app'))
(scope / (platform + '-qualification.json')).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
