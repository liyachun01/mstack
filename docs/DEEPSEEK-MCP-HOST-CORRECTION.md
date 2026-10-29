# DeepSeek MCP Host correction — approved attempt failed

## Outcome (2026-10-02)

User “do” approved this exact step. **Executed once; both native MCP clients still failed with HTTP 403. No second retry.** The original proposal below is history, not a command to repeat.

- Revalidated original Web PID **392532**, pinned artifacts, full retained home/key/global versions and all **21** container snapshots. Fresh private archive `backups/deepseek-host-fix-20261002.uggaz34u/current-home.tar` compared successfully; original overlay copied into private `infra/harnesses/deepseek/state/host-fix-12cetz1k/original-overlay.yml`. Directories 0700, files 0600. Nothing deleted/restored.
- Exactly four authenticated HEAD requests: each graph route gave **403** for the ordinary transport Host, **405** for fixed `127.0.0.1:58080`. Same key/routes; only Host differed. This substantiates authority-dependent rejection and removes that rejection with a low-level HTTP client. HEAD has no response body here; no DNS-error body was captured, and 405 is not MCP success. No model/MCP method submitted by this diagnostic.
- Gracefully stopped only PID 392532; checked port release **before** editing the watched YAML. Added the two approved fixed Host values plus historical comments, no Authorization/URL/gateway change. Added one inert test under `integrations/deepseek/tests/`: **23** tests and installed native parser/composer/schema checks pass.
- Relaunched once using unchanged clean environment/arguments, Node **24.19.0**, official CLI/MCP **0.2.0-rc.2**, retained home, same repo cwd and two overlays. New Ubuntu PID **402276**, Web loopback **3080**, left running. Native unauthenticated **401**, launch exchange **303**, authenticated entry **200**, read-only inventory **200**.
- Inventory: `include:mcp-stack-graphify` and `include:mcp-stack-codegraph` enabled/**failed**; SDK version-negotiation denied with **403**. `include:vision-toolkit` disabled/no live fiber; existing voice provider/UI preserved active. No graph tool names/query, model job, recording/model download, package installation, global setup, container action or extra component. Current patched Web is **unqualified for graph use**.
- Root cause from **read-only inspection of the installed Node binary's own built-in source**: `internal/deps/undici/undici` unconditionally executes `httpRequest.headersList.delete("host", true)` in its outgoing HTTP-fetch path. The installed official plugin passes our headers to `StreamableHTTPClientTransport`; that SDK uses native `fetch`. Thus the config header is discarded, unlike the Python low-level HEAD client. The attempted HEAD qualification did not cover the production HTTP implementation; that was the missing check in this proposal. No SDK/runtime monkey patch, protocol pin or security relaxation applied.
- Complete retained-home content/modes/symlinks, key/content/mode, six global package versions and all 21 container snapshots unchanged after the attempt. Private process/log/HEAD/inventory/outcome records retained in `infra/harnesses/deepseek/state/host-fix-12cetz1k/`; do not publish the token-bearing log. Original-header rollback material retained; rollback relaunch/vision activation is not automatic.

Next proposed solution is a [separately approved project-local loopback TCP forwarder](DEEPSEEK-LOOPBACK-FORWARDER-PROPOSAL.md), not another Host-header retry. No forwarder source/service or changed MCP URL has been installed/started.

## Original proposal (historical; not permission to repeat)

2026-10-02 preparation: the native activation left DeepSeek Web running at loopback 3080, PID **392532**, retained home preserved, vision disabled. Both official MCP client entries failed with **HTTP 403 during version negotiation**. No retry had been performed at this checkpoint. See [the initial outcome](DEEPSEEK-NATIVE-MCP-PROPOSAL.md).

## Cause and preferred correction

The project overlay connects physically through `host.orb.internal:58080`, while the existing gateway has DNS-rebinding protection enabled for both MCP routes. The [official documentation](https://agentgateway.dev/docs/standalone/latest/integrations/mcp/servers/http/) restricts Host/Origin to loopback and documents a 403 for non-loopback values. This is the likely cause; the exact HTTP body is not yet captured. It is not evidence of an invalid key, broken graph backend or incompatible negotiated protocol.

Prefer a **client-only, fixed loopback HTTP Host header**, retaining the OrbStack transport address. This is an explicit trusted local CLI connection to our loopback-published gateway, not a wildcard Host/Origin allowlist. Keep gateway DNS protection, bearer authentication, loopback publication, backend isolation and tool restrictions intact. No new proxy, tunnel, image, package or global config. Do not disable DNS protection to make this work.

The installed official MCP plugin forwards its `headers` to the SDK's `requestInit.headers`; actual Node/SDK propagation and protocol fallback still require qualification. Do not claim a fix before live verification.

## Exact proposed step

Target: Ubuntu project overlay and only the idle Web process at **3080**. Source/version: existing Node **24.19.0**, official CLI/MCP **0.2.0-rc.2**, vision **0.1.46** retained/disabled. Brief UI interruption; no installation. Obtain explicit approval for this entire narrow step before executing.

1. Recheck Web PID/start identity, versions/artifact hashes, protected home/key/config and all 21 containers. Refresh a private retained-home backup and copy the original overlay into ignored restricted project state. Confirm the user is idle. If unexpected state changed, stop/report.
2. Before stopping or editing, perform only bounded, authenticated **HTTP HEAD** diagnostics on the two existing MCP URLs, once each with the ordinary transport Host and once each with `Host: 127.0.0.1:58080`. No MCP initialize/discover/tools/call, model job or other endpoint. Bearer key stays in memory; disable proxy use/redirects; record safe statuses and exact-match known DNS-rebinding message only. The ordinary-host response must substantiate the rejection and the fixed-host response must remove that rejection; if ambiguous or another failure, stop without editing/restarting. HEAD's acceptance does not establish MCP success.
3. Gracefully stop only the freshly verified Web PID, bounded wait, no broad kill/SIGKILL. **Stop before editing the watched overlay**, avoiding an unapproved hot-reload/retry. If it does not stop or 3080 is occupied, stop/report.
4. With `apply_patch`, add this one public header alongside the existing Authorization expression in **both** client rows of `infra/harnesses/deepseek/mcp-stack.cordis.yml`:

   ```yaml
   Host: '127.0.0.1:58080'
   ```

   URLs remain `http://host.orb.internal:58080/mcp/graphify` and `/mcp/codegraph`; no Origin header is added, no bearer expression change. Add a matching inert header-contract test under `integrations/deepseek/tests/test_mcp_overlay.py`; run the existing 22 tests plus that new test and the installed native parser/schema check. No real key evaluation or startup in offline tests. Update YAML's historical preparation-only comment while stopped.
5. Relaunch **once**, using the exact clean environment, existing retained home, cwd, pinned Node/CLI invocation, two `--patch` paths and host/port from [the approved activation](DEEPSEEK-NATIVE-MCP-PROPOSAL.md). The invocation itself is unchanged; only the two explicit Host values differ. Use a fresh 0700 infra state directory/0600 log; no auto-retry or new environment variables. Keep vision disabled and voice selection unchanged. Native clients may initialize/discover the two graph routes, but no graph tool call/model prompt is approved.
6. Verify native 401 → 303/cookie → authenticated Web 200 and read-only `pluginInventory/list`. Require `include:mcp-stack-graphify` and `include:mcp-stack-codegraph` enabled/**active**, vision disabled. Failed entries are a failed qualification even if Web is online. No plugin-manager mutations or preset/session creation. Report only actual observed state; inventory alone is not a model-facing tool-list or query test.
7. Compare protected home/global packages/key and all 21 container snapshots. Retain successful Web process for use. On any failed connection, stop further work and report; do not patch the SDK, adjust protocol pins, change gateway policies or silently retry. Leave any still-running Web process clearly labeled unqualified; no rollback relaunch/vision activation without approval.

## Impact and rollback

No Docker/Compose action, port allocation, global harness registration, Ubuntu mise, Basic Memory, n8n, PKM, model download or provider cost. Original home/key/container data remain unchanged except ordinary authorized Web runtime writes, which must be accounted for separately. Native graph discovery is the only live registration, not a model query. Project files remain shareable, secret state private.

Rollback: separately approve stopping only the owned Web process, restoring the two original header blocks from the private copy with `apply_patch`, and any desired relaunch. Removing both project `--patch` arguments can reactivate vision; that startup is not implicitly approved. Do not restore stale account/session data or remove backups. No automatic cleanup/rollback startup is proposed.
