# CodeGraph temporary direct HTTP test

Current follow-up: [persistent backend A](CODEGRAPH-GATEWAY-CONNECTION-PROPOSAL.md) and [bootstrap correction](CODEGRAPH-HTTP-BOOTSTRAP-CORRECTION.md) are completed; facade 1.0.1 and full direct/Graphify/gateway regressions pass. Original B failed/rolled back, leaving the gateway Graphify-only; [B retry](CODEGRAPH-GATEWAY-B-RETRY-PROPOSAL.md) awaits separate approval. The temporary-test completion report below is historical, not the current container/config state.

Authorized by the user's “continue test” on 2026-10-01. **Completed; temporary container stopped and removed.** This one step creates a local adapter and temporary isolated test, not a persistent service/gateway/harness registration. Basic Memory remains deferred, {{mstack:CLIENT_REPO_TITLE}} immutable, macOS/Ubuntu toolchains untouched by this step.

## Completed results

- Exact existing image/native classes/bundled Node qualified successfully; no pull/build/npm/SDK/FastMCP/host install or upstream patch. One shared engine opened the retained index read-only; process inventory showed only init and the bundled Node adapter, no daemon/watcher subprocess.
- All direct qualification checks passed: runtime readiness/isolation; immutable 3-file/47-node/98-edge index and fixture call edges; missing/wrong/duplicate auth; Host/Origin/protocol/Accept/content-type/path/JSON/UTF-8/batch/size rejection; initialization/session scope/discovery; excluded tool/root/project/resource/prompt gates; useful native fixture/source/status answers; simultaneous independent fresh source sessions, reconnect/delete isolation; 32-session bound and session cleanup.
- Small-project native discovery remains exactly `codegraph_explore`; `codegraph_status` succeeds only as an explicitly allowed direct call. No fabricated tool discovery, full-repository coverage or automatic memory/profile enforcement is claimed.
- All **20 pre-existing container snapshots and 267 pre-existing protected file hashes unchanged**, including main SQLite database, empty WAL, SHM, retained compile cache, Basic Memory notes/config, gateway/Graphify keys/config/index and checked Ubuntu configs. One new hash-only server config entry makes 268 in the protected map; the new ignored backend credential is checked separately for mode/hash/separation. No existing key rotation.
- Foundation, connected Graphify direct and Graphify gateway regression verifiers all passed. The previously documented gateway malformed-resource-URI HTTP 500 remains a limitation, not an authorization pass. No Basic Memory call/test occurred.
- Temporary container was identity-checked, stopped and removed; its network is internal and now empty. Five new infra files, separate ignored credential/hash config, image and original source/index are retained. No persistent CodeGraph service or gateway/harness registration.
- Initial verifier expected absolute source paths; the existing index stores relative paths. Corrected only the new verifier's exact three-file assertion, then reran successfully in the same container; no source/index/mount/policy/version change or restart.
- macOS mise matches the historical Graphify-B hash. macOS Codex config differs from that older baseline, but its recorded modification time is 14:11:45 +0800, preceding this test's adapter creation at 14:42:23; this turn did not edit it. No fresh pre-test macOS Codex hash was captured, so do not claim that older comparison proves this step changed it or that all host configs were unchanged. The current comparison is retained as a qualification limit; Ubuntu config hashes are part of the unchanged fresh baseline.

Next: separately approve [persistent CodeGraph backend A](CODEGRAPH-GATEWAY-CONNECTION-PROPOSAL.md), then independently propose gateway connection B. No automatic start or registration follows from these tests.

## Exact scope and pins

- Existing CodeGraph **1.6.1**, source commit `f4ddf508516332419ea3c95702810765936cf679`; bundled Node **24.16.0**.
- Existing local Linux ARM64 image `sha256:4b8cb16b0c3b5bb7446c3f90b8fd2b12f099b0d0029f8bf30113ad482bf75420`; `pull_policy: never`, no build/package/download.
- New versionable files only: `infra/codegraph/http/{serve_http.cjs,compose.yaml,prepare.py,verify.py,README.md}` plus this runbook and status/TODO/README records. No changes to root/stdio Compose, existing scripts/project config, mise, gateway or discovery instructions.
- New ignored `.secrets/codegraph-http-backend-key` (0600) and hash-only `infra/codegraph/state/http/server.json` (0644 inside 0700 state); preparer refuses symlinks/existing state/key and never rotates existing credentials. Distinct from gateway/Graphify keys.
- Container/project `mcp-stack-codegraph-http-test`, service `codegraph-http`, network `mcp-stack-codegraph-transport` internal-only; no published port, gateway attachment or outside network. HTTP listens on 0.0.0.0:8000 inside that isolated network only. Test requests use `docker exec` and loopback.
- Seven read-only file/directory binds: adapter, hash config, two verification scripts, CodeGraph fixture, existing project config and `.codegraph` SQLite directory. Exact three-file index remains **47 nodes / 98 edges**; nothing else indexed/exposed.
- UID/GID 501:501, read-only root, cap-drop ALL, no-new-privileges, init, 2 CPU/2 GiB, 128 PIDs, no restart; 64 MiB temporary RAM filesystem. No persistent compile cache writes.
- Exact environment: telemetry 0, DO_NOT_TRACK 1, NO_UPDATE_CHECK/NO_DAEMON/NO_WATCH 1; MCP_TOOLS explore,status; QUERY_POOL_SIZE 0; NODE_COMPILE_CACHE `/tmp/node-compile-cache`, HOME `/tmp/codegraph-home`, XDG cache/config `/tmp/codegraph-cache` and `/tmp/codegraph-config`. No plaintext credential environment/mount/log.

Commands, endpoints, gates, retention and exact stop/remove rollback are in [the infra runbook](../infra/codegraph/http/README.md). No broad cleanup or live service lifecycle command is included. Retain source/config/key/image/index/empty network after test cleanup.

## Why not just wrap the CLI?

The pinned CLI's `--no-watch` disables watching, not connect-time reconciliation/writer ownership. Launching it per HTTP client risks multiple writers; sharing one stdio session mixes native per-client explore history. Instead import the existing bundle's native classes: **one read-only engine with independent MCPSession instances**. No writer, daemon, watcher, catch-up sync or query pool. Assert the index opened before listening; fail without fallback if the native runtime/private contract or read-only mount fails.

The local facade, not upstream CodeGraph, owns the restricted tools-only **2025-06-18** Streamable HTTP lifecycle (single JSON POST messages, 202 notification, secure session IDs, DELETE cleanup, GET 405/no SSE). Native stdio initialization remains **2024-11-05**, explicitly adapted with facade identity/capabilities/instructions, never claimed as upstream HTTP support. Fixed project/root, single Bearer credential, strict Host/no browser Origin, unknown/foreign tool and method rejection before dispatch. Empty optional resource/prompt discovery is retained; no resource/prompt execution. Upstream small-project discovery remains one tool, `codegraph_explore`; status is permitted explicitly but not invented as discoverable. No automatic task routing.

## Qualification checklist

- Pin/runtime/native module exports, engine readiness, container isolation/mounts/resources/network/flags.
- Immutable SQLite diagnostic only after no writer/zero WAL: exact scope/counts/fixture call edges.
- Missing/wrong/duplicate auth; Host/Origin; protocol/Accept/content type/path; malformed JSON/UTF-8/batches/oversized input.
- Initialize/ready/session/notification/discovery, root/project selector denials, excluded and unknown tool/direct resource/prompt/root calls.
- Useful fixture/real Python source/status calls; concurrent independent fresh source sessions; reconnect; delete one session without affecting the other; capacity bound and cleanup.
- Existing source/index including WAL/SHM hashes, credential separation, all pre-existing container/protected-file snapshots; foundation/Graphify regression checks only, no Basic Memory calls.
- Stop/remove only the exact test container; no production SLA, full spec/conformance claim, TTL/fault timeout or host-restart test implied.

## Prior discovery incident

On the preceding turn an ostensibly read-only Ubuntu SQLite `mode=ro` inspection changed `codegraph.db-shm` bytes. The main database and empty WAL, other 266 protected file hashes and all 20 container snapshots were unchanged. Work paused and the user was informed; “continue test” accepts proceeding with the retained regenerated shared-memory metadata. The prior snapshot was hash-only, so exact prior SHM bytes were not restored. This is not an index migration/re-index. The new verifier uses immutable diagnostics under the verified no-writer/empty-WAL condition, and the container's index bind is read-only. Keep the incident explicit rather than claiming previous discovery changed nothing.

## Primary sources inspected

- [Pinned native shared engine](https://github.com/colbymchenry/codegraph/blob/f4ddf508516332419ea3c95702810765936cf679/src/mcp/engine.ts)
- [Pinned per-client session and native legacy handshake](https://github.com/colbymchenry/codegraph/blob/f4ddf508516332419ea3c95702810765936cf679/src/mcp/session.ts)
- [Pinned session-scoped explore state](https://github.com/colbymchenry/codegraph/blob/f4ddf508516332419ea3c95702810765936cf679/src/mcp/explore-session-state.ts)
- [HTTP protocol 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
