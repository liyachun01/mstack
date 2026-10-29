# Official n8n app: approved partial attempt and recovery proposal

Prepared/approved **2026-10-04**, followed by separately approved image retry, secret-volume and cache-tmpfs repairs. **n8n2.41.6 is healthy, zero restarts, local readiness/editor/setup/JS asset200.** [Completed qualification/backup/resource limits](N8N-STATIC-CACHE-PROPOSAL.md); [secret repair history](N8N-SECRET-PERMISSIONS-PROPOSAL.md). Open macOS **http://127.0.0.1:5678/** and create your owner account privately. Scope remains the app only, not the external runner, Assistant/sandbox, models, harness registration or workflows. Attempt history below is retained; the original YAML represents the first attempt, not the repaired active configuration in `infra/n8n/compose.yaml`.

## Earlier approved image retry outcome

User “approve” authorized one retry/start. Added a separately guarded continuation,
retaining original evidence and a fresh post-user-restart baseline. Existing image
source/Compose/keys/networks unchanged. The pull completed; exact digest/platform/
official user/version verified. Created app volume and broker/local networks, then
only `mcp-stack-n8n-1`, using `--no-deps --pull never`.

Startup exits1: **EACCES reading `/run/secrets/n8n_password`**, no OOM. The helper
stopped at its first failed readiness-state check, with no manual retry/restart,
permission change or automatic cleanup. Docker's preapproved `unless-stopped`
policy leaves the failed app in a restart loop. No app migration/readiness/UI or
owner/workflow qualification. All21 pre-existing containers unchanged against the
post-user-restart baseline; DB metadata/protected files/home/three keys unchanged.
Private evidence: `infra/n8n/state/retry-after-host-restart-i5fht3la/`. **13 n8n
offline contracts, shell syntax and23 DeepSeek Python tests pass**; not runtime
success. The [secret-volume repair](N8N-SECRET-PERMISSIONS-PROPOSAL.md) requires
separate confirmation; no change to host file permissions or running app as root.

## Actual partial outcome (2026-10-04)

- Created the exact app Compose, guarded shell entry point, reusable `integrations/n8n/app_setup.py`, README and offline contracts. Recorded only the approved network membership in PG Compose and ignored private operational state.
- Captured private baseline/original definitions at `backups/n8n-app-before-20261004-vy_phq7l/` (0700/0600). Created the two new `.secrets/` keys exclusively at0600; existing database password retained.
- Created internal `mcp-stack-n8n-db`, attached existing PG with alias `n8n-postgres` **without restart**. Compose validation passed. App-only pull submitted once to macOS OrbStack, then timed out after600seconds; no automatic retry or cleanup.
- Post-failure checks: **all21 existing containers unchanged except that one approved PG attachment**; database owners/ACLs/role flags, protected files and complete retained DeepSeek home unchanged. No completed app image, app container, app volume or broker/local network exists. UI5678 is not available; app migrations/readiness/owner/workflows remain unqualified.
- Private evidence: `infra/n8n/state/20261004-vy_phq7l/partial-outcome.json`. The initial helper discarded subprocess progress on timeout, so the actual pull error/progress was not retained; this is a diagnostic limitation, not evidence of a particular failed layer. Corrected the helper to retain timeout output privately with no retry; **10 offline contracts and shell syntax pass**.
- Preflight initially rejected PG's distribution-suffixed version string before mutation. Corrected to numeric `server_version_num=180006`; PostgreSQL did not change. Host HTTP checks now protect `/dev/null` inside a shell command against `macctl` absolute-argument translation.

### User host update and current recovery proposal — not executed

After the failed attempt, the user reported updating Docker configuration and restarting it. Read-only recheck confirms macOS context/engine `orbstack`, **no registry mirrors now configured**, existing OrbStack proxy retained, all21 container IDs retained and all16 stopped containers still stopped. The five running containers have new start/network timestamps from that user-initiated restart; PG is healthy and its dedicated internal n8n attachment persists. DB metadata/protected files/DeepSeek home are unchanged, no app/image exists and port5678 is free. This external change invalidates the original start-time baseline; do not describe it as unchanged or overwrite original evidence.

**Current proposed next approval supersedes the alternate-registry proposal below:** one retry from the **original approved `n8nio/n8n:2.41.6@sha256:87e0bab2c93192e8dd885ff7b0697c22a1bd97489568a8c67cc140fd7dbb342d`**, followed only on verified success by the first app creation/start. No image-reference or global Docker edit. Add a separately guarded partial-state continuation to `integrations/n8n/app_setup.py` and the existing `infra/n8n/install-app.sh` interface, with offline tests; retain the original baseline and fresh private post-host-restart baseline. Revalidate existing IDs/status/ports/memberships, DB/protected files/home, two private keys, no app/volume/broker/local collision and original Compose hash. Reuse keys and DB network; do not repeat prepare, secret creation or network attachment. Retain pull progress privately under `infra/n8n/state/`, bound the single retry and stop on failure. App port/persistence/resource/exclusion/verification/rollback scope remains exactly as originally approved.

```sh
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml pull n8n
# Only after successful pinned-image qualification:
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml up -d --no-deps --pull never n8n
```

This retry/start is **not executed**. No runner, account creation, workflow, memory/harness connection, models or other service lifecycle action. No automatic rollback or cleanup.

### Earlier read-only delivery diagnosis and alternate proposal — superseded, not executed

The engine already uses a proxy and two registry mirrors; none was changed. Bounded macOS direct metadata requests found `docker.1ms.run` returns the exact approved manifest200, while `docker.xuanyuan.me` returns403 for this manifest. Direct `registry-1.docker.io` returns200 and the **same SHA-256**; its largest ARM64 blob HEAD also returns200. `docker.n8n.io` returns429 after its authentication challenge. These establish endpoint behavior, **not a confirmed engine-transfer root cause or successful layer download**.

Proposed next approval: request the **same official version/digest** explicitly from `registry-1.docker.io/n8nio/n8n:2.41.6@sha256:87e0bab2c93192e8dd885ff7b0697c22a1bd97489568a8c67cc140fd7dbb342d`, with no global mirror/proxy edit, no new credentials and no secret/network recreation. Change only the app image reference in `infra/n8n/compose.yaml`, matching approved-contract evidence and verifier; leave the original YAML below as historical attempt evidence. Implement a separately gated continuation that rechecks partial-state identities/hashes/PG health/port and exact image, retains bounded pull progress privately, refuses an existing app/collision, and never reruns prepare/activate.

Exact proposed macOS operations, **not run**:

```sh
macctl run docker pull registry-1.docker.io/n8nio/n8n:2.41.6@sha256:87e0bab2c93192e8dd885ff7b0697c22a1bd97489568a8c67cc140fd7dbb342d
# Only after successful digest/platform/version qualification:
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml up -d --no-deps --pull never n8n
```

One bounded pull, then the first app creation/start and original acceptance checks. Port5678, existing secrets, named volume/network design, resource limits and all exclusions remain unchanged. No PG restart, runner or workflow installation. Failure retains private diagnostics and stops. Data-preserving rollback remains the individually reviewed actions below; do not delete the existing keys/network or rerun the initial installer.

## Target, artifact and read-only evidence

- Existing macOS OrbStack Docker/Compose, reached from Ubuntu through `macctl run`; Linux ARM64 engine. No host/Ubuntu Node, npm, mise, Docker or other tool installation.
- Official stable [n8n 2.41.6](https://github.com/n8n-io/n8n/releases/tag/n8n%402.41.6), published 2026-10-02; supersedes the old metadata-only 2.41.5 candidate. Matched future runner must also be 2.41.6. User approval of an older candidate is not assumed to approve this version.
- Official app: `n8nio/n8n:2.41.6@sha256:87e0bab2c93192e8dd885ff7b0697c22a1bd97489568a8c67cc140fd7dbb342d`.
- Registry metadata verified without downloading layers: Linux ARM64 child `sha256:333bb59293813033cdcfe5db71b1653f2ad0218b6afe037082a7ca20ab125c42`; compressed ARM64 layers **269,088,986 bytes** (~257 MiB), not final disk/RAM use. Config blob reports user `node`, native `tini -- /docker-entrypoint.sh`, version label 2.41.6. No custom binary/build or vendor patch.
- Future runner metadata only: `ghcr.io/n8n-io/runners:2.41.6@sha256:443eaee69319997627e2129ed8d512c4f4ea2418a744393cf26e843237399299`, ARM64 child `sha256:2fbb78e44e935e21ac24d7807fd968c72b9440b0df7d16d8a7b8ad0743c7a47d`, compressed layers **188,092,786 bytes**. No pull/start approved here. Runner hardening/health/secret transport needs its own exact proposal.
- Reviewed official [MCP interpreter advisory](https://github.com/n8n-io/n8n/security/advisories/GHSA-5jr4-xmvf-frmj) and [OAuth persistence advisory](https://github.com/n8n-io/n8n/security/advisories/GHSA-3qcw-p65v-c7vq); both identify 2.41.4 as the patched release on the stable branch. 2.41.6 is later; this is not a comprehensive vulnerability scan or a claim of no other vulnerabilities. Instance MCP and external OAuth/Assistant use are not enabled in this step.
- Port **5678** has no macOS listener, and no retained container publishes it. Proposed container/network/volume names below are absent. Recheck immediately before mutation; refuse collisions.
- Existing PG image/DB credentials stay unchanged. Docker user namespace/file sharing matters: an existing secret mounted through OrbStack reports container UID/GID 501 and mode 644 despite private Ubuntu source permissions. Do not claim host 0600 means container 0600 or silently chmod/chown existing mounts. Qualify only the new app's secret readability and its own volume settings; runner never gets the app secrets.

## Files and persistence to create/change after approval

- `infra/n8n/compose.yaml`: the exact app settings below, no runner service yet.
- `infra/n8n/install-app.sh`: approval-gated, fail-closed preflight/backup/secret/network/pull/start/verification helper implementing this scope. No auto-retry, password overwrite, broad Compose action or installer fallback.
- `infra/postgres/compose.yaml`: add **only** the external `n8n_db` network membership and `n8n-postgres` alias, retaining the existing memory membership, ports, image, mounts, credentials and health definition. This records the same hot-attached network for future PG recreation. **Do not run PG Compose up or recreate/restart PG in this step.**
- `.gitignore`: add `infra/n8n/state/` for private restricted operational records.
- Fresh ignored `infra/n8n/state/<unique-operation>/` and `backups/n8n-app-before-<unique-operation>/`, 0700 directories/0600 records. Back up changed definitions and baseline DB/containers/protected-state metadata before mutation; no whole personal-data export.
- Create only `.secrets/n8n_encryption_key` and `.secrets/n8n_runner_token` (64-character random hex, private 0600, no overwrites). Reuse existing `.secrets/n8n_password`; never print keys or evaluated Compose/env. Explicit encryption key is required for later credential recovery; keep it with protected backups, not portable workflow exports.
- New named app volume **`mcp-stack-n8n-data`**, mounted at `/home/node/.n8n`; persists config/binary application state. Workflow/credential/execution tables and migrations use only the existing `n8n` DB inside **`mcp-stack-postgres-data`**. No migration of Basic Memory tables or new PG volume.

## Proposed exact app Compose definition

All paths below are relative to the explicitly selected repository project directory, not `infra/n8n` or macOS home. Compose secrets are local bind-backed files, not a managed vault; Docker administrators can access them and process state. Host and mounted permissions must be verified separately.

```yaml
name: mcp-stack
services:
  n8n:
    image: n8nio/n8n:2.41.6@sha256:87e0bab2c93192e8dd885ff7b0697c22a1bd97489568a8c67cc140fd7dbb342d
    container_name: mcp-stack-n8n-1
    restart: unless-stopped
    read_only: true
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    cpus: 1.0
    mem_limit: 1g
    pids_limit: 256
    stop_grace_period: 30s
    environment:
      TZ: Asia/Shanghai
      GENERIC_TIMEZONE: Asia/Shanghai
      NODE_OPTIONS: --max-old-space-size=768
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: n8n-postgres
      DB_POSTGRESDB_PORT: "5432"
      DB_POSTGRESDB_DATABASE: n8n
      DB_POSTGRESDB_USER: n8n
      DB_POSTGRESDB_SCHEMA: public
      DB_POSTGRESDB_PASSWORD_FILE: /run/secrets/n8n_password
      DB_POSTGRESDB_POOL_SIZE: "2"
      N8N_ENCRYPTION_KEY_FILE: /run/secrets/n8n_encryption_key
      N8N_RUNNERS_AUTH_TOKEN_FILE: /run/secrets/n8n_runner_token
      N8N_RUNNERS_MODE: external
      N8N_RUNNERS_BROKER_LISTEN_ADDRESS: 0.0.0.0
      N8N_HOST: 127.0.0.1
      N8N_LISTEN_ADDRESS: 0.0.0.0
      N8N_PORT: "5678"
      N8N_PROTOCOL: http
      N8N_EDITOR_BASE_URL: http://127.0.0.1:5678/
      WEBHOOK_URL: http://127.0.0.1:5678/
      N8N_SECURE_COOKIE: "false"
      N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS: "true"
      N8N_BLOCK_ENV_ACCESS_IN_NODE: "true"
      N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES: "true"
      N8N_COMMUNITY_PACKAGES_ENABLED: "false"
      N8N_DIAGNOSTICS_ENABLED: "false"
      N8N_VERSION_NOTIFICATIONS_ENABLED: "false"
      N8N_TEMPLATES_ENABLED: "false"
      N8N_AI_ASSISTANT_BASE_URL: ""
      NODES_EXCLUDE: '["n8n-nodes-base.executeCommand","n8n-nodes-base.localFileTrigger","n8n-nodes-base.readWriteFile"]'
      EXECUTIONS_DATA_PRUNE: "true"
      EXECUTIONS_DATA_MAX_AGE: "168"
      EXECUTIONS_DATA_PRUNE_MAX_COUNT: "1000"
      EXECUTIONS_TIMEOUT: "60"
      EXECUTIONS_TIMEOUT_MAX: "300"
      N8N_LOG_LEVEL: info
    ports: ["127.0.0.1:5678:5678"]
    volumes: ["n8n_data:/home/node/.n8n"]
    tmpfs: ["/tmp:size=128m,mode=1777"]
    secrets: [n8n_password, n8n_encryption_key, n8n_runner_token]
    networks: [n8n_db, n8n_broker, n8n_local]
    logging:
      driver: json-file
      options: {max-size: "5m", max-file: "2"}
    healthcheck:
      test: [CMD, node, -e, "fetch('http://127.0.0.1:5678/healthz/readiness').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
      interval: 15s
      timeout: 5s
      retries: 20
      start_period: 90s
volumes:
  n8n_data: {name: mcp-stack-n8n-data}
networks:
  n8n_db: {external: true, name: mcp-stack-n8n-db}
  n8n_broker: {name: mcp-stack-n8n-broker, internal: true}
  n8n_local: {name: mcp-stack-n8n-local}
secrets:
  n8n_password: {file: ./.secrets/n8n_password}
  n8n_encryption_key: {file: ./.secrets/n8n_encryption_key}
  n8n_runner_token: {file: ./.secrets/n8n_runner_token}
```

HTTP/no Secure cookie is intentional **only for this loopback-only PoC**; no TLS downgrade for a public deployment. A public/remote UI needs a separate TLS/auth proposal. The default app user remains official `node`; no privileged/root container or Docker socket. File/command nodes and environment access are disabled. The local network permits app egress for later individually approved connections; no API/model/PKM calls are performed now. Basic Memory/graph-backend/{{mstack:CLIENT_REPO}} network membership is absent.

Broker port **5679 is unpublished**, external Code runner mode only. The UI/app may be qualified without a runner; **Code nodes will not execute until the separate runner installation passes**. Do not silently fall back to an internal runner. The broker also listens on the app's other container interfaces: only PG/app will share the DB bridge, which is not a replacement for broker authentication. Isolation is logical, not protection from Docker admins or a compromised shared PG administrator.

## Exact lifecycle sequence after approval

Historical initial sequence from Ubuntu repository root (already attempted; **do not rerun**):

```sh
bash infra/n8n/install-app.sh --approved-app-2.41.6 --prepare
# After the exact approved PG/ignore definition delta:
bash infra/n8n/install-app.sh --approved-app-2.41.6 \
  --backup-directory /home/developer/workspace/mcp-stack/backups/n8n-app-before-20261004-vy_phq7l
```

The helper was created/executed with separate prepare/activate phases. It verified Docker/Compose/domain, unchanged PG identity/health/18.6/image, restricted DB/login, private keys, absent target container/volume/networks and port freedom; captured retained-container/home/protected-state baselines and original definitions. It now refuses collisions from this partial attempt. The commands below record the approved original sequence, not recovery instructions.

Generate only the two approved secret files with exclusive creation, apply the declared files with `apply_patch`, then use these exact scoped macOS Docker operations (relative paths avoid `macctl`'s absolute-container-argument translation):

```sh
macctl run docker network create --driver bridge --internal \
  --label com.mcp-stack.owner=n8n mcp-stack-n8n-db
macctl run docker network connect --alias n8n-postgres \
  mcp-stack-n8n-db mcp-stack-postgres-1
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml config --quiet
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml pull n8n
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml up -d --no-deps n8n
```

No `up postgres`, root Compose up/down, `--remove-orphans`, PG restart, extra network connect or runner pull/start. Application startup performs official migrations **only in n8n's new DB**. Allow the normal declared restart policy for ongoing service recovery, but do not manually repeat failed setup/pulls, loosen permissions or change image/configuration without reporting and reviewing the cause. Record partial residue on any failure; no automatic cleanup/rollback.

## Verification, handoff and limits

1. Inspect actual image digest/version, non-root user/caps/no privilege/Docker socket, requested resources, volume, three exact memberships, loopback-only UI and no broker publication; verify new secret readability/settings-file permissions without revealing contents. Official pinned source was checked for `_FILE` loading in `packages/cli/src/config/index.ts` and `packages/@n8n/config/src/decorators.ts`; validate actual runtime rather than assuming source inspection is sufficient.
2. Require bounded startup, readiness **200**, official editor/setup shell **200**, successful DB migrations in `n8n`, and no internal runner fallback. Review logs privately; no raw key/env/config dumps. UI shell does not prove browser rendering or workflow execution. If startup fails, retain diagnostics and report it, not an endless reconnect cycle.
3. Compare all 21 retained container identities/status/start times/restarts/ports/memberships. The **only** permitted existing-container change is PG's additional `mcp-stack-n8n-db` membership/alias, without restart; its original memory membership remains. Existing database owners/ACLs/role flags, Basic Memory data/service and DeepSeek home/protected artifacts remain unchanged apart from approved infra definition additions.
4. Measure bounded app/PG CPU/RAM and volume use. The 1 CPU/1 GiB limit is an upper bound, not a claim about idle usage or battery draw. Broker/runner/workflow traffic remains untested here. Never clean stopped {{mstack:CLIENT_REPO}}/other containers or intentional caffeinate.
5. Report app installation precisely; leave it running. User opens **http://127.0.0.1:5678/** and creates the owner account themselves. Do not collect their password, submit signup, activate a license, add provider keys, import workflows or execute tasks. Owner setup, persistence/recreation tests and browser qualification remain separate guided steps.
6. Next independent proposal: matching official **external task runner**, then a model-free manual router workflow; neither is installed/executed by app approval. Harness gateway/Basic Memory/PKM connections remain separate.

## Data-preserving rollback (review separately; not run automatically)

After verifying fresh IDs, stopping **only** `mcp-stack-n8n-1` preserves the app volume, DB, keys, networks and original definition backups:

```sh
macctl run docker stop --time 30 mcp-stack-n8n-1
```

No volume/image/network/DB/secret deletion, broad Compose down, globals restore or PG restart. If later approved to remove just the hot PG network attachment, stop the app first, verify current members and use `docker network disconnect mcp-stack-n8n-db mcp-stack-postgres-1`; restore only the new PG Compose membership with `apply_patch`. Retain all data. App migrations are not undone by stopping the container. A later image downgrade needs qualified DB restore/migration planning, not changing the tag.

Sources: [official external runners](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners/), [PG compatibility/permissions](https://docs.n8n.io/deploy/host-n8n/configure-n8n/choose-n8ns-database/), [security variables](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/security/), [Assistant remains unconfigured](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/use-environment-variables/ai-assistant/), [pinned official image source](https://github.com/n8n-io/n8n/blob/n8n%402.41.6/docker/images/n8n/Dockerfile). No paid license/provider request needed for this foundation.
