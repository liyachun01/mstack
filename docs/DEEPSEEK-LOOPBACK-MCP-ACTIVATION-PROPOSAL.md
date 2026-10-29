# DeepSeek native MCP through the local forwarder — activation qualified

2026-10-03. **Completed:** both native graph MCP entries are enabled/**active** in the retained-home Web host, PID **414648**, Ubuntu **127.0.0.1:3080**. The user's explicit request to resolve the stuck integration authorized the previously proposed two URL edits and one idle Web relaunch; no repeat approval loop. The [forwarder-only step](DEEPSEEK-LOOPBACK-FORWARDER-PROPOSAL.md) remains unchanged/running as PID **402899**. The scope below records the original bounded proposal; old candidate PIDs are historical, never actionable without fresh identity verification.

## Root cause and completed evidence

The gateway rejects non-loopback HTTP authority as part of its DNS-rebinding protection. The original `host.orb.internal:58080` URL therefore received 403. The attempted custom Host correction could not work: pinned Node 24.19.0's native fetch deletes custom Host headers. Python's lower-level HEAD success was not evidence of compatibility with the production DeepSeek HTTP implementation. Reconnecting unchanged clients cannot repair this authority mismatch. The qualified byte-only forwarder lets the native client use an actual loopback URL without relaxing gateway protection or patching vendor code.

Before touching Web, the **actual installed SDK 2.0.0**, pinned Node and the same Client negotiation options passed one authenticated discovery on each loopback route. Graphify negotiated **2025-11-25** and returned **7** tools; CodeGraph negotiated **2025-06-18** and returned **1**. Each owned diagnostic session was terminated (DELETE 202) and client closed. CodeGraph's optional SSE GET returned 405, while initialization and tools/list succeeded; this is not a failed discovery. There were **zero tools/call and zero model requests**. Names below are observed SDK discovery results, not a separately inspected live Web tool registry:

- Graphify: `graphify_query_graph`, `graphify_get_node`, `graphify_get_neighbors`, `graphify_get_community`, `graphify_god_nodes`, `graphify_graph_stats`, `graphify_shortest_path`.
- CodeGraph: `codegraph_codegraph_explore`.

The official tool-definition factory accepted the returned schemas and derived the expected `mcp__stack_graphify__…` / `mcp__stack_codegraph__…` names without executing tools. Two new **offline** SDK regression cases prove supported legacy negotiation/discovery and terminal 403 denial with no retry. The URL/header contract was first shown failing against the old YAML, then passed after correction; the helper's global fetch guard forbids unexpected network during those offline cases. All **23 Python tests**, **10 forwarder tests**, **2 SDK cases**, and native parse/composition/JS-syntax/MCP-schema checks pass.

Official read-only `session/list`, with its source-defined `_request: {}` wire argument, reported **8 sessions / 0 running** without activating an Agent. A fresh verified private home archive and original-overlay/test copies preceded graceful SIGTERM of the identity-verified old Web PID 402276. Both URLs changed to `127.0.0.1:58081`; both ineffective Host headers were removed while Authorization/server names/timeouts/reconnect settings stayed unchanged. YAML was edited only while Web was stopped, avoiding watched-config HMR attempts.

Web was launched **once** as PID **414648**, with the exact bounded invocation below. An early port precheck found only a TIME_WAIT socket, not another listener; matching Node's address-reuse semantics resolved the diagnostic check before any new process was launched. Live qualification passed **401 → 303/cookie → authenticated 200**, and official read-only `pluginInventory/list` reported:

| Native entry | Enabled | Fiber phase |
| --- | --- | --- |
| `include:mcp-stack-graphify` | true | active |
| `include:mcp-stack-codegraph` | true | active |
| `include:vision-toolkit` | false | null |
| `include:speech-to-text-sensevoice` | true | active |
| `include:ui-voice-input` | true | active |

The official bridge awaits connection and initial tool synchronization before becoming active: this qualifies **native initial registration/discovery**, not merely a reachable webpage. No model prompt, graph query, voice preparation/recording, new session, package install, SDK patch, gateway relaxation or additional Web launch occurred.

Preservation checks passed: complete retained home content/modes/links/root mode, private key/permissions, global package manifests, **38 protected artifacts** and forwarder PID/start identity unchanged; the only changed artifact among the original 39 is the intended MCP overlay. All **21** Docker container identities/status/start times/restart counts/ports/networks match the current-turn baseline, including {{mstack:CLIENT_REPO}}. No container was started/stopped/recreated. No Basic Memory, n8n, Codex or PKM registration/use.

Restricted evidence: `infra/harnesses/deepseek/state/loopback-mcp-20261003-hads2zul/` (0700 directory; 0600 baseline, SDK discovery, idle check, process, Web qualification and preservation records/log). Verified rollback material: `backups/deepseek-loopback-20261003.iihnyiyl/` (0700 directory; 0600 current-home archive, compared archive logs and original patches/test). Tokens, cookies, key values and private home manifests were not published. Backups remain untouched.

**Learning:** qualify transport behavior with the pinned production runtime and installed SDK, then require native active-entry evidence. A different HTTP client's success or Web 200 is not an end-to-end acceptance test. Record a failing regression before correcting the configuration; do not retry a known unchanged 403.

## Original approved scope (historical candidate PIDs)

Target: only the user's **idle** retained-home DeepSeek Web process on Ubuntu loopback **3080**. Reuse Node **24.19.0**, official CLI/MCP **0.2.0-rc.2**, installed vision **0.1.46** disabled only for qualification, existing voice selection unchanged. No package/model/provider login or forwarder/gateway/container lifecycle. Brief Web UI interruption; reload may be needed. No active agent turn/job may be interrupted.

1. Recheck actual Web/forwarder PID/start identity, loopback listeners, artifacts, key/private profile/bundle/patch state, absence of unexpected `.env`, protected home/service files/global packages and all 21 containers. Forwarder is candidate PID **402899**, Web **402276**; never signal stale PIDs. Refresh a private current-home archive/manifest and an original-overlay rollback copy under ignored project backup/state (0700 dirs/0600 files). Preserve all user changes; unexpected versions/scope/provider settings require review, not guessing.
2. Gracefully stop only the revalidated idle Web PID with SIGTERM; bounded wait/port-release check. No broad kill/SIGKILL. Do **not** stop/restart the forwarder, Docker gateway or backend services. Stop before editing watched YAML to avoid hot-reload connections.
3. With `apply_patch`, change only both existing URLs in `infra/harnesses/deepseek/mcp-stack.cordis.yml`:

   ```yaml
   # Graphify
   url: http://127.0.0.1:58081/mcp/graphify
   # CodeGraph
   url: http://127.0.0.1:58081/mcp/codegraph
   ```

   Remove both ineffective custom `Host: '127.0.0.1:58080'` entries. Keep the existing private key-file Authorization expression/anchor, server names, tools/timeouts, strict startup failure and disabled reconnect. No Origin header, bearer copy, gateway/forwarder change, new endpoint, corpus expansion or profile/global patch. Update comments and existing inert route/header-contract tests under `integrations/deepseek/tests/test_mcp_overlay.py` to expect the new exact loopback URLs and Authorization-only headers. Run all **23** Python tests, **10** forwarder tests and native parser/composer/schema validation. No key evaluation/profile boot during offline tests.
4. Start Web **once** from this repository, with the exact invocation below. Fresh private infra launch log/PID/start record; no daemon manager, automatic retry, alias, inherited proxy/provider environment or relocated home. Existing settings/credentials/sessions remain in `/home/developer/.dsh`. The forwarder already runs; this command does not launch another one.

   ```sh
   env -i \
     PATH=/home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin:/usr/bin:/bin \
     LANG=C.UTF-8 DSH_HOME=/home/developer/.dsh \
     DSH_TELEMETRY_DISABLED=1 NODE_DISABLE_COMPILE_CACHE=1 \
     MCP_STACK_GATEWAY_KEY_FILE=/home/developer/workspace/mcp-stack/.secrets/agentgateway-client-key \
     /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node \
     /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/@deepseek-ai/dsh/lib/bin.js \
     --profile web \
     --patch /home/developer/workspace/mcp-stack/infra/harnesses/deepseek/mcp-stack.cordis.yml \
     --patch /home/developer/workspace/mcp-stack/infra/harnesses/deepseek/no-vision.cordis.yml \
     --no-open --host 127.0.0.1 --port 3080
   ```

5. Native clients may initialize/negotiate/discover/sync the two existing graph routes. This is registration/discovery only: no graph tool invocation, model prompt/job, preset/session creation, shell execution, voice recording/setup, provider/account login, Basic Memory/n8n/Codex/PKM use or memory write. SDK's native protocol negotiation is allowed; a failed entry does **not** authorize patching the SDK, protocol overrides, reconnect changes, security relaxation, additional restart or component install.
6. Verify native Web readiness/401 → 303 launch-cookie → authenticated entry 200 and read-only `pluginInventory/list`. Token/cookie stay in memory/private log; never publish launch URL/headers/config. Require `include:mcp-stack-graphify` and `include:mcp-stack-codegraph` enabled/**active**, no entry failures; vision disabled and existing voice state preserved. Web 200 alone is insufficient. Installed official bridge awaits initial tool sync, but inventory alone does not show actual tool names or qualify model usage. Derived expected namespaces are `mcp__stack_graphify__graphify_*` and `mcp__stack_codegraph__codegraph_codegraph_explore`; label expectations honestly if no live registry names are observed.
7. Compare protected state/home/key/packages/forwarder PID and all 21 container snapshots. Account for ordinary authorized Web runtime writes without overwriting settings/credentials/sessions. On success leave Web/forwarder running; report exact observed evidence, versions/paths and limits. On failure leave any still-running Web clearly unqualified, stop further work/report; no automatic rollback startup or retry.

## Operating limits and rollback

Forwarder source remains built-ins-only and transport-only, not a gateway policy change. It expires idle TCP connections after **10 minutes**; native reconnect remains disabled for this first check. Successful initial connection is not a guarantee of indefinite idle/recovery behavior. Long-session reconnection tuning needs its own later scope. Both indexes are partial approved projections; root overlay makes clients available to sessions, not automatic task/repository filtering. Reserve this patched host for approved `mcp-stack` coding work; no CodeGraph in PKM/personal tasks and no default calling both graphs.

No paid request/install/data migration or existing container action. Original home backups and original overlay remain private rollback material. Rollback requires separately approved stop of only the owned Web process, restoring the prior YAML/header blocks with `apply_patch` while stopped, and any chosen relaunch. Removing the vision-disable patch can prepare/clean its Python runtime, so that startup is not implicitly approved. Do not restore stale sessions/credentials or delete backups. Forwarder stop/removal and later Basic Memory/n8n/Codex/PKM remain independent approvals.
