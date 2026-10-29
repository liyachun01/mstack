# DeepSeek native graph MCP overlay and activation proposal

2026-10-02: preparation and the subsequent activation were separately approved. **Activation attempted once; Web is online, but both graph MCP entries failed with HTTP 403. Integration is not complete.** The original proposal below is retained as history; do not execute it again without a new approval.

Latest: the [separately approved Host correction](DEEPSEEK-MCP-HOST-CORRECTION.md) also failed once. Current Web PID **402276**, vision disabled, both MCP clients failed. Pinned Node fetch deletes custom Host headers; the next [forwarder-only proposal](DEEPSEEK-LOOPBACK-FORWARDER-PROPOSAL.md) requires its own approval. PID 392532 and all initial-attempt observations below are historical.

## Approved activation outcome

- Fresh restricted backup: `backups/deepseek-native-mcp-20261002.ePESDt/current-home.tar`, with private baseline/compare records. Archive comparison passed before relaunch.
- Revalidated and gracefully stopped only original Ubuntu PID **363650**; launched pinned Node **24.19.0** / official CLI and MCP **0.2.0-rc.2** once, using the exact invocation below and the existing retained home. New PID **392532**, loopback **3080**, project cwd. No installation or global configuration change.
- Native Web checks: unauthenticated **401**, temporary-token exchange **303**, authenticated entry **200**, read-only `pluginInventory/list` **200**. Temporary token/cookie were kept private. No model prompt, agent job, account login or graph query was sent.
- Native Loader prefixes ids with `include:`. Inventory observed `include:mcp-stack-graphify` and `include:mcp-stack-codegraph`: enabled, **failed**, not active. Both official SDK errors say version negotiation was denied with **HTTP 403**. No model-facing graph names were observed; expected names below are not a live tool-list assertion. The first inventory filter omitted the Loader prefix; a second read corrected it without mutation or connection retry.
- `include:vision-toolkit`: disabled, no live fiber. Existing voice provider/UI entries were preserved and active; their source shows startup checks cached files, while preparation/model loading requires an explicit later action. No recording, voice setup, Python preparation or model download was performed. Voice was already selected in the pre-proposal home, not newly enabled here.
- Complete retained home content/modes/symlinks, gateway key/content/mode, six global package versions and all **21** container identity/status/start/restart/port/network snapshots are unchanged after activation. No cache/profile/session/credential file changes were observed. **22** offline tests and native parser/composer/schema checks still pass.
- Private launch/process/verification records: `infra/harnesses/deepseek/state/native-mcp-1he3pvlq/`, directory 0700/files 0600. Raw server log contains a temporary launch-token URL; never publish it. No automatic retry, security relaxation, rollback startup or other service action was performed. **Web remains running with failed graph entries and vision disabled**, not with a successful MCP integration.

Likely cause: the overlay uses the transport hostname `host.orb.internal`; both gateway MCP backends enable `dnsRebindingProtection`. The [official gateway documentation](https://agentgateway.dev/docs/standalone/latest/integrations/mcp/servers/http/) says this check accepts only loopback Host/Origin values and otherwise returns 403. That matches both observed failures, but the SDK log omitted the response body, so the precise rejection is still an inference. TCP reachability alone did not qualify HTTP authority validation. A [separate header diagnostic/correction proposal](DEEPSEEK-MCP-HOST-CORRECTION.md) follows; nothing there has been executed.

## Prepared result

`infra/harnesses/deepseek/mcp-stack.cordis.yml` inserts two existing official **0.2.0-rc.2** `@deepseek-ai/dsh-mcp-client` rows, using Streamable HTTP and the existing gateway client key. No plugin install or custom bridge. The inspected plugin entry SHA-256 is `758d8fc473b700b5d351158d06ce9f9e92c16e8b25497b08bb7bd2122a87f5dd`.

- Graphify: `http://host.orb.internal:58080/mcp/graphify`, namespace `stack_graphify`, seven existing query tools.
- CodeGraph: `http://host.orb.internal:58080/mcp/codegraph`, namespace `stack_codegraph`, one existing explore tool.
- Auth: process-only `MCP_STACK_GATEWAY_KEY_FILE` points to existing ignored `.secrets/agentgateway-client-key` (0600, parent 0700); the native `!!js` expression checks the explicit project path/regular-file permissions/key shape and constructs the bearer header in memory. No actual key in YAML/argv/source/public logs.
- Optional `infra/harnesses/deepseek/no-vision.cordis.yml` disables only `vision-toolkit` activation for the first MCP check, without changing its installation or retained bundle selection. Its target id is verified against the installed vendor bundle patch.

**22** Python static/synthetic/helper tests pass. Existing PyYAML **6.0.3**, no install. The installed official parser/patch composer accepts both overlays; JS syntax compilation and installed MCP Config schema checks pass with a dummy auth placeholder. No expression evaluation, credential reading, profile initialization or plugin activation during validation. Native composition covers shipped base+web layers plus a synthetic vision row, not the user's private overrides.

Prepared file SHA-256: `mcp-stack.cordis.yml` = `ba84871251184602dea6641946129bf9a0994b0ec87f0c2019eca50882d7c295`; `no-vision.cordis.yml` = `a390ab6a9faa68920d9ff3faa40572455ac9f53ec6bf05affd88a7caada6f589`. One offline check's argument-count assertion was corrected (no runtime action) before the final native validation pass. Final protected checks: complete retained home and existing key content/mode unchanged; original Web PID/start identity still running on 3080; all 21 container identities/status/start/restart/port/network snapshots unchanged. No rollback/cleanup needed for preparation.

Ubuntu TCP checks: `127.0.0.1:58080` refused; `host.orb.internal:58080` and `mac.orb.internal:58080` accepted, **no application requests sent**. This does not prove authenticated MCP/protocol support through the alias. No gateway listener/network/auth change proposed.

The user-started `dsh web` was observed as Ubuntu PID **363650**, Node **24.19.0**, workspace `/home/developer`, listening at Ubuntu loopback 3080; OrbStack forwards macOS loopback 3080. Retained home is `/home/developer/.dsh` (no process-level DSH_HOME override). Its profile patch currently has three entries; no home-level patch exists. No private override values or launch token printed. These live observations must be refreshed before relaunch; do not kill a stale PID or infer the profile is idle.

## Proposed activation — separate explicit approval required

Target: **only the user's idle DeepSeek Web instance**, Ubuntu Node **24.19.0**, official CLI/MCP **0.2.0-rc.2**, Web port **3080**, same retained home. Brief UI interruption; browser reload may be needed. Do not proceed during an active agent turn/job. If the process/installation/private overrides or permission scope changed, stop and report instead of guessing or starting a second server.

1. Recheck exact listener ownership/PID/start identity, versions/hashes, the two new file hashes, key permissions, existing profile/bundle/patch identities and missing unexpected project `.env` layers. Detect native MCP id collisions/private patches or unreviewed extra components before start. Preserve other host/Ubuntu processes and all 21 containers. Do not expose secrets from config dumps/errors.
2. Create a fresh restricted project backup of the **current** retained home/config/session state before relaunch; previous backups predate user activity. Record private manifests without publishing hashes of credentials. Backup/log directories under ignored `backups/` and `infra/harnesses/deepseek/state/`, mode 0700 and files 0600. Never restore stale credentials/sessions automatically.
3. After the user confirms the instance is idle, signal **only** the freshly verified Web PID with SIGTERM. Current candidate command is `kill -TERM 363650`; it is not safe as a standalone stale command. Wait boundedly for exit/port release. No broad name/port/group kill and no SIGKILL without another approval; if it does not stop, leave it alone and report.
4. Launch from `/home/developer/workspace/mcp-stack` with the following exact native invocation (shown for scope, **not executed**). Allowlist the child environment using `env -i`; existing provider/account configuration stays in the retained home, not copied into environment. This filters inherited proxy/provider variables; do not silently add unrelated credentials if the existing setup depends on them.

```sh
env -i \
  PATH=/home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin:/usr/bin:/bin \
  LANG=C.UTF-8 \
  DSH_HOME=/home/developer/.dsh \
  DSH_TELEMETRY_DISABLED=1 \
  NODE_DISABLE_COMPILE_CACHE=1 \
  MCP_STACK_GATEWAY_KEY_FILE=/home/developer/workspace/mcp-stack/.secrets/agentgateway-client-key \
  /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node \
  /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/@deepseek-ai/dsh/lib/bin.js \
  --profile web \
  --patch /home/developer/workspace/mcp-stack/infra/harnesses/deepseek/mcp-stack.cordis.yml \
  --patch /home/developer/workspace/mcp-stack/infra/harnesses/deepseek/no-vision.cordis.yml \
  --no-open --host 127.0.0.1 --port 3080
```

Capture server output only in a fresh private infra log: the native announcement includes a temporary launch-token URL. Do not print it to chat or pass bearer credentials/cookies in command arguments. No daemon manager, global shell alias/config, Ubuntu mise, package manager or server installation.

The process may perform ordinary retained-home runtime initialization; it must preserve settings/credentials/sessions and must not relocate/reset the home, overwrite private patches or install/reconcile plugins. Vision activation/Python preparation/cache cleanup is disabled for this first check. No account login, model prompt/agent job, shell tool, indexing/watch/sync, Basic Memory/n8n/PKM connection or gateway lifecycle change is authorized. The MCP client itself performs initialization/discovery on the two existing graph routes; **that is the narrowly requested registration**, not a model call. Initial reconnect is disabled; unexpected discovery/registration failures require diagnosis, not auto-retry or installation.

## Acceptance and limits

Use native Web readiness/authentication checks without creating jobs. Inspect the official read-only plugin inventory (`pluginInventory/list`, via the existing Plugins UI/Remote) and require both ids `mcp-stack-graphify` and `mcp-stack-codegraph` enabled/active, no MCP entry errors. Vision must be disabled; Web online alone is insufficient. Only the inventory read is proposed; no plugin-manager mutation/config write or model request. The existing official MCP bridge awaits initial connection and tool sync; inspect its safe status diagnostics rather than claiming success from HTTP 200 alone.

Expected model-facing names are `mcp__stack_graphify__graphify_<tool>` for query_graph/get_node/get_neighbors/get_community/god_nodes/graph_stats/shortest_path, and `mcp__stack_codegraph__codegraph_codegraph_explore`. Document which names were actually observed; derived expectations are not a live tool-list assertion. A guided model-driven query/use test requires separate approval and potential provider cost review.

Both indexes are partial/rebuildable, not complete source. This root overlay makes the graph clients available to sessions on the patched host; it does **not** hard-filter by task/repository. Reserve it for approved `mcp-stack` coding work; do not use CodeGraph for personal/PKM sessions or auto-call both graphs. No Basic Memory row is included; that connection remains separately gated. Long-running reconnect tuning, Codex registration, n8n and PKM remain later steps.

Compare existing key/global package identities, protected vision cache/profile/package files and all 21 container snapshots before/after. Account for native Web runtime writes separately rather than asserting the complete retained home cannot change during a real startup. Preserve user changes; unexpected unrelated mutations stop the step. No existing service/port/network volume changes.

## Rollback and persistence

No global/profile patch is written: omitting the two `--patch` arguments on a **separately approved** relaunch removes these registrations and restores ordinary vision selection. Stop only the newly owned process before any rollback; do not launch a second listener at 3080. Restoring the original user launch can reactivate vision and other user hooks, so no automatic rollback startup is authorized by this proposal. Retain all backups/logs; no deletion or credentials/session restore without separate scoped approval.

Project YAML/test/source is shareable; keys/home/session/logs remain private. `--patch` does not automatically persist into the user's launch command or configure other hosts. No commit/push performed. See [infra notes](../infra/harnesses/deepseek/README.md), [routing policy](MEMORY-ROUTING.md) and [runbook](OPERATIONS-RUNBOOK.md).

Sources: [official native MCP plugin](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md), [official `--patch` connection guide](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/mcp-memory.md), and pinned installed parser/schema/vendor bundle sources. Web docs may advance beyond the installed preview; qualification above uses the installed **0.2.0-rc.2** artifact, not an automatic latest upgrade.
