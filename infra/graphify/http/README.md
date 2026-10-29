# Restricted Graphify HTTP transport

Approved scope: one temporary direct-test service using the already-installed
Graphify 0.9.72 image / official SDK 1.29.0; not a persistent service or gateway/
harness registration. [Exact proposal/runbook](../../../docs/GRAPHIFY-HTTP-SETUP-PROPOSAL.md).

Completed 2026-10-01 after “Approve”: all direct checks passed, including missing/
wrong/duplicate auth, exactly seven useful tools, PR/foreign-project gate errors,
six scoped resources/invalid URI rejection, exact Host/Origin protection, fresh
initialize/reconnect and concurrent reads. Source/index hashes unchanged. The
temporary container was removed; internal network retained empty. All 19 prior
container snapshots/260 prior protected hashes and checked macOS configs match
baseline; the new hash config is the sole added protected-map entry (261 total).
Live gateway checks passed; no Basic Memory calls or gateway connection.

HTTP here is a local transport adapter around the existing restricted Graphify
server, not a hosted provider or separate graph engine. [Persistent backend
setup A](../../../docs/GRAPHIFY-GATEWAY-CONNECTION-PROPOSAL.md) was approved with
“Continue” and completed: `service.compose.yaml` runs `mcp-stack-graphify-http`
with `unless-stopped`, no host port, unchanged image/gate/index/key and seven
read-only mounts. All direct tests passed again; 19 prior container snapshots/
267 protected hashes and checked macOS configs unchanged. The gateway foundation
verifier passed; no Basic Memory call or gateway connection occurred in A.
[Connection B](../../../docs/GRAPHIFY-GATEWAY-B-PROPOSAL.md) is now separately
approved/completed: the gateway joins the internal network and serves seven
tools at macOS `/mcp/graphify`. Both direct connected and gateway checks passed;
the malformed unprefixed resource URI HTTP 500 is a documented routing limitation,
not an authorization pass. No harness registration or automatic memory use.

`serve_http.py` imports the existing seven-tool gate unchanged, adds explicit
resource guards, exact Host/Origin validation and a distinct backend Bearer key.
Only a SHA-256 key hash is mounted; plaintext stays in ignored
`.secrets/graphify-http-backend-key` (0600). `prepare.py` refuses overwrite;
retain generated ignored `infra/graphify/state/http/server.json` for approved
restarts rather than generating/rotating credentials implicitly.

Compose project/container: `mcp-stack-graphify-http-test`; internal network
`mcp-stack-graphify-transport`; no host port. Canonical HTTP path `/mcp/`,
authenticated health `/healthz`. Existing narrow index and three source files
are mounted read-only; no extraction, watcher, models, API calls or imports of
the projected test scripts. Query/automatic-refresh logging opt-outs retained.

Use existing macOS OrbStack Docker via `macctl`, targeting this overlay and the
macOS repository `--project-directory` explicitly. Never combine with root
Compose or remove orphans/volumes. Direct verifier does not auto-start services:

```sh
python3 infra/graphify/http/verify.py
```

For the now-running persistent service with its approved gateway connection:

```sh
python3 infra/graphify/http/verify.py --service --gateway-connected
```

The temporary-container default does not auto-start anything. Do not run a second
service or re-extract the graph. Persistent start/
stop commands and data-preserving rollback are in the A runbook; obtain approval
before further lifecycle actions. `external: true` in the persistent definition
reuses the verified internal network; it does not expose Graphify publicly.

The original temporary test is already removed; do not stop/remove the current
persistent service as test cleanup. Retain image, source, index, credentials and
occupied internal network. After approved B rollback restores the foundation,
use `--service` alone to require Graphify as the sole network member. Any future
lifecycle/network/config/harness change requires its own proposal/approval.
Basic Memory remains deferred.
