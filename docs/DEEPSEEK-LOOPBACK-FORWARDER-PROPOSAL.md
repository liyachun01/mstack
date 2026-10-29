# DeepSeek local gateway forwarder — approved and qualified

2026-10-02. User **“go”** explicitly approved the forwarder-only setup after scope confirmation. **Source/config authored, one process started, native-fetch HEAD qualification passed. DeepSeek Web/MCP configuration was not changed.** The original proposal below remains the scope/operating recipe, not permission for an additional lifecycle action.

## Completed result

- New reusable source: `integrations/deepseek/gateway_forwarder.mjs`; runtime config: `infra/harnesses/deepseek/gateway-forwarder.json`; synthetic tests: `integrations/deepseek/tests/test_gateway_forwarder.mjs`. Built-ins only, no package/image/toolchain install, SDK patch, global config, Ubuntu mise or service manager.
- Reused Node **24.19.0** at `/home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node`. New owned Ubuntu PID **402899**, repo cwd, listener **127.0.0.1:58081**, upstream **host.orb.internal:58080** pinned after DNS verification to observed **0.250.250.254**. Accepts exactly the approved config; public/unexpected/mixed/IPv6 resolutions fail closed. No generic proxy, credentials/payload inspection or HTTP rewriting. Max 32 connections, 5-second connect/DNS timeout, 10-minute idle timeout, 5-second shutdown drain; no auto-start/retry/restart policy.
- The synthetic address is OrbStack-local, not RFC1918. Only that exact observed address is accepted, not all `0/8` or private networks. [Official OrbStack networking documentation](https://docs.orbstack.dev/machines/network) identifies `host.orb.internal` as the Mac-host path; this machine's DNS/route and prior HTTP probes supply the exact address. No DNS/hosts/global networking changes.
- **10** synthetic/stubbed forwarder tests pass: strict config/DNS boundaries, redacted failures/timeouts, pipe/half-close cleanup, capacity/refusal, errors, idempotent/bounded shutdown and no listener retry. Existing **23** Python tests still pass. Syntax check/source review passed before the single start. These are not live capacity/load/shutdown/reboot tests.
- Live verification used **the pinned Node native fetch** with no Host override, proxies or redirects: exactly six HEAD requests. Valid bearer: **405** on each MCP route; missing/wrong bearer: **401** on each. No MCP method, discovery/session/tool/model/voice request. Authentication and loopback-authority transport checks pass; **405 is not a protocol/tool integration pass**. Diagnostic client sockets closed, independently checked with `ss`.
- Listener observed only at Ubuntu loopback. Existing OrbStack automatically mirrors it to macOS **127.0.0.1:58081** (observed OrbStack-owned listener); no Docker port publication or explicit host network configuration was added. This ordinary OrbStack side effect qualifies the earlier “no macOS port publication” wording; neither wildcard nor LAN listener was observed.
- One idle process sample: **0.0% CPU**, **64,376 KiB RSS (~63 MiB)**. This is a point-in-time/cumulative process sample, not a battery measurement or full-stack budget.
- Complete retained DeepSeek home/content/modes/symlinks, gateway key/content/mode, global package manifests, **39** protected source/service-config/key/runtime files, original Web PID **402276**/start identity and all **21** container identity/status/start/restart/port/network snapshots are unchanged. Basic Memory/{{mstack:CLIENT_REPO}}/caffeinate and all stopped containers untouched. DeepSeek graph entries remain failed; vision remains disabled from the earlier launch. No current MCP YAML edit/reload/restart, new authentication or index work.
- Private 0700 records: `infra/harnesses/deepseek/state/gateway-forwarder-azpycwwg/`, 0600 `baseline.json`, `process.json`, `server.log`, `verification.json`, `preservation.json`. No deletion/rollback needed. Source/config/tests are shareable; records/key/home remain ignored/private. Earlier home backups retained untouched.

The next separately gated step is [native MCP URL change and one idle Web relaunch](DEEPSEEK-LOOPBACK-MCP-ACTIVATION-PROPOSAL.md). It has **not** been performed. Do not treat this transport qualification as registration approval.

## Original approved proposal (historical where it says not created)

The [approved Host correction failed](DEEPSEEK-MCP-HOST-CORRECTION.md): pinned Node 24.19.0 fetch deletes the custom Host header. The official MCP plugin cannot express the required authority through its present header-only interface. Preserve that official installation and the gateway's DNS protection instead of monkey-patching either.

## Recommendation and scope

Use a tiny project-owned **TCP forwarder inside Ubuntu**, listening only on `127.0.0.1:58081`, forwarding bytes to the existing macOS OrbStack gateway at `host.orb.internal:58080`. Future MCP URLs can then genuinely use Ubuntu localhost, so native fetch generates a loopback Host itself. The gateway still requires its bearer key and enforces its tool policies. No HTTP/header rewriting, proxy credentials, model inference, new container, npm dependency or third-party daemon.

This approval would cover **the forwarder only**, not another DeepSeek restart/registration. Native MCP URL changes and discovery will be a separate next proposal after the transport passes. Current Web PID 402276 stays running, graphs failed, vision disabled. Basic Memory/n8n/Codex/PKM remain independently gated.

## Proposed setup, exact locations and command

- Execution domain: existing OrbStack Ubuntu `devbox`; reuse pinned Node **24.19.0**. No Ubuntu mise/global config, system package manager or macOS setup.
- Source to author with `apply_patch`: `integrations/deepseek/gateway_forwarder.mjs`, using only Node's built-in `net`, `dns`, `fs` and validation primitives. Reusable tests: `integrations/deepseek/tests/test_gateway_forwarder.mjs`, using built-in `node:test` and synthetic/stubbed sockets; no package installation/test dependency or model call.
- Runtime configuration to author: `infra/harnesses/deepseek/gateway-forwarder.json`, exact listener `127.0.0.1:58081`, exact upstream hostname `host.orb.internal`, port `58080`; reject other targets/listener addresses. Do not make this a generic open proxy. Bounded 32 connections, 5-second connect timeout, 10-minute idle timeout, backpressure, error/half-close cleanup and bounded graceful shutdown. Validate resolved upstream is an approved private/local address, never public; do not modify DNS/hosts files.
- Re-inventory listener ownership/all containers before allocating port. Ubuntu 58081 was free at proposal preparation; recheck, never stop another listener. No macOS port publication. Loopback access is local, not a filesystem/user sandbox; another local user still needs the gateway key. Forwarder does not read/store/log the key or inspect payload bytes.
- Launch only after offline checks pass, from this repository with explicit Node, clean PATH/LANG/compile-cache settings and private stdout/stderr under a new ignored 0700 infra state directory, files 0600. No credential/provider/proxy environment, global alias, service manager, automatic startup or restart policy. Long-lived owned process with recorded PID/start identity. No auto-retry if setup fails.

```sh
NODE_DISABLE_COMPILE_CACHE=1 /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node --test integrations/deepseek/tests/test_gateway_forwarder.mjs

env -i \
  PATH=/home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin:/usr/bin:/bin \
  LANG=C.UTF-8 NODE_DISABLE_COMPILE_CACHE=1 \
  /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node \
  integrations/deepseek/gateway_forwarder.mjs \
  --config infra/harnesses/deepseek/gateway-forwarder.json
```

The code/config do not exist yet. Permission here would authorize authoring/validating this narrowly specified source and starting **one** forwarder, not silently importing or installing a daemon. Review tests/source/config before start; stop if unexpected privileged changes or dependencies are needed.

## Verification and impact

Use the **same pinned Node native fetch** as DeepSeek, not Python-only HTTP, for bounded authenticated HEAD requests to `http://127.0.0.1:58081/mcp/graphify` and `/mcp/codegraph`; expect **405, not 403**. Key read privately in the verifier, not the forwarder, never argv/public logs. No redirects/proxies. Negative missing/wrong-key HEAD must be rejected. No initialize/discover/tool/query/model/job/voice setup. TCP forwarding success is not a protocol/tool integration pass.

Check exact loopback listener/PID, cleanup of owned diagnostic sockets, input validation/limits and protected home/key/packages/all 21 container snapshots. No container lifecycle, image pull, database write, gateway policy change or repository indexing. Resource cost: one additional small idle Node process and sockets while used, no compute/model/container workload; measure rather than promise a specific battery saving. It is an on-demand local adapter, not an auto-start service.

Next **separate** registration proposal, only after this passes: stop idle Web before editing its watched overlay, change both URL authorities to `127.0.0.1:58081`, remove ineffective custom Host headers, update inert tests, relaunch once with retained home/vision gate and require both native MCP entries active. None of those changes is approved by the forwarder setup itself.

## Rollback

Retain source/config/logs. Stop only the newly owned forwarder using its freshly verified PID/start identity and SIGTERM; no broad port/process kill, deletion or SIGKILL. Current Web remains untouched because its URLs are not changed in this step. Any cleanup or subsequent Web/vision startup requires separate approval. Report final source paths, actual PID/resource/listener/HEAD evidence and rollback availability after setup; stop before the next component.
