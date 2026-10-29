# DeepSeek isolated Web test: authentication correction and retry

2026-10-02: **approved with “go”; helper correction and one isolated retry completed successfully**. The [first approved attempt](DEEPSEEK-WEB-SMOKE-PROPOSAL.md) started successfully through native readiness, but our unauthenticated HTTP client failed qualification. The correction changed only the reusable test client and tests, not vendor packages/runtime/authentication policy. Original proposal details below are retained as the scope record, not permission to rerun.

## Completion evidence

- Corrected `integrations/deepseek/web_smoke.py`: strict loopback launch URL validation, explicit HTTP-error/status handling, no automatic redirects, in-memory cookie exchange, safe stage evidence and retained-home comparison even after namespace timeout. No auth bypass or browser/account login.
- **16** synthetic/static/helper tests passed, including actual urllib redirect/error/cookie processors over an in-memory transport (no network). Fresh source audit/pinned versions/process/state/disk/global/home/container preflight passed.
- Executed the approved command **once**. Native readiness, unauthenticated root **401**, temporary launch exchange **303**, usable in-memory cookie, authenticated page **200**, frontend shell asset **200** and React seed all passed. Fresh user/network namespace identities differed from the parent; only private loopback was raised, no external route attached. No vision mount, agent job/session, model/MCP request, account login or installation.
- Owned Node server stopped; independent `/proc` check found no remaining test/DeepSeek entry process. Complete retained home/root mode, global package versions, CLI bin link and pinned CLI/frontend/vision client hashes unchanged. All **21** container identities/status/start/restart/port/network snapshots unchanged, including all stopped containers. No rollback needed.
- New fixture `infra/harnesses/deepseek/state/web-smoke-1_2ytcx9/` is 0700; `server.log`, `namespace.log`, `evidence.json` are 0600 and ignored. Only base+web bundles are present, no vision cache. Token/cookie values were not printed or serialized into public evidence. Failed fixture `web-smoke-ei3ocglm/` and old CLI/plugin backups retained, no deletion.
- Original helper copy: `infra/harnesses/deepseek/state/web_smoke.before-auth-20261002.py` (0600, ignored), compared byte-for-byte before modification; original SHA-256 `57ba22113e0533b7cff709144e9fb1fdf228ec6161b8f7fc81c2cb8078b066eb`. Scoped source rollback remains available with separately approved `apply_patch`; no package/global restore is needed.

This qualifies the isolated Web foundation **only**, not browser rendering, actual vision/Python runtime, the retained profile/credential/session compatibility, normal launcher behavior, harness MCP registration or Basic Memory/n8n/PKM integration. Next work is separately scoped project harness configuration/connection qualification; no additional startup or registration performed by this approval.

## Target and scope

Ubuntu `devbox`, existing official `@deepseek-ai/dsh` / frontend **0.2.0-rc.2**, Node **24.19.0**, existing `unshare` **2.41.3** and `ip` **6.19.0**. No installation or manager invocation. Vision **0.1.46** remains installed but excluded; no Python/runtime/cache activation. All retained home data and existing services remain protected.

Change only `integrations/deepseek/web_smoke.py`, its synthetic `tests/test_web_smoke.py`, and completion documentation. Runtime output stays in a new ignored 0700 `infra/harnesses/deepseek/state/web-smoke-*/`, restricted logs 0600. Preserve the failed fixture and all old backups; no cleanup.

## Approved correction (implemented)

1. Preserve namespace verification, clean fixture/environment, base+web-only bundles, readiness/time limits and owned-process cleanup. No fallback privileges or network.
2. Parse the newly created server's native announcement **in memory**. Accept only exact `http://127.0.0.1:13080/`, one nonempty `token` query parameter, no userinfo/fragment/extra parameters. Never emit the URL/token or use retained user credentials.
3. First request the clean root with no cookie and assert **401** as live evidence. Handle `HTTPError` explicitly: emit only safe status/stage labels, never exception URLs, bodies, cookies or headers. Unexpected responses fail promptly instead of becoming a readiness timeout.
4. Request the validated temporary launch URL with a proxy-disabled opener and in-memory cookie jar. Disable automatic redirects; require **303**, exact location `./`, and a cookie stored in memory. Then request the clean same-origin root with that cookie and require **200** plus the expected page marker; fetch only the validated same-origin local shell asset and require **200** plus React seed. Do not call API/RPC, create an agent session/job or use account authentication. This tests the server's standard local browser-cookie exchange, not DeepSeek account login.
5. Record only secret-free stage/status evidence, including failure stage. Add synthetic tests for malformed/off-origin announcements, non-following redirect behavior, HTTP status handling and token redaction; no network/vendor execution in these tests. Retain private full logs only under infra. Ensure the retained-home comparison also runs after namespace timeout; never print private manifests.

## Approved commands (executed; not a standing retry approval)

After implementing the scoped helper correction with `apply_patch`, run synthetic tests:

```sh
python3 -I -B -m unittest discover -s integrations/deepseek/tests -v
```

If those pass, refresh the same pinned source/process/disk/state/home/global/container baselines. Then execute **once**:

```sh
python3 -I -B integrations/deepseek/web_smoke.py --execute-approved \
  --node /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node \
  --cli-root /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/@deepseek-ai/dsh \
  --state-root /home/developer/workspace/mcp-stack/infra/harnesses/deepseek/state \
  --existing-home /home/developer/.dsh
```

Server environment remains only `PATH=/usr/bin:/bin`, `LANG=C.UTF-8`, fresh test `DSH_HOME`, `DSH_TELEMETRY_DISABLED=1`, `NODE_DISABLE_COMPILE_CACHE=1`. Port **13080** remains namespace-loopback-only, unreachable from host/macOS/browser and not published. No external route, provider key, account login, browser opener, model/MCP request, registration, database, n8n, Basic Memory or PKM action.

## Verification and recovery

Require isolated native readiness; live unauthenticated 401, temporary-token 303/cookie exchange, authenticated entry 200 and local asset 200; verify own-process shutdown. Compare full retained home/root mode, global versions/CLI entry/link and all 21 container snapshots. No browser rendering, vision activation, retained-profile compatibility or gateway integration pass is implied.

A failed check stops the owned process and retains private diagnostics. No automatic rerun or broadening. Original source remains recoverable from the explicit patch/history in this task; record its pre-edit hash and preserve a restricted project-state source copy before modifying. No live-data restore should be needed; never overwrite user credentials/sessions or touch other services. Source rollback would be a separately approved `apply_patch` restoration, not a global package rollback. Existing CLI/plugin backups remain available and untouched.

Approval covers this helper correction, synthetic tests and **one** bounded isolated live retry only. It does not approve starting the real retained profile or subsequent harness integrations.
