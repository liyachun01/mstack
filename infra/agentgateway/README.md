# Agentgateway — foundation and two graph endpoints

**Current override, 2026-10-08:** the old graph runtime was absent at discovery.
The same pinned gateway is now restored in `mcp-stack` with authenticated project
routes and blank service connections. Use [project connections](projects/README.md)
and [HANDOVER](../../docs/HANDOVER.md). The rest of this file records historical
graph qualification; its live-endpoint claims/start recipe are not current.

Official v1.5.0 ARM64, pinned by image digest in `compose.yaml`. Gateway-only foundation and network correction approved/completed on 2026-10-01. Existing OrbStack Docker engine on macOS; no new host CLIs or Ubuntu mise.

## Current scope

- macOS `http://127.0.0.1:58080`, mandatory bearer API key.
- Authenticated `/healthz`: 200; bare `/mcp`: 503; `/mcp/graphify`: seven real Graphify query tools; `/mcp/codegraph`: one real `codegraph_codegraph_explore` tool; other paths: 404.
- [Graphify connection B](graphify/README.md) and [CodeGraph B session qualification](codegraph/README.md) are separately approved/completed. No admin/UI/metrics/readiness listener, gateway database, model provider, Basic Memory backend, harness or automatic task-profile integration.
- Dedicated `mcp-stack-gateway-local` normal bridge allows outbound connectivity. It contains only the gateway, not Basic Memory/PostgreSQL/{{mstack:CLIENT_REPO}}. It is not an egress firewall.
- Gateway also joins the separate internal `mcp-stack-graphify-transport` and `mcp-stack-codegraph-transport` networks. Each contains only its backend and gateway; neither backend has a host port. No database/{{mstack:CLIENT_REPO}}/other server shares them.
- Non-root/read-only runtime, bounded resources and logs; three read-only mounts (combined config/two backend-key copies), no sources/indexes/notes/Docker socket. Supplementary container group 501 permits reading the protected backend-key copies, not host home access. Logs live in OrbStack engine storage, capped at two 5 MB files.
- Root Compose does not include this optional overlay. Never use `down` or `--remove-orphans` when operating it alone; those could affect other project services.

## Configuration and secrets

`config.template.json` is versionable and contains a placeholder, not a live key/hash. Ignored `state/config.json` contains the generated high-entropy key's hash. Plaintext client key is only in ignored repository `.secrets/agentgateway-client-key`, mode 0600. Do not print it, pass it in argv or add it to global harness config.

`prepare.py` refuses existing key/config: **do not rerun it as an update command**. Scope any future key rotation/config change separately. State directory is 0700, rendered file 0644 for the non-root single-file bind mount. Existing key/config were preserved through gateway recreation; no database/volume is involved. Named Docker volumes are not backups; separately approved secure backup/restore remains future work.

The live gateway mounts ignored `state/codegraph/config.json` (client hash and
backend file references only), `state/graphify/backend.key` and
`state/codegraph/backend.key` (macOS 501:501 / 0640), within state 0700. Original
foundation/Graphify-only configs and all three 0600 original keys stay intact.
See the [combined operating notes](codegraph/README.md); preparers refuse
overwrite. Do not embed plaintext credentials into templates.

## Verification

From Ubuntu `/home/developer/workspace/mcp-stack`:

```sh
python3 infra/agentgateway/verify.py
python3 infra/agentgateway/codegraph/verify.py
python3 infra/agentgateway/graphify/verify.py --codegraph-connected
python3 infra/codegraph/http/verify.py --service --gateway-connected
python3 infra/graphify/http/verify.py --service --gateway-connected --codegraph-connected
```

Uses existing macOS `curl` through `macctl` with authentication supplied on stdin. Absolute executable/output paths are intentionally avoided because `macctl` can translate them to Ubuntu paths. The foundation check contacts only HTTP routes; graph suites call only the scoped read-only graphs, never Basic Memory/models or index writers.

## Lifecycle — obtain the required approval before execution

Use the explicit macOS repository path, existing Docker/Compose and targeted service commands. No image pull is implicit (`pull_policy: never`).

Current operation uses the base Compose file **plus**
`infra/agentgateway/codegraph/compose.yaml` **only**, as documented in the combined B runbook. Never merge both integration overlays.
The following base-only start restores the foundation without Graphify; it is
not the current configured start recipe. Obtain approval before any lifecycle
action, including rollback or restart. To preserve both endpoints, use the
base + CodeGraph overlay targeted command in [the combined runbook](codegraph/README.md).

```sh
HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" ps agentgateway
# Targeted, data-preserving rollback after target/approval checks:
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" stop agentgateway
# Foundation-only start/rollback, not the current Graphify-connected recipe:
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" up -d --no-deps --pull never agentgateway
```

Old empty/internal `mcp-stack-gateway` is intentionally retained as rollback material. Do not clean it or other networks/images/volumes without a scoped removal proposal. Current container is `mcp-stack-agentgateway-1`, restart policy `unless-stopped`; gateway process running does not mean Docker HEALTHCHECK or MCP functionality is verified.

## Next approval boundary

Current: [session qualification correction/retry](../../docs/CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md) approved/completed; both graph endpoints are live. Strict CodeGraph DELETE/reuse 404 and native capacity passed. Stateless Graphify can resume a deleted encoded token on the same route with valid authentication; its final owned-entry DELETE is not permanent revocation. Eight in-memory/cold cross-route replay cases returned 404; missing/wrong/backend keys rejected. Do not use session IDs as API credentials or infer exhaustive tenant isolation. Earlier failed B retries remain historical.

Synthetic qualification, both persistent graph backends and their gateway connections are completed. Malformed unprefixed Graphify resource URI maps to HTTP 500 before dispatch, a known limitation, not authorization success. Next: select a harness for a separately scoped project-local integration proposal. Corpus expansion, Basic Memory integration, harness registration, n8n, PKM, backups/restores and models remain unimplemented. Basic Memory stays deferred; no later component is approved by this qualification.

See [foundation history](../../docs/AGENTGATEWAY-FOUNDATION-PROPOSAL.md), [correction/completion report](../../docs/AGENTGATEWAY-NETWORK-CORRECTION.md), [staged plan](../../docs/AGENTGATEWAY-SETUP-PROPOSAL.md) and the [setup guard](../../.agents/skills/mcp-stack-setup-guard/SKILL.md).
