"""Create one separate backend credential/hash configuration; no rotation."""

import hashlib
import json
import os
import secrets
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[3]
    directory = root / ".secrets"
    key_file = directory / "codegraph-http-backend-key"
    parent = root / "infra/codegraph/state"
    state = parent / "http"
    config = state / "server.json"
    if any(p.is_symlink() for p in (directory, key_file, parent, state, config)):
        raise SystemExit("Refusing symlinked credential/state paths")
    if key_file.exists() or state.exists():
        raise SystemExit("Refusing existing CodeGraph HTTP credentials/state; no rotation")
    if not directory.is_dir() or not parent.is_dir():
        raise SystemExit("Expected existing project secrets/state directories")
    key = secrets.token_hex(32)
    state.mkdir(mode=0o700)
    os.chmod(state, 0o700)
    for path, mode, data in (
        (key_file, 0o600, key + "\n"),
        (config, 0o644, json.dumps({"api_key_sha256": hashlib.sha256(key.encode()).hexdigest()}) + "\n"),
    ):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
        os.chmod(path, mode)
    print("Created separate CodeGraph backend key (0600) and hash-only config; no credentials printed")


if __name__ == "__main__":
    main()
