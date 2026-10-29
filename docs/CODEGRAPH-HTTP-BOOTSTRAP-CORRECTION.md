# CodeGraph adapter bootstrap correction — completed, direct only

**Approved with “continue your major work” and completed on 2026-10-01.** [Gateway B failed and was rolled back](CODEGRAPH-GATEWAY-B-PROPOSAL.md); the corrected CodeGraph direct suite and Graphify/gateway regressions now pass. A subsequent [gateway B retry](CODEGRAPH-GATEWAY-B-RETRY-PROPOSAL.md) is separate approval; no gateway lifecycle/config/membership change here.

## Completion report

- Updated only the local adapter's bootstrap protocol gate and facade version to **1.0.1**, plus its direct verifier. Upstream CodeGraph 1.6.1, bundled Node 24.16.0, image, read-only engine, index, credentials, Compose definitions and limits unchanged. Recognized initialization preferences negotiate **2025-06-18**; this does not implement all versions or enable SSE/modern sessionless behavior.
- Saved the byte-identical pre-fix source in ignored `infra/codegraph/state/http/serve_http.cjs.before-bootstrap-fix`, mode 0600 inside 0700 state. Recreated only `mcp-stack-codegraph-http`, left running internal-only with no port or gateway member. No pull/build/install/migration/re-index/watch/model/Basic Memory action.
- Python/embedded Node/adapter syntax checks passed. Complete direct qualification passed, including five bootstrap preferences (absent header and four recognized versions), notification/discovery/useful real-source queries, newer/unknown subsequent POST/GET/DELETE rejection with session survival, initialization scope, auth/Host/Origin/body/tool/project gates, independent concurrency, **32-session capacity and explicit cleanup**. Original exact three-file **47-node/98-edge** index, database/WAL/SHM/source bytes unchanged.
- Gateway foundation, Graphify gateway and connected Graphify direct suites all passed. Existing malformed unprefixed Graphify resource-URI HTTP 500 remains a known routing-error limitation, never an authorization pass. CodeGraph gateway discovery/calls/replay remain unverified: live gateway is still Graphify-only.
- Fresh baseline captured **after separately requested tmux cleanup**: all **20 non-CodeGraph container snapshots / 268 old protected hashes** unchanged; 21 containers remain. The sole new protected path is the source rollback copy (269 total). Of ten additional protected files, only the authorized adapter differs. Fresh macOS mise/Codex hashes and checked Ubuntu configs unchanged during this CodeGraph step. {{mstack:CLIENT_REPO_TITLE}}/PostgreSQL/Basic Memory untouched.
- Preflight adapter syntax command initially used a standalone absolute container argument, which `macctl` translated incorrectly; no syntax check ran in that attempt. Corrected by putting the container path inside Node code, then successfully checked the actual adapter. Compose ownership/orphan warnings were retained without changing the internal network or cleaning up any service.
- Rollback below remains available; no cleanup needed. Original failed B config/key/source retained but not live. Next: independently approve the [B retry with test-owned session deletion/capacity requalification](CODEGRAPH-GATEWAY-B-RETRY-PROPOSAL.md).

## Original approved scope (executed)

## Evidence and proposed exact change

The adapter's pre-parse header check rejects 2025-11-25 initialization with HTTP 400 before its supported 2025-06-18 can be negotiated. Pinned gateway source forwards that initial client header; the direct reproduction confirmed the rejection/no session. This is our adapter limitation, not an upstream image/index defect. [MCP lifecycle negotiation](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle) distinguishes initialization from subsequent negotiated operation; [official Python transport 1.29.0](https://github.com/modelcontextprotocol/python-sdk/blob/v1.29.0/src/mcp/server/streamable_http.py#L511) validates initialization separately. No Python SDK is installed or substituted by this proposal.

Target: existing macOS OrbStack Docker engine through Ubuntu `macctl run`. Reuse exact CodeGraph 1.6.1/bundled Node 24.16.0 image `sha256:4b8cb16b0c3b5bb7446c3f90b8fd2b12f099b0d0029f8bf30113ad482bf75420`; no pull/build/npm/framework/SDK/model/host/global/mise change.

After approval:

1. Capture fresh all-container/protected-file and both machines' relevant config baselines. Save an ignored source-only rollback copy at `infra/codegraph/state/http/serve_http.cjs.before-bootstrap-fix`, mode 0600 inside existing 0700 state. Never overwrite a pre-existing backup or modify credentials.
2. Edit only `infra/codegraph/http/serve_http.cjs` protocol-validation ordering and facade patch version (1.0.0 → 1.0.1). Preserve all auth/duplicate-header/Host/Origin/path/body/session/tool/project/read-only-engine/mount/network/resource limits. No new capability or library.
3. Authenticate and validate Host/Origin/path/size/JSON before determining whether a POST is an actual valid, sessionless initialize request. For that request only, permit recognized initial HTTP version preferences `2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25` (or an absent header), and reply with **2025-06-18**. Unknown/malformed headers remain 400. Do not implement or advertise modern sessionless protocols, SSE, roots or other capabilities. An initialize with an existing session remains invalid. Body version is a preference, not a claim the facade supports it.
4. All subsequent POST/GET/DELETE requests keep strict negotiated **2025-06-18** header validation; absent header may use the already-known session version as before. Newer/unknown subsequent headers remain 400. Never disable protocol validation globally, change gateway policy or forward client credentials to backends.
5. Extend only `infra/codegraph/http/verify.py` with regression checks: supported bootstrap, absent-header bootstrap, 2025-11-25 and 2025-03-26 initial preference successfully negotiating 2025-06-18; then notification/list/source query with negotiated header; 2025-11-25/unknown subsequent headers rejected; unknown initial header still rejected. Clean up only each test-owned session. Existing complete direct suite remains mandatory, including exact three-file/47-node/98-edge index, immutable diagnostics, full gates and concurrent sessions.
6. Recreate **only `mcp-stack-codegraph-http`** to load the changed bind-mounted adapter, with a brief internal-only interruption. This resets its transient sessions; no currently connected gateway/harness uses it after B rollback. Keep the seven RO binds, original image/key/hash/index, CPU/RAM/tmpfs/privilege/flags/restart/sole internal network unchanged. Record results and leave the corrected A running only if all tests pass.

Update `infra/codegraph/http/README.md`, the direct/A/B runbooks and status/TODO with actual outcomes. Do not edit root/temporary/service Compose, original source scripts/project/index or any Graphify/gateway implementation/state. Do not retry B, enable memory, register a harness, refresh/index or touch {{mstack:CLIENT_REPO_TITLE}} here.

## Exact commands after approval

After checking the expected CodeGraph name/image/project/service and the sole internal network member:

```sh
MCP_STACK_HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/codegraph/http/compose.service.yaml" config --quiet
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/codegraph/http/compose.service.yaml" up -d --no-deps --no-build --pull never --force-recreate codegraph-http
python3 infra/codegraph/http/verify.py --service
python3 infra/agentgateway/verify.py
python3 infra/agentgateway/graphify/verify.py
python3 infra/graphify/http/verify.py --service --gateway-connected
```

No prepare/key rotation, new port/network, orphan cleanup or other service lifecycle command. Protect all non-CodeGraph containers and all original data/config/key/global hashes; only the authorized adapter/verifier edits, rollback copy and CodeGraph identity/start may differ.

## Rollback and completion boundary

If any new/existing direct check fails, restore the exact pre-correction adapter from the protected source-only backup using `apply_patch`, restore the prior direct verifier behavior if needed, then repeat the exact scoped CodeGraph recreation and direct/regression checks above. Keep both original/backup hashes, diagnose sanitized results and stop rather than adding versions/capabilities or relaxing gates. Do not remove the image/index/credential/state/network or alter the Graphify-connected gateway. Recovery uses the unchanged A Compose; no database/volume operations.

If correction passes, report what changed and all checks/deviations, then prepare a separate B retry proposal preserving its original gateway policy/config/credentials and adding explicit negotiated-session cleanup/capacity checks. This correction alone does not establish gateway interoperability, cross-route replay protection, n8n/profile/harness integration or full MCP conformance.
