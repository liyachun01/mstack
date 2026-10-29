# CodeGraph gateway B retry — attempted, rolled back

Historical checkpoint. The subsequent separately approved [session qualification correction/retry](CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md) completed successfully; current gateway serves both graph endpoints. Graphify-only state and uncaptured-resumption statements below describe this earlier attempt, not today's final runtime.

**Approved with “continue major work” on 2026-10-01; attempted and rolled back.** The [local adapter bootstrap correction](CODEGRAPH-HTTP-BOOTSTRAP-CORRECTION.md) enabled real CodeGraph gateway operation. This retry failed its newly added Graphify post-DELETE reuse assertion, not CodeGraph initialization. Live gateway is restored to Graphify-only; both graph backends stay running, Basic Memory deferred. [Next proposed test-semantics correction/retry](CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md) requires new approval.

## Actual results (2026-10-01, Asia/Shanghai)

- Modified only `infra/agentgateway/codegraph/verify.py`: sanitized handshake diagnostics, tracking of genuinely created sessions before validation, bounded `finally` deletion, delete-one/other-session isolation. Retained source/config/keys/Compose unchanged. Direct CodeGraph preflight, pinned schema, exact old-route preservation, key/hash/mode correspondence and three-bind/three-network merged Compose checks passed.
- Recreated only the gateway at **15:47:17 +08:00**, official pinned 1.5.0 image, no pull/build/install. Real backend negotiation returned HTTP 200 / **2025-06-18**, exactly **one `codegraph_codegraph_explore`** tool. Useful fixture/real Python-source queries, hidden tool/method/project selectors, credential separation, fresh/concurrent callers, unknown-session denial and **four bidirectional in-memory cross-route replay checks** all passed. Negative tests were explicit 400/404/RPC -32602, never 5xx.
- All four test-owned CodeGraph gateway sessions were DELETEd with HTTP 202; each subsequent tools/list reuse was **404**. Delete-one left the other caller usable. Graphify's one test-owned session DELETE also returned **202**, but the new common post-DELETE rejection assertion failed with AssertionError; the sanitized verifier did not retain the exact Graphify reuse status/body. Do not claim its reuse returned 200 solely from this log, or that every session was permanently revoked.
- Rolled back at **15:47:44 +08:00**, using base + original Graphify overlay, not the backend-free foundation. No backend restart, key rotation or cleanup. CodeGraph full direct suite then passed, including **exact 32-session capacity and cleanup**, establishing no retained CodeGraph-native session leak at that checkpoint. Gateway foundation, Graphify gateway and connected Graphify direct suites passed. Combined-B direct/Graphify regression modes were not reached before rollback and are not claimed passed.
- All **20 non-gateway container snapshots / 269 protected hashes / ten extra protected files / eight retained-config-and-verifier hashes** unchanged; 21 containers remain. Fresh macOS mise/Codex hashes and protected Ubuntu configs unchanged. {{mstack:CLIENT_REPO_TITLE}}, stopped containers, PostgreSQL/Basic Memory/data/indexes untouched. Compose orphan warning ignored without removal. Working Graphify-only gateway left running.
- The user confirmed `caffeinate` is deliberate for continued AI work with the lid closed; preserve it. No power assertion/process was changed. This user intent does not establish actual closed-lid behavior on every hardware/power configuration.

### Source finding — not yet a captured runtime reproduction

Our Graphify adapter uses `StreamableHTTPSessionManager(..., stateless=True)` in `infra/graphify/http/serve_http.py`: there is no per-client native Graphify HTTP session to revoke. Pinned agentgateway [removes its cached entry on DELETE](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/session.rs#L895), but [get_or_resume_session decodes a missing cached token and rebuilds its relay](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/session.rs#L783). This points to resumable-token semantics, not a universal permanent-revocation guarantee. CodeGraph differs because its actual native session ID was deleted and then returned 404.

The new assertion assumed permanent post-DELETE rejection for both backends; that assumption may be inappropriate for stateless Graphify. The exact failing response needs bounded sanitized characterization, not silent acceptance of errors or weakened auth/CEL. In-memory cross-route checks already passed; deleted/cache-miss tokens require additional explicit checks. Do not use a session ID as an API credential or general tenant boundary, declare the source inference a captured runtime result, patch upstream, turn Graphify stateful or retry automatically.

## Original approved retry scope (executed)

## Exact impact and artifacts

Target: existing macOS OrbStack Docker engine via Ubuntu `macctl run`. Briefly recreate only `mcp-stack-agentgateway-1` at existing macOS loopback **58080**, resetting its transient gateway sessions. No backend lifecycle action, image pull/build/package/model/host/mise/harness/database/index change.

Reuse official agentgateway **1.5.0**, commit `fe6732474a96a0363dfb9822859af4e9bab360fa`, existing image `ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896`. CodeGraph remains **1.6.1**, bundled Node **24.16.0**, local facade **1.0.1**, image `sha256:4b8cb16b0c3b5bb7446c3f90b8fd2b12f099b0d0029f8bf30113ad482bf75420`, same seven RO mounts and partial three-file 47-node/98-edge index. Graphify 0.9.72 and its seven-tool gate/index unchanged.

Use **base gateway Compose + retained `infra/agentgateway/codegraph/compose.yaml` only**. Reuse ignored `infra/agentgateway/state/codegraph/config.json` (hash-only, 0644 inside 0700) and `backend.key` (macOS 501:501 / 0640), validating exact template/hash/key correspondence without printing secrets. Original keys stay in `.secrets/`, 0600, unrotated. Do not rerun any preparer or overwrite state.

The combined overlay gives exactly three RO file binds (combined config and the two backend key copies), no note/index/home/socket mounts, and three networks: existing normal gateway bridge plus the two existing internal backend networks. Keep UID/GID 65532 and supplementary group 501, privilege/resource/tmpfs/log/restart limits unchanged. No new ports, listener, persistent volume or secret-bearing environment variable.

Retain `/healthz`, `/mcp/graphify` and bare `/mcp` 503. Add exact `/mcp/codegraph` with existing CEL rule permitting only target `codegraph` / underlying tool `codegraph_explore`, stateful mode, always-prefixed names and fail-closed upstream behavior. Expected tool `codegraph_codegraph_explore` must be verified rather than assumed. Native status is direct-only. Separate endpoints are not an all-tools combined endpoint or automatic task-profile routing.

## Files/tests after approval

1. Capture fresh all-container, protected-data/key/config and macOS/Ubuntu config baselines. Check expected gateway identity/image/project/service and exact backend/network memberships. Confirm retained state matches the approved template and pinned schema/merged Compose; abort on drift.
2. Modify **only `infra/agentgateway/codegraph/verify.py`** for sanitized initialization diagnostics (HTTP status, negotiated version and tool count only; no body/key/session-ID output) and test-owned session tracking/deletion. Use existing stdlib/macOS curl, credentials over stdin, bounded requests. Register a session as soon as initialization yields its ID, before later validation, so partial failures can still clean it up. Track only genuinely created sessions, never cross-route replay aliases or unknown IDs.
3. Explicitly DELETE each owned session on its original endpoint with its negotiated protocol header, in `finally` on success/failure. Assert deletion accepted and subsequent reuse rejected; test deleting one while another still works. Clean the Graphify session created by the B verifier too. Do not enumerate/delete other clients' sessions or infer a 2xx DELETE alone proves native cleanup.
4. Pinned source supports [gateway session deletion](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/streamablehttp.rs#L254), [fan-out deletion](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/handler.rs#L1208) and [upstream HTTP DELETE](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/upstream/streamablehttp.rs#L148); actual behavior remains to be qualified. After B-owned sessions close, run the existing **unchanged full CodeGraph direct suite with `--service --gateway-connected`**, including its exact 32-session capacity/cleanup test. This detects leaked native sessions without enlarging limits, weakening assertions, adding an introspection endpoint, restarting a backend or relying on TTL expiry.
5. Keep every original B check: client/backend/cross-backend auth separation, exactly one tool, useful fixture/real-source queries, excluded status/search/sync/unknown/unprefixed/wrong-target/resource/prompt/project calls, fresh/concurrent source sessions and **bidirectional cross-endpoint replay using both source and destination tool names**. Accept only explicit 4xx/RPC/tool denial for negative checks, never HTTP 5xx or mere absence of results. Preserve the known malformed unprefixed Graphify URI 500 limitation as a separate routing error, not authorization success.
6. Run all B regression modes below and compare snapshots/hashes. Update operating notes/status with actual results. If a policy, transport, cleanup/capacity or regression test fails, execute only the rollback below; do not change adapters/CEL/version/mounts or relax expectations to pass. Native cleanup failure is a blocker to a stable retry, not permission to clear unknown sessions or restart CodeGraph.

## Exact lifecycle and verification commands

After the preflight/test-only edits above:

```sh
MCP_STACK_HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/codegraph/compose.yaml" config --quiet
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/codegraph/compose.yaml" up -d --no-deps --no-build --pull never --force-recreate agentgateway
python3 -B infra/agentgateway/verify.py
python3 -B infra/agentgateway/codegraph/verify.py
python3 -B infra/codegraph/http/verify.py --service --gateway-connected
python3 -B infra/agentgateway/graphify/verify.py --codegraph-connected
python3 -B infra/graphify/http/verify.py --service --gateway-connected --codegraph-connected
```

Sequence B cleanup and CodeGraph capacity checks before unrelated Graphify gateway probes. Verify all non-gateway container identities/start/status/health/ports and original protected bytes unchanged. No harness registration, corpus expansion, watcher, n8n/PKM integration or automatic memory calls follow from success.

## Authorized rollback on any failure

First attempt cleanup of only this verifier's owned sessions with bounded requests; cleanup failure must not prevent restoring the prior gateway. Then recreate **only the gateway with base + original Graphify overlay**, preserving the working Graphify route (not the backend-free foundation):

```sh
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/graphify/compose.yaml" up -d --no-deps --no-build --pull never --force-recreate agentgateway
python3 -B infra/agentgateway/verify.py
python3 -B infra/agentgateway/graphify/verify.py
python3 -B infra/graphify/http/verify.py --service --gateway-connected
python3 -B infra/codegraph/http/verify.py --service
```

Retain source/state/keys/indexes/images/networks and the corrected CodeGraph backend. Never `down`, remove orphans/volumes, restart a backend to clear sessions, or touch {{mstack:CLIENT_REPO_TITLE}}. If direct capacity after rollback fails due to residual sessions, report it honestly and stop for a scoped recovery decision; do not claim complete recovery or automatically expand this proposal.
