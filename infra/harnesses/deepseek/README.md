# DeepSeek native MCP configuration — activation failed

## Current toolchain selection — 2026-10-15

New approved launches resolve the existing exact mise selections in `mise.toml`:
Ubuntu Node **24.19.0** and official `@deepseek-ai/dsh` **0.2.0-rc.2**. The
repo-owned launcher is `integrations/agents/deepseek_launch.py`; it checks
installed package metadata and refuses missing tools instead of installing them.
The native Node executable is
`/home/developer/.local/share/mise/installs/node/24.19.0/bin/node`. The current
mise npm installation stores the harness in
`/home/developer/.local/share/mise/installs/npm-deepseek-ai-dsh/0.2.0-rc.2/node_modules/@deepseek-ai/dsh`.

This toolchain migration does not restart a retained Web/forwarder process,
activate an MCP overlay or verify model/provider access. Existing profile state,
sessions and credentials are preserved. Do not run the normal launcher merely
for a package-version check: its preparation path reads the explicitly configured
credential. Use the credential-free offline checks below.

The mise harness includes `@deepseek-ai/dsh-mcp-client` **0.2.0-rc.2**. Its Aube
package layout uses symlinks, so the native composition checker canonicalizes the
CLI root before resolving dependencies, matching Node's normal behavior. The
offline check passes against the new mise tree, including the pinned plugin
source hash and two synthetic SDK regressions. The retained Web profile still
resolves dependencies through existing links in `~/.dsh/profiles/node_modules`
into the old fnm package tree. Those links and the profile's independent vision
**0.1.46** dependencies remain unchanged to preserve its exact dependency graph.
The fnm store must remain even after old processes exit; this profile still
depends on it. Retained-profile startup with the new top-level harness remains
untested. Do not infer a normal profile launch from the offline result or
automatically rewire/copy dependencies to remove the old store.

## Historical MCP qualification — 2026-10-02

The following PIDs, online status and container counts are dated observations,
not a fresh runtime inventory. Inspect current ownership before any approved
lifecycle operation.

2026-10-02: the [separately approved local forwarder](../../../docs/DEEPSEEK-LOOPBACK-FORWARDER-PROPOSAL.md) is now running/transport-qualified on Ubuntu **127.0.0.1:58081**, PID **402899**, existing Node **24.19.0**. Native-fetch valid-key HEAD is 405 on both routes; missing/wrong keys are 401. No MCP method/model call or additional package. **10** forwarder tests and **23** existing Python tests pass. Source is in `integrations/`, config here in `infra/`, no global toolchain change. Protected state/home/key/all 21 containers and Web identity unchanged.

Web remains online at loopback **3080**, original PID **402276**, with the earlier failing graph URLs/Host headers. Vision stays disabled from that launch. **Transport qualification is not a working MCP integration**: [native URL edit/one idle Web relaunch](../../../docs/DEEPSEEK-LOOPBACK-MCP-ACTIVATION-PROPOSAL.md) awaits its own approval. [Initial failure](../../../docs/DEEPSEEK-NATIVE-MCP-PROPOSAL.md) and [Host correction failure/backup](../../../docs/DEEPSEEK-MCP-HOST-CORRECTION.md) remain recorded. Preparation-only notes below are historical where they say not loaded.

Use the already installed official `@deepseek-ai/dsh-mcp-client` **0.2.0-rc.2**.
No new package, custom MCP bridge, global alias/config or harness replacement.

- `mcp-stack.cordis.yml`: opt-in native `--patch` overlay, two Streamable HTTP clients for the existing restricted gateway routes. Coding/repository profile; no Basic Memory or n8n connection.
- `no-vision.cordis.yml`: optional first-connection qualification gate for the installed `vision-toolkit` row. It disables activation only in that launched process, not the saved bundle/installation. This avoids startup-time Python preparation/cache cleanup; do not silently load it for ordinary launches.
- `gateway-forwarder.json`: exact loopback/OrbStack target and resource boundaries; no credential. New built-ins-only TCP source is `integrations/deepseek/gateway_forwarder.mjs`; no header rewriting or model/MCP client inside it. OrbStack automatically mirrors the loopback listener to Mac loopback, not a Docker publication or host config edit.
- Ignored `state/`: private runtime logs/test fixtures. No live credentials in these versionable YAML files.

Current Web still uses `http://host.orb.internal:58080/mcp/graphify` and `/mcp/codegraph`; native requests failed with **403 on both routes**. Pinned Node fetch deletes custom Host headers. The newly qualified forwarder exposes the transport at `http://127.0.0.1:58081/mcp/graphify` and `/mcp/codegraph`, but **those URLs have not been placed in Web's watched YAML**. Keep current YAML unchanged until approved idle stop/edit/relaunch. Do not use Ubuntu localhost 58080, expose gateway ports, disable protection or patch the SDK automatically.

Authorization is resolved by the native loader's `!!js` expression only on activation. It requires an explicit `MCP_STACK_GATEWAY_KEY_FILE` equal to the repository-root `.secrets/agentgateway-client-key` path, a non-symlink regular file with no group/other permissions and a 64-character hex key. Nothing is copied or printed; never dump evaluated configuration/HTTP headers. The existing key is 0600 under a 0700 directory.

Initial qualification deliberately disables automatic reconnect and sets a 10-second tool-call timeout; this does not bound the SDK's separate initial connection/discovery timeout. `failOnStartupError: true` rejects a failed MCP entry, but optional entry failure may not stop the whole Web app. **Web online does not prove MCP connected.** Long-running reconnect policy is a later configuration decision.

Both indexes are narrow approved projections, not complete repositories. These host-level entries would be available to sessions on the patched host; they do not implement automatic task classification/session filtering. Use this patched host for approved `mcp-stack` coding work only, select relevant tools and reassess on task/repository change. PKM/personal sessions should not inherit this CodeGraph overlay. The existing gateway limits allowed calls; YAML availability is not a new security boundary.

Offline checks (existing dependencies only; no harness startup/key read):

```sh
python3 -I -B -m unittest discover -s integrations/deepseek/tests -v
NODE_DISABLE_COMPILE_CACHE=1 /home/developer/.local/share/mise/installs/node/24.19.0/bin/node \
  --test --test-isolation=none integrations/deepseek/tests/test_gateway_forwarder.mjs
NODE_DISABLE_COMPILE_CACHE=1 /home/developer/.local/share/mise/installs/node/24.19.0/bin/node \
  integrations/deepseek/tests/check_native_overlay.mjs \
  /home/developer/.local/share/mise/installs/npm-deepseek-ai-dsh/0.2.0-rc.2/node_modules/@deepseek-ai/dsh
```

Native validation parses/composes shipped base+web layers over an empty fixture, tests a synthetic vision-row disable, compiles (does not execute) header JS and validates non-secret fields against the installed MCP schema using a dummy auth string. It does not load private profile overrides, evaluate the key expression, import vision, start plugins or connect. Python checks use existing PyYAML **6.0.3**; no test dependency installation was performed.

## Forwarder operations — approval-gated

Process is on-demand, currently left running; no auto-start/restart manager. Config is validated against exact approved values; DNS must still resolve to the pinned OrbStack-local `0.250.250.254`. A changed address fails closed and needs review, not an allowlist wildcard. Max 32 clients; 5-second connect/DNS bound, 10-minute idle expiry, 5-second shutdown drain. Long-lived native MCP reconnect behavior is unqualified and remains separate.

Private launch/baseline/verification records: `infra/harnesses/deepseek/state/gateway-forwarder-azpycwwg/`, 0700/0600. Log contains fixed readiness/shutdown/error-stage labels only, no traffic/key. One observed idle sample: ~63 MiB RSS, 0.0% process CPU; not a battery measurement. Live capacity/shutdown/reboot behavior has not been tested; synthetic coverage is recorded separately.

Before any **approved** lifecycle action, recheck listener ownership, exact executable/cwd/PID/start identity in the private `process.json`, existing services and protected state. Do not run a second process while 58081 is occupied. Exact clean launch command is in [the forwarder runbook](../../../docs/DEEPSEEK-LOOPBACK-FORWARDER-PROPOSAL.md). Data-preserving rollback stops only the matching owned forwarder PID with SIGTERM; never broad port/name kills or delete source/config/logs. Current Web is untouched by that stop because it has not switched URLs. Do not restore stale home backups or implicitly reactivate vision.

[Native MCP URL edit/relaunch proposal](../../../docs/DEEPSEEK-LOOPBACK-MCP-ACTIVATION-PROPOSAL.md) requires fresh approval; the completed forwarder setup does not authorize it. Retain `/home/developer/.dsh` settings/credentials/sessions and the prior rollback copies. Basic Memory/n8n/Codex/PKM remain separately gated.

[Official overlay guide](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/mcp-memory.md), [official MCP plugin reference](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md).
