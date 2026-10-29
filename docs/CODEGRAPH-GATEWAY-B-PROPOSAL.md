# CodeGraph gateway B — attempted, rolled back

**Approved with “continue” on 2026-10-01; initialization/discovery failed and the approved Graphify-connected rollback completed.** [Persistent CodeGraph backend A](CODEGRAPH-GATEWAY-CONNECTION-PROPOSAL.md) stays running and its direct suite passes. The live gateway is Graphify-only again; CodeGraph is not connected. Basic Memory remains deferred.

## Attempt and verified rollback

- Created the five approved files under `infra/agentgateway/codegraph/` and the three explicit connected verifier modes. Python syntax, exact preservation of existing routes/settings, pinned 1.5.0 JSON schema and merged Compose checks passed. The merged definition has exactly three RO binds/three networks with every other gateway runtime field unchanged.
- Created ignored `state/codegraph/config.json` (hash-only, 0644 within 0700) and an existing CodeGraph backend-key copy, verified macOS 501:501 / 0640. Original three credentials, backend hash configs, Graphify config/key copy and both adapters/indexes unchanged. No pull/build/framework/model/host install or key rotation.
- Recreated only the gateway with B. Pinned-image/isolation/network/file-permission checks and missing/wrong/backend-as-client/client-as-backend/cross-backend credential tests passed. The first positive CodeGraph initialization/discovery checkpoint failed with AssertionError. Useful tool calls, restricted discovery, dispatch/replay/concurrency and full B regressions were not reached and must not be claimed passed. The initial sanitized verifier did not retain the gateway response status/body, so no exact gateway error code is established for that attempt.
- Immediately restored the gateway using **base + original Graphify overlay**, not the backend-free foundation. Only the gateway was recreated twice total (attempt and rollback). Foundation, full Graphify gateway, connected Graphify direct and CodeGraph A direct tests then passed. The original Graphify malformed-resource-URI HTTP 500 limitation remains recorded, never counted as authorization success. No orphan cleanup, backend restart/stop, writer/sync/watch or Basic Memory call.
- All **20 non-gateway container snapshots / 268 protected file hashes / 10 additional protected key/adapter/Compose files** match the fresh 21-container baseline. Both backends and {{mstack:CLIENT_REPO_TITLE}} remain intact; only gateway identity/start changed. New B source/state are retained as recovery material, not live config. No cleanup/removal/commit/push.
- Fresh macOS Codex config hash is unchanged. macOS global mise config changed from the fresh baseline, with mtime 15:15:05 +0800 during this turn; these commands did not edit it and its cause was not investigated. Preserve this unrelated change, do not restore global config or claim all host hashes match. Checked Ubuntu configs remain unchanged in the protected set.

### Confirmed compatibility blocker

The local adapter checks the HTTP protocol header against its sole supported version **2025-06-18 before parsing initialize**. This verifier's gateway client offers **2025-11-25**; pinned gateway [request context forwarding](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/upstream/streamablehttp.rs) applies incoming headers to the backend request. A standalone authenticated read-only reproduction with the identical initial 2025-11-25 header/body returns HTTP **400**, `Unsupported protocol`, and no session. Thus there is a confirmed bootstrap-negotiation incompatibility; the failure checkpoint itself did not capture raw gateway diagnostics.

The [MCP initialization lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle) permits replying with a supported version when the client's preferred version differs. The pinned [official Python transport](https://github.com/modelcontextprotocol/python-sdk/blob/v1.29.0/src/mcp/server/streamable_http.py#L511) handles initialize separately from subsequent session/protocol header validation. This is a flaw/limitation in our built-in-only adapter, not evidence that CodeGraph indexing or the gateway credentials failed, and does not justify changing an official binary or weakening auth/project gates.

[Local adapter bootstrap correction/direct requalification](CODEGRAPH-HTTP-BOOTSTRAP-CORRECTION.md) is now approved/completed, facade 1.0.1 and all direct/regression checks passing. Next approval: the [B retry with test-owned session cleanup and capacity requalification](CODEGRAPH-GATEWAY-B-RETRY-PROPOSAL.md). Do not rerun B’s preparer or recreate B automatically. Gateway discovery/calls/replay/concurrency remain unverified; the historical failure above is retained.

## Original approved B scope (attempted; retained for retry review)

## Impact, versions and exact boundaries

Recreate only `mcp-stack-agentgateway-1`, with a brief interruption at existing macOS `127.0.0.1:58080`. Keep its existing Graphify route and original client credential. Reuse official agentgateway **1.5.0**, release commit `fe6732474a96a0363dfb9822859af4e9bab360fa`, existing ARM64 image `ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896`; no pull/build/patch/SDK/package installation.

CodeGraph stays running with its exact CodeGraph 1.6.1/Node 24.16.0 image, seven read-only mounts, no writer/watch/sync and partial three-file index. Graphify stays running, unchanged. Neither backend is restarted, stopped or fault-injected. PostgreSQL/Basic Memory/{{mstack:CLIENT_REPO_TITLE}} stay untouched, including already-stopped containers. No new published port or gateway listener.

Add exact `/mcp/codegraph` before the existing unavailable `/mcp` prefix route. Preserve `/mcp/graphify`, `/healthz`, bare `/mcp` 503, disabled admin/UI/API and all existing API-key/settings unchanged. This provides **two separately scoped endpoints**, not a new all-tools combined endpoint or automatic task classification.

## Files and configuration after approval

Create exactly five versionable files under `infra/agentgateway/codegraph/`: `config.template.json`, `compose.yaml`, `prepare.py`, `verify.py`, and `README.md`. No such files/state are created merely by this proposal.

- Template: copy the current Graphify gateway template unchanged and insert only the following CodeGraph route. Render the original client-key hash into a new ignored `infra/agentgateway/state/codegraph/config.json`, mode 0644 inside state 0700. Never overwrite the old foundation/Graphify configs/templates.
- Preparer: existing Ubuntu Python stdlib; validate current gateway config against the prior template, all three distinct 64-hex original keys and backend hash configs, permissions and absence of symlinks/existing output. Copy only the existing CodeGraph backend key to new ignored `infra/agentgateway/state/codegraph/backend.key`, initially 0600. No key generation/rotation or copying the Graphify token again. Abort on drift, never overwrite.
- Explicit macOS chmod of only this new key copy to 0640; assert macOS owner/group 501:501. Existing gateway UID/GID 65532:65532 and supplementary group 501 stay unchanged. No root/world-readable secret, host group/config change or directory/home mount. The original CodeGraph key remains 0600 and unchanged.
- Overlay below is used with **base gateway Compose plus this new combined overlay only**. Keep existing Graphify overlay unchanged for rollback; do not merge backend/root Compose definitions or old/new gateway overlays. Exactly three RO file binds, three intended networks, original loopback publication/resources/security/restart/tmpfs/log settings. No plaintext key environment or client-key passthrough.
- Extend CodeGraph direct verifier with `--gateway-connected` requiring `--service`, asserting exactly CodeGraph + the expected gateway on its internal network and gateway's exact three networks. Extend Graphify direct and Graphify gateway verifiers with explicit `--codegraph-connected` mode for B's exact three-network/three-bind config, without relaxing their default/pre-B assertions or existing probes. Original adapters, source/indexes, backend definitions and key/hash configs unchanged.
- New gateway verifier: bounded stdlib/macOS curl over stdin-only credentials, sanitized output, no auto-start/lifecycle/package behavior. Update infra operating notes and repository status/TODO after actual results.

### Exact new route

```json
{
  "name": "codegraph",
  "gateways": ["foundation"],
  "matches": [{"path": {"exact": "/mcp/codegraph"}}],
  "policies": {"mcpAuthorization": {"rules": [
    "mcp.tool.target == \"codegraph\" && mcp.tool.name == \"codegraph_explore\""
  ]}},
  "backends": [{"mcp": {
    "targets": [{
      "name": "codegraph",
      "mcp": {"host": "http://codegraph-http:8000/mcp"},
      "policies": {"backendAuth": {"key": {
        "value": {"file": "/run/secrets/codegraph-backend-key"},
        "location": {"header": {"name": "authorization", "prefix": "Bearer "}}
      }}}
    }],
    "statefulMode": "stateful", "prefixMode": "always",
    "failureMode": "failClosed", "dnsRebindingProtection": true
  }}]
}
```

Only the actually discoverable `codegraph_explore` is authorized through this first gateway route. Expect its always-prefixed discovery name `codegraph_codegraph_explore`; verify actual runtime naming before declaring success. The native `codegraph_status` remains an explicitly permitted **direct backend** tool but is intentionally denied by the gateway, not invented as a discoverable tool. Resource/prompt execution, unknown/unprefixed/wrong-target tools and project overrides are rejected; keep the backend's fixed-project gate as a second boundary. No automatic profile filtering claim.

CodeGraph's facade negotiates 2025-06-18, unlike native legacy stdio. Actual gateway-to-backend initialization, protocol headers and independent native sessions must pass runtime qualification; current Graphify success is not evidence of CodeGraph compatibility. Stop/rollback if interoperability requires a changed adapter/policy/version rather than silently patching or widening access.

### Exact combined overlay

```yaml
services:
  agentgateway:
    group_add: ["501"]
    networks: [gateway, graphify, codegraph]
    volumes:
      - type: bind
        source: ./infra/agentgateway/state/codegraph/config.json
        target: /config/config.json
        read_only: true
        bind: {create_host_path: false}
      - type: bind
        source: ./infra/agentgateway/state/graphify/backend.key
        target: /run/secrets/graphify-backend-key
        read_only: true
        bind: {create_host_path: false}
      - type: bind
        source: ./infra/agentgateway/state/codegraph/backend.key
        target: /run/secrets/codegraph-backend-key
        read_only: true
        bind: {create_host_path: false}
networks:
  graphify:
    name: mcp-stack-graphify-transport
    external: true
  codegraph:
    name: mcp-stack-codegraph-transport
    external: true
```

`external: true` here means reuse the two existing **Internal: true** Docker networks, not public access. Recheck exact existing membership/ownership before recreation; do not recreate networks or alter backend definitions. Validate the merged three-bind/three-network Compose config and pinned gateway JSON schema before applying.

## Commands only after B approval

Capture fresh all-container/protected-file/global-config baselines first; verify expected gateway/backend identities and healthy direct probes. Then:

```sh
MCP_STACK_HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
python3 infra/agentgateway/codegraph/prepare.py
macctl run chmod 640 "$MCP_STACK_HOST_REPO/infra/agentgateway/state/codegraph/backend.key"
macctl run stat -f '%u:%g %Lp' "$MCP_STACK_HOST_REPO/infra/agentgateway/state/codegraph/backend.key"
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/codegraph/compose.yaml" config --quiet
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/codegraph/compose.yaml" up -d --no-deps --no-build --pull never --force-recreate agentgateway
python3 infra/agentgateway/verify.py
python3 infra/agentgateway/codegraph/verify.py
python3 infra/agentgateway/graphify/verify.py --codegraph-connected
python3 infra/codegraph/http/verify.py --service --gateway-connected
python3 infra/graphify/http/verify.py --service --gateway-connected --codegraph-connected
```

Those new verifier options/files are proposed, not implemented yet. Ignore overlay orphan warnings; never use `--remove-orphans`, broad `down`, prune or volume deletion.

## Required qualification and rollback

Require meaningful fixture/real-source calls via macOS `http://127.0.0.1:58080/mcp/codegraph`, exact restricted discovery, missing/wrong keys and both backend-as-client/client-as-backend separation (including cross-backend key rejection), status/search/sync/unknown/unprefixed/wrong-target/resource/prompt/project denials without successful disclosure. Do not treat 5xx as authorization success. Probe both endpoint session boundaries, replay rejection/no foreign-target exposure, genuinely concurrent fresh source sessions, reconnect and unknown session behavior. Cross-route replay that errors 5xx is a limitation, not a pass; require strict denial/no backend result and assess unexpected mappings separately. Keep existing Graphify malformed unprefixed resource URI HTTP 500 as its known separate limitation.

All original Graphify gateway/direct checks, CodeGraph direct checks and foundation must pass. Protect all original source/index/WAL/SHM/config/keys/global configs and all 20 non-gateway containers in the 21-container baseline; only gateway recreation/membership/mount/config-source plus new ignored output may differ. Do not induce a live outage by stopping either backend; prior synthetic outage qualification is not a new live outage test.

On any validation/runtime failure, report sanitized diagnostics and restore **the current Graphify-connected gateway**, not the old backend-free foundation:

```sh
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/graphify/compose.yaml" up -d --no-deps --no-build --pull never --force-recreate agentgateway
python3 infra/agentgateway/verify.py
python3 infra/agentgateway/graphify/verify.py
python3 infra/graphify/http/verify.py --service --gateway-connected
python3 infra/codegraph/http/verify.py --service
```

Both backends/data remain running/intact; CodeGraph's network again has only CodeGraph after rollback. Retain new source/state as recovery material, no cleanup/key rotation. Stop and ask for a revised proposal if fixes need material adapter/policy/image/mount/auth changes. If B passes, leave the gateway connected, report outcomes/deviations/rollback, then stop before any next harness/combined-endpoint/workflow installation.

This reuses the file-key/auth/schema pattern already qualified in [Graphify B](GRAPHIFY-GATEWAY-B-PROPOSAL.md); it is not a completed CodeGraph gateway interoperability or multi-harness/profile test.
