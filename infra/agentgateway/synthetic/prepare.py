"""Prepare only the approved synthetic hash config; never rotate live secrets."""

import hashlib
import json
import os
import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[3]
    key_path = root / ".secrets/agentgateway-client-key"
    state_parent = root / "infra/agentgateway/state"
    state = state_parent / "synthetic"
    output = state / "config.json"
    if key_path.is_symlink() or state_parent.is_symlink() or state.is_symlink():
        raise SystemExit("Refusing symlinked secret/state paths")
    if output.exists() or output.is_symlink():
        raise SystemExit("Refusing to overwrite synthetic configuration")
    key = key_path.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", key):
        raise SystemExit("Unexpected existing key format; key not printed")
    template = (Path(__file__).parent / "config.template.json").read_text()
    config = json.loads(template.replace(
        "__CLIENT_KEY_SHA256__", hashlib.sha256(key.encode()).hexdigest()))
    state.mkdir(mode=0o700)
    os.chmod(state, 0o700)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "w") as stream:
        json.dump(config, stream, indent=2)
        stream.write("\n")
    os.chmod(output, 0o644)
    print("Prepared isolated hash-only synthetic config; live key/config unchanged")


if __name__ == "__main__":
    main()
