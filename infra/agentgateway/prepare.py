import hashlib
import json
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[2]
secret_dir = root / ".secrets"
state = root / "infra/agentgateway/state"
key_path = secret_dir / "agentgateway-client-key"
config_path = state / "config.json"
if key_path.exists() or config_path.exists():
    raise SystemExit("Refusing to overwrite existing gateway key/config")
secret_dir.mkdir(mode=0o700, exist_ok=True)
state.mkdir(mode=0o700, exist_ok=True)
os.chmod(state, 0o700)
key = secrets.token_hex(32)
template = (root / "infra/agentgateway/config.template.json").read_text()
config = json.loads(template.replace("__CLIENT_KEY_SHA256__", hashlib.sha256(key.encode()).hexdigest()))
fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as file:
    file.write(key + "\n")
fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
with os.fdopen(fd, "w") as file:
    json.dump(config, file, indent=2)
    file.write("\n")
os.chmod(key_path, 0o600)
os.chmod(config_path, 0o644)
print("Generated project-local gateway key and hash-only config; no credentials printed")
