# CodeGraph temporary direct HTTP qualification

Latest: [session qualification correction/retry completed](../../../docs/CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md). Gateway now joins this backend's internal network, exposing only `codegraph_codegraph_explore` at `/mcp/codegraph`; no host backend port/harness registration. All gateway and connected direct tests, eight route-replay denials and the full 32-session capacity/cleanup suite passed. Backend, facade 1.0.1, index and keys stayed unchanged. Use `python3 -B infra/codegraph/http/verify.py --service --gateway-connected` for the current topology.

Earlier checkpoint: [bootstrap correction completed](../../../docs/CODEGRAPH-HTTP-BOOTSTRAP-CORRECTION.md), local facade **1.0.1**; supported initial preferences (or absent header) negotiate **2025-06-18**, with strict subsequent protocol validation. Only CodeGraph was recreated then; unchanged index/key/image/limits, source rollback copy retained. Gateway connection subsequently qualified above. The sections below retain the original temporary/persistent setup procedure and historical results, not current restart approval.

Authorized by “continue test” on 2026-10-01; **direct qualification passed and the temporary container was stopped/removed**. [Persistent backend A](../../../docs/CODEGRAPH-GATEWAY-CONNECTION-PROPOSAL.md) was subsequently approved with “approve”, started and fully directly tested. `mcp-stack-codegraph-http` stays running, internal-only with no published port and unchanged adapter/index/key. See [the direct-test runbook](../../../docs/CODEGRAPH-HTTP-SETUP-PROPOSAL.md) for pins, scope and limitations. Gateway connection B was later separately approved/qualified above; no harness registration.

No host/Ubuntu Node/mise/Docker install and no npm, SDK, FastMCP, model or image download. The adapter uses the existing CodeGraph 1.6.1 bundle's `MCPEngine`/`MCPSession` and Node built-ins. These are private upstream interfaces: upgrades need a new qualification, not a version bump alone. It owns the tools-only 2025-06-18 HTTP lifecycle; the upstream's stdio handshake remains 2024-11-05. GET `/mcp` returns 405; no SSE, resumability, sampling or roots requests are offered.

Read-only engine, no query worker pool, daemon, writer lock, watcher or catch-up sync. The existing SQLite directory and exactly three source files are bound read-only. Index scope/freshness limitations are in initialization instructions. All project selectors and unapproved tool/method calls are rejected before native dispatch. Upstream small-project discovery advertises only `codegraph_explore`; explicitly allowed `codegraph_status` is also callable. This is not automatic task-profile enforcement.

Endpoint: container-only `http://codegraph-http:8000/mcp`; internal `mcp-stack-codegraph-transport`; no published port. Separate ignored key `.secrets/codegraph-http-backend-key` (0600), hash-only `infra/codegraph/state/http/server.json`; no plaintext key in the container's mounts/environment/logs. All requests require a single correct Bearer key; unrelated Host and every browser Origin are rejected. 32 independent client sessions, ten-minute idle expiry, one active request per session, 64 KiB body, 30-second dispatch deadline, 2 MiB response cap. TTL expiry, timeout/fault paths and production interoperability are not established by the initial direct qualification.

From Ubuntu, exact test commands:

```sh
python3 infra/codegraph/http/prepare.py
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-codegraph-http-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/http/compose.yaml config --quiet
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-codegraph-http-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/http/compose.yaml up -d --no-deps --no-build --pull never codegraph-http
python3 infra/codegraph/http/verify.py
```

The preparer refuses existing credentials/state rather than rotating. Do not repeat it for a retry. A new service start needs approval; the direct verifier does not start anything. Do not run the old stdio verifier: it opens a writer and can reconcile the index.

## Persistent service operating mode

Use `compose.service.yaml` alone (not merged with the temporary definition), project `mcp-stack`, service `codegraph-http`; full commands and exact stop/remove rollback are in the [A runbook](../../../docs/CODEGRAPH-GATEWAY-CONNECTION-PROPOSAL.md). Direct verification of the already-running backend:

```sh
python3 infra/codegraph/http/verify.py --service --gateway-connected
```

Do not rerun the preparer or start/recreate anything just to verify. The temporary default verifier remains available for its separately approved container only. The internal network is retained from the test project, so the persistent Compose start warns about its ownership label; it is verified internal and now restricted to this backend plus gateway. Do not change it to external/recreate it or use Compose `down`/orphan cleanup automatically. `unless-stopped` is configured; host-restart recovery and Docker HEALTHCHECK are not tested/added.

After checking the exact test container's image/project/service labels, stop/remove only it:

```sh
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-codegraph-http-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/http/compose.yaml stop codegraph-http
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack-codegraph-http-test -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/http/compose.yaml rm -f codegraph-http
```

Source/config/key/existing index/image and the empty test network remain available. Removing them is separate approval; no `down`, `--remove-orphans`, volume deletion or broad prune. Never relax a read-only mount to make an opening/query failure pass.
