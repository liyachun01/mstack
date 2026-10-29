# Approved Basic Memory runbook

Approved and completed on 2026-10-01 using the installed PostgreSQL 18.6 instance. Basic Memory 0.23.2 is running healthy; read/write/text search and note persistence after container re-creation passed. No embedding model download or harness registration has occurred. See `SETUP-STATUS.md` for the after report and resolved dependency versions.

## Component and scope

- Target: existing macOS OrbStack Docker engine, Compose project `mcp-stack`.
- Source/version: upstream Basic Memory `0.23.2`, official ARM64-capable GHCR image pinned to multi-platform digest `sha256:939f1173d96626c280763e14622f2381d49fbbb7db17cae2e832f4f639405643`.
- Configuration: opt-in `infra/basic-memory/compose.yaml`; wrapper `scripts/start-basic-memory.sh`. The root `compose.yaml` is a database-only entry point including `infra/postgres/compose.yaml`.
- No Node/Python installation on macOS or Ubuntu. Python and its dependencies stay in the upstream container; no Ubuntu mise changes.
- Database: existing `basic_memory` database/role on the approved PG18 service. Basic Memory runs its own first-start migrations there; it has no administrator password or access to `{{mstack:CLIENT_REPO}}` credentials.
- Secret: reuses `.secrets/basic_memory_password` mounted read-only. The wrapper constructs `BASIC_MEMORY_DATABASE_URL` inside the process environment without logging it. App config may persist this URL, so treat `infra/basic-memory/state` as secret-bearing and back it up securely.
- Endpoint: macOS `http://127.0.0.1:58000/mcp`, Streamable HTTP. The service is also reachable by trusted containers on `mcp-stack-memory`. It is not a public/authenticated endpoint; no Internet exposure or harness registration is included.
- Readable Markdown: `/home/developer/workspace/mcp-stack/knowledge/main`, mounted at `/app/data/main`.
- Configuration/logs: `/home/developer/workspace/mcp-stack/infra/basic-memory/state`, mounted at `/app/state`. Both locations are gitignored. Proposed runtime UID/GID is `501:501`, matching the current repository owner; confirm permissions during startup, without recursive ownership changes to the repository. No user/system-level application configuration is written on either host.
- Environment: PostgreSQL backend; local-only routing; project `main` constrained under `/app/data`; Logfire disabled; framework update check `off`; pool size/overflow `5/5`. See the overlay for exact values.
- First pass uses text search with semantic search disabled, preventing automatic embedding-model downloads or paid API use. pgvector remains installed. Select and approve a local embedding model in the following memory step, especially for Chinese/English notes.

Upstream's development PostgreSQL template uses PG17, but this setup's migrations and direct MCP workflow passed on PG18.6. This proves the tested workflow, not every future upgrade. SQLite is a viable embedded alternative with fewer operating dependencies, but no workload benchmark established it as faster here; retain the approved PostgreSQL backend. If later migrations fail, stop this service and report; do not downgrade PG18, grant superuser, or touch another database automatically.

## Exact approved first-install commands (historical; do not overwrite backups)

Run inside `/home/developer/workspace/mcp-stack`. Recheck port `58000`, current database health, repository ownership, available disk, and the `{{mstack:CLIENT_REPO}}` inventory before starting. Also take a restricted backup of `basic_memory` before first application migrations.

```sh
# Restrict backup files and save the pre-migration database (password not printed).
umask 077
install -d -m 700 backups
(set -C
macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  exec -T postgres pg_dump -U postgres -d basic_memory -Fc \
  > backups/basic-memory-before-app-20261001.dump
)
# Noclobber refuses an existing backup; use a new timestamp if one exists.

# These create only the two app data paths.
install -d -m 700 infra/basic-memory/state
install -d -m 755 knowledge/main

macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/basic-memory/compose.yaml \
  pull basic-memory

macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/basic-memory/compose.yaml \
  up -d --no-deps --wait --wait-timeout 180 basic-memory
```

`--no-deps` prevents this step from recreating or restarting PostgreSQL. Starting Basic Memory authorizes only its owned application's migrations as described above.

## Verification and after report

Repeat the read-only MCP workflow from Ubuntu using the container's installed Python:

```sh
macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/basic-memory/compose.yaml \
  exec -T basic-memory python - --read-only < scripts/verify-basic-memory.py
```

Create mode (without `--read-only`) is only for first verification: it refuses to overwrite the retained sample note. Do not rerun it on a populated project just to check health.

- Verify image/runtime version, UID, mount ownership, restart policy, DB backend, loopback binding, and process health without printing environment/config secrets.
- Initialize a real MCP session, list tools, create/read/search a clearly labeled verification note, confirm its Markdown appears at `knowledge/main`, and confirm the application indexed it in PostgreSQL. The image's `--version` health check is not sufficient.
- Verify note persistence across a scoped Basic Memory restart; retain a documented sample note or delete only that identified test note.
- Recheck the PostgreSQL and `{{mstack:CLIENT_REPO}}` container inventories for unexpected changes.
- Record success or specific failures, rollback, and the next embedding-model proposal. Stop before that model download, MetaMCP, n8n, or Codex registration.

## Rollback

Stop **only** Basic Memory with the same project directory and both Compose files:

```sh
macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/basic-memory/compose.yaml \
  stop basic-memory
```

This preserves notes, configuration, and PostgreSQL data. Stopping does not undo application migrations. Restore the separately taken pre-migration backup only with explicit direction; never use `down -v` or delete the database volume.

## Primary sources

- [Basic Memory 0.23.2 release](https://github.com/basicmachines-co/basic-memory/releases/tag/v0.23.2)
- [Tagged container build](https://github.com/basicmachines-co/basic-memory/blob/v0.23.2/Dockerfile)
- [Tagged PostgreSQL template](https://github.com/basicmachines-co/basic-memory/blob/v0.23.2/docker-compose-postgres.yml)
- [Tagged backend/semantic configuration](https://github.com/basicmachines-co/basic-memory/blob/v0.23.2/src/basic_memory/config_models.py)
- [Tagged MCP transports and auto-update behavior](https://github.com/basicmachines-co/basic-memory/blob/v0.23.2/src/basic_memory/cli/commands/mcp.py)
