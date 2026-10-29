# DeepSeek: React findings and isolated Web foundation test

2026-10-02: **original attempt failed HTTP qualification; separately approved authentication correction/retry subsequently passed**. See [completion evidence](DEEPSEEK-WEB-AUTH-CORRECTION.md): native readiness, unauthenticated 401, temporary-token 303/cookie exchange, entry/asset 200, owned-process stop and protected-state checks. Existing official CLI/frontend **0.2.0-rc.2** and Node **24.19.0** were used without installation, vision activation or model/MCP calls. Original failure/proposal below remain historical, not an automatic retry authorization.

## Approved attempt outcome (2026-10-02)

The user's “approve” authorized the exact command below. Fresh pinned Node/CLI/plugin/source checks passed; no existing DeepSeek process was detected, the ignored state parent was 0700 and approximately 243 GB disk space was available. Fresh user/network namespaces worked and the test-owned server emitted its native readiness announcement. The HTTP loop nevertheless exhausted its 60-second readiness bound. No entry/asset HTTP 200 or browser rendering pass is claimed.

Read-only source inspection identifies a test-client defect: `dsh-client-connection`'s `BrowserAuth.authorizeIndex` requires the process launch token to exchange for a signed browser cookie (303 to `./`), then that cookie to serve the index. `dsh-host-frontend-static` calls this authorization before rendering. Our helper requested the clean `/` without token/cookie; it also caught `HTTPError` as `URLError` and suppressed the status until timeout. The original attempt did not record response statuses, so **401 is source-supported diagnosis, not captured live evidence**. No vendor patch, authentication bypass or dependency installation is indicated.

The runner stopped its owned process; independent `/proc` checks found no remaining approved-test/DeepSeek entry processes. Complete retained `.dsh` content/modes/symlinks and root mode, global package identities, CLI entry hash/bin link and all **21** container ID/status/start/restart/port/network snapshots match the fresh baseline. Existing backups were not used or altered; no rollback is needed.

Private diagnostic fixture retained at `infra/harnesses/deepseek/state/web-smoke-ei3ocglm/` (0700); `server.log` and `namespace.log` are 0600 and ignored. The server log contains a temporary token-bearing URL and was not printed. Namespace stderr is the runner's generic failure message. No cleanup/deletion performed. The live retained profile, vision/Python cache, credentials/sessions, models, gateway/harness integration and Basic Memory/n8n/PKM remain untested and unchanged.

## Findings: React is a browser-shell dependency

The installed frontend entry `@deepseek-ai/dsh-web-frontend/dist/assets/index-5SrrfWpU.js` contains React **18.3.1** version markers and a shell seed factory providing `react`, `react/jsx-runtime`, `react-dom`, `react-dom/client` and framework primitives. That factory is passed to the native client module system's `staticModules`; its loader resolves seed names before factories/graph entries.

Vision **0.1.46** `lib/client.js` registers its lazy factory using `window.__ModuleLoader__.load`. Its three constant browser imports are `react`, `react/jsx-runtime` and `@deepseek-ai/dsh-client-ui-primitives`; **all three are present in the shell seed**. React 18.3.1 falls within the declared `^18.2.0` range. Thus the standalone npm/pnpm peer warning is not evidence that another React package must be installed. Do not install one to silence the warning.

Repeatable read-only audit:

```sh
python3 -I -B integrations/deepseek/inspect_frontend.py \
  --cli-root /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/@deepseek-ai/dsh \
  --vision-root /home/developer/.dsh/profiles/web/node_modules/@anionex/dsh-vision-toolkit
python3 -I -B -m unittest discover -s integrations/deepseek/tests -v
```

Audit passed; **9** synthetic/helper tests passed. Frontend entry SHA-256 `af3ff948cf3f132edbddebea93e2f9f02233b390a94bd4c9842182300be811bb`; vision client SHA-256 `c0afbca90cd524b4e40ba8b7769d1e286103eed3701dd8466bf9b5ea90b0340e`. These are source-contract checks, not browser execution/rendering or actual plugin activation. Sources: inspected pinned installed artifacts, [official project/safety links](https://github.com/deepseek-ai/deepseek-harness), [plugin maintainer](https://github.com/Anionex/dsh-vision-toolkit).

## Why not launch the retained full profile yet

Vision's `apply` prepares an artifact-access key and initializes a runtime manager. Its default factory calls `prepareUpstreamRuntime`; default **managed** mode can create a virtualenv, use uv/pip, install locked dependencies and fall back to downloading Python if an interpreter cannot be resolved. It can also clean old cache generations. `--ignore-scripts` during package installation does not prevent these later startup actions. Do not treat full profile boot as a no-install check.

The **pre-existing**, untouched cache under `/home/developer/.dsh/cache/dsh-vision-toolkit` has a runtime marker for Python **3.14.4**, Pillow **12.3.0**, NumPy **2.4.6**, vtracer **0.6.15**. Its upstream commit/content hash/requirements hash match the newly installed plugin's packaged snapshot and lock; its interpreter path exists. No interpreter was executed, module imported, package installed or cache modified during discovery. This marker match is a possible reuse path, **not proof of executable/environment health or approval to reuse/reconfigure it**.

Choose foundation-first: boot a disposable profile with **only existing base+web bundles** and no vision mount. Preserve the installed live plugin, config, sessions, Python cache and package managers. Qualify vision activation separately later without assuming its runtime/bootstrap is necessary for graph/Basic Memory MCP integration.

## Original approved startup — executed once, do not retry automatically

Source runner already prepared at `integrations/deepseek/web_smoke.py`; tests verify its explicit approval gate and owned-process cleanup helpers without invoking a harness or namespace. Existing utilities verified read-only: `/usr/bin/unshare` (util-linux **2.41.3**), `/usr/sbin/ip` (iproute2 **6.19.0**); no installation proposed. Kernel user/network namespace availability is **not** tested yet: the approved attempt will abort if denied, never invoke sudo, change AppArmor/sysctls or launch without isolation.

Immediately before execution, recheck recognized DeepSeek processes (do not stop any), pinned Node/CLI/plugin/source identities, available disk, global tool identities and all existing container IDs/status/start times/restart counts/ports/networks. Hash the existing complete `.dsh` home privately; no credentials/settings/sessions copied into the fixture. Confirm the existing ignored state parent is 0700 and no runtime profile or external install has been added since review.

After explicit approval, from `/home/developer/workspace/mcp-stack`:

```sh
python3 -I -B integrations/deepseek/web_smoke.py --execute-approved \
  --node /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node \
  --cli-root /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/@deepseek-ai/dsh \
  --state-root /home/developer/workspace/mcp-stack/infra/harnesses/deepseek/state \
  --existing-home /home/developer/.dsh
```

The runner creates a unique `infra/harnesses/deepseek/state/web-smoke-*/` (0700), a clean `home/profiles/web/package.json` containing only `@deepseek-ai/dsh-base` + `@deepseek-ai/dsh-web-app`, clean work directory and restricted logs. It uses existing package resolution: no package-manager invocation, peer install, copied plugin/node_modules/Python cache, config relocation or live global-home modification.

It invokes **existing** `unshare --user --map-root-user --net --fork --kill-child=TERM`, then the same Python runner inside the new namespaces. Namespace identities must differ from the parent before it raises **only the new namespace's** loopback interface using `ip link set lo up`. Mapping the test user to root here grants capabilities in that new namespace, **not host root/sudo, a Docker privilege or access to host networking**. No route/network is attached; DNS/Internet/host services are unreachable from the test. This is network isolation, not a filesystem sandbox: the harness submits no agent job/tool operation.

The node child gets a fresh allowlisted environment only: `PATH=/usr/bin:/bin`, `LANG=C.UTF-8`, test `DSH_HOME`, `DSH_TELEMETRY_DISABLED=1`, `NODE_DISABLE_COMPILE_CACHE=1`. It starts with explicit Node/CLI paths and `--profile web --no-open --host 127.0.0.1 --port 13080`. No inherited provider credentials, proxy, `.env`, `NODE_OPTIONS` or GUI environment; invoking work directory is fresh. `DSH_HOME` is process-level before dotenv resolution. Upstream may initialize its ordinary profile/settings/token state, **only inside the fixture**. No vision bundle, model request, login, MCP connection, n8n/database/PKM action, external download or registration.

Port **13080 is inside the private network namespace only**: not a Docker published port, macOS listener, host-wide binding or URL to open from your browser. It cannot conflict with a live host listener on that number. The internal test waits for the native audited-ready announcement, requests `/` and the local frontend entry asset, and checks HTTP 200/React seed presence. It does not invoke API tools, create a session/job or exercise the browser DOM. Raw startup output may contain a new auth URL/token: remains in ignored mode-0600 `server.log`, never printed/shared.

Readiness is bounded at 60 seconds; requests have 2-second timeouts, namespace attempt bounded at 90 seconds. Cleanup signals only the newly created Node process group, waits 10 seconds, then SIGKILLs it if necessary; no process lookup by port/name or broad kill. Parent-death handling also reaps the owned server. Isolation/startup/HTTP failures abort, retain private diagnostic state and require a new proposal for any fix; no automatic retry, broader privileges or package install.

## Verify and recover

Report native readiness, entry/asset responses, own-process shutdown, private state path and limitations. Compare complete retained home hashes/modes/symlinks, global identity and all retained containers before/after without publishing secret hashes. Confirm no owned server remains. Browser rendering, retained-profile credential/session compatibility, actual vision activation, Python health/model use and gateway connections remain **untested** even if this foundation smoke passes.

No live data migration or installation means no global restore is normally needed. If unexpected protected changes occur, stop and diagnose; never overwrite current credentials/sessions from old backups automatically. Only test-owned processes may be stopped by this approval. Keep the restricted fixture/logs for inspection; deleting them requires scoped cleanup approval later. Existing CLI/plugin backups remain untouched.
