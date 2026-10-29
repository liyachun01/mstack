# Gateway session qualification correction/retry — completed

[Previous retry](CODEGRAPH-GATEWAY-B-RETRY-PROPOSAL.md) proved real CodeGraph gateway discovery/calls/gates/concurrency and in-memory route isolation, then rolled back because the newly added Graphify post-DELETE rejection assertion failed. The user approved this separately scoped correction/retry with **“continue” on 2026-10-01**. Qualification passed; the live gateway now serves both graph endpoints. The original approved scope and rollback below remain the operating reference, not permission for future restarts.

## Actual results (2026-10-01, Asia/Shanghai)

- Changed only `infra/agentgateway/codegraph/verify.py` and documentation. Added a bounded `--graphify-session-diagnostic` mode, separate DELETE/close methods, backend-specific cleanup expectations, deleted-token authentication tests and four cold route-replay checks. No adapter, gateway template/config, key, Compose, image, host toolchain or upstream patch change.
- Fresh protection baselines captured before tests. Retained config/template/key/modes, pinned upstream schema and merged Compose preflight passed. An initial read-only preflight script mistakenly looked for `binds` rather than the existing `routes` key; corrected the inspection, not the config. Existing direct CodeGraph suite passed before gateway recreation.
- Diagnostic on the already-running Graphify-only gateway created exactly one owned session, negotiated **2025-11-25**, DELETE **202**, then authenticated tools/list **200** with exactly the seven permitted `graphify_` tools. Missing/wrong/both backend credentials with that deleted token returned 401/403. Final DELETE **202**, with no post-cleanup POST. This is observed authenticated resumption, **not rejection or permanent token revocation**.
- Recreated only `mcp-stack-agentgateway-1` at **15:56:41 +08:00**, reusing official agentgateway **1.5.0** and the retained combined config (base + CodeGraph overlay only). No pull/build/install/backend restart. Exact three RO mounts/three networks/security/resource settings verified. Compose's other-service orphan warning was intentionally ignored without cleanup.
- Real CodeGraph initialization **200**, protocol **2025-06-18**, exactly one **`codegraph_codegraph_explore`** tool; useful fixture/actual-source calls, hidden tool/resource/prompt/project gates, all credential separation checks, independent fresh/concurrent callers and unknown-session denial passed. Delete-one preserved another caller. All four B-owned CodeGraph sessions DELETE **202**, with reuse **404**.
- **Eight bidirectional endpoint-replay cases passed**: four in-memory and four after DELETE/cache miss, both source/destination tool names, destination's negotiated protocol in every case. All returned **404**, with no source result or credential disclosure. Deleted tokens still required the client API key. Graphify same-route resumption repeated with seven tools; the owned/reconstructed cache entry was explicitly DELETEd again before cold replay and at final cleanup. Session IDs are not credentials or a general tenant-isolation guarantee.
- After B-owned cleanup, unchanged full connected CodeGraph direct suite passed, including **exact 32-session capacity/explicit cleanup**. Full connected Graphify gateway suite (all seven tools/gates/concurrency), connected Graphify direct suite and gateway foundation passed. Existing malformed unprefixed Graphify resource URI still returns **500 before dispatch**: recorded separately, never an authorization pass. No claim of backend-outage/restart durability or exhaustive production interoperability is added by these tests.
- All **20 non-gateway container snapshots, 269 protected hashes, ten extra protected files, eight retained config/verifier hashes, checked macOS mise/Codex and protected Ubuntu configs** unchanged. All 21 containers retained, including 16 stopped containers. PostgreSQL, Basic Memory, {{mstack:CLIENT_REPO}}, sources/indexes/notes untouched. Deliberate caffeinate/power settings unchanged. No rollback needed; original Graphify-only rollback remains available under scoped approval.
- Current macOS endpoints: `/mcp/graphify` (seven tools) and `/mcp/codegraph` (one explore tool), same mandatory client key at loopback **58080**; `/healthz` 200, bare `/mcp` 503. Backends remain internal-only. This is not an all-tools endpoint, harness registration, automatic task-profile selection, n8n setup or Basic Memory integration. Next: separately select/approve project-scoped harness integration; Basic Memory stays deferred and backups/restores remain future work.

## Why revise the test rather than change the server

CodeGraph has native sessions: deletion/reuse must remain 404, and the unchanged direct capacity suite must establish no leaks. Graphify is deliberately stateless; native per-client state is absent. The pinned gateway supports recovering encoded upstream-session state when its cached session entry is gone. A successful DELETE is therefore not evidence of permanent token revocation for stateless upstreams. The previous test applied that stronger expectation indiscriminately. [Source and observed results](CODEGRAPH-GATEWAY-B-RETRY-PROPOSAL.md) distinguish this inference from an exact runtime response.

Recommendation: retain stateless Graphify and official gateway unchanged; characterize/qualify authenticated same-route resumption, keep strict CodeGraph cleanup and strengthen cold-token route/auth tests. Do **not** make Graphify stateful, add a revocation database, patch/build the gateway, change API keys or relax tool/project authorization merely to satisfy the test. If permanent Graphify token revocation is a user requirement, select a separately scoped implementation before proceeding instead of approving this expectation change.

## Approved scope (executed)

Execution: existing macOS OrbStack Docker through Ubuntu `macctl run`. Reuse agentgateway **1.5.0**, commit `fe6732474a96a0363dfb9822859af4e9bab360fa`, image `ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896`; unchanged CodeGraph 1.6.1 / Node 24.16.0 / facade 1.0.1 image `sha256:4b8cb16b0c3b5bb7446c3f90b8fd2b12f099b0d0029f8bf30113ad482bf75420` and Graphify 0.9.72. No download/build/framework/model/host/mise change.

1. Fresh protected/container/global-config baselines and exact retained-template/key/pinned-schema/Compose preflight. No preparer or state/key overwrite.
2. Modify **only `infra/agentgateway/codegraph/verify.py`**, plus operating/status documentation. Add a bounded Graphify-only diagnostic mode for the already-running gateway: create exactly one owned Graphify session, DELETE it, capture only status/result-shape/tool-count/negotiated-version summaries for subsequent tools/list. No response text/session/token output. Reuse of that token must either be an explicit 4xx/RPC denial, or HTTP 200 with exactly the existing seven permitted prefixed Graphify tools. Reject 5xx, unexpected tools/data or malformed envelopes. A characterization failure stops before any gateway recreation.
3. If authenticated same-route resumption is confirmed, report it explicitly as accepted lifecycle semantics, **not authorization denial**. Test that missing/wrong/backend credentials using that token still fail; retain the seven-tool/resource/prompt/project gates. DELETE the owned/reconstructed Graphify gateway entry again at the end, without a post-cleanup POST that would resurrect it. `finally` cleanup is bounded and touches only genuinely owned sessions. No automatic removal of unknown/other callers' sessions. Stateless native Graphify owns no client session to leak; do not describe the encoded token as revoked.
4. Preserve CodeGraph's DELETE acceptance + subsequent 404/rejection, delete-one isolation and full direct **32-session bound/cleanup** exactly. Do not widen limits, wait for TTL, add introspection endpoints or restart a backend to clear sessions.
5. Recreate **only the gateway**, briefly interrupting existing loopback **58080**, with the retained combined overlay (base + `infra/agentgateway/codegraph/compose.yaml` only). Same three RO binds/three networks/security/resource/restart/log settings, same original client credential and two protected backend-key copies, same `/healthz`, `/mcp/graphify`, exact `/mcp/codegraph`, bare `/mcp` 503 and tools-only CEL rules. No backend lifecycle/index/database/harness action.
6. Run every previously approved B positive/negative/concurrency check. Keep the four in-memory bidirectional route replay cases and add **four after-DELETE/cache-miss replay cases**, using both source and destination tool names and the **destination's negotiated protocol** so a mere protocol mismatch cannot masquerade as route isolation. For each cold replay require explicit 4xx/RPC/tool rejection with no source result or secret disclosure; never accept 5xx. Add missing/wrong-key checks against deleted tokens. If any authenticated cross-route request succeeds, rollback and stop: no automatic policy fix or softened replay assertion.
7. After own-session cleanup, run the unchanged CodeGraph connected direct capacity suite, full Graphify gateway connected mode and Graphify direct connected mode, foundation checks and protected comparisons. Do not call Basic Memory, index sources, install/register harnesses, change power settings or touch deliberate caffeinate. Update current results only after all checks pass.

## Files, persistence and lifecycle commands

Runtime config/key files remain the original ignored `infra/agentgateway/state/codegraph/config.json` (0644 within 0700), `state/codegraph/backend.key` and `state/graphify/backend.key` (macOS 501:501 / 0640). Original credentials remain under `.secrets/`, 0600. Adapter/index/source mounts unchanged, internal backend networks/no published backend ports retained. Expected gateway CodeGraph tool remains `codegraph_codegraph_explore`, Graphify exactly seven. This is two endpoints, not automatic task classification or a combined all-tools route.

After implementing/qualifying the diagnostic mode and preflight:

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

No new port, image, volume or gateway/backend config revision. Session resumption/revocation expectations change as described; authentication/tool/project/cross-route rejection expectations do not. Permanent revocation across deletion/restart is not a general claim of this stack.

## Rollback / stop conditions

On any unexpected diagnostic or qualification result, stop; if B was applied, attempt bounded owned-session cleanup then restore **only the gateway with base + original Graphify overlay**, even if cleanup fails:

```sh
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/graphify/compose.yaml" up -d --no-deps --no-build --pull never --force-recreate agentgateway
python3 -B infra/agentgateway/verify.py
python3 -B infra/agentgateway/graphify/verify.py
python3 -B infra/graphify/http/verify.py --service --gateway-connected
python3 -B infra/codegraph/http/verify.py --service
```

Keep backends/data/images/keys/source/state/networks intact. Never `down`, orphan/volume cleanup, backend restart, upstream patch or API-key rotation. Report actual lifecycle/cleanup failures and request a new scoped decision; do not claim complete recovery if native capacity/protection checks fail. Basic Memory and later n8n/harness/PKM steps remain separately gated.
