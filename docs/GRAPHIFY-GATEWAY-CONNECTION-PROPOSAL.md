# Graphify persistent HTTP backend and later gateway connection

Status (2026-10-01): **A approved with “Continue” and completed; B separately approved/completed with a recorded limitation**. The previous
[temporary HTTP direct qualification](GRAPHIFY-HTTP-SETUP-PROPOSAL.md) is complete.
Approval A below records its completed step. Gateway connection B subsequently
received separate confirmation; see the [B results and malformed-URI limitation](GRAPHIFY-GATEWAY-B-PROPOSAL.md).
A did not bundle that approval. Preserve A's original scope/history below.

## A completion report

- Created `infra/graphify/http/service.compose.yaml` with exactly the four
  approved definition changes; Compose validation passed. Extended the direct
  verifier with `--service` and fixed-name/project/service/restart assertions.
- Started `mcp-stack-graphify-http` on the existing macOS OrbStack engine, exact
  pinned ARM64 image, `unless-stopped`, no published ports, sole internal network,
  seven read-only binds and unchanged privilege/resource/log limits. It remains
  running. No Docker HEALTHCHECK is configured; authenticated readiness passed.
- Runtime versions: Graphify 0.9.72, Python 3.12.14, official MCP SDK 1.29.0,
  Starlette 1.3.1, uvicorn 0.47.0. No pull, rebuild or package/model installation.
- All direct tests passed: missing/wrong/duplicate authentication; seven useful
  tools; excluded PR and foreign-project dispatch gates; six scoped resources and
  invalid URI denial; Host/Origin; fresh initialize/reconnect/concurrent reads;
  unchanged three-source/index hashes. The graph remains 37 nodes/48 edges.
- Gateway foundation verifier passed. All **19 pre-existing container snapshots
  and 267 protected file hashes** match the fresh baseline; exactly one new
  container was added. Checked macOS mise/Codex hashes also match. The larger
  protected count than the previous HTTP checkpoint reflects additional protected
  config/key paths in this baseline, not new memory data.
- Compose warned that the gateway/Basic Memory/PostgreSQL containers are orphans
  relative to this optional overlay. No orphan cleanup was performed; all three
  are intentionally managed through separate definitions and remain unchanged.
- Keys/hash configs, wrapper/seven-tool gate, narrow index and root/mise config
  were retained. No Basic Memory call, database change, gateway wiring, harness
  registration, watcher, model or {{mstack:CLIENT_REPO}} action occurred.
- Data-preserving rollback below remains available. No cleanup is required;
  stopping this service preserves all retained files/image/network. Automatic
  restart after a Docker/host restart has not been exercised.

## What “Graphify HTTP” means

It is a project-local HTTP adapter around the existing restricted Graphify MCP
server, not a remote Graphify provider or a second graph engine. One container
runs the adapter and Graphify together. The graph remains the existing read-only
three-file projection; HTTP does not add indexing, models or automatic memory.

The intended later path is harness → agentgateway → Graphify HTTP → existing
Graphify graph. Gateway wiring is now implemented through separate B; harness
registration is not. Basic Memory and CodeGraph are not gateway backends.

## Approval A — persistent Graphify backend only

Target: existing **macOS OrbStack Docker engine**, invoked from Ubuntu through
`macctl run`. No macOS/Ubuntu CLI, mise, package or image installation is needed.
Fresh read-only checks found the exact ARM64 image present and
`mcp-stack-graphify-transport` internal and empty. Repeat these checks and inventory
all existing containers immediately before the approved start.

Reuse without rebuild/pull:

- Graphify 0.9.72, source commit `1cd9a36c0c57a661d2d2234bc3207e887e1ba104`.
- Local immutable image ID `sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac`.
- Python 3.12.14, official MCP SDK 1.29.0, Starlette 1.3.1, uvicorn 0.47.0,
  already in that image. No standalone FastMCP service/package is added.
- Existing `serve_http.py`, unchanged seven-tool `serve_filtered.py`, backend
  credential and hash config. Do not rerun `prepare.py` or rotate credentials.

### Exact file changes

Create `infra/graphify/http/service.compose.yaml` by copying the qualified
`infra/graphify/http/compose.yaml` definition, with **only** these changes:

| Field | Qualified temporary definition | Persistent definition |
| --- | --- | --- |
| Top-level `name` | `mcp-stack-graphify-http-test` | `mcp-stack` |
| `container_name` | `mcp-stack-graphify-http-test` | `mcp-stack-graphify-http` |
| `restart` | `"no"` | `unless-stopped` |
| Network declaration | Named network with `internal: true` | Same named network with `external: true`; remove `internal` from the declaration |

`external: true` means Compose reuses an existing Docker network, **not** that it
is publicly accessible. Verify Docker's actual `Internal: true` before use;
abort on a missing, non-internal or unexpectedly occupied network. Never combine
the temporary and persistent Compose files: conflicting network definitions
must not be merged. The temporary definition stays unchanged.

Update `infra/graphify/http/verify.py` with an explicit `--service` option for this
fixed persistent container name, `unless-stopped` restart policy and Compose
ownership checks (`project=mcp-stack`, `service=graphify-http`). Default remains
the qualified temporary-container verifier. Keep all direct authentication,
tool/resource/scope/Host/Origin/reconnect/concurrent-read tests unchanged. No
auto-start, new dependency or relaxed security assertion.

Update the HTTP README and project status/TODO with actual results after setup.
No root Compose, mise, live gateway config/key, wrapper, gate, index or source
projection edit is included.

### Unchanged runtime, mounts and persistence

- No published port. Container listens on 8000, canonical `/mcp/` and authenticated
  `/healthz`; only the internal transport network is attached. No egress network.
- UID/GID `501:501`; read-only root; init; all capabilities dropped;
  no-new-privileges; 1 CPU, 512 MiB RAM, 128 PIDs; stop grace 10 seconds.
- `python /opt/mcp-stack/serve_http.py`; `pull_policy: never`;
  container-only 64 MiB `/tmp` tmpfs with noexec/nosuid/nodev.
- Environment remains `GRAPHIFY_NO_AUTO_REFRESH=1`,
  `GRAPHIFY_QUERY_LOG_DISABLE=1`, `PYTHONDONTWRITEBYTECODE=1`,
  `PYTHONUNBUFFERED=1`, `HOME=/tmp/graphify-home`,
  `XDG_CACHE_HOME=/tmp/graphify-cache`, `XDG_CONFIG_HOME=/tmp/graphify-config`.
  These paths are inside the container, not host/global configuration.
- All seven bind mounts remain read-only, with `create_host_path: false`:
  `serve_http.py` → `/opt/mcp-stack/serve_http.py`;
  `serve_filtered.py` → `/opt/mcp-stack/serve_filtered.py`;
  `infra/graphify/state/http/server.json` → `/config/server.json`;
  `infra/graphify/state/mcp-stack` → `/state`;
  `scripts/verify-basic-memory.py`, `scripts/verify-codegraph.py` and
  `infra/graphify/fixtures/call-chain.py` → their existing absolute repository
  paths. Projected scripts are graph source only, never executed/imported.
- Ignored `.secrets/graphify-http-backend-key` remains 0600, not mounted into
  Graphify; hash-only `server.json` remains 0644 within protected state directories.
  No new credentials, durable volumes, files in system config or database access.
- Existing graph: 3 files, 37 nodes, 48 edges, 6 communities. No corpus expansion,
  extraction, watcher, LLM/model download, paid API or Basic Memory call.
- Engine logs remain bounded to two 5 MB files. No Docker HEALTHCHECK is added;
  process running/restart policy alone is not authenticated MCP health.

### Exact start, verification and rollback commands

Run only after A is approved. `--project-directory` deliberately resolves the
relative mounts against the macOS repository, not the overlay directory.

```sh
MCP_STACK_HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
macctl run docker network inspect mcp-stack-graphify-transport
macctl run docker image inspect sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/graphify/http/service.compose.yaml" config --quiet
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/graphify/http/service.compose.yaml" up -d --no-deps --no-build --pull never graphify-http
python3 infra/graphify/http/verify.py --service
python3 infra/agentgateway/verify.py
```

The direct verifier supplies the private credential over stdin, never argv,
environment or printed output. Capture inspection privately, check container
ownership and mounts, compare existing container identities/start/status/health/
ports and protected source/state/key/config hashes before and after. Existing
Basic Memory/PostgreSQL/gateway and every {{mstack:CLIENT_REPO}} resource must stay unchanged.
Only one new Graphify container/network membership is expected.

On success leave Graphify running and report results before presenting B. On
failure, report sanitized diagnostics and stop only the newly owned Graphify
service using the data-preserving rollback explicitly included in A:

```sh
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/graphify/http/service.compose.yaml" stop graphify-http
```

Retain the stopped container, image, index, credentials, config and network. Do
not use `down`, `--remove-orphans`, prune, volume removal or unrelated lifecycle
commands. File creation is versionable but does not authorize commit/push.

## Later B — gateway connection, not part of approval A

After A succeeds, prepare exact files/commands and ask again. Proposed direction:

- Join only agentgateway to the existing internal Graphify network, preserving
  its existing gateway network and loopback 58080 listener. Graphify remains
  internal-only. No new public listener or network for other memory components.
- Add an explicit Graphify endpoint, likely `/mcp/graphify`, preserving the
  foundation `/healthz` and bare `/mcp` placeholder behavior. Seven permitted
  query tools only initially; qualify discovery **and** direct-call denial.
  This endpoint is not automatic task classification or harness integration.
- Use a distinct static backend credential, **not** the incoming gateway client
  key. The pinned 1.5.0 [schema](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/schema/config.json)
  supports `backendAuth.key.value` file references. Prefer a protected,
  ignored project-local runtime copy mounted read-only into the non-root gateway
  rather than embedding plaintext into its hash-only foundation config. Exact
  file permissions, header behavior and runtime reads must be qualified in B;
  do not loosen existing key permissions or assume schema support proves runtime
  integration. See [official backend authentication documentation](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/backend-authn/).
- A gateway recreate/config/mount change may briefly interrupt 58080. B must
  explicitly approve it, its tests and rollback to the unchanged foundation.
  Read-only single-file bind mounts need care when atomically replacing files.
- Verify actual inter-container HTTP, authentication separation, useful graph
  results, seven-tool discovery/denial, scoped arguments and concurrent sessions.
  Existing synthetic fail-closed qualification is not a claim that this live
  Graphify connection has already passed. Stop and report before CodeGraph.

Excluded from both stages: {{mstack:CLIENT_REPO}} work, Basic Memory usage/integration/models,
CodeGraph connection/index/watcher changes, n8n, PKM, global harness registration,
Ubuntu mise, VM migration and standalone workflow-skill extraction.
