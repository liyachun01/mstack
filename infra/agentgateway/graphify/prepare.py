"""Prepare only the approved Graphify gateway config/key copy; never rotate keys."""

import hashlib
import json
import os
import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[3]
    state = root / "infra/agentgateway/state/graphify"
    client_path = root / ".secrets/agentgateway-client-key"
    backend_path = root / ".secrets/graphify-http-backend-key"
    foundation = root / "infra/agentgateway/state/config.json"
    backend_config = root / "infra/graphify/state/http/server.json"
    for path in (state, client_path, backend_path, foundation, backend_config):
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink():
                raise RuntimeError("Refusing symlinked config/secret/state path")
    if state.exists():
        raise RuntimeError("Refusing existing Graphify gateway state; not an update command")
    for path in (client_path, backend_path):
        if path.stat().st_mode & 0o777 != 0o600:
            raise RuntimeError("Existing secret permissions differ from approved baseline")
    client = client_path.read_text().strip()
    backend = backend_path.read_text().strip()
    if not all(re.fullmatch(r"[0-9a-f]{64}", key) for key in (client, backend)) or client == backend:
        raise RuntimeError("Invalid or non-distinct existing credentials")
    digest = hashlib.sha256(client.encode()).hexdigest()
    original = json.loads((root / "infra/agentgateway/config.template.json").read_text().replace(
        "__CLIENT_KEY_SHA256__", digest))
    if json.loads(foundation.read_text()) != original:
        raise RuntimeError("Foundation config drifted; refusing to prepare integration")
    if json.loads(backend_config.read_text()) != {"api_key_sha256": hashlib.sha256(backend.encode()).hexdigest()}:
        raise RuntimeError("Backend key/hash config mismatch")
    config = json.loads((Path(__file__).parent / "config.template.json").read_text().replace(
        "__CLIENT_KEY_SHA256__", digest))
    state.mkdir(mode=0o700)
    os.chmod(state, 0o700)
    for name, content, mode in (("config.json", json.dumps(config, indent=2) + "\n", 0o644),
                                ("backend.key", backend, 0o600)):
        fd = os.open(state / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.chmod(state / name, mode)
    print("Prepared ignored hash-only Graphify gateway config and distinct backend key copy; originals unchanged")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL Graphify gateway preparation: " + type(error).__name__)
        raise SystemExit(1) from None
