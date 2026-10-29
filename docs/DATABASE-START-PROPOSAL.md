# Approved database runbook: PostgreSQL + pgvector through Compose

Approved and completed on 2026-10-01. PostgreSQL `18.6` and pgvector `0.8.6` are running healthy. This supersedes the earlier Supabase CLI startup proposal. See `SETUP-STATUS.md` for execution details and the isolated image-download retry.

## Component

- Runtime: macOS OrbStack Docker/Compose, using its existing CLI and engine.
- Project: `mcp-stack`; service: `postgres`; expected container: `mcp-stack-postgres-1`.
- Image: `pgvector/pgvector:0.8.6-pg18-trixie`, pinned to index digest `sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff`.
- Linux ARM64 manifest: `sha256:d589b1c85160432264bbe7d532bcae4d3813c39702a8faf6971ec42c81b71e21`. Record PostgreSQL's minor version from the running server; the digest fixes the image content.
- Only added extension: pgvector (`vector`), version `0.8.6`. Standard PostgreSQL full-text search needs no additional extension.
- Address: `127.0.0.1:55322`, targeting container port `5432`.
- Durable volume: `mcp-stack-postgres-data`; network: `mcp-stack-memory`.
- PG18 mount: `/var/lib/postgresql`; actual data directory: `/var/lib/postgresql/18/docker`. Do not use the PG17 image's older mount layout.
- Database and non-superuser application role: `basic_memory`; administrator: `postgres`.
- Password files: `.secrets/postgres_password` and `.secrets/basic_memory_password`. The preparation script generates distinct random passwords without displaying them and preserves existing nonempty files. Git ignores `.secrets`; its directory has mode `0700` and files use `0644` so the postgres user can read the read-only mounts. Do not publish these files.

## Exact approved startup commands

Run from `/home/developer/workspace/mcp-stack` inside Ubuntu. Immediately beforehand, check port `55322`, Docker context `orbstack`, and absence of unexpected matching project resources.

```sh
bash scripts/prepare-db-secrets.sh

macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  pull postgres

macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  up -d --wait --wait-timeout 180 postgres
```

The image already contains pgvector. First startup of the empty project volume creates the database/role and enables the extension using `infra/postgres/init/10-memory.sh`. No OS package installation, Supabase CLI operation, cloud project, or Basic Memory application installation is involved. Application migrations are a later step.

## Verification

- Inspect health, image digest, restart policy, labels, volume, network, and exact loopback binding.
- Query PostgreSQL and pgvector versions, and role flags (`rolsuper`, `rolcreatedb`, `rolcreaterole`). Verify the application role is not privileged.
- Authenticate over TCP as `basic_memory` using its secret and evaluate a vector distance. Use a transaction/temporary table to test writes without retaining test data.
- Verify a macOS loopback connection to `55322` and the named persistence mount.
- Compare existing `{{mstack:CLIENT_REPO}}` container IDs/status with the pre-start inventory.
- Record the after report, then stop before installing another component.

Repeat the SQL, application TCP authentication, vector write/query, and macOS listener checks from Ubuntu:

```sh
bash scripts/verify-db.sh
```

All checks passed at first startup; test data uses a temporary table in a rolled-back transaction. The mount was inspected, but a full backup/restore or container re-creation test remains deferred.

## Rollback and persistence

Stop only this service while keeping its container, network, and database volume:

```sh
macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  stop postgres
```

If container/network removal is requested later, use this exact project's `down` without `--volumes`. Never use `down -v`, `docker system prune`, or volume deletion as routine rollback. Keep password files with the data and back them up securely. Initialization scripts/password files initialize only a fresh volume; editing those files does not rotate existing database passwords.

## Supabase later

Keep `infra/supabase/config.toml` as an optional future starting point. Before enabling it, allocate different ports, check its supported PostgreSQL version, plan service integration and data migration, and obtain separate approval. Images/files for AppFlowy do not alone require migrating this database: see [database/storage assessment](DATABASE-AND-STORAGE.md).

## Sources

- [pgvector Docker image and supported tags](https://github.com/pgvector/pgvector#docker)
- [PostgreSQL image initialization, password files, and volumes](https://hub.docker.com/_/postgres)
- [Compose file-backed secrets](https://docs.docker.com/compose/how-tos/use-secrets/)
