# Agentgateway synthetic MCP qualification

Status: **synthetic qualification completed after separately approved Host correction**, 2026-10-01. A authorized by “approve”; B by “Now contnue!” initially exposed the fixture mismatch; correction/retry authorized by “continue”. All eight gateway checks passed on retry, both temporary containers removed, protected resources unchanged. [Correction and full results](AGENTGATEWAY-SYNTHETIC-HOST-CORRECTION.md). Historical failed-run reports below are retained for audit. This is bounded synthetic qualification, not real memory-server integration.

## Historical approval B first run — not qualified until corrected retry

- Implemented the bounded gateway verifier in `infra/agentgateway/synthetic/verify.py`; AST and embedded direct-probe syntax passed. Recreated only the verified fixture from its exact existing image; direct tests passed again, and mounts/network/no published ports/non-root/read-only settings were inspected.
- Started only the proposed isolated gateway on macOS `127.0.0.1:58081`. Inspected exact official image ID, UID/GID 65532:65532, read-only root/hash config mount, loopback publication, sole synthetic network, 1 CPU/512 MiB/128 PIDs, dropped capabilities and no-new-privileges. Actual binary 1.5.0, release commit `fe6732474a96a0363dfb9822859af4e9bab360fa`, Rust 1.98.0/aarch64-unknown-linux-gnu. No download/build/host install or live gateway restart/config change.
- **1 of 8 matrix checks passed:** missing/invalid API keys rejected on all four MCP profiles. The other seven could not proceed: authenticated initialize returned HTTP 421, correctly recorded as failure rather than denied-tool/security success. No aggregation/CEL/discovery/call-denial/session/fanout guarantee established.
- Fixture operational logs recorded `Invalid Host header: fixture`; the reviewed SDK allowlist contains `fixture:8000` but not the observed portless `fixture`. Client-side localhost/port header probes did not fix the internal mismatch. No allowlist/config relaxation was applied. Proposed correction is a single explicit internal hostname addition, not a wildcard or disabled protection, requiring separate approval.
- One non-mutating version diagnostic initially failed because macctl translated absolute `/app/agentgateway` into a macOS path. Corrected invocation `docker exec ... ./app/agentgateway --version` succeeded; no container/config change was needed. Keep this path caveat for future diagnostics.
- Reported the failure, inspected exact Compose ownership, stopped/removed **only** the two temporary containers. Empty synthetic network and retained source/config remain; no volumes/files/images or real data removed. Foundation HTTP checks passed again on 58080.
- Fresh pre/post snapshots: all **19 pre-existing containers** identical in recorded identity/start/status/health/ports; all **260 protected file hashes** identical; checked macOS global mise/Codex configuration hashes identical. Existing Basic Memory, PG, notes/indexes, live gateway/key/config and already-stopped {{mstack:CLIENT_REPO}}/backend services unchanged. No Basic Memory calls or global harness registration.
- Next: obtain approval for the [exact fixture Host correction and bounded retry](AGENTGATEWAY-SYNTHETIC-HOST-CORRECTION.md); do not begin real-server integration while qualification is incomplete.

## Approval A completion report

- Created `infra/agentgateway/synthetic/{compose.yaml,config.template.json,prepare.py,fixture.py,verify.py,README.md}`. The template exactly matches the reviewed generator; all Python files and the embedded direct probe passed AST syntax checks, Compose validation passed, and the template passed the pinned gateway JSON schema with a dummy hash.
- Prepared only ignored `infra/agentgateway/state/synthetic/config.json`: directory 0700, hash-only config 0644. Reused the existing client key without rotation; original key/config hashes remained unchanged. No plaintext key mounted in either test definition.
- Started only `mcp-stack-gateway-fixture` in Compose project `mcp-stack-gateway-test`. Inspected exact approved image ID, Linux ARM64, UID/GID 501:501, read-only root and sole script bind mount, no published ports, one dedicated bridge, capabilities dropped, no-new-privileges, 1 CPU / 256 MiB / 128 PIDs and restart policy `no`. No download/build/host install or Graphify import.
- Direct runtime versions verified: Python 3.12.14, official MCP SDK 1.29.0, Starlette 1.3.1, uvicorn 0.47.0. Both alpha and beta negotiated MCP 2025-11-25, listed exactly echo/blocked, dispatched both tools plus the synthetic prompt/resource, and returned the correct target-specific content. Each corresponding dispatch counter was exactly 1.
- Invalid Host rejected with HTTP 421; invalid Origin rejected with HTTP 403 on both endpoints. Beta outage control produced HTTP 503 while alpha discovery remained available; beta discovery recovered after restoration. Finally restored beta and reset all counters to zero.
- Reported setup/test success, then inspected ownership and stopped/removed **only** that fixture. Its disposable in-memory sessions/counters were discarded; no files, images or volumes deleted. The fixture is reproducible from retained source/image. Dedicated network retained empty; ignored config and source retained. No cleanup failure or setup deviation.
- Fresh pre/post snapshots: all **19 pre-existing containers** identical in recorded identity/start/status/health/ports; all **260 protected file hashes** identical, including live gateway/key/config, root Compose/mise, memory/graph state and checked Ubuntu harness config. Checked macOS global mise/Codex configuration hashes also identical. Foundation HTTP verifier passed again on 58080; no Basic Memory calls. {{mstack:CLIENT_REPO_TITLE}}/backend services already stopped in the fresh baseline remained unchanged.
- **No test gateway, aggregation or gateway CEL-policy/session/outage enforcement test ran.** `verify.py --fixture-only` is implemented and verified; its default mode explicitly refuses gateway qualification until approval B and that verifier implementation. Direct fixture Host/Origin checks are not gateway security results.

At the approval A checkpoint the next request was B; B and its separately approved corrected retry have since run as described above. Live gateway on 58080 remains unchanged; no real memories/harness integration.

## Outcome and boundaries

Temporarily run a second gateway and one Python fixture container hosting two logical MCP servers. Verify aggregation, discovery filtering, pre-dispatch denial, runtime policy errors, session isolation and backend-outage behavior without changing the foundation gateway on macOS `127.0.0.1:58080`.

No new packages, builds, image pulls, models, paid APIs, database changes, global configuration, Ubuntu mise configuration or harness registration. No Basic Memory calls, real graph imports, corpus mounts, watchers or indexing. n8n, Notion/AppFlowy, backups/restores and the standalone host/VM workflow skill remain later steps. Helm remains excluded.

Read-only discovery found the existing images below present and port 58081 unoccupied; recheck immediately before starting. {{mstack:CLIENT_REPO_TITLE}} database and Studio containers were already stopped during discovery, unlike the earlier foundation checkpoint. Do not restart or investigate them in this step; compare against a fresh baseline, not historical running-state assumptions.

## Exact artifacts and execution domain

- Test gateway: existing official agentgateway **1.5.0**, Linux ARM64, `ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896`. Release source commit `fe6732474a96a0363dfb9822859af4e9bab360fa`.
- Fixture runtime: existing project Graphify **0.9.72** image by exact local Docker image ID `sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac`. Its Python **3.12.14**, official MCP SDK **1.29.0**, Starlette **1.3.1** and uvicorn **0.47.0** supply the runtime. Override its entrypoint; do not import or launch Graphify. This is runtime reuse, not a Graphify HTTP adapter or another FastMCP installation. An absent/mismatched image is a blocker, not permission to pull/build a replacement.
- Both containers use the existing macOS OrbStack Docker engine through `macctl run docker`. Local preparation/verifier use existing Ubuntu Python, without dependencies or auto-install.
- Separate Compose project `mcp-stack-gateway-test`; only services `fixture` and `test-gateway`; fixed container names below. Never include the root Compose file.
- Dedicated normal bridge `mcp-stack-gateway-synthetic`, with only these two containers; no connection to live gateway/memory/{{mstack:CLIENT_REPO}} networks. Normal bridges permit outbound connectivity; this is not an egress sandbox. The fixture/test configuration makes no external calls.
- Only gateway port published: macOS **127.0.0.1:58081 → 4000**. Fixture internal port **8000**, unpublished. Gateway management, metrics, readiness listeners and request logging disabled as in the foundation.
- Resource ceilings: gateway 1 CPU / 512 MiB; fixture 1 CPU / 256 MiB; each 128 PIDs and 16 MiB `/tmp`. These are ceilings, not expected steady-state usage. Both transient, `restart: "no"`.

## Project files (created under approval A)

All runtime definitions stay under `infra/agentgateway/synthetic/`:

- `compose.yaml`: exact overlay below.
- `config.template.json`: the configuration produced by the pure generator below, retaining the hash placeholder.
- `prepare.py`: locate repository from its own path; read the existing `.secrets/agentgateway-client-key`; validate its format; hash it without printing; create only `infra/agentgateway/state/synthetic/` (0700) and its new `config.json` (0644). Refuse existing output/symlinks. Never overwrite/rotate the foundation key/config. The gateway receives only the hash; the fixture receives neither key nor config.
- `fixture.py`: two independent low-level SDK servers and their Streamable HTTP managers, Starlette mounts, in-memory counters/outage control, as specified below. No filesystem writes, models, Graphify imports or application credentials.
- `verify.py`: Ubuntu standard-library verifier; macOS curl via stdin configuration for requests and synthetic-container-only `docker exec` for counters/control. No secrets in argv/environment/output. Fixed endpoints and container name; bounded timeouts; sanitized PASS/FAIL output.
- `README.md`: approved scope, commands, results and recovery.

`infra/agentgateway/state/` is already ignored. Retain synthetic configuration and sanitized results there for diagnosis; no notes/indexes/volumes are created or removed. Update this proposal and repository status/TODO links after the approved step. Root Compose, `infra/mise.toml`, agent instructions, existing configurations and all user/system-level files remain unchanged.

### Compose overlay

Invoke with the repository as `--project-directory`; relative bind paths deliberately resolve there, not beside this overlay.

```yaml
name: mcp-stack-gateway-test
services:
  fixture:
    image: sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac
    platform: linux/arm64
    pull_policy: never
    container_name: mcp-stack-gateway-fixture
    user: "501:501"
    entrypoint: ["python"]
    command: ["/fixture/fixture.py"]
    environment:
      PYTHONDONTWRITEBYTECODE: "1"
      PYTHONUNBUFFERED: "1"
    restart: "no"
    read_only: true
    init: true
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    cpus: 1
    mem_limit: 256m
    pids_limit: 128
    stop_grace_period: 10s
    networks: [synthetic]
    tmpfs: ["/tmp:rw,nosuid,nodev,noexec,size=16777216,mode=1777"]
    volumes:
      - type: bind
        source: ./infra/agentgateway/synthetic/fixture.py
        target: /fixture/fixture.py
        read_only: true
        bind: {create_host_path: false}
    logging:
      driver: json-file
      options: {max-size: "5m", max-file: "2"}
  test-gateway:
    image: ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896
    platform: linux/arm64
    pull_policy: never
    container_name: mcp-stack-gateway-synthetic
    user: "65532:65532"
    command: ["-f", "/config/config.json"]
    restart: "no"
    read_only: true
    init: true
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    cpus: 1
    mem_limit: 512m
    pids_limit: 128
    stop_grace_period: 10s
    ports: ["127.0.0.1:58081:4000"]
    networks: [synthetic]
    tmpfs: ["/tmp:rw,nosuid,nodev,noexec,size=16777216,mode=1777"]
    volumes:
      - type: bind
        source: ./infra/agentgateway/state/synthetic/config.json
        target: /config/config.json
        read_only: true
        bind: {create_host_path: false}
    logging:
      driver: json-file
      options: {max-size: "5m", max-file: "2"}
networks:
  synthetic:
    name: mcp-stack-gateway-synthetic
    internal: false
```

### Exact proposed gateway configuration

This pure generator defines the template; it performs no IO. Each MCP route contains **one backend with two targets**, not two load-balanced backends. All routes explicitly attach to the named gateway. Authorization evaluates original target/tool names before gateway prefixing.

```python
from copy import deepcopy

backend = {"mcp": {
    "targets": [
        {"name": "alpha", "mcp": {"host": "http://fixture:8000/alpha/mcp"}},
        {"name": "beta", "mcp": {"host": "http://fixture:8000/beta/mcp"}},
    ],
    "statefulMode": "stateful",
    "prefixMode": "always",
    "failureMode": "failClosed",
    "dnsRebindingProtection": True,
}}
profiles = {
    "aggregate": 'mcp.tool.name == "echo" && mcp.tool.target in ["alpha", "beta"]',
    "alpha-only": 'mcp.tool.name == "echo" && mcp.tool.target == "alpha"',
    "deny": 'false',
    "policy-error": 'mcp.tool.name == "echo" && jwt.sub == "synthetic-admin"',
}
configuration = {
    "config": {
        "adminAddr": "off", "statsAddr": "off", "readinessAddr": "off",
        "enableIpv6": False, "workerThreads": 1,
        "storage": {"mode": "readOnly"},
        "logging": {"level": "warn", "filter": "false"},
    },
    "gateways": {"synthetic": {
        "port": 4000,
        "apiKey": {"mode": "strict", "keys": [{
            "keyHash": "sha256:__CLIENT_KEY_SHA256__",
            "metadata": {"user": "local-synthetic-test"},
        }]},
    }},
    "routes": [{
        "name": "health", "gateways": ["synthetic"],
        "matches": [{"path": {"exact": "/healthz"}}],
        "policies": {"directResponse": {"status": 200}},
    }],
}
for name, rule in profiles.items():
    configuration["routes"].append({
        "name": name, "gateways": ["synthetic"],
        "matches": [{"path": {"exact": "/" + name}}],
        "policies": {"mcpAuthorization": {"rules": [rule]}},
        "backends": [deepcopy(backend)],
    })
configuration["routes"].append({
    "name": "not-found", "gateways": ["synthetic"],
    "policies": {"directResponse": {"status": 404}},
})
```

Never represent deny-all as `rules: []`: pinned upstream treats an absent/empty rule set as permissive. These are explicit allow rules, not deny expressions whose evaluation errors could fail to deny. `failureMode: failClosed` handles backend fanout failure; it is separate from authorization-error behavior and both need runtime testing.

The `policy-error` expression intentionally references a missing JWT claim while authenticating with an API key. It must compile and reach runtime evaluation; configuration rejection is **not** a passing runtime fail-closed test. Do not silently replace it with `false`, install a JWT provider or relax another policy if qualification fails. DNS rebinding protection must remain enabled; the verifier uses `http://127.0.0.1:58081` without browser Origin headers.

### Fixture and verifier contracts

Use official SDK `Server`, not FastMCP. Each server has its own `StreamableHTTPSessionManager(json_response=True, stateless=True)` and root lifespan enters each manager through `AsyncExitStack`. Mount their ASGI apps at `/alpha` and `/beta`; gateway targets `/alpha/mcp` and `/beta/mcp`. Bind uvicorn to `0.0.0.0:8000` inside the unpublished container, with access logs disabled. SDK transport Host allowlist after separately approved correction: `fixture`, `fixture:8000`, `127.0.0.1:8000`, `localhost:8000`; no wildcard/disabled rebinding protection.

Each server advertises tool `echo` (synthetic text only) and `blocked`, prompt `blocked_prompt`, and resource `synthetic://<target>/blocked`. Handlers increment in-memory per-target counters before returning only constant/echo fixture data. Counter keys: `echo`, `blocked`, `prompt`, `resource`. Counter/control paths are not MCP tools and not routed through the gateway. Fixture `GET /stats` returns counters; `POST /control` toggles only beta request handling between normal behavior and HTTP 503, without stopping a container. No persistent counter files.

Before treating a rejected call as a security pass, verify the fixture itself advertises and dispatches the correct raw names on each endpoint, then reset counters. Read/control it only via `macctl run docker exec mcp-stack-gateway-fixture python -c ...` with standard-library `urllib.request` to `127.0.0.1:8000`. This also supports bounded direct fixture MCP probes; no host port needed. Pass `python`, not an absolute Linux binary path, to avoid macctl argument translation.

The verifier sends macOS curl requests with the key and JSON payload via `--config -` stdin. Never put the key in shell arguments, env variables or printed exceptions. Capture headers/body/status; support JSON and SSE responses; negotiate initialize, send `notifications/initialized`, and preserve `Mcp-Session-Id` and negotiated protocol version. Require expected JSON-RPC IDs and bounded responses. A curl failure, connection timeout, malformed response or unrelated fixture error is a **test failure**, not evidence of denied access. Cap requests at 10 seconds, each probe sequence at 30 seconds and the entire verifier at 180 seconds.

## Required verification matrix

| Check | Passing result |
| --- | --- |
| Missing/wrong API key | Rejected at gateway; no fixture handler dispatched |
| `/aggregate` discovery | Exactly `alpha_echo`, `beta_echo`; same raw name does not collide |
| Allowed tool calls | Correct target/text; only that target's echo counter increments |
| Hidden tool direct call | Both `<target>_blocked` calls rejected; blocked counters stay zero |
| `/alpha-only` | Only `alpha_echo`; direct `beta_echo` rejected with beta echo counter unchanged |
| `/deny` | Empty tools/prompts/resources discovery; valid direct calls denied with all dispatch counters unchanged |
| `/policy-error` | Config compiles; missing-claim evaluation grants nothing; tool discovery empty and direct echo rejected without dispatch |
| Prompt/resource bypass | No advertised prompts/resources; correctly prefixed direct get/read rejected without handler increments |
| Session isolation | Two independent allowed sessions work; reusing aggregate session on alpha-only cannot obtain/call beta; unknown sessions rejected |
| Backend outage | Beta HTTP 503 causes aggregate discovery/initialization error rather than successful partial alpha-only inventory |
| Recovery | Restore beta in `finally`; fresh aggregate session again discovers/calls both echo tools |
| Protection/cleanup | Only two approved containers changed; original gateway/key/config, protected files and other containers unchanged; foundation checks still pass |

For normal resource URIs the pinned gateway uses `alpha+synthetic://alpha/blocked` / `beta+synthetic://beta/blocked`; prompts/tools use `<target>_<original-name>`. Validate these against successful raw fixture probes and pinned source before counting a denial. Test both discovery and direct-call paths: hiding a name alone is not sufficient.

Record exact protocol errors/statuses and sanitized counter deltas per test. A gateway startup error is a qualification failure. Passing these synthetic tests does not establish real-server compatibility, all protocol-method security, trustworthy automatic task detection, production security or load capacity. Profile endpoints are selected explicitly by the verifier, not automatically by n8n or a harness. Same-key synthetic profiles are not user/tenant separation; later real profiles need separately scoped client authorization.

## Command sequence (A completed; B requires separate approval)

First inspect existing container/network names, both exact images, port ownership, existing key/config hashes and protected files, plus current macOS/Ubuntu tool configuration. Stop on conflicts; do not recycle another resource or stop {{mstack:CLIENT_REPO}}. Create the reviewed files using `apply_patch`, syntax/schema-check without bytecode writes, and then run:

```sh
python3 infra/agentgateway/synthetic/prepare.py
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml config --quiet
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml up -d --no-build --pull never fixture
```

Inspect the fixture's sole bind mount/network/security settings and verify direct synthetic dispatch/readiness. Report fixture setup, then **ask separately for approval B before starting the test gateway**. Stop/remove the fixture after its direct test so approval A leaves no persistent service; its RAM-only counters can be recreated for B. If it fails, report and clean up only the fixture; do not start the test gateway.

Approval B, if subsequently granted, restarts only the verified fixture and starts the isolated test gateway:

```sh
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml up -d --no-build --pull never fixture
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml up -d --no-build --pull never --no-deps test-gateway
python3 infra/agentgateway/synthetic/verify.py
```

Report actual test gateway version, mounts/network/loopback binding, resources and startup before testing. Verification controls affect only the disposable fixture, never lifecycle of the real graph/database services. After testing, success or failure, resolve the exact two container targets and always stop/remove only them:

```sh
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml stop test-gateway fixture
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml rm -f test-gateway fixture
python3 infra/agentgateway/verify.py
```

The same targeted stop/remove commands are rollback. For approval A use only `stop fixture` and `rm -f fixture` on the same explicit project/file, never target the unapproved test gateway. Removal discards only disposable in-memory counters/sessions; no volumes/data files/images are deleted. Retain the empty dedicated network and generated config/source/report for diagnosis, explicitly report this retained state. Do not run `down`, `--remove-orphans`, pruning or key rotation. If cleanup fails, report exact remaining targets/port and request direction rather than touching other services.

Compare fresh pre/post container identity/start/status/health/ports and protected file hashes. Report fixture setup, test gateway setup, each failure/deviation, cleanup and unchanged foundation separately, then stop before proposing any real MCP transport integration. Changed images, ports, auth policy, mounts, package additions or real-server connections need new approval.

## Primary evidence

- [Pinned 1.5.0 schema](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/schema/config.json): targets, prefix/state/failure settings and policy shapes.
- [Pinned MCP authorization](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/rbac.rs) and [HTTP rule evaluation](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/http/authorization.rs): empty-rule behavior and explicit allow/require versus deny-error handling.
- [Pinned handler](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/handler.rs): original-name authorization, prefixes and resource URI namespaces.
- [MCP authorization documentation](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authz/): discovery and access policies. Pinned source takes precedence over moving latest docs.
- [Official SDK 1.29.0 low-level HTTP example](https://github.com/modelcontextprotocol/python-sdk/blob/v1.29.0/examples/servers/simple-streamablehttp-stateless/mcp_simple_streamablehttp_stateless/server.py) and [session manager](https://github.com/modelcontextprotocol/python-sdk/blob/v1.29.0/src/mcp/server/streamable_http_manager.py): no new FastMCP dependency needed.

## Original approval B request (authorized, executed and cleaned up)

Approval A above is completed; do not rerun preparation over the retained config. **Approve B:** recreate only the verified fixture, start only the isolated test gateway on loopback 58081 with the existing exact official image and hash-only configuration, implement/run the gateway matrix, then stop/remove both temporary containers. Report each setup and cleanup. No live-gateway restart/config change, pulls/packages, global config or real memory-server connection is authorized by B.

Static validation, direct fixture tests and all eight gateway checks now passed after the separately approved correction. No approval remains pending for this completed synthetic phase. Real Graphify/CodeGraph transport/gateway/harness work needs new exact proposals; Basic Memory remains deferred.
