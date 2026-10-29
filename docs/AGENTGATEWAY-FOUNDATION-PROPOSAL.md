# Agentgateway foundation — approval request

Prepared 2026-10-01; approved by the user with **“Do”**, followed by approval of the network correction with **“Continue!”**. **Foundation complete: official v1.5.0 gateway running at macOS `127.0.0.1:58080`, HTTP authentication/routes verified.** See the [actual results and corrected network](AGENTGATEWAY-NETWORK-CORRECTION.md). The original proposed file contents/commands below are retained for audit and include the subsequently corrected route/network/curl assumptions; use the actual files under `infra/agentgateway/` for operations, not these historical code blocks. Do not rerun preparation or rotate the existing key. Helm is deferred. No real MCP backend or harness is connected; synthetic qualification and each server connection still require separate approval.

## Exact scope and discovery

- Execution domain: existing macOS OrbStack Docker engine, invoked from Ubuntu with `macctl run`. No host binary/CLI, Rust, Node, Helm, Kubernetes, Ubuntu mise or global configuration change.
- Official v1.5.0, source `fe6732474a96a0363dfb9822859af4e9bab360fa`.
- Image: `ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896`, explicitly `linux/arm64`. Metadata identifies ARM64 child `sha256:f64c27c8bd8aa25f07864dab07072026e375f22c6298c2c2d64f7d6c08a24130`, entrypoint `/app/agentgateway`, default UID 65532, matching release revision. Approximately 39 MB compressed layers; actual unpacked disk/RAM usage is not yet measured.
- Read-only inventory: 14 running containers, only two for `mcp-stack` (PostgreSQL and Basic Memory). No agentgateway image/container, and no `mcp-stack-gateway` network. Other projects are out of scope. Docker Compose v5.1.2 and `/usr/bin/curl` already exist on macOS.
- Proposed publication: **macOS `127.0.0.1:58080` → container 4000**. Docker's published-port inventory and macOS listener check found no current use; repeat immediately before startup. Ubuntu `localhost` is not macOS `localhost`; the test uses macOS curl through `macctl`, not a new forwarding service or public bind.
- One long-running container: `mcp-stack-agentgateway-1`, project `mcp-stack`. A temporary `--version` container is removed before starting that service. No synthetic backend container in this step.

## Security and data boundaries

Strict bearer API-key authentication on the entire listener; upstream's default optional mode is explicitly overridden. Generate a random 256-bit client key, keep its plaintext only in ignored `.secrets/agentgateway-client-key` (0600), and configure only its SHA-256 hash. No token in command arguments, Compose environment variables, printed output or versioned files.

Mount only the rendered config file, read-only. Use non-root 65532:65532, read-only root, dropped capabilities, no-new-privileges, 1 CPU/512 MiB/128 PIDs and a bounded 16 MiB temporary filesystem. New internal network `mcp-stack-gateway`; no attachment to PostgreSQL, Basic Memory or {{mstack:CLIENT_REPO}} networks. This reduces outbound connectivity but is not a claim of a perfect host firewall. No Docker socket, repository/source/index mounts, database connection, model/provider, analytics store, UI or admin/metrics/readiness listener.

Routes deliberately expose no tools: authenticated `/healthz` returns 200, `/mcp` returns 503 (not configured), all other paths return 404. No gateway registration or MCP initialization tests against Basic Memory, Graphify or CodeGraph. This is a safe foundation, **not a usable memory endpoint or proof of MCP authorization**.

## Files to create only after approval

Existing root `compose.yaml` and `infra/mise.toml` remain unchanged. Add `infra/agentgateway/state/` to `.gitignore` before generating state. No commit/push.

### `infra/agentgateway/compose.yaml`

```yaml
services:
  agentgateway:
    image: ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896
    platform: linux/arm64
    pull_policy: never
    user: "65532:65532"
    command: ["-f", "/config/config.json"]
    restart: unless-stopped
    read_only: true
    init: true
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    cpus: 1
    mem_limit: 512m
    pids_limit: 128
    stop_grace_period: 15s
    ports: ["127.0.0.1:58080:4000"]
    networks: [gateway]
    tmpfs: ["/tmp:rw,nosuid,nodev,noexec,size=16777216,mode=1777"]
    volumes:
      - type: bind
        source: ./infra/agentgateway/state/config.json
        target: /config/config.json
        read_only: true
        bind:
          create_host_path: false
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "2"
networks:
  gateway:
    name: mcp-stack-gateway
    internal: true
```

No shell/curl exists by assumption inside this image; health is verified externally, not by an invented container healthcheck. Docker log files live in OrbStack's engine storage with the cap above; they are the unavoidable engine-level exception, not a new user/system application config. Access logs are disabled in the config below. Operational error logs still require review without printing secrets.

### `infra/agentgateway/config.template.json`

JSON is also valid YAML input. The placeholder is replaced before startup; never start the template as-is.

```json
{
  "config": {
    "adminAddr": "off",
    "statsAddr": "off",
    "readinessAddr": "off",
    "enableIpv6": false,
    "workerThreads": 1,
    "storage": {"mode": "readOnly"},
    "logging": {"level": "warn", "filter": "false"}
  },
  "gateways": {
    "foundation": {
      "port": 4000,
      "apiKey": {
        "mode": "strict",
        "keys": [{"keyHash": "sha256:__CLIENT_KEY_SHA256__", "metadata": {"user": "local-foundation"}}]
      }
    }
  },
  "routes": [
    {"name": "health", "matches": [{"path": {"exact": "/healthz"}}], "policies": {"directResponse": {"status": 200}}},
    {"name": "mcp-not-configured", "matches": [{"path": {"pathPrefix": "/mcp"}}], "policies": {"directResponse": {"status": 503}}},
    {"name": "not-found", "policies": {"directResponse": {"status": 404}}}
  ]
}
```

### `infra/agentgateway/prepare.py`

Existing Ubuntu Python, stdlib only. Creates only these project files; refuses to overwrite an existing key/config so repeat execution cannot silently rotate credentials or destroy configuration. State directory 0700, rendered file 0644: it contains only a high-entropy key's hash and must be readable by the non-root container through the single-file mount. Host-side state-directory access remains restricted. Preserve existing `.secrets` contents and modes.

```python
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
```

If preparation partially fails, stop and inspect the exact two paths; do not rerun by automatically deleting/rotating them. Neither file exists now.

### `infra/agentgateway/verify.py`

Existing Ubuntu Python calls existing macOS curl. Credentials travel via stdin to curl, not argv or shell expansion. No proxy, verbose tracing, token output, database calls or MCP tool calls.

```python
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parents[2]
key = (root / ".secrets/agentgateway-client-key").read_text().strip()
assert len(key) == 64 and all(c in "0123456789abcdef" for c in key)

def status(path, credential=None):
    config = "" if credential is None else 'header = "Authorization: Bearer ' + credential + '"\n'
    result = subprocess.run(
        ["macctl", "run", "/usr/bin/curl", "--config", "-", "--silent",
         "--show-error", "--noproxy", "*", "--max-time", "3",
         "--output", "/dev/null", "--write-out", "%{http_code}",
         "http://127.0.0.1:58080" + path],
        cwd=root, input=config, text=True, capture_output=True, timeout=10,
    )
    return int(result.stdout) if result.returncode == 0 and result.stdout.isdigit() else 0

deadline = time.monotonic() + 30
while status("/healthz", key) != 200:
    if time.monotonic() >= deadline:
        raise SystemExit("Gateway did not become ready; inspect sanitized operational logs")
    time.sleep(1)

for path in ["/healthz", "/mcp", "/ui", "/api/runtime", "/unmatched"]:
    for credential in [None, "invalid-foundation-key"]:
        actual = status(path, credential)
        if actual not in [401, 403]:
            raise SystemExit(f"Authentication rejection failed for {path}: HTTP {actual}")

for path, expected in [("/healthz", 200), ("/mcp", 503), ("/ui", 404),
                       ("/api/runtime", 404), ("/unmatched", 404)]:
    actual = status(path, key)
    if actual != expected:
        raise SystemExit(f"Route check failed for {path}: HTTP {actual}, expected {expected}")
print("PASS: authenticated health, missing/invalid-key rejection, unavailable MCP and no public UI/API")
```

## Exact command sequence after approval

Run from Ubuntu `/home/developer/workspace/mcp-stack`. Files above are materialized using `apply_patch` after approval, and ignore rules added before preparation. `HOST_REPO` below is task-specific, not a repurposed system variable. Passing explicit macOS paths avoids the known `macctl` absolute-container-path translation pitfall.

```sh
HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
macctl run docker ps -a --format '{{.ID}} {{.Names}} {{.State}} {{.Ports}}'
macctl run lsof -nP -iTCP:58080 -sTCP:LISTEN
python3 infra/agentgateway/prepare.py
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" config --quiet
macctl run docker pull --platform linux/arm64 ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" run --rm --no-deps -T agentgateway --version
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" up -d --no-deps --pull never agentgateway
python3 infra/agentgateway/verify.py
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" ps agentgateway
```

`lsof` returning 1 with no output means no listener, not a failed installation. If the image is already present, validate the identical digest instead of pulling unnecessarily. Refuse to reuse an unexpected existing container/network/config. Compose may warn about other `mcp-stack` containers being orphans because this overlay is invoked alone: **never use `--remove-orphans` or `down` to silence it**. This file is optional, not included by root Compose.

Record filtered existing container IDs, names, start timestamps, status/health and published ports before startup and compare after. Inspect only the new container's image identity, command, mounts, UID, limits, capability/security settings, network and published address; check there is no gateway volume or host/system config. Never dump full existing container environments or secret-bearing configuration. Capture the resolved binary version/revision and actual new image size. Logs/settings or runtime failures are not grounds for relaxing authentication, running as root or widening mounts/ports; stop and report if the approved constraints do not work.

Static checks before asking approval: the proposed rendered configuration is validated against the commit-pinned JSON schema using the **already available** Ubuntu `jsonschema` package. This is not a runtime parse/startup/negative-auth test. No new packages are installed. Runtime checks above remain pending; an externally verified route is not a Docker HEALTHCHECK or proof of MCP filtering. A same-config gateway recreation/persistence check is excluded from this first step and can be proposed separately.

## Data-preserving rollback after approval

Resolve the container's Compose labels first. Stop/remove **only the new gateway**, leaving existing containers, image, credentials and project configuration available for recovery:

```sh
HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" stop agentgateway
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" rm -f agentgateway
```

The empty project gateway network can be retained; do not remove shared networks, volumes or images as cleanup. No database migration or memory rollback is involved. Physical deletion of the retained key/config/image would need separate authorization.

## What follows, not covered by this approval

Synthetic two-target aggregation, tool discovery/call-denial, policy-error and outage tests require a separate bounded proposal. Then qualify Graphify's restricted transport and CodeGraph's one-writer transport independently, before any real server or selected harness registration. Basic Memory remains deferred; n8n, PKM, embedding/model setup and unrelated projects are not included. No Helm/Kubernetes setup is planned now.

## Primary evidence

- [Official v1.5.0 release](https://github.com/agentgateway/agentgateway/releases/tag/v1.5.0)
- [Commit-pinned configuration schema](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/schema/config.json)
- [Commit-pinned API-key authentication implementation](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/http/apikey.rs)
- [MCP session-isolation advisory](https://github.com/agentgateway/agentgateway/security/advisories/GHSA-mvgg-jvj2-4frq): fixed in v1.4.0, before this pin. Additional reviewed Kubernetes cross-namespace advisories and OpenAPI-conversion advisory do not require those features here. Published advisories are not a full dependency/container vulnerability audit.
- [Official Docker explicit-file setup](https://agentgateway.dev/docs/standalone/latest/documentation/setup/install/docker/)

Approval requested: create the listed project-local files/key, pull the exact official ARM64 image if absent, start only this gateway and perform only the foundation verification/targeted rollback above. Report results immediately afterward and stop before the next setup step.
