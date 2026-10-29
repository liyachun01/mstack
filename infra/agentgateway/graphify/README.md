# Graphify gateway connection

Approved with “Approve” and completed 2026-10-01. Uses existing agentgateway 1.5.0
and running Graphify 0.9.72; no image/toolchain/model installation. [Exact setup,
results, limitation and rollback](../../../docs/GRAPHIFY-GATEWAY-B-PROPOSAL.md).

macOS endpoint: `http://127.0.0.1:58080/mcp/graphify`, mandatory existing gateway
client Bearer key. Backend uses its distinct existing token via a protected
ignored file copy, not client passthrough. Never print either key or register
globally. The macOS loopback URL is not assumed reachable from Ubuntu loopback;
these verifiers use existing macOS curl through `macctl` with credentials on stdin.
Harness/Ubuntu client networking will be proposed separately.

Only seven `graphify_`-prefixed tools are exposed. PR tools, foreign-project
arguments, valid resource reads and prompt calls are denied. Resource discovery
is empty; optional prompt/template discovery reports unsupported `-32601`.
Malformed unprefixed resource URI returns HTTP 500 **before backend dispatch**,
a documented error-reporting limitation, not an authorization pass. No task
classification, automatic memory use, full repository indexing or harness
registration is implemented.

Versionable files: `config.template.json`, `compose.yaml`, `prepare.py`, `verify.py`.
Ignored runtime files: `infra/agentgateway/state/graphify/config.json` (0644,
hash-only) and `backend.key` (macOS 501:501, 0640); state directory 0700. Original
keys remain 0600. Gateway UID/GID 65532:65532 has supplementary container group 501
and originally two read-only file mounts; the now-live combined CodeGraph overlay uses three. No host group/config changes. `prepare.py`
refuses existing state and is not an update/restart command.

Checks (do not auto-start or modify services):

```sh
python3 infra/agentgateway/verify.py
python3 infra/agentgateway/graphify/verify.py --codegraph-connected
python3 infra/graphify/http/verify.py --service --gateway-connected --codegraph-connected
```

Current gateway definition is the base `infra/agentgateway/compose.yaml` **plus**
`infra/agentgateway/codegraph/compose.yaml` **only**, not both integration overlays.
The [combined qualification](../../../docs/CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md) passed with Graphify's route unchanged. Use explicit macOS repository `--project-directory` and project `mcp-stack`. Root Compose stays unchanged. This directory's overlay restores Graphify-only operation; base-only restores the backend-free foundation. Neither is the current start recipe.
All lifecycle/config/upgrade/removal actions still require setup-guard approval.
Never use `down`, `--remove-orphans`, prune or volume deletion. Rollback preserves
Graphify/data/keys; backend lifecycle is separate. Stateless Graphify's deleted
gateway token can resume on the same route with valid client authentication;
DELETE is not permanent token revocation. Missing/wrong/backend credentials and
both in-memory/cold cross-route replay are verified denied. No stateful adapter
or revocation database was added.
