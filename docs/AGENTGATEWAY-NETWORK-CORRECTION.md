# Agentgateway foundation network correction — completed

2026-10-01. The gateway-only installation was approved with “Do”; the network correction was subsequently approved with **“Continue!”**. **Correction completed; gateway running and foundation HTTP tests passed.** The original partial-installation findings below are retained as history, not current failure status.

## Completion report

- Changed only `infra/agentgateway/compose.yaml` network name/internal flag to the proposed `mcp-stack-gateway-local`, `internal: false`. Created that normal bridge and recreated only the gateway; no new image pull/package, secret rotation, database or second service.
- Running container `mcp-stack-agentgateway-1`, ID `dac540183d085d4b8db83b70afc4121f822f68a928fa44cd28247f8a6de799e2`, restart count 0 at inspection. Actual publication is `127.0.0.1:58080 -> 4000/tcp`.
- `python3 infra/agentgateway/verify.py` passed: authenticated health 200, authenticated MCP placeholder 503, other routes 404, missing/invalid-key rejection on all five routes. No admin/UI/config API exposed. These are HTTP foundation checks, not MCP discovery/call-filter/aggregation tests.
- Inspected non-root 65532:65532, read-only root/config, all capabilities dropped, no-new-privileges, 1 CPU/512 MiB/128 PIDs, `unless-stopped` and bounded Docker logs. Sole bind mount remains the rendered hash-only config. No real memory/backend/source/index/socket mounts.
- All 18 other existing containers' IDs/start/status/health/ports and all 260 protected file hashes remained identical. Checked macOS mise/Codex configuration hashes matched. Original gateway key/rendered config/template hashes matched: no credential/config regeneration.
- Normal network contains only the gateway. Old `mcp-stack-gateway` is empty/internal and retained deliberately; no cleanup/deletion. Network recreation removed only the superseded stopped gateway container; image/config/key are preserved and the new container is reproducible from Compose.
- Point-in-time idle sample: approximately 6.2 MiB RAM and 0.08% CPU, not a load-test/capacity guarantee. Docker reports the retained image as 39,070,952 bytes.
- Compose emitted the expected other-service orphan warning; no `--remove-orphans`, shared-network edits or changes to Basic Memory/PostgreSQL/{{mstack:CLIENT_REPO}} occurred.
- Rollback remains the targeted gateway stop below; files/key/image/networks remain available. Outbound connectivity is now permitted by the approved normal bridge, but no external backend/model calls are configured or tested.

Next: prepare a separate synthetic MCP aggregation/authorization proposal. Do not connect real memory servers or register a harness on the basis of this completed foundation.

## Historical partial-installation findings

- Official ARM64 image pulled at the approved index `sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896`; Docker reports 39,070,952 bytes. The temporary version container reports 1.5.0, release commit `fe6732474a96a0363dfb9822859af4e9bab360fa`, Rust 1.98.0 and `aarch64-unknown-linux-gnu`; it auto-removed.
- Config/template, Compose overlay and preparation/verification scripts are under `infra/agentgateway/`. Ignored key `.secrets/agentgateway-client-key` is 0600; ignored state directory is 0700 and mounted hash-only config is 0644. No key was printed, put in argv/environment, or rotated.
- The first startup failed with `routes.health must set gateways`. My proposed routes omitted explicit attachment to the named `foundation` gateway. Static schema validation accepted the omission, because the schema permits default gateway attachment, but the runtime had no gateway named `default`. All three routes now explicitly set `gateways: [foundation]`, in template and rendered config. No security setting changed.
- Corrected configuration started successfully; the stopped gateway's last exit is clean (0). Non-root 65532:65532, read-only root/config, capability drop, no-new-privileges and approved limits were verified by inspection. It has only the config-file bind, no memory/database/Docker socket mount.
- Actual `NetworkSettings.Ports` was `{"4000/tcp": null}` even though requested `HostConfig.PortBindings` specified loopback 58080. macOS `127.0.0.1:58080` refused connections. This engine did not realize the publication on the **internal** network. Merely being reachable on a private container IP is not the promised loopback endpoint.
- The verifier's absolute `/usr/bin/curl` and `/dev/null` arguments also exposed the known `macctl` absolute-path translation behavior (exec-format/output errors). The script now uses host PATH `curl` and stdout (`--output -`), parsing only the final HTTP status line without printing response bodies or credentials. It has not passed endpoint tests yet. A single no-key private-IP diagnostic returned HTTP 401 before the output-path failure; this is not proof that all authentication/route tests pass.
- The gateway was stopped to end the restart loop and then stopped again after the publication diagnostic. No extra test container remains. The network, image, key and config are retained; there was no material deletion.
- All **18 pre-existing containers** retained their IDs/start timestamps/status/health/ports. All **260 protected file hashes** matched (existing root/mise/harness config, Basic Memory state/notes and graph state). Checked macOS global mise and Codex configuration hashes also matched. No Basic Memory tests, shutdown, model work, migrations or {{mstack:CLIENT_REPO}} changes occurred. Baseline capture initially needed a safe missing-Health template lookup and a larger output allowance; those read-only retries changed nothing.

The installation proposal's configuration/network assumptions were my mistakes. No missing package or user approval caused these failures.

## Proposed correction

Keep the same image, key, routes, loopback publication, limits and mounts. Change **only the gateway's project-local network** to a normal user-defined bridge:

```diff
 networks:
   gateway:
-    name: mcp-stack-gateway
-    internal: true
+    name: mcp-stack-gateway-local
+    internal: false
```

Why a new name: avoid modifying/deleting the existing internal network or silently reusing a network with incompatible properties. Retain the old empty network as rollback material; no broad Docker cleanup.

Tradeoff: this restores normal published-port behavior but **permits outbound networking through Docker's normal bridge rules**. No outbound destinations, provider calls or MCP backends are configured. It is not an egress allowlist or firewall; the gateway may be able to reach host-published services, though this step will not contact them. The gateway still joins neither {{mstack:CLIENT_REPO}} nor the memory network, and inbound publication stays `127.0.0.1:58080`. Do not add global Docker/OrbStack firewall settings, proxies, extra relay containers, privileged access or a public bind.

If strict no-egress isolation is required, keep the current gateway stopped and design a separately approved ingress/egress solution instead; do not claim that a normal bridge preserves the original internal-network guarantee.

## Approved correction commands (executed)

Apply the two network-line changes above using `apply_patch`. Do not rerun `prepare.py`, which correctly refuses existing key/config. Recheck network ownership/absence and port availability first:

```sh
HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
macctl run docker ps -a --format '{{.ID}} {{.Names}} {{.State}} {{.Ports}}'
macctl run docker network ls --format '{{.Name}}'
macctl run lsof -nP -iTCP:58080 -sTCP:LISTEN
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" config --quiet
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" up -d --no-deps --pull never --force-recreate agentgateway
python3 infra/agentgateway/verify.py
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" ps agentgateway
```

This recreates only the stopped, project-owned `mcp-stack-agentgateway-1` and creates `mcp-stack-gateway-local`; no image pull, packages, secret rotation, database, additional service or harness registration. Ignore overlay orphan warnings; never use `--remove-orphans` or `down`.

## Verification and rollback

Require actual loopback publication and a running process, then run corrected verifier: authenticated health 200, authenticated `/mcp` 503, other routes 404; missing/invalid credentials rejected for all five routes. Inspect the new container's network, image, security settings and sole config mount; compare existing containers and protected file hashes again. Do not claim MCP aggregation/filter enforcement is tested by these HTTP checks. If any check fails, stop only this gateway and report; never relax authentication or broaden the bind to get a pass.

Data-preserving rollback:

```sh
HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
macctl run docker compose -p mcp-stack --project-directory "$HOST_REPO" -f "$HOST_REPO/infra/agentgateway/compose.yaml" stop agentgateway
```

Retain credentials, config, image and both project networks. To restore the former **stopped** definition, reverse the network diff using `apply_patch` after stopping; do not restart the known-unpublished internal-network setup as a workaround. Cleanup/removal or a different network design requires a separate proposal.

Approval received and executed: the normal-bridge correction, gateway-only recreation/start and unchanged-scope foundation checks. Outbound connectivity was the explicit added permission. Synthetic MCP tests and any real server/harness setup still require separate approval.

Sources: [agentgateway route attachment](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/routes/), [Docker bridge networking and published ports](https://docs.docker.com/engine/network/drivers/bridge/). The internal-network publication failure above is our observed runtime result, not a universal claim that every internal network implementation behaves identically.
