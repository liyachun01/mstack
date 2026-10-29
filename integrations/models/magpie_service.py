"""Launch the installed, pinned Magpie in the background with project-owned state."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
cfg = json.loads((ROOT / 'infra/magpie/config.json').read_text())
binary = Path(cfg['binary'])
if hashlib.sha256(binary.read_bytes()).hexdigest() != cfg['binary_sha256']:
    raise SystemExit('Magpie binary changed; qualify the new version before starting it')
env = dict(os.environ)
env['MAGPIE_NO_ACCOUNTS'] = '1'
env['MAGPIE_WEB_KEY'] = (ROOT / 'infra/magpie/state/web-key').read_text().strip()
os.umask(0o077)
os.execve(str(binary), [str(binary), 'web', '--no-open', '--addr', '127.0.0.1:3430'], env)
