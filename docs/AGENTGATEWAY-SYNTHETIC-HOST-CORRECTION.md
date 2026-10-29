# Synthetic fixture Host correction and bounded retry

Status: **approved with “continue” and completed on 2026-10-01**. Exact fixture Host correction applied; direct fixture checks and all eight gateway checks passed; both temporary containers removed. Historical proposal/evidence below retained. No official binary patch or custom gateway build was needed for this fixture mismatch.

## Completion report

- Applied only the approved explicit `fixture` Host addition in `infra/agentgateway/synthetic/fixture.py`; kept DNS protection enabled and origins restricted. Added direct positive Host test to `verify.py`; both alpha/beta accepted the intended internal Host and continued rejecting unrelated Hosts (421) and Origins (403). Direct initialization/discovery/tool/prompt/resource/counter/outage/recovery checks passed.
- Recreated only the disposable fixture and isolated gateway using the same exact existing images below, no pulls/builds/host installs. Inspected non-root/read-only/mount/network/resource/loopback restrictions. Gateway binary still official 1.5.0, commit `fe6732474a96a0363dfb9822859af4e9bab360fa`, Rust 1.98.0, release aarch64-unknown-linux-gnu. Reported each setup separately. No Compose/template/generated-config/client-key/auth-rule/mount/port change or live gateway restart.
- Gateway matrix passed twice; final run strengthened the existing two-session check with two actual concurrent stdlib-threaded calls and exact target counter deltas. This changed verifier logic only, not runtime security/configuration. Negotiated protocol 2025-11-25. See detailed outcomes below.
- Scoped ownership checks preceded cleanup; stopped/removed only `mcp-stack-gateway-synthetic` and `mcp-stack-gateway-fixture`. RAM-only sessions/counters discarded, no durable data removed. Port 58081 unused; dedicated synthetic network retained empty, source/config retained for reproduction. No cleanup failures.
- Fresh pre/post snapshots: all **19 existing containers** identical in recorded identity/start/status/health/ports; all **260 protected file hashes** identical; checked macOS global mise/Codex config hashes identical. Foundation HTTP authentication/routes passed again at 58080. Basic Memory, PostgreSQL, notes/graph indexes, root Compose/mise, existing key/config and already-stopped {{mstack:CLIENT_REPO}}/backend resources untouched; no Basic Memory calls, providers/models or global harness registration.

| Gateway check | Observed result |
| --- | --- |
| API-key authentication | Missing/wrong keys rejected on all four profiles; no handler dispatch |
| Aggregation and collisions | Exactly alpha_echo/beta_echo; allowed calls reached intended target only |
| Hidden tools/prompts/resources | Discovery filtered; correctly prefixed direct calls rejected HTTP 400 with unchanged dispatch counters |
| Alpha-only profile | Only alpha_echo advertised/callable; beta_echo rejected HTTP 400 without dispatch |
| Explicit deny-all | Empty discovery, valid tool/prompt/resource calls rejected HTTP 400 without dispatch |
| Missing-claim policy | Valid configuration/initialize, empty tools; direct echo rejected HTTP 400 without dispatch |
| Sessions | Different active sessions and concurrent calls worked; cross-route session replay rejected (404), unknown session rejected, no unauthorized dispatch |
| Backend outage/recovery | Beta outage made existing discovery and fresh initialize return 503, not partial inventory; restored beta, fresh discovery/both calls passed |

Limits: synthetic qualification only, not real-server integration, exhaustive protocol security, production/load certification, tenant separation or automatic profile selection. Live foundation `/mcp` still intentionally returns 503 because no real MCP server is connected. Basic Memory integration remains deferred. No further installation/lifecycle step is authorized by these results.

Next proposed phase: prepare an exact Graphify HTTP transport/direct-test proposal reusing its restricted seven-tool adapter and existing read-only scoped index. Obtain approval before service setup, then separately qualify gateway connection. CodeGraph transport/single-writer design follows independently; no corpus expansion/watcher/harness registration implied.

## Evidence and scope

The approved temporary gateway was official agentgateway 1.5.0 at commit `fe6732474a96a0363dfb9822859af4e9bab360fa`, with the exact existing ARM64 image and strict API key. All four MCP profiles rejected missing/invalid credentials. Every subsequent authenticated initialization returned HTTP 421, so aggregation and gateway authorization/session/outage qualification remain **failed/blocked**, not verified.

The fixture logs explicitly recorded `Invalid Host header: fixture`. Its SDK allowlist was the proposal's `fixture:8000`, `127.0.0.1:8000`, `localhost:8000`; the gateway's actual internal request used the same service hostname without the port. Direct loopback probes passed because their Host was `127.0.0.1:8000`. Changing the client-facing Host between localhost/127.0.0.1 and ports did not fix it; this is fixture-side transport validation, not a demonstrated failure of the gateway's client-facing DNS protection or CEL policies.

Both temporary containers were stopped/removed after the failed run. Live gateway/key/config, real memory/database/graph state, global config and {{mstack:CLIENT_REPO}} were untouched. The empty synthetic network and files remain available for a reproducible retry.

The SDK checks exact Host strings when DNS protection is enabled; adding only the already-scoped Docker service hostname is sufficient to address the observed mismatch without wildcard hosts, external origins or disabling protection. [Pinned SDK transport security](https://github.com/modelcontextprotocol/python-sdk/blob/v1.29.0/src/mcp/server/transport_security.py). The gateway's independent localhost-only Host/Origin validation remains enabled. [Pinned gateway DNS validation](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/dns_rebinding.rs).

## Exact proposed change

Modify only `infra/agentgateway/synthetic/fixture.py`'s internal transport allowlist:

```diff
-            allowed_hosts=["fixture:8000", "127.0.0.1:8000", "localhost:8000"],
+            allowed_hosts=["fixture", "fixture:8000", "127.0.0.1:8000", "localhost:8000"],
```

Update `infra/agentgateway/synthetic/verify.py` to directly verify a request with `Host: fixture` succeeds, while its existing unrelated Host and Origin probes still reject. No template/generated-config/key/Compose/image/mount/resource change. Record the amendment/results in proposal/status/README/TODO. Apply via `apply_patch` only after confirmation.

## Runtime proposal

Execution domain: the existing macOS OrbStack Docker engine, invoked from Ubuntu through `macctl`; existing Ubuntu Python for the verifier. No mise, host package, image pull/build or new dependency. No Basic Memory call, real source/notes access, model/provider, harness or n8n registration.

Use the same already-present artifacts:

- Fixture runtime: local exact image ID `sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac`; Python 3.12.14 / SDK 1.29.0 / Starlette 1.3.1 / uvicorn 0.47.0. Graphify is not imported/launched.
- Gateway: official `ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896`, version 1.5.0, Linux ARM64.

Recheck exact image IDs, absence of both container names, empty network, free port 58081, live-key/config and protected-file hashes before startup. Do not rerun `prepare.py`: retain the hash-only config prepared in A. If the approved config/image is missing or changed, stop rather than regenerate/download silently.

Project `mcp-stack-gateway-test`; services `fixture` / `test-gateway`; containers `mcp-stack-gateway-fixture` / `mcp-stack-gateway-synthetic`; normal bridge `mcp-stack-gateway-synthetic` (outbound possible, no external calls configured). Only gateway loopback `127.0.0.1:58081 → 4000` is published. Fixture port 8000 is unpublished. Both non-root, read-only, no-new-privileges/cap-drop, 128 PIDs, 16 MiB tmpfs, restart `no`; fixture 1 CPU/256 MiB with only script mount, gateway 1 CPU/512 MiB with only hash config mount. Existing environment `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1` only on fixture. No new credentials; existing `.secrets/agentgateway-client-key` stays 0600 and off argv/env/output.

```sh
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml config --quiet
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml up -d --no-build --pull never fixture
python3 infra/agentgateway/synthetic/verify.py --fixture-only
```

Report the corrected fixture setup/direct-test result. Only on success start the already-approved test gateway for this bounded retry:

```sh
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml up -d --no-build --pull never --no-deps test-gateway
python3 infra/agentgateway/synthetic/verify.py
```

Verify exact binary version using container-relative `./app/agentgateway --version`, avoiding macctl's absolute-argument translation. Report each startup. Run the original eight-check gateway matrix, record actual errors/counter deltas, never count transport failures as authorization passes; restore beta/reset counters in `finally`. The existing verifier has 180-second overall/30-second probe/10-second request limits and only synthetic-container controls. If a further security/config/transport amendment is needed, report and stop before making it.

Always resolve ownership, then clean up success or failure:

```sh
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml stop test-gateway fixture
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-gateway-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/synthetic/compose.yaml rm -f test-gateway fixture
python3 infra/agentgateway/verify.py
```

Rollback is these same targeted stop/remove commands; if only fixture started, target only fixture. No `down`, orphans/pruning, networks/volumes/images/key deletion or real-service lifecycle calls. Retain the empty dedicated network, source and ignored hash config. Discarded RAM-only counters/sessions are disposable; recreate from fixture if needed. To reverse the source amendment after cleanup, remove only the explicit `fixture` allowlist item/direct positive test via `apply_patch`; no durable data changes.

Compare fresh pre/post container identity/start/status/health/ports and protected hashes, plus checked macOS config. Report deviations and cleanup; stop before real memory-server integration. Live foundation on 58080 remains unchanged throughout.

## Original approval request (now completed)

Approve adding only exact internal Host `fixture` to the disposable fixture allowlist, verifying it directly, and rerunning the already-reviewed isolated gateway tests/cleanup with the same existing images and settings. This is not approval to relax gateway authentication, disable DNS protection or connect real memories.
