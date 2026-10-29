# Windmill — shared PostgreSQL

## Recovery — 2026-10-09

Restored after the current server/worker containers and image were found absent.
The retained database/credentials/cache/log volumes were backed up and reused;
673 successful migrations remain, with one recent worker heartbeat and healthy
UI/version/assets. The current image pin selects the original qualified ARM64
manifest directly because registry/provenance downloads failed; it is the same
CE1.823.1 release and filesystem layers. No owner account was reset, script run,
database reprovisioned or trial environment recreated. See
[the recovery report](SERVICE-RECOVERY-2026-10-09.md).

## Original installation — 2026-10-05

Installed and qualified 2026-10-05. Open [Windmill](http://127.0.0.1:58090/) on
macOS. The fresh database means trial accounts/workflows were discarded. Follow
[official first-login guidance](https://www.windmill.dev/docs/advanced/self_host#first-time-login)
to create your owner account/workspace; keep your password in your password
manager. No agent login or script execution was performed.

## Runtime

- Official pinned ARM64 **CE1.823.1**; one server and one worker.
- Containers: `mcp-stack-windmill-server`, `mcp-stack-windmill-worker`.
- Compose project **`mcp-stack`**; explicit file
  `infra/windmill/compose.yaml`, services `windmill-server`/`windmill-worker`.
  Root Compose is unchanged. Existing cache/log volumes are external and reused.
- Existing `mcp-stack-postgres-1`, database/login `windmill`; isolated application
  DB, shared PG instance/volume `mcp-stack-postgres-data` and memory network.
- Separate application caches: `mcp-stack-windmill-worker-cache`,
  `mcp-stack-windmill-worker-logs`.
- Private generated credential `.secrets/windmill_password`0600 and URL file
  `infra/windmill/state/shared.env`0600; state directory0700. Never print them.
- UI loopback58090; no new host DB/worker port. Non-privileged worker, no Docker
  socket/project mounts, per-job NSJAIL/PID isolation disabled. Trusted code only.

The original downloaded Compose/Caddy assets and `compose.trial.yaml` are retained
as reference. **Never run bare Compose in this directory.** Do not rerun the old
trial installer or `provision-shared.sql`; the live database/roles already exist.

## Read-only checks

From the Ubuntu repository root:

```sh
macctl run docker ps -a --filter name=mcp-stack-windmill --format '{{.Names}} {{.Status}} {{.Ports}}'
macctl run curl --noproxy '*' --fail --silent --show-error http://127.0.0.1:58090/api/version
macctl run docker exec mcp-stack-postgres-1 psql -X -U postgres -d windmill -At -c "SELECT count(*) FROM worker_ping WHERE ping_at > now() - interval '60 seconds';"
```

At qualification: UI/versionHTTP200, server healthy, one recent worker,673
successful migrations, zero restarts. Runtime password access to Basic Memory
and n8n is denied. These checks do not prove a script ran or backup restore works.

## Stop/resume only when requested

The owner may use these scoped commands; agents still follow lifecycle approval.
They preserve the new database and volumes and do not stop shared PostgreSQL.

```sh
macctl run docker stop mcp-stack-windmill-worker mcp-stack-windmill-server
# Resume only after existing shared PostgreSQL is healthy:
macctl run docker start mcp-stack-windmill-server mcp-stack-windmill-worker
```

No trial rollback remains: its three volumes were intentionally deleted. The
current database is durable storage, not a backup by itself. A logical export
and offline cache/log volume archive were verified during October 9 recovery;
an isolated restore remains untested. Any future export must
target only `windmill`; never delete/reset the shared PG volume to reset this app.

[Deployment and cleanup evidence](WINDMILL-SHARED-PG-PROPOSAL.md).
No automatic next integration, model, financial job or scheduler setup follows.

## Project grouping correction — 2026-10-05

At the user's request, Windmill now belongs to the same Docker Compose project
`mcp-stack` as the other services. At preflight both Windmill containers were
absent; the database, credentials and two volumes remained. Only its two services
were recreated using the same pinned image and retained data; no provisioning,
volume deletion or PostgreSQL recreation was performed.

Current scoped recreation command (only when authorized):

```sh
macctl run docker compose -p mstack --env-file infra/windmill/state/shared.env -f infra/windmill/compose.yaml up -d --no-deps --pull never windmill-server windmill-worker
```

Never use `--remove-orphans` or project-wide `down`: other stack services are
managed by their own definitions in the same project. The old
`compose.shared.yaml` is retained as historical standalone-project source; do
not launch it alongside the current definition. To roll back grouping if explicitly
requested, stop/remove only the two Windmill containers without `-v`, then use
the old standalone definition and the same env/volumes. No data rollback needed.
Private grouping evidence: `infra/windmill/state/namespace-77fbkbin/`.
