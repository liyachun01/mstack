# CodeGraph persistent backend A — completed

Current follow-up: [adapter bootstrap correction](CODEGRAPH-HTTP-BOOTSTRAP-CORRECTION.md) is approved/completed, facade 1.0.1; full direct and Graphify/gateway regressions passed after recreating only CodeGraph. Original gateway B failed/rolled back; [B retry](CODEGRAPH-GATEWAY-B-RETRY-PROPOSAL.md) needs separate approval. A remains running/internal-only; the completion report below records its original setup checkpoint.

**Approved with “approve” and completed on 2026-10-01.** The [temporary direct HTTP test](CODEGRAPH-HTTP-SETUP-PROPOSAL.md) is completed and its container removed. This step covers only retaining that qualified backend as an internal long-running service. [Gateway connection B](CODEGRAPH-GATEWAY-B-PROPOSAL.md) is a later, separate approval; no gateway configuration, gateway network membership, client credential or harness registration changed here.

## Completion report

- Created `infra/codegraph/http/compose.service.yaml` with exactly the three approved name/container/restart changes and added explicit `--service` verification. The adapter, preparer, original test Compose, original key/hash config and three-file source/index projection are unchanged. Exact definition comparison, Python syntax and Compose validation passed.
- Running `mcp-stack-codegraph-http` on the existing macOS OrbStack engine: CodeGraph 1.6.1/bundled Node 24.16.0, exact existing ARM64 image, UID/GID 501, read-only root/seven binds, no published port, `unless-stopped`, 2 CPU/2 GiB/PID/tmpfs/privilege/log limits unchanged. Only its internal network is attached, with one container member. No image/build/package/SDK/model/host/global/mise installation.
- All complete direct checks passed: runtime/index readiness, retained exact 3-file/47-node/98-edge graph and call edges; authentication/HTTP input/Host/Origin gates; fixed-root initialization/tool discovery; direct excluded tool/project/resource/prompt/root-method denials; useful fixture/native source/status; actual concurrent fresh sessions/reconnect/delete isolation; session-capacity bound/cleanup; unchanged source/index/WAL/SHM bytes and distinct credentials. Process inspection showed only init and bundled Node, no writer/daemon/watcher subprocess.
- Gateway foundation, Graphify gateway and connected Graphify direct regression checks all passed. Their original seven-tool route and recorded malformed unprefixed URI HTTP 500 limitation remain unchanged. No Basic Memory call/test, database migration or {{mstack:CLIENT_REPO_TITLE}} action occurred.
- All **20 pre-existing container snapshots, 268 protected hashes and 10 additional protected key/adapter/Compose/gateway files** match the fresh baseline. Exactly one new running container is added (21 total). Fresh macOS mise/Codex hashes match; checked Ubuntu configs remain in the unchanged protected set. This does not rewrite the preceding test's historical missing fresh macOS baseline.
- Compose reused the retained empty test network and warned about its earlier test-project ownership label; actual network remains internal, with only the new backend attached. The approved declaration stays unchanged (`internal: true`); no fourth network-definition edit, recreation or security relaxation was introduced. The other four stack services were reported as overlay “orphans”; no removal/cleanup occurred.
- Two diagnostic preflight commands needed corrections: the existing Graphify persistent Compose filename is `service.compose.yaml`, not `compose.service.yaml`; a string comparison accidentally also replaced the container-name substring. Corrected both checks before starting any container; the approved service definition itself was already correct and no protected data changed.
- Backend is left running; data-preserving rollback below remains available. No cleanup needed. `unless-stopped` is configured, not an exercised host-restart recovery test; no Docker HEALTHCHECK or production stability claim.

Next: [exact gateway connection B proposal](CODEGRAPH-GATEWAY-B-PROPOSAL.md), not yet approved/executed. No automatic memory usage, gateway registration or harness setup follows from A.

## Original approved scope (executed)

Execution: existing macOS OrbStack Docker engine through Ubuntu `macctl run`, no host toolchain/mise change. Reuse exact installed CodeGraph 1.6.1 image `sha256:4b8cb16b0c3b5bb7446c3f90b8fd2b12f099b0d0029f8bf30113ad482bf75420` and bundled Node 24.16.0. No image/package/model download/build, framework installation or Basic Memory testing.

After approval create `infra/codegraph/http/compose.service.yaml` by copying the qualified test definition with only three runtime identity/lifecycle changes: Compose project `mcp-stack`, container `mcp-stack-codegraph-http`, restart `unless-stopped`. Retain service `codegraph-http`, exact image, entrypoint/command, all seven read-only binds, original hash config/key, environment, CPU/RAM/PID/tmpfs/log limits and internal-only `mcp-stack-codegraph-transport` network. The root Compose stays unchanged. No published port, gateway attach, broader source projection, writer/index sync/watch, external API or database migration.

Add an explicit `--service` mode to `infra/codegraph/http/verify.py`, checking the new name/project/restart and otherwise running the same complete direct suite with only that backend on its network. Update its infra README and repository runbook/status/TODO/README after results. Do not edit the qualified adapter, preparer, existing source/index/scripts/project config, original test Compose or any global/harness config. If a material runtime/security/version/mount change is needed, stop and request a revised proposal.

Current ignored credential/config retained: `.secrets/codegraph-http-backend-key` 0600 and `infra/codegraph/state/http/server.json` hash-only 0644 inside 0700. Do not rerun prepare/rotate/copy plaintext keys. Cache/temp writes remain container RAM only. Read-only engine/shared index and independent per-client native sessions unchanged.

## Commands after approval

First capture fresh existing-container/protected-file and both machines' relevant config hashes, validate expected image/key/state and absence of the exact service name. Then:

```sh
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/http/compose.service.yaml config --quiet
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/http/compose.service.yaml up -d --no-deps --no-build --pull never codegraph-http
python3 infra/codegraph/http/verify.py --service
python3 infra/agentgateway/verify.py
python3 infra/agentgateway/graphify/verify.py
python3 infra/graphify/http/verify.py --service --gateway-connected
```

`--service` is now implemented and tested. Warnings about other mcp-stack services being “orphans” are expected; never use `--remove-orphans`. Snapshot comparison preserves all existing resources, including already-stopped {{mstack:CLIENT_REPO_TITLE}} services. A passed and this one new container is left running. This does not exercise a real host restart or add a Docker HEALTHCHECK.

## Data-preserving rollback

After resolving and checking exact name/image/project/service labels, stop/remove only the new backend on failure or a separately requested rollback:

```sh
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/http/compose.service.yaml stop codegraph-http
macctl run docker compose --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -p mcp-stack -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/http/compose.service.yaml rm -f codegraph-http
```

Retain image/source/original index/backend credential/hash config and empty internal network. Do not prune, remove volumes or stop/recreate any existing service. After A, propose B's exact live-gateway route/auth/network/key-mount/session/failure policy separately; B will briefly recreate only the gateway if approved, not implicitly follow from A.
