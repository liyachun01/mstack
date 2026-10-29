"""Prepare approved combined gateway config/existing CodeGraph key copy only."""

import hashlib
import json
import os
import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[3]
    state = root / "infra/agentgateway/state/codegraph"
    paths = [root / ".secrets" / name for name in (
        "agentgateway-client-key", "graphify-http-backend-key", "codegraph-http-backend-key")]
    configs = [root / f"infra/{name}/state/http/server.json" for name in ("graphify", "codegraph")]
    original_config = root / "infra/agentgateway/state/graphify/config.json"
    for path in [state, original_config, *paths, *configs]:
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise RuntimeError("Refusing symlinked config/secret/state path")
    if state.exists():
        raise RuntimeError("Refusing existing CodeGraph gateway state; no overwrite")
    if any(path.stat().st_mode & 0o777 != 0o600 for path in paths):
        raise RuntimeError("Original credential permissions differ from approval")
    keys = [path.read_text().strip() for path in paths]
    if not all(re.fullmatch(r"[0-9a-f]{64}", key) for key in keys) or len(set(keys)) != 3:
        raise RuntimeError("Invalid or non-distinct existing credentials")
    digest = hashlib.sha256(keys[0].encode()).hexdigest()
    template = json.loads((root / "infra/agentgateway/graphify/config.template.json").read_text())
    rendered = json.loads(json.dumps(template).replace("__CLIENT_KEY_SHA256__", digest))
    if json.loads(original_config.read_text()) != rendered:
        raise RuntimeError("Existing Graphify gateway config drift")
    for path, key in zip(configs, keys[1:]):
        if json.loads(path.read_text()) != {"api_key_sha256": hashlib.sha256(key.encode()).hexdigest()}:
            raise RuntimeError("Backend key/hash mismatch")
    new_template = json.loads((Path(__file__).parent / "config.template.json").read_text())
    retained = {**new_template, "routes": [r for r in new_template["routes"] if r["name"] != "codegraph"]}
    if retained != template or len(new_template["routes"]) != len(template["routes"]) + 1:
        raise RuntimeError("Unexpected change to existing gateway routes/settings")
    config = json.loads(json.dumps(new_template).replace("__CLIENT_KEY_SHA256__", digest))
    state.mkdir(mode=0o700)
    os.chmod(state, 0o700)
    for name, data, mode in (("config.json", json.dumps(config, indent=2) + "\n", 0o644),
                             ("backend.key", keys[2], 0o600)):
        fd = os.open(state / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
        os.chmod(state / name, mode)
    print("Prepared combined hash-only gateway config and existing CodeGraph key copy; originals unchanged")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL CodeGraph gateway preparation: " + type(error).__name__)
        raise SystemExit(1) from None
