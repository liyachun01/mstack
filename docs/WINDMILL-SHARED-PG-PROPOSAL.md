# Windmill replacement — completed 2026-10-05

Approved by the user with “do”; executed 2026-10-05. The same message also
explicitly approved removal of the Activepieces test environment and its data.
The procedure below is retained as the approved record, **not a rerunnable
installer**. Trial resources and credentials no longer exist.

## Execution outcome

- Windmill **CE v1.823.1** now runs as one server and one worker against the
  existing PG18.6 instance using its dedicated `windmill` database/login.
- All673 startup migrations successful; UI/versionHTTP200; server healthy;
  one recent worker heartbeat; zero application restarts at qualification.
- Password-authenticated Windmill login succeeds on its database and is denied
  on Basic Memory/n8n. No superuser/CREATEDB/CREATEROLE granted to that login.
- Shared PostgreSQL container was not restarted/recreated. Existing database
  owners/ACLs and original role privileges match the pre-operation baseline.
- Removed trial server/worker/DB, all three trial volumes, trial network,
  `.secrets/windmill_trial_password` and `infra/windmill/state/trial.env`.
- Separately removed all four Activepieces containers, both data volumes and
  its network/runtime `.env`; cache is empty. [Exact cleanup record](ACTIVEPIECES-RETIREMENT.md).
- All22 unrelated containers and17 other volumes unchanged after both cleanups.
  Existing infra source hashes matched before intentional documentation updates,
  except the explicitly removed Activepieces runtime `.env`.
- Preserved all component definitions and historical documentation. No image
  pruning, host tool changes, model calls, jobs or harness/PKM registrations.
- Worker startup reports unshare unavailable, consistent with the approved
  non-privileged/no per-job isolation configuration; worker then registers and
  listens normally. This remains trusted-code-only, not a production sandbox.
- No failure-driven repairs or privilege changes were needed. Trial data deletion
  is irreversible without a pre-existing backup; none was made in this operation.
- Private evidence: `infra/windmill/state/replacement-3411t0az/`, including
  `qualification.json`, `cleanup-qualification.json`, baseline and private logs.

Use the [current runbook](WINDMILL-RUNBOOK.md). Owner setup/script execution remains
unperformed; this deployment does not claim financial-workflow qualification.

## Approved procedure (historical; do not rerun)

## Result and fixed scope

- macOS OrbStack Docker through existing `macctl run`; no toolchain installs.
- Reuse cached official ARM64 Windmill **CE1.823.1**, image
  `ghcr.io/windmill-labs/windmill:1.823.1@sha256:20932690bab6b1820bba7a4b5934998ec69fa3f82c0ddd9a500114e53ef51f50`.
  Cached digest/architecture were reverified, without a pull.
- Existing `mcp-stack-postgres-1`: PG18.6 + pgvector0.8.6, image
  `pgvector/pgvector:0.8.6-pg18-trixie@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff`.
  No PG restart/recreation/version change. Its `mcp-stack-postgres-data` volume
  remains. Add only `windmill` DB/login and `windmill_user`, `windmill_admin` roles.
- New standalone Compose project `mcp-stack-windmill`, containers
  `mcp-stack-windmill-server`, `mcp-stack-windmill-worker`. One worker only.
- Existing external network `mcp-stack-memory`, database DNS
  `mcp-stack-postgres-1:5432`. This deliberately shares network reachability with
  Basic Memory; it is not network isolation between applications. Existing
  Basic Memory/n8n database ACLs deny PUBLIC access; do not change them.
- UI stays at macOS `127.0.0.1:58090`; no extra host port or proxy required.
- Fresh volumes `mcp-stack-windmill-worker-cache` and
  `mcp-stack-windmill-worker-logs`. Fresh login/workspace; trial records discarded.
- No PostgreSQL superuser credential enters Windmill. `windmill_admin` is a
  NOLOGIN BYPASSRLS role required upstream; Windmill can assume it, so this is
  not an untrusted-code sandbox. No grants to existing application databases.
- Preserve trial security/resource limits: non-privileged, no host/socket mounts,
  no-new-privileges; job NSJAIL/PID isolation remains disabled. Trusted scripts
  only. Server768MiB/0.5CPU, worker2GiB/1CPU; remove trial PG512MiB/0.5CPU ceiling.
  Shared PostgreSQL absorbs the DB workload; this is no measured savings claim.

Reviewed source: [pinned role initialization](https://github.com/windmill-labs/windmill/blob/4096c3da74138e3476c2cd9996cbb455aaf8e926/init-db-as-superuser.sql).
Windmill documents using an existing database with a non-superuser runtime login
and precreated roles in its [self-host guide](https://www.windmill.dev/docs/advanced/self_host).

## Prepared files and credentials

- `infra/windmill/compose.shared.yaml`: explicit standalone two-service definition;
  `pull_policy: never`; not included by root Compose.
- `infra/windmill/provision-shared.sql`: new roles/database and scoped grants;
  not an automatic PG init hook. Startup performs Windmill migrations in the new DB.
- New `.secrets/windmill_password`0600: random32-byte hex secret, generated only
  after approval; never use existing administrator/application passwords.
- New `infra/windmill/state/shared.env`0600 inside0700 directory:
  `WM_DATABASE_URL=postgres://windmill:<generated>@mcp-stack-postgres-1:5432/windmill`.
  Windmill receives `DATABASE_URL`; Compose also sets MODE/BASE_URL and the
  existing worker flags. Docker admins can inspect environment credentials.
- Private operation evidence under `infra/windmill/state/replacement-<unique>/`;
  no password, rendered Compose or environment inspection in chat output.
- Keep original downloaded assets, trial Compose, setup helper, tests and docs.
  Trial runtime secret/env files are disposable state; remove only named files
  below after successful replacement. No deletion of `infra/` component directories
  or source definitions. Keep non-secret historical verification evidence.

## Exact execution sequence after confirmation

Commands below are a reviewable procedure, not a report of executed operations.
Run from the Ubuntu repository root. Use existing Python/macctl only. Fail closed
on any failed command; do not continue deletion if verification fails.

1. Repeat read-only inventory: container IDs/project labels/mounts, named volumes,
   image digest, port58090 ownership, shared PG health and role/database names.
   Refuse an unrelated58090 listener, an existing target project/database/role or
   credential file. Verify the three old containers and three old volumes belong
   to `mcp-stack-windmill-trial`. Record metadata for all other containers (without
   environment); preserve all {{mstack:CLIENT_REPO}}, Activepieces, n8n, graph and memory state.

2. Generate fresh credentials and execute only the prepared database SQL. The
   following Python block is the exact credential/provisioning operation; prior
   preflight is required. It preserves partial state on errors for diagnosis.

```python
from pathlib import Path
import os, secrets, subprocess
root = Path('/home/developer/workspace/mcp-stack')
state = root / 'infra/windmill/state'
password_file = root / '.secrets/windmill_password'
env_file = state / 'shared.env'
for parent in (state, password_file.parent):
    if parent.is_symlink() or not parent.is_dir():
        raise RuntimeError('Expected existing private directory')
    if parent.stat().st_mode & 0o077:
        raise RuntimeError('Private directory permissions required')
for path in (password_file, env_file):
    if path.exists() or path.is_symlink():
        raise RuntimeError('Refuse to overwrite credentials')
password = secrets.token_hex(32)
for path, body in (
    (password_file, password + '\n'),
    (env_file, 'WM_DATABASE_URL=postgres://windmill:' + password +
     '@mcp-stack-postgres-1:5432/windmill\n'),
):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(body)
sql = "\\set wm_password '" + password + "'\n"
sql += (root / 'infra/windmill/provision-shared.sql').read_text()
result = subprocess.run(
    ['macctl', 'run', 'docker', 'exec', '-i', 'mcp-stack-postgres-1',
     'psql', '-X', '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-d', 'postgres'],
    input=sql, text=True, capture_output=True, cwd=root, timeout=60,
)
if result.returncode:
    raise RuntimeError('Provisioning failed; preserve state and inspect privately')
```

3. Validate Compose privately, stop only the two trial application processes,
   then start the replacement. An inherited `WM_DATABASE_URL` must be absent;
   never use the downloaded `docker-compose.yml` or bare Compose invocation.

```sh
macctl run docker compose -p mcp-stack-windmill --env-file infra/windmill/state/shared.env -f infra/windmill/compose.shared.yaml config --quiet
macctl run docker stop mcp-stack-windmill-trial-worker mcp-stack-windmill-trial-server
macctl run docker compose -p mcp-stack-windmill --env-file infra/windmill/state/shared.env -f infra/windmill/compose.shared.yaml up -d --no-deps --pull never server worker
```

4. Wait boundedly for server health (up to5 minutes, individual waits at most15s).
   Check both new processes, restart counts, version/UI and new DB migrations;
   compare every unrelated container's metadata and existing DB owners/ACLs with
   baseline. Check the runtime login cannot connect to `basic_memory` or `n8n`
   using its generated credential privately, and has no superuser/CREATEDB/
   CREATEROLE attributes. Verify the worker registers in the new Windmill database.

```sh
macctl run docker inspect --format '{{.State.Health.Status}}' mcp-stack-windmill-server
macctl run docker ps -a --filter label=com.docker.compose.project=mcp-stack-windmill --format '{{.Names}} {{.Status}} {{.Ports}}'
macctl run curl --noproxy '*' --fail --silent --show-error http://127.0.0.1:58090/api/version
macctl run curl --noproxy '*' --fail --silent --show-error --output /dev/null http://127.0.0.1:58090/
macctl run docker exec mcp-stack-postgres-1 psql -X -U postgres -d windmill -c 'SELECT count(*) FROM worker_ping;'
```

Successful health/worker registration is **not** proof of script execution or
production suitability. No owner credential reads, browser bypass, jobs, schedules,
model calls, real financial data or brokerage integration in this replacement.

5. **Only after all checks pass**, retire exactly the old resources. Recheck
   labels/mounts immediately before deletion. This permanently discards trial
   workflows, users, job history, database and caches as requested; no backup
   is implied. Retain reusable cached images, which the replacement still uses.

```sh
macctl run docker stop mcp-stack-windmill-trial-db
macctl run docker rm mcp-stack-windmill-trial-worker mcp-stack-windmill-trial-server mcp-stack-windmill-trial-db
macctl run docker volume rm mcp-stack-windmill-trial-postgres-data mcp-stack-windmill-trial-worker-cache mcp-stack-windmill-trial-worker-logs
macctl run docker network rm mcp-stack-windmill-trial
```

Remove only `.secrets/windmill_trial_password` and
`infra/windmill/state/trial.env`, after verifying they are regular files, not
symlinks. Keep all source definitions and docs. Verify no old project containers,
volumes or network remain; recheck the replacement and protected resources.
Update this document/runbook to actual results, then stop.

## Failure and rollback

Before step5, preserve trial data and restart its original application containers
if the new application fails; stop the new server/worker first to release58090:

```sh
macctl run docker stop mcp-stack-windmill-worker mcp-stack-windmill-server
macctl run docker start mcp-stack-windmill-trial-server mcp-stack-windmill-trial-worker
```

No automatic retries, privilege escalation, PG restart or broad cleanup. New DB,
roles and credentials remain for diagnosis. If explicitly abandoning the fresh
replacement after verifying ownership/no unrelated use, removal is scoped to its
two containers/cache volumes and `DROP DATABASE windmill` (after disconnecting
its sessions), then `DROP ROLE windmill, windmill_admin, windmill_user`; no shared
PG volume or other database is removed. If provisioning failed before the DB
exists, inspect the partial objects rather than blindly replaying the SQL.

**After step5 the trial data cannot be recovered without a prior backup.** The
source definition can recreate a new empty trial, not restore discarded records.
Shared PG remains intact throughout. This proposal authorizes no later component.

## Preparation validation

- macOS Compose validates `compose.shared.yaml` with a synthetic database URL;
  no runtime secret was read and no service started.
- The14 existing trial offline tests still pass; these validate the preserved
  trial, not the new database migration.
- New document links and embedded Python syntax pass local checks.
- Live read-only inventory confirms cached ARM64 digest, shared PG health,
  absent Windmill DB/roles, and restrictive Basic Memory/n8n database ACLs.
- At preparation time SQL execution, authentication and deployment were unverified.
  These deployment checks subsequently passed as recorded above; actual script
  execution remains untested.
- An initial validation command hit macctl's absolute-argument translation for
  `/dev/null`; validation succeeded with `/dev/null` inside a fixed macOS shell
  command. No installation or runtime mutation occurred in either attempt.
