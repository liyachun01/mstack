# CodeGraph gateway connection B

[Session qualification correction/retry completed](../../../docs/CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md), approved with “continue” on 2026-10-01. **The combined config is live.** Real CodeGraph negotiation/explore/source/gates/concurrency, eight in-memory/cold cross-route replay denials, owned-session cleanup and all connected regression suites passed. CodeGraph's full direct 32-session capacity passed after cleanup. Facade 1.0.1, both backends/indexes/keys unchanged. Earlier failed attempts and rollbacks remain in the [history](../../../docs/CODEGRAPH-GATEWAY-B-RETRY-PROPOSAL.md).

Adds tools-only macOS `http://127.0.0.1:58080/mcp/codegraph` to the existing Graphify-connected gateway. Original client key required; separate existing CodeGraph backend key copied only to a protected ignored file. No plaintext token in template/config/env/argv. Original adapter/index/credentials and both backend containers remain unchanged. Basic Memory is deferred; no harness registration or automatic profile/tool use.

The combined gateway definition is **base `infra/agentgateway/compose.yaml` plus this directory's `compose.yaml` only**, never old and new integration overlays together or root/backend Compose definitions. Three exact RO file mounts and three networks: normal gateway bridge plus the two existing internal backend networks. Both backends remain internal-only, no published ports. The existing Graphify route is unchanged. CodeGraph permits only its discoverable explore tool through the gateway; native status is direct-backend-only. No all-tools combined endpoint is added.

```sh
python3 infra/agentgateway/verify.py
python3 infra/agentgateway/codegraph/verify.py
python3 infra/agentgateway/graphify/verify.py --codegraph-connected
python3 infra/codegraph/http/verify.py --service --gateway-connected
python3 infra/graphify/http/verify.py --service --gateway-connected --codegraph-connected
```

Verification starts nothing. Commands above target the current combined config. Do not rerun `prepare.py`. Actual `codegraph_codegraph_explore` naming/dispatch and CodeGraph DELETE 202/reuse 404 are verified. Stateless Graphify differs: authenticated same-route tools/list can resume a deleted encoded gateway token (200/seven tools); final Graphify cleanup DELETEs the owned entry without a recreating POST. Missing/wrong/backend keys and cross-route replay remain denied. Do not claim Graphify permanent token revocation or use session IDs as credentials. Known malformed unprefixed Graphify resource-URI HTTP 500 remains separate, never authorization success.

The `--graphify-session-diagnostic` option is specifically for an already-running **Graphify-only** gateway after an approved rollback, not the current combined topology; it starts nothing and verifies the exact old topology.

Current lifecycle recipe, **only after a new scoped lifecycle approval**:

```sh
MCP_STACK_HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/codegraph/compose.yaml" config --quiet
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/codegraph/compose.yaml" up -d --no-deps --no-build --pull never --force-recreate agentgateway
```

On failure B's approved rollback recreates only the gateway with **base + original Graphify overlay**, preserving the previously working Graphify route and leaving both backends/data running. Old default Graphify checks and `python3 infra/codegraph/http/verify.py --service` then apply. No backend-free foundation rollback, cleanup, broad `down` or orphan/volume deletion.
