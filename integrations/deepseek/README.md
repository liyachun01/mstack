# DeepSeek integration qualification

Reusable source/tests live here; runtime profiles, tokens, logs and caches belong under `infra/harnesses/deepseek/`. These scripts are not installed harness MCP registrations or normal session launchers. Follow the project setup guard.

The separately authorized 2026-10-15 Ubuntu toolchain migration selects existing
mise Node **24.19.0** and official `@deepseek-ai/dsh` **0.2.0-rc.2** through
`infra/harnesses/deepseek/mise.toml`. The normal project launcher lives at
`integrations/agents/deepseek_launch.py`; it resolves installed exact tools and
checks metadata without automatically downloading. This change does not start
the harness, reconnect MCP, read credentials for the checks below or change the
retained profile. Dated qualification results further below remain historical.

The native composition checker canonicalizes the symlinked mise/Aube CLI root
before dependency resolution. It passes against the new tree's
`@deepseek-ai/dsh-mcp-client` **0.2.0-rc.2**, including its pinned source hash and
two synthetic SDK regressions. No legacy tree is needed for this check. The
retained Web profile still resolves dependencies through unchanged
`~/.dsh/profiles/node_modules` links into the fnm tree; its independent vision
**0.1.46** dependency is preserved. Keep that old store after live processes
drain as well. Retained-profile startup with the new top-level harness remains
untested; this migration does not rewire profile dependencies or imply a normal
profile launch.

- `inspect_frontend.py`: reads pinned package manifests/browser assets without importing/evaluating vendor JavaScript. Verifies the browser shell's React seed and the vision client's native factory imports. Its result is **static**, not a browser/render/vision-runtime test.
- `web_smoke.py`: **separately approval-gated**, credential-free temporary Web foundation test. Requires existing Ubuntu `unshare`/`ip`, creates a private fresh user/network namespace with loopback only, uses a new restricted `DSH_HOME` and base+web bundles (no vision), drops inherited credentials, disables telemetry, makes no model/MCP calls, and reaps its owned server. Validates the temporary launch URL, denies automatic redirects and tests unauthenticated 401 → temporary-token 303/cookie → authenticated page/asset 200. Cookie/token stay in memory and restricted/ignored logs; evidence contains only safe statuses/booleans. No fallback if isolation fails. This is not a filesystem sandbox; no agent job is submitted. Existing home hashes stay in memory and are compared without emitting secrets, including after namespace timeout.
- `tests/`: synthetic/static/helper tests; no dsh, namespace or browser startup. `test_mcp_overlay.py` parses YAML with inert JS tags using existing PyYAML 6.0.3. `check_native_overlay.mjs` uses the installed official parser/patch composer/MCP schema and a dummy credential, without evaluating the key expression, reading private overrides, importing vision or connecting.
- `gateway_forwarder.mjs`: separately approved, built-ins-only TCP adapter; exact Ubuntu loopback listener and pinned OrbStack-host address. No credential read, payload inspection, HTTP rewriting, MCP request, package install or restart manager. Runtime config is `infra/harnesses/deepseek/gateway-forwarder.json`. Importing the module in tests does not run its CLI/start a listener. `tests/test_gateway_forwarder.mjs` has **10** synthetic/stubbed tests; no live sockets/listeners/network/secret reads.

Tests (not service startup):

```sh
python3 -I -B -m unittest discover -s integrations/deepseek/tests -v
NODE_DISABLE_COMPILE_CACHE=1 /home/developer/.local/share/mise/installs/node/24.19.0/bin/node \
  --test --test-isolation=none integrations/deepseek/tests/test_gateway_forwarder.mjs
NODE_DISABLE_COMPILE_CACHE=1 /home/developer/.local/share/mise/installs/node/24.19.0/bin/node \
  integrations/deepseek/tests/check_native_overlay.mjs \
  /home/developer/.local/share/mise/installs/npm-deepseek-ai-dsh/0.2.0-rc.2/node_modules/@deepseek-ai/dsh
```

See [static findings and first attempt](../../docs/DEEPSEEK-WEB-SMOKE-PROPOSAL.md) and [approved authentication correction/retry completion](../../docs/DEEPSEEK-WEB-AUTH-CORRECTION.md). **16** synthetic/helper tests and one isolated live foundation retry passed on 2026-10-02; server stopped, retained home/global identities/all 21 containers unchanged. This does not qualify browser rendering, vision/Python activation, normal retained-profile startup or MCP integration. Every further live run still needs its own explicit approval. Existing home/config preservation remains the normal-launch requirement; the temporary home is exclusively a test fixture, not a configuration migration.

Subsequent native MCP preparation and Host correction: **23** Python tests/native composition/schema/syntax checks pass. Actual opt-in YAML belongs in [infra/harnesses/deepseek](../../infra/harnesses/deepseek/README.md). Retained-home Web is online with vision disabled, but initial activation and [Host correction](../../docs/DEEPSEEK-MCP-HOST-CORRECTION.md) failed with HTTP 403. Pinned Node fetch deletes Host; Python HEAD did not qualify that implementation. The [approved forwarder](../../docs/DEEPSEEK-LOOPBACK-FORWARDER-PROPOSAL.md) is now running and qualified through pinned Node native fetch: valid bearer HEAD 405, missing/wrong bearer 401 on both routes, no MCP method submitted. Ten forwarder tests pass, protected home/key/global packages/configs/all 21 containers/Web identity unchanged. Current MCP YAML remains failing/unchanged; [new native URL/registration proposal](../../docs/DEEPSEEK-LOOPBACK-MCP-ACTIVATION-PROPOSAL.md) is separately pending. Do not auto-reload/retry or monkey-patch the official SDK.
