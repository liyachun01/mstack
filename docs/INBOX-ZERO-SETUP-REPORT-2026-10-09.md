> Retired on 2026-10-15 at the user’s request. This is historical evidence; do not execute setup commands. See [retirement record](../infra/maintenance/mail-retirement/README.md).

# Inbox Zero Option B foundation

Completed 2026-10-09, Asia/Shanghai. The user requested the cloned-repo/custom
Option B, a dedicated database on shared PostgreSQL, and container initialization
on the existing macOS system Docker engine.

**Open on macOS:** http://localhost:58085/login

**Login is not configured yet.** First sign-in requires Google or Microsoft OAuth.
The email-code form cannot create the first account and no initial code is saved
on the VM. See [the first-login guide](INBOX-ZERO-FIRST-LOGIN.md).

Later the same day, the user selected Gmail and requested Outlook/Hotmail too.
Their configuration is prepared with one localhost OAuth origin, explicit
Microsoft `common` authority and optional contacts disabled. Only web was
recreated; all 22 other containers and existing secrets remain unchanged. Local
UI, keyed database health, Redis checks and all 293 migrations pass. Google and
Microsoft client credentials/owner consent remain pending; no mailbox is linked.

## What changed

- Cloned the official upstream repo at
  `0ae922dfd758f89e66aaa14272e6b88d3120bcce` into the separate ignored
  `integrations/inbox-zero/upstream/` Git checkout. It remains clean.
- Prepared project-owned Compose, private env settings, SQL and recovery/run
  instructions in `infra/inbox-zero/`. The matching official prebuilt ARM64
  image runs initially; source customization can be built later. No host
  dependency installation, setup wizard, hooks or marketing clone ran.
- Recovered existing shared **PostgreSQL 18.6 / pgvector 0.8.6**, whose container,
  image and networks were absent. Retained volume `mcp-stack-postgres-data` was
  confirmed as cleanly shut down PG18, backed up offline and verified before
  recreating only its original pinned service. Existing Basic Memory/n8n/Windmill
  application containers were not started.
- Created database and restricted non-superuser owner **`inbox_zero`**. Password
  is separate from every other service/admin credential. Existing databases,
  role definitions and schemas were preserved.
- Applied **all 293 migrations** explicitly; final database has **103 public
  tables**, zero users and zero linked email accounts. Web startup migrations
  are disabled so a migration failure cannot be silently tolerated.
- Started `inbox-zero-web`, Redis **7.4.11-alpine** and its authenticated HTTP
  bridge in Compose project **`mcp-stack`**, on the existing macOS OrbStack engine.
  Images are pinned by digest. No Linux Docker daemon or additional host Node,
  npm, pnpm or Inbox Zero CLI was installed.

## Qualified behavior

- Shared PG, web and Redis are healthy; HTTP bridge passes authenticated checks.
  Current containers have zero automatic restarts.
- macOS port **58085** responds; publication is loopback only. Database uses
  its original loopback **55322** port. Redis and bridge have no host ports.
- Keyed app `/api/health` returns HTTP 200 and reports its database healthy;
  wrong health key returns 401. Login HTML and three static assets return 200.
  These are HTTP checks, not a rendered-browser or mailbox acceptance test.
- Redis HTTP body-based POST PING returns 200/PONG, unauthenticated requests
  return 400 with an authorization error, and the bundled `@upstash/redis` SDK
  returns PONG. The bridge does not support GET commands in URL paths.
- Authenticated transactional owner write/rollback passed. Actual new-role
  connections to `basic_memory`, `n8n` and `windmill` are denied; their roles
  cannot connect to `inbox_zero`.
- All **15 pre-existing container identities** are preserved. Existing three
  application schema dumps match before/after, excluding dump restriction
  nonces; all pre-existing role-definition statements are unchanged.
- Redis has its dedicated AOF volume `mcp-stack-inbox-zero-redis-data`. PG keeps
  its original volume. The web container alone joins the app/database networks;
  Redis/bridge do not join the shared database network.

Initial web validation caught a required Pub/Sub topic string even with Google
disabled. A pending `skipped` value was added and only the new web container was
recreated. Final validation passed; no cloud Pub/Sub resource or OAuth flow ran.

## Deliberately pending application setup

Google and Microsoft credentials are unconfigured, so provider login is disabled.
The model string is a nonfunctional pending placeholder with no key, not a usable
model selection. No mailbox/provider API call or model call ran. Sending,
auto-drafts, cron, worker, external API and MCP remain disabled/unstarted.

The foundation is initialized; it cannot process mail until the intended provider
and model are configured and qualified. HTTPS/webhook delivery and future
project mail access remain separate decisions. Existing Codex/native credentials
and gateway routes were preserved.

## Evidence and recovery

Private random credentials live in `infra/inbox-zero/.secrets/` (0700 directory,
0600 files). Ignored `infra/inbox-zero/state/` contains image/migration/database,
runtime/preservation checks and the verified pre-recovery archive plus globals
and existing schema backups. Offline archive is **15,157,295 bytes**; SHA-256
`9375ef8a39ddad1bbd53260e275852844248a1f13d74dbb2c452a16d0d842546`.
No backup replay or application restore drill was performed.
An additional post-migration baseline `pg_dump -Fc` is saved privately
(364,137 bytes). The [public qualification receipt](../infra/inbox-zero/qualification.json)
contains versions, endpoint and validation results without credentials.

Use the [runtime and rollback runbook](../infra/inbox-zero/README.md) and updated
[integration plan](INBOX-ZERO-SETUP-PLAN.md). Repeat read-only infrastructure
qualification with `python3 integrations/inbox-zero/qualify.py`. Stop only the
three exact Inbox Zero services; preserve PG/Redis volumes and encryption keys.
Never use project-wide `down`, remove-orphans, data deletion or prune.

[Official Option B and external-database deployment](https://docs.getinboxzero.com/hosting/self-hosting),
[Redis HTTP bridge protocol](https://github.com/hiett/serverless-redis-http#differences-between-upstash-and-redis-to-note).
