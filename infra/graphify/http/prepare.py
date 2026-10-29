"""Create separate local Graphify backend key/hash; never overwrite live keys."""

import hashlib
import json
import os
import secrets
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[3]
    secret_dir = root / ".secrets"
    key_path = secret_dir / "graphify-http-backend-key"
    state_parent = root / "infra/graphify/state"
    state = state_parent / "http"
    config_path = state / "server.json"
    if any(path.is_symlink() for path in
           (secret_dir, key_path, state_parent, state, config_path)):
        raise SystemExit("Refusing symlinked credential/state paths")
    if key_path.exists() or state.exists() or config_path.exists():
        raise SystemExit("Refusing existing Graphify HTTP credential/state; no rotation")
    if not secret_dir.is_dir() or not state_parent.is_dir():
        raise SystemExit("Expected existing project secret/state directories")
    key = secrets.token_hex(32)
    state.mkdir(mode=0o700)
    os.chmod(state, 0o700)
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(key + "\n")
    os.chmod(key_path, 0o600)
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "w") as stream:
        json.dump({"api_key_sha256": hashlib.sha256(key.encode()).hexdigest()}, stream)
        stream.write("\n")
    os.chmod(config_path, 0o644)
    print("Created separate Graphify backend key (0600) and hash-only config; credentials not printed")


if __name__ == "__main__":
    main()
