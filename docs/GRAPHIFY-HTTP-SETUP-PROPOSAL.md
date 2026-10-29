# Graphify restricted HTTP transport — direct qualification

Status: **approved with “Approve” and completed**, 2026-10-01. Restricted HTTP wrapper installed/directly qualified; temporary container stopped/removed. No persistent service, gateway connection or harness registration. This follows completed [synthetic gateway qualification](AGENTGATEWAY-SYNTHETIC-HOST-CORRECTION.md). Approved scope/definitions below are retained as the runbook, not ongoing lifecycle authorization.

## Completion report

- Created only the five approved project files: `infra/graphify/http/{compose.yaml,serve_http.py,prepare.py,verify.py,README.md}`. Compose/wrapper match the reviewed code; AST/embedded-probe syntax and Compose validation passed. Existing `serve_filtered.py`, stdio overlay, projected source files, root Compose and mise declarations were not edited. No upstream patch or additional FastMCP framework.
- Prepared distinct ignored `.secrets/graphify-http-backend-key` (0600) and hash-only `infra/graphify/state/http/server.json` (0644; parent 0700). Backend key differs from gateway client key; digest correspondence verified without printing credentials. No plaintext token mounted or supplied through argv/env. Credential/config retained; preparation refuses overwriting them.
- Started only `mcp-stack-graphify-http-test` using exact existing Linux ARM64 image ID `sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac`. Verified UID/GID 501:501, read-only root/seven exact read-only binds, no host ports, sole internal network `mcp-stack-graphify-transport`, dropped capabilities/no-new-privileges, 1 CPU/512 MiB/128 PIDs, temporary `/tmp`, restart `no`, query/update opt-outs and no model/provider keys. Runtime verified Python 3.12.14 / Graphify 0.9.72 / official SDK 1.29.0 / Starlette 1.3.1 / uvicorn 0.47.0. No pull/build/package/mise/toolchain changes.
- Reported setup before tests. All direct HTTP acceptance checks passed, including the exact gate markers and meaningful results described below. No projected source script was imported/executed; no re-extraction, watcher or Basic Memory/CodeGraph call. Read-only graph/source hashes stayed identical during queries; retained scope remains 3 files/37 nodes/48 edges/6 communities/zero original LLM tokens, not full repository knowledge.
- Inspected exact ownership/image, then stopped/removed **only** the test container. Internal network retained empty; no volumes/images/notes/indexes deleted. RAM-only process/cache state discarded; wrapper, credential/hash config and original index retained for approved reproduction. No cleanup failure, startup/test failure or security/config deviation.
- Fresh pre/post snapshots: **all 19 pre-existing container records** identical in identity/start/status/health/ports; **all 260 pre-existing protected-file hashes** identical. The complete map gained exactly one intentional new entry, `infra/graphify/state/http/server.json` (261 afterward), not a changed/deleted existing file. Checked macOS global mise/Codex hashes identical. Existing memory/graph data/root Compose/project mise/checked Ubuntu configuration preserved; no live gateway/key/config edits or {{mstack:CLIENT_REPO}}/backend lifecycle actions. Foundation HTTP verifier passed again at 58080.

| Direct HTTP check | Observed result |
| --- | --- |
| Authentication | Missing/wrong/duplicate keys: 401 with empty body on health and MCP |
| Path/version | Canonical `/mcp/`; valid-key `/mcp` redirects 307; initialize `graphify` version 1.29.0 (SDK, not package) |
| Discovery | Exactly seven permitted tools; no project selector, unexpected capabilities, prompts or resource templates |
| Useful queries | All seven tools returned expected fixture/node/community/neighbors/path/ranking/stats results |
| Tool scope | Three PR tools and foreign `project_path` rejected with `isError` + original pre-dispatch `mcp-stack gate:` marker |
| Resources | Exactly six scoped URIs/read results; unknown/file/foreign-selector URIs rejected with explicit RPC -32602 gate error |
| Host/Origin | Intended internal hostname with/without port accepted; unrelated Host 421, Origin 403 |
| Read-only/reconnect | Fresh initialization/reconnect and actual concurrent read-only calls passed; source/index hashes unchanged |

`GRAPH_REPORT.md` remains absent as expected from original minimal extraction; resource returns the verified missing-report result rather than triggering extraction. Backend is stateless HTTP, not a tenant/session authorization layer. Tests ran inside the container via HTTP loopback; **actual gateway-to-backend traffic and backend-secret handling in gateway config are not verified**. No public access/TLS/load/full-corpus certification or automatic task-profile routing implied.

Next proposed phase: prepare exact persistent-service/network/backend-auth/gateway connection plan using this qualified wrapper, preserving its read-only scope/gates and explicitly reviewing secret-bearing configuration permissions. Obtain separate approval before starting it or editing live gateway routes/networks. CodeGraph's separate transport/one-writer design follows independently; Basic Memory integration remains deferred.

## Decision and single-step scope

Reuse the installed Graphify image and the existing seven-tool restricted factory; add a small official-SDK Streamable HTTP wrapper. Directly qualify it in **one temporary container with no published ports**, then stop/remove that container. Gateway connection and a persistent Graphify service are later, separately approved steps.

No pull/build/package install, standalone FastMCP, mise change, model/API, full-repository extraction, watcher, new graph, Basic Memory call, CodeGraph process/writer, harness registration or n8n/PKM setup. Live gateway on 58080, Basic Memory/PG and {{mstack:CLIENT_REPO}} stay untouched. This adapts transport, not graph content or memory routing.

Read-only qualification found the exact image already present, the new file/container/network names unused, and retained Graphify graph still **3 files / 37 nodes / 48 edges / 6 communities**. Those three files are `scripts/verify-basic-memory.py`, `scripts/verify-codegraph.py`, `infra/graphify/fixtures/call-chain.py`. Mounting a test script as indexed source does not import/run that script or query Basic Memory/CodeGraph. Recheck provenance/state and resource names immediately before startup. This narrow index is not complete repository knowledge.

## Artifact, domain and isolation

- Existing local immutable Docker image ID **`sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac`**, Linux ARM64, Graphify **0.9.72** / source commit `1cd9a36c0c57a661d2d2234bc3207e887e1ba104`.
- Existing dependencies: Python **3.12.14**, official MCP SDK **1.29.0**, Starlette **1.3.1**, uvicorn **0.47.0**. Version checks at startup; absent/mismatched image is a blocker, not permission to download a replacement. Do not execute upstream CLI auto-install/refresh paths.
- Existing macOS OrbStack Docker/Compose through `macctl`; preparation/verifier use existing Ubuntu standard-library Python. No Ubuntu mise or duplicated Docker client installation.
- Separate Compose project **`mcp-stack-graphify-http-test`**, service `graphify-http`, container **`mcp-stack-graphify-http-test`**, network **`mcp-stack-graphify-transport`**, internal bridge (`internal: true`). No joins to live gateway/memory/{{mstack:CLIENT_REPO}} networks, no Docker socket/home/credential/corpus-root mounts.
- Container-only HTTP **8000**, path `/mcp`; **no host port**. Bind 0.0.0.0 only inside the isolated container. Direct verifier uses `docker exec` HTTP to 127.0.0.1:8000, not host publication. This bypasses a cross-container hop intentionally; real gateway transport needs later testing.
- UID/GID 501:501, read-only root and every bind, 1 CPU/512 MiB/128 PIDs, 64 MiB noexec `/tmp`, capabilities dropped, no-new-privileges, restart `no`. No persistent test process after completion. Retain only new source, credential/hash config and empty network.
- Preserve existing query/update opt-outs and container-local temporary home/cache settings; never alter host homes/caches or global settings.

## Approved files and credentials

Created under this approval via `apply_patch`:

- `infra/graphify/http/compose.yaml`: overlay below; root Compose and old Graphify overlay remain unchanged.
- `infra/graphify/http/serve_http.py`: wrapper below importing the existing `restricted_server` unchanged. No upstream package patch. Tool discovery/dispatch/foreign-project restrictions are inherited; add explicit six-resource discovery/read guards, no new tools/prompts/resources.
- `infra/graphify/http/prepare.py`: standard-library preparation; generate one random 256-bit lowercase hex backend key in ignored `.secrets/graphify-http-backend-key` (0600), write only its SHA-256 digest as `{"api_key_sha256":"<64 hex characters>"}` in ignored `infra/graphify/state/http/server.json` (0644) within new directory 0700. Use exclusive-create, reject existing outputs/symlinks and refuse overwrite/rotation. Existing `.secrets` and live gateway key/config unchanged. Plaintext key is never mounted into the container or put in env/argv/logs.
- `infra/graphify/http/verify.py`: standard-library direct HTTP verifier contract below, no automatic container creation; reads the new backend key locally and sends it through `docker exec -i ... python -` stdin along with test code/data. Capture and print only sanitized PASS/FAIL; no token or graph/source response body in routine output. Existing source/verifier scripts are not imported or edited.
- `infra/graphify/http/README.md`: commands, exact scope/version, results and rollback.

New backend token is separate from the client-to-gateway token. Gateway does not receive or configure this token in this step. Later backend authentication will need a separately reviewed secret-bearing gateway configuration, not global harness configuration. No TLS is added in this internal/local-only test; do not expose this endpoint publicly.

### Exact Compose overlay

Relative bind paths resolve from the explicitly supplied repository `--project-directory`, not the overlay's directory.

```yaml
name: mcp-stack-graphify-http-test
services:
  graphify-http:
    image: sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac
    platform: linux/arm64
    pull_policy: never
    container_name: mcp-stack-graphify-http-test
    user: "501:501"
    entrypoint: ["python"]
    command: ["/opt/mcp-stack/serve_http.py"]
    restart: "no"
    read_only: true
    init: true
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    cpus: 1
    mem_limit: 512m
    pids_limit: 128
    stop_grace_period: 10s
    networks: [transport]
    environment:
      GRAPHIFY_NO_AUTO_REFRESH: "1"
      GRAPHIFY_QUERY_LOG_DISABLE: "1"
      PYTHONDONTWRITEBYTECODE: "1"
      PYTHONUNBUFFERED: "1"
      HOME: /tmp/graphify-home
      XDG_CACHE_HOME: /tmp/graphify-cache
      XDG_CONFIG_HOME: /tmp/graphify-config
    tmpfs: ["/tmp:rw,nosuid,nodev,noexec,size=67108864,mode=1777"]
    volumes:
      - type: bind
        source: ./infra/graphify/http/serve_http.py
        target: /opt/mcp-stack/serve_http.py
        read_only: true
        bind: {create_host_path: false}
      - type: bind
        source: ./infra/graphify/serve_filtered.py
        target: /opt/mcp-stack/serve_filtered.py
        read_only: true
        bind: {create_host_path: false}
      - type: bind
        source: ./infra/graphify/state/http/server.json
        target: /config/server.json
        read_only: true
        bind: {create_host_path: false}
      - type: bind
        source: ./infra/graphify/state/mcp-stack
        target: /state
        read_only: true
        bind: {create_host_path: false}
      - type: bind
        source: ./scripts/verify-basic-memory.py
        target: /home/developer/workspace/mcp-stack/scripts/verify-basic-memory.py
        read_only: true
        bind: {create_host_path: false}
      - type: bind
        source: ./scripts/verify-codegraph.py
        target: /home/developer/workspace/mcp-stack/scripts/verify-codegraph.py
        read_only: true
        bind: {create_host_path: false}
      - type: bind
        source: ./infra/graphify/fixtures/call-chain.py
        target: /home/developer/workspace/mcp-stack/infra/graphify/fixtures/call-chain.py
        read_only: true
        bind: {create_host_path: false}
    logging:
      driver: json-file
      options: {max-size: "5m", max-file: "2"}
networks:
  transport:
    name: mcp-stack-graphify-transport
    internal: true
```

### Proposed HTTP wrapper

This uses the installed SDK/Starlette, not another FastMCP framework. Preserve `infra/graphify/serve_filtered.py` exactly. Resource gates are explicit rather than relying on upstream's text-only unknown-URI responses.

```python
import hashlib
import hmac
import importlib.metadata
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

import mcp.types as types
import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import McpError
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount, Route
from serve_filtered import restricted_server

for package, version in {"graphifyy": "0.9.72", "mcp": "1.29.0",
                         "starlette": "1.3.1", "uvicorn": "0.47.0"}.items():
    if importlib.metadata.version(package) != version:
        raise RuntimeError("Unapproved HTTP runtime version")
graph = Path("/state/graphify-out/graph.json").resolve(strict=True)
if graph != Path("/state/graphify-out/graph.json"):
    raise RuntimeError("Unapproved graph path")
config = json.loads(Path("/config/server.json").read_text())
digest = config["api_key_sha256"]
if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
    raise RuntimeError("Invalid backend key hash")
server = restricted_server(graph)
resources = {"graphify://" + name for name in
             ("report", "stats", "god-nodes", "surprises", "audit", "questions")}
original_list = server.request_handlers[types.ListResourcesRequest]
original_read = server.request_handlers[types.ReadResourceRequest]

async def list_resources(request):
    result = await original_list(request)
    if {str(resource.uri) for resource in result.root.resources} != resources:
        raise RuntimeError("Pinned resource surface changed")
    return result

async def read_resource(request):
    if str(request.params.uri) not in resources:
        raise McpError(types.ErrorData(code=-32602, message="mcp-stack gate: resource not permitted"))
    return await original_read(request)

server.request_handlers[types.ListResourcesRequest] = list_resources
server.request_handlers[types.ReadResourceRequest] = read_resource
manager = StreamableHTTPSessionManager(
    server, json_response=True, stateless=True, max_request_body_size=262144,
    security_settings=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["graphify-http", "graphify-http:8000",
                       "127.0.0.1:8000", "localhost:8000"], allowed_origins=[]))

@asynccontextmanager
async def lifespan(app):
    async with manager.run():
        yield

async def health(request):
    return Response(status_code=200)

class BackendAuth:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            values = [value for name, value in scope["headers"] if name.lower() == b"authorization"]
            match = re.fullmatch(rb"Bearer ([0-9a-f]{64})", values[0]) if len(values) == 1 else None
            if match is None or not hmac.compare_digest(hashlib.sha256(match[1]).hexdigest(), digest):
                await Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})(scope, receive, send)
                return
        await self.app(scope, receive, send)

app = BackendAuth(Starlette(debug=False, lifespan=lifespan, routes=[
    Route("/healthz", health), Mount("/mcp", app=manager.asgi_app)]))
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False, log_level="warning")
```

`/mcp/` is the canonical direct-test path (Starlette mount); any redirect on `/mcp` must preserve authentication and be documented. Use the canonical path for a future gateway proposal rather than assuming redirect compatibility. Stateless HTTP is intentional for a read-only server; future agentgateway owns client sessions. One process/one worker; no extraction or auto-refresh service.

## Direct verifier acceptance contract

All lifecycle actions remain outside the verifier; it never auto-starts a container or downloads packages. Outer Ubuntu verifier captures hashes of all existing Graphify state and the three projected source files, parses the retained graph fixture IDs/community locally without executing source, and invokes only `mcp-stack-graphify-http-test` through stdin. No graph/content/credential output, just sanitized test summaries.

Inner standard-library HTTP probe uses proxy-disabled `urllib.request` at 127.0.0.1:8000 with Bearer token from stdin, explicit JSON Content-Type/Accept, MCP initialize and initialized notification; honor negotiated protocol. Requests <=10 seconds, readiness <=30 seconds, whole test <=180 seconds; connection/malformed/protocol errors fail, never count as denied access. Invoke a fresh initialize/reconnect and concurrent read-only requests without treating stateless backend as a session-authorization authority.

Required tests:

1. Missing, wrong and duplicate Bearer headers rejected (401) on health and MCP, without Graphify dispatch/data. Valid token health 200; initialize server name `graphify`/version checked against the native factory (its previously observed protocol version field is SDK 1.29.0, not package 0.9.72). Both canonical `/mcp/` and redirect behavior documented; no browser CORS allowances.
2. Discover exactly the existing seven tools (`query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`), no advertised `project_path`; no unexpected prompts, resource templates or additional capabilities. If the pinned surface differs, fail rather than expand it.
3. Call all seven with the retained fixture labels/IDs/community using the arguments already verified in `scripts/verify-graphify.py`; assert useful target-specific content and known path, not just HTTP success. Print no response body. Inspect node/edge counts against retained graph.
4. Call `list_prs`, `get_pr_impact`, `triage_prs` and a permitted tool with foreign `project_path`; require `isError` and exact `mcp-stack gate:` marker, not an upstream unavailable-tool error. Wrapper dispatches through the unchanged gate before the upstream handler. No foreign repository mount or read.
5. Discover exactly the existing six resource URIs and read each. `graphify://report` may return the already-known report-not-found result because initial extraction deliberately did not create a report; do not run extraction to fill it. Unknown/file URIs must yield the wrapper's explicit RPC gate error. Confirm no path selector via resource reads.
6. Authenticated invalid Host/Origin rejected by transport settings; intended Docker hostname `graphify-http` (with/without port) accepted. No wildcard/disabled DNS protection; this anticipates the already-observed gateway Host normalization.
7. Two fresh initialized callers and concurrent graph-stat/query calls return stable expected content. Verify graph stats across reconnect and assert unchanged source/state hashes. This tests read-only HTTP handling, not full-corpus or load scalability.
8. Inspect actual image/version, UID, limits, mounts, no host publication, sole internal network, query/update opt-outs and absence of model/provider credentials. Stop/remove the temporary service; compare all pre-existing container snapshots/protected file hashes and checked macOS mise/harness configuration. Existing Graphify gate/script/stdio overlay stay unchanged. Live gateway foundation verifier may be run; no Basic Memory test.

## Recorded approved-step commands (completed; rerun needs approval)

After fresh read-only inventory and file/syntax/config validation, prepare new credential/hash config and start **only** this component:

```sh
python3 infra/graphify/http/prepare.py
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-graphify-http-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/graphify/http/compose.yaml config --quiet
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-graphify-http-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/graphify/http/compose.yaml up -d --no-build --pull never graphify-http
python3 infra/graphify/http/verify.py
```

Report service setup/version/mounts before executing tests. If qualification fails, record the exact error and clean up; do not rebuild, widen gates/mounts/hosts, add packages, change the graph or touch real gateway config to get a pass. New security/transport changes need a separate proposal.

Always inspect exact container ownership/image, then stop/remove only the test component (success or failure):

```sh
macctl run docker inspect mcp-stack-graphify-http-test --format '{{.Image}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "com.docker.compose.service"}}'
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-graphify-http-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/graphify/http/compose.yaml stop graphify-http
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-graphify-http-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/graphify/http/compose.yaml rm -f graphify-http
python3 infra/agentgateway/verify.py
```

These same targeted stop/remove commands are rollback. Retain the empty internal network, new ignored backend key/hash config and wrapper/verifier source for future approved integration. Only disposable process sessions/caches disappear; no notes/graph files/images/volumes are removed. No `down`, orphans/pruning, broad deletions or global uninstall. Credential/file cleanup needs separate explicit approval; don't rotate or delete existing keys automatically.

After this step report exact changes, tests/deviations, preservation checks and retained state; stop before persistent service setup or gateway connection. Future gateway connection must explicitly use backend authentication, review credential-bearing config permissions, choose network/ports/routes and tool/resource authorization, qualify actual inter-container traffic and preserve routing/deferral. CodeGraph needs its own bridge/one-writer plan; it is not part of this proposal.

## Primary evidence and validation

- [Pinned Graphify shared server factory](https://github.com/Graphify-Labs/graphify/blob/1cd9a36c0c57a661d2d2234bc3207e887e1ba104/graphify/serve.py): shared query factory and six default-graph resources; using upstream HTTP directly would not apply this repository's seven-tool gate.
- [Official SDK 1.29.0 HTTP manager](https://github.com/modelcontextprotocol/python-sdk/blob/v1.29.0/src/mcp/server/streamable_http_manager.py) and [transport security](https://github.com/modelcontextprotocol/python-sdk/blob/v1.29.0/src/mcp/server/transport_security.py): existing runtime, lifecycle, body limit and exact Host/Origin checking.
- [Existing direct runbook](GRAPHIFY-SETUP-PROPOSAL.md) records image/dependency checksums, read-only reconnect and the scoped corpus; these are preserved, not re-extracted.

Before confirmation, only document code/YAML parsing, source/graph inspection and image/container/network inventory are permitted. Importing the proposed wrapper would load a real graph/startup code and is not a static check; defer it to the approved container. Static syntax is not runtime qualification.

Initial documentation-only checks passed before approval: wrapper AST syntax, Compose YAML parsing, exactly one service, internal network/no ports, seven read-only explicit bind mounts, pull policy never and transient restart policy. The subsequent approved lifecycle/runtime qualification is completed above; static checks alone were not treated as runtime evidence.

## Original approval request (authorized and completed)

Approve this one temporary **authenticated Graphify HTTP transport/direct-test setup and cleanup**, using the existing exact image and read-only three-file index; create only the five new project files and distinct ignored backend key/hash config above. No published port, persistent service, gateway/harness connection, re-indexing or Basic Memory use is authorized.
