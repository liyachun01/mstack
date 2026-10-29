# Bounded Windmill trial — deployed 2026-10-05

> Retired2026-10-05: the Windmill trial containers, all three volumes, network
> and runtime credentials were deleted after successful shared-PG replacement.
> This is historical evidence; trial lifecycle commands no longer apply.
> Use [the current Windmill runbook](WINDMILL-RUNBOOK.md).

Prepared 2026-10-05 at the user's request; exact deployment approved with “go”.
This reopens **Windmill evaluation only**, not other deferred integrations.
The approved image, credentials, isolated database/server/worker are now installed.
Original `infra/windmill/docker-compose.yml`, `Caddyfile` and `.env` are untouched.
See [the trial runbook](WINDMILL-TRIAL-RUNBOOK.md) for access and lifecycle commands.

## Deployment result

- macOS OrbStack only; official API reports **CE v1.823.1**, PG reports **18.6**.
- Three new processes running, zero restarts; PG/server healthy; UI and version
  endpoint HTTP200. Worker job execution and owner login were not performed.
- All **22 pre-existing containers** retain their IDs, images, state/start times,
  restart counts, ports, networks and complete mount records.
- Verification deviation: initial comparison stopped on reordered Docker mount
  arrays, not changed mounts. Canonical comparison plus a regression test fixes
  this false positive. Fresh read-only verification passed; installer not rerun.
- **14 offline tests pass**. New password/env files0600; state directory0700.
- Private evidence: `infra/windmill/state/install-li4tytgf/qualification.json`.
- Approved trusted-code-only restriction remains; no integrations or model calls.

## Concrete install scope

- Execution domain: **existing macOS OrbStack Docker**, context/engine `orbstack`,
  ARM64, invoked from Ubuntu through existing `macctl run`. No Ubuntu Docker,
  mise, npm/pnpm, CLI, browser tooling or host runtime installation.
- One isolated trial project **mcp-stack-windmill-trial**: new `db`, `server`
  and **one** `worker` container, using only `infra/windmill/compose.trial.yaml`.
  Do not merge the downloaded Compose file or root Compose entry point.
- Official stable Windmill **1.823.1**, released 2026-10-05T06:25:16Z;
  source commit `4096c3da74138e3476c2cd9996cbb455aaf8e926`. Same standard official
  image for server/worker; no source builds, patches or third-party fork.
- Official PostgreSQL **18.6-alpine**, already cached with the exact digest and
  ARM64/PG_VERSION verified. This reuses **image bytes only**, never the stopped
  backend container, its volume or any existing PG instance/database/credentials.
- UI **http://127.0.0.1:58090/** → server8000, loopback only. Both container and
  host-listener checks found no existing published/listening58090. Recheck before
  activation. No database, worker, broker, SMTP or debugger port published.
- Separate ordinary Docker bridge `mcp-stack-windmill-trial`. No membership in
  existing PG, memory, graph, n8n or {{mstack:CLIENT_REPO}} networks. Outbound networking remains
  available for the application and future user-requested dependencies; this is
  **not** a verified egress firewall/security boundary against hostile scripts.
- Resource ceilings: PG0.5CPU/512MiB, server0.5CPU/768MiB, worker1CPU/2GiB.
  Aggregate **2CPU/3.25GiB maximum**, not reserved RAM, measured idle use or a
  battery guarantee. Bounded PID counts; Docker logs two5MiB files/service.
  Restart policy `unless-stopped` applies only to the new trial containers.

| Official image | Pinned index digest | ARM64 manifest |
| --- | --- | --- |
| `ghcr.io/windmill-labs/windmill:1.823.1` | `sha256:20932690bab6b1820bba7a4b5934998ec69fa3f82c0ddd9a500114e53ef51f50` | `sha256:a0c7f7ea7db229cabd05d06615b961d1700e6755ad9489b62aff27739735b362` |
| `postgres:18.6-alpine` | `sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873` | `sha256:89f747171c4b0af0eacf5984550060be79786dbe286eb60cfa691d79d1e8b23f` |

Registry metadata was inspected before approval. Windmill's ARM64 compressed layers total
**1,467,974,956 bytes (~1.37GiB)**; extracted/container/cache disk use is larger.
Approved image pull/start and HTTP/process checks are complete; no vulnerability
scan, script-execution qualification or production-hardening claim.

## Confirmed security choice

**Non-privileged, trusted-personal-scripts-only trial.** Worker has
`privileged:false`, all capabilities dropped, `no-new-privileges:true`, no Docker
socket, host PID/network, device or project/home-directory mounts. Server also
drops capabilities. PG retains standard image entrypoint capabilities for its
own directory initialization, never privileged mode or existing storage.

To avoid silently retaining the downloaded worker's broad privilege, trial
configuration sets `DISABLE_NSJAIL=true`, `ENABLE_UNSHARE_PID=false` and
`FAVOR_UNSHARE_PID=false`. These flags and defaults were inspected in the pinned
release source. **This disables per-job NSJAIL/PID isolation.** Docker container
isolation is not equivalent. Scripts can access the worker's own environment,
trial database credential/files and outbound network; only run code you trust.
Do not add real API credentials, private repositories, untrusted Hub jobs, host
mounts or collaborators as part of this trial. No claim of a production sandbox.
[Official isolation guidance](https://www.windmill.dev/docs/advanced/security_isolation).

No native worker, indexer, LSP/extra service, debugger, multiplayer, Caddy or SMTP
in this first UI/script evaluation. Editor language-server assistance and extra
service features are not promised. These are exclusions, **not automatic later
install steps**. This trial does not replace/remove n8n.

## Files, credentials and persistence

Repository implementation:

- `infra/windmill/compose.trial.yaml`: explicit standalone runtime definition,
  `pull_policy:never`; Compose validates with a synthetic URL, no secret reads.
- `integrations/windmill/trial_setup.py`: one-shot approved operation helper,
  uses existing Python/macctl/Docker only. Flag is a guard, not user consent.
- `integrations/windmill/tests/test_trial_definition.py`: 14 offline contracts.
- `.gitignore`: `infra/windmill/state/` added for future restricted runtime state.

After exact approval, generated one new random32-byte hex password:

- `.secrets/windmill_trial_password`, **0600**, original; PG reads it through
  a read-only Compose secret. Never read/copy other existing secrets.
- `infra/windmill/state/trial.env`, **0600** under0700 state directory;
  `WM_TRIAL_DATABASE_URL` → worker/server `DATABASE_URL`, pointing only to
  `db:5432/windmill`. Docker administrators can inspect runtime environment;
  this is not an encrypted vault. Inherited host URL variables fail closed.
- New DB/user `windmill`; this initial role is superuser **within the dedicated
  Windmill cluster only**, following the official local bootstrap pattern.
  Windmill startup migrations/roles/seed state affect that new cluster only.
  No calls or grants against existing stack/{{mstack:CLIENT_REPO}} databases.
- Named volumes: `mcp-stack-windmill-trial-postgres-data` at
  `/var/lib/postgresql` (PG18 parent path), `mcp-stack-windmill-trial-worker-cache`
  and `mcp-stack-windmill-trial-worker-logs`. No existing volume reused.
- Private operation logs/baseline/result under
  `infra/windmill/state/install-<unique>/` (**0700**, files0600). Never print raw
  logs/rendered Compose/credential contents. DB password is not the UI password.

Windmill DB holds its durable application/job state. Cache/log volumes are
separate. Trial data is not backed up merely by being in named volumes. Future
export/isolated restore is separately scoped; no shared-cluster migration now.

## Exact approved invocation and operations

From `/home/developer/workspace/mcp-stack` in Ubuntu, **after confirmation**:

```sh
python3 integrations/windmill/trial_setup.py --approved-trusted-trial-1.823.1
```

Helper checks the execution domain, fresh container/network/volume names, private
parents, port and absence of trial credentials; it refuses reruns/collisions.
It records existing-container metadata without reading their environment or
application data. Only absent pinned images are pulled; PG is currently cached.
Exact runtime command shapes, all on macOS via `macctl run`:

```sh
docker pull --platform linux/arm64 ghcr.io/windmill-labs/windmill:1.823.1@sha256:20932690bab6b1820bba7a4b5934998ec69fa3f82c0ddd9a500114e53ef51f50
# Only if the already verified exact PG image is absent at activation:
docker pull --platform linux/arm64 postgres:18.6-alpine@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873
docker compose -p mcp-stack-windmill-trial --env-file infra/windmill/state/trial.env -f infra/windmill/compose.trial.yaml config --quiet
docker compose -p mcp-stack-windmill-trial --env-file infra/windmill/state/trial.env -f infra/windmill/compose.trial.yaml up -d --no-deps --pull never db
# After the new PG is healthy, start the two approved Windmill processes:
docker compose -p mcp-stack-windmill-trial --env-file infra/windmill/state/trial.env -f infra/windmill/compose.trial.yaml up -d --no-deps --pull never server worker
```

Private credentials are generated inside the helper, not shell arguments or
repository patches. Before/after reports identify DB then server/worker actions.
No automatic registry retry, tag substitution, privilege fix, new component or
cleanup. If qualification fails, report the private evidence path and stop;
new resources remain bounded and preserved for review, not silently deleted.

## Verification and rollback boundary

Completed before install: 13 offline tests and existing macOS Compose
`config --quiet` using synthetic env and `/dev/null` instead of the user's `.env`.
Official release/manifests/ARM64, PG cache identity and port inventory verified.

After approved start: new PG and server health, host UI and `/api/version`200,
all three new processes running with zero restarts, and exact unchanged metadata
for every pre-existing container. Worker process readiness is **not** proof of
successful jobs. Owner login, real script/jobs, paid calls, memory/PKM/MCP/harness
connections, persistence/recreation and restore are not qualified or executed
by this installer. The user creates/changes their UI login privately.

Rollback is scoped to these newly installed resources. If requested, inspect
project labels and exact names first, then stop **only**:

```sh
macctl run docker stop mcp-stack-windmill-trial-worker mcp-stack-windmill-trial-server mcp-stack-windmill-trial-db
```

Stopping preserves new volumes/credentials/cache/logs for recovery. No automatic
removal, `down -v`, pruning, rollback over shared PG, old container restart or
backup deletion. Removal/export needs its own scoped confirmation if you later
choose it. Preserve your original downloaded assets for comparison.

**Stopping point:** finish the approved three-container trial and report its URL/
limits. No follow-on installs, integrations, models, browser permission changes
or recurring-monitoring jobs. The exact version/download and
**trusted-code-only, no per-job sandbox** tradeoff were
confirmed before runtime changes; this is not another open-ended setup roadmap.

Sources: [official Docker setup](https://www.windmill.dev/docs/advanced/self_host#docker),
[release](https://github.com/windmill-labs/windmill/releases/tag/v1.823.1),
[pinned worker isolation flags](https://github.com/windmill-labs/windmill/blob/v1.823.1/backend/windmill-worker/src/worker.rs),
[official PG image](https://hub.docker.com/_/postgres).
