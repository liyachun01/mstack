# Database sharing and future object storage

Assessment: 2026-10-01. This document is a recommendation, not approval to install AppFlowy, Supabase, or an object store.

## Now

Use the approved PostgreSQL 18 + pgvector Compose service for Basic Memory. Keep `infra/supabase/` disabled. The first database and application role are both named `basic_memory`.

Agentgateway is now the selected gateway, not installed. Its core routing can use file configuration without a database; propose that mode first rather than creating a gateway database automatically. Upstream also documents optional PostgreSQL for database-backed features. If needed later, qualify compatibility and propose a separate `agentgateway` database/non-superuser role on this instance, with explicit migration and backup approval. Do not reuse Basic Memory's database or accept the gateway's generated SQLite defaults silently. See the [gateway assessment](AGENTGATEWAY-SETUP-PROPOSAL.md).

## Share a server, not every application's schema namespace

For later components, prefer one PostgreSQL instance with **separate databases and non-superuser roles** per component, where their supported PostgreSQL versions permit it. Each database can have its own required schemas and extensions. Limit each role's connection and object permissions explicitly; sharing an instance still shares resources, upgrades, and outage risk.

Do not put unrelated third-party migrations into one database merely by assigning schema names. First verify that every component supports a custom schema/search path throughout initialization, migrations, and runtime queries. Some integrations assume `public` or use additional schemas such as `auth`.

No additional component database or schema is created at this step. AppFlowy's current official Compose template uses PostgreSQL 16; PostgreSQL 18 compatibility must be tested before attaching it to this instance. Do not downgrade Basic Memory's database to make an untested component fit.

## AppFlowy images/files do not require full Supabase

The current official AppFlowy Compose template separates PostgreSQL from S3-compatible object storage. It includes MinIO by default and allows an external S3 service. Adding image/file storage is therefore not, by itself, a reason to move Basic Memory into Supabase.

At the AppFlowy step, evaluate its supported local object-store configuration, authentication, browser-accessible presigned URLs, bucket permissions, backup, and restore. Supabase Storage exposes an S3-compatible API, but this is not proof of plug-and-play AppFlowy compatibility; test it if that option is chosen.

Preserve the Supabase option for concrete Auth/API/Storage/Realtime needs. A later full Supabase deployment requires its own supported PostgreSQL image/major version and migration plan. Never point a different PostgreSQL major at `mcp-stack-postgres-data`, and never attach any new component to `{{mstack:CLIENT_REPO}}`.

Before a future database move, back up roles/grants and application databases, restore into an isolated target, test the applications, and keep the original volume for rollback. Object storage has separate data and backups; database dumps alone do not contain image objects.

## AppFlowy distribution change to review later

The former public `AppFlowy-Cloud` repository was archived on 2026-09-11. Upstream directs current self-hosted deployments to `AppFlowy-SelfHost-Commercial` and official prebuilt images. Evaluate its licensing and supported integration options with the user before setup; this finding does not authorize silently replacing the chosen PKM product.

## Primary sources

- [AppFlowy's current Compose template](https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial/blob/main/docker-compose.yml)
- [AppFlowy upstream distribution notice](https://github.com/AppFlowy-IO/AppFlowy-Cloud#switch-to-the-appflowy-selfhost-commercial-repo)
- [Supabase Storage S3 compatibility](https://supabase.com/docs/guides/storage/s3/compatibility)
- [PostgreSQL Docker image: PG18 volume layout](https://hub.docker.com/_/postgres)
