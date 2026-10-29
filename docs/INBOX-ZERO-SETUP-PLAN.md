> Retired on 2026-10-15 at the user’s request. This is historical evidence; do not execute setup commands. See [retirement record](../infra/maintenance/mail-retirement/README.md).

# Inbox Zero integration plan

Updated 2026-10-09, Asia/Shanghai. **The user selected custom Option B, reusing
shared PostgreSQL and initializing containers on the macOS OrbStack engine.**
**Foundation completed:** source checkout/configuration, shared PG recovery,
dedicated database/role, all 293 migrations and three app containers are qualified.
Open macOS `http://127.0.0.1:58085/login`. Provider authentication, model use and
MCP registration remain pending; see the [completion report](INBOX-ZERO-SETUP-REPORT-2026-10-09.md).
The broader
[orb-devbox migration](ORB-DEVBOX-MISE-AUDIT-2026-10-09.md) remains separate.

## Goal and supported starting point

Add Inbox Zero as the mail application in mcp-stack, then qualify a scoped mail
connection for future work. The official quick start uses an optional setup CLI
followed by container startup and also permits manual configuration. **Host Node
24+ is required for the setup CLI or source installation; ongoing full-stack
Docker operation uses Node inside the image.** The setup CLI is different from
the API CLI that operates an existing mailbox.
[Docker deployment requirements](https://docs.getinboxzero.com/hosting/self-hosting),
[container startup source](https://github.com/elie222/inbox-zero/blob/0ae922dfd758f89e66aaa14272e6b88d3120bcce/docker/scripts/start.sh),
[Quick start](https://docs.getinboxzero.com/hosting/quick-start),
[setup CLI reference](https://docs.getinboxzero.com/hosting/setup-cli-reference).

Use mise for any host CLI/runtime; use the existing macOS OrbStack engine for
the application containers. Keep deployment settings in `infra/inbox-zero/`
and reusable connection/qualification code in `integrations/inbox-zero/`.
No global npm install, Ubuntu Docker installation or cloud setup is needed.

The VM owns the configuration and any optional CLI invocation. Containers run
on the existing macOS OrbStack engine, not on a second Docker daemon in `devbox`.
Docker/Compose remain system infrastructure. Both machines already have
mise-managed Node 24.21.0 installed; macOS selects Node/npm by project or explicit
invocation and has no global version selected. Reuse an existing qualified
runtime if using the CLI, or prepare Compose manually without host Node.

**Selected Option B:** the upstream Git repo is cloned at the inspected commit
under `integrations/inbox-zero/upstream/`; custom Compose/env/database settings
live under `infra/inbox-zero/`. The matching prebuilt image is used initially.
Custom PostgreSQL URLs do not require building app source. No host `pnpm install`
or interactive setup wizard ran; the upstream source pins pnpm 11.19.0, so the
installed pnpm 10 must not be substituted if future source work needs it.
See the [runtime/recovery runbook](../infra/inbox-zero/README.md).

## Read-only artifact evidence

The public npm registry reports `@inbox-zero/cli` **2.30.0**. Its metadata says
Node >=18, but the hosting guide requires Node 24+, so use the guide's requirement
and the qualified Node 24 project selection. The CLI tarball has registry
integrity/provenance metadata; it has not been downloaded or executed.
[Package metadata](https://registry.npmjs.org/@inbox-zero%2fcli/2.30.0).

Upstream source inspected at commit
`0ae922dfd758f89e66aaa14272e6b88d3120bcce`. Public registry manifest/config reads,
without an image pull, found:

| Artifact | Candidate immutable reference |
| --- | --- |
| Inbox Zero multi-platform image | `ghcr.io/elie222/inbox-zero@sha256:16dfa1b9dacbc3ed0c971900361d42888aa6e23a65e6af424a79ade5473d7d6a` |
| Inbox Zero Linux ARM64 manifest | `sha256:ca060296f4e5cadccd1a4848c74c8dc2780c04d4638018a633b4c5d6a9abef20` |
| Redis HTTP bridge multi-platform image | `hiett/serverless-redis-http@sha256:5b0bb9239fce53abf87b2018a7a0deb9ec7bd900c5360738fe5fbeeb426f9150` |
| Redis HTTP bridge Linux ARM64 manifest | `sha256:2856363e6ee1ec3afce43decc10ef96bb37ef3f1e7d27be30acb2434f386f440` |

The app image's revision label matches the inspected source commit. Its ARM64
layers total about 660 MiB compressed. The bridge's ARM64 layers total about
60 MiB; its image creation timestamp is May 2024. These are availability/source
metadata checks, **not runtime or vulnerability qualification**. Pin PostgreSQL
and Redis patch versions/digests during the concrete installation proposal.
Revalidate availability immediately before use.

## Adapt the supported Compose deployment

The inspected upstream file defines PostgreSQL 16, Redis 7, a Redis HTTP bridge,
web, optional worker, and cron. It uses floating image tags, forces app image
pulls, publishes web on all interfaces, and shares one data volume between
PostgreSQL and Redis. Those defaults need adaptation. Use exact image digests,
loopback web publication, separate database/Redis volumes, prefixed service
names and a dedicated network in the existing `mcp-stack` Compose namespace.
Manage exact services through an optional overlay; do not run the upstream CLI's
start/stop/update commands against the combined stack.
[Inspected upstream Compose](https://github.com/elie222/inbox-zero/blob/0ae922dfd758f89e66aaa14272e6b88d3120bcce/docker-compose.yml).

Selected services: `inbox-zero-web`, `inbox-zero-redis`,
`inbox-zero-redis-http`, plus a one-off `inbox-zero-migrate`. The user superseded
the earlier dedicated PostgreSQL container proposal. Reuse the existing shared
**PostgreSQL 18.6 / pgvector 0.8.6** service/volume, with new database and restricted
owner `inbox_zero`; no `inbox-zero-db` container or separate PG volume is created.
Cron and the queue worker remain pending their intended behavior review.

Discovery found the shared PG container/image/networks absent but its 104.7 MB
volume retained. An inactive-volume backup was archived, checksum/content
verified, and confirmed as cleanly shut-down PG18 before recovery. Only the
original PG service was recreated with its existing pinned image/volume/settings,
adding dedicated database transport; no other historical application was started.
Basic Memory, n8n and Windmill databases/roles remain present. The new role passed
authenticated transactional write/rollback and actual connection denial to all
three existing application databases; their roles cannot connect to Inbox Zero.
Private evidence is in `infra/inbox-zero/state/`.

Proposed UI port: macOS `127.0.0.1:58085` to container 3000. It was absent from
the inspected Linux/macOS listener and Docker publication inventories; check
again before allocation. Database, Redis and bridge need no published host ports.
Use the existing `mcp-stack-postgres-data` and separately named
`mcp-stack-inbox-zero-redis-data` volumes. Do not reuse {{mstack:CLIENT_REPO_CAMEL}} volumes.

Proposed private settings: ignored `infra/inbox-zero/.secrets/runtime.env`,
mode 0600 under a mode-0700 directory. Public templates contain names/placeholders
only. Review OAuth client secrets, encryption/session keys, database and Redis
credentials, cron authentication and any model key. Resolve host path translation
before Compose reads the file or bind mounts anything; Ubuntu and macOS are
separate execution domains.

## Mail access and future harness connection

Choose Gmail, Microsoft or both before preparing account-specific configuration.
OAuth requires the appropriate provider app registration/consent. Gmail push
delivery additionally uses Pub/Sub and a reachable HTTPS webhook; a loopback
UI does not provide continuous inbound notifications. The guide describes a
tunnel for local development, but no tunnel, public endpoint or cloud project
is created by this plan. Review that choice after local UI qualification.
[Gmail Pub/Sub](https://docs.getinboxzero.com/hosting/google-pubsub),
[Microsoft OAuth](https://docs.getinboxzero.com/hosting/microsoft-oauth).

Inbox Zero's optional MCP server is disabled by default and uses OAuth rather
than API keys. Start future qualification with `mcp:read`; draft/rule writes
and mail sending have separate scopes. Permissions cover every inbox linked
to the Inbox Zero user, including later-linked inboxes, so an account selector
does not establish project isolation. Validate the client OAuth flow and mailbox
boundary before proposing an agentgateway route or project harness registration.
[MCP server contract](https://docs.getinboxzero.com/api-reference/mcp).

Model selection and email automation are independent choices. No paid model
fallback, auto-send rule, bulk archive/unsubscribe, background mailbox capture,
or Anytype/memory synchronization follows from hosting the application. Cron
and workers can perform actual scheduled actions, so start them only when the
owner's intended mail behavior has been reviewed.

## Concrete checkpoints

1. **Option B files.** Clone the pinned upstream repo, adapt Compose/env settings
   to the shared PG, and keep source customization separate from runtime config.
   Validate private rendered settings without printing them; use the exact
   commands, ports, persistence and backup procedures in the runtime runbook.
2. **Shared PG and foundation start.** Back up the inactive retained PG volume,
   recover only its original pinned service, back up role/schema metadata, and
   create/qualify the new dedicated database/role. Pull the pinned ARM64 app,
   Redis 7.4.11 and bridge images. Run migrations explicitly before web startup;
   the upstream script otherwise tolerates failure, so automatic web-start
   migration is disabled here. Start only the exact Inbox Zero services.
   Neither provider is configured; the model string is a nonfunctional pending
   placeholder with no key. No mailbox or model call is part of this checkpoint.
3. **UI and persistence acceptance.** Verify app/database/Redis health, login
   origin, internal-only data services, persistence/recreation behavior and an
   Inbox Zero-only backup/restore. Compare protected container identities/ports.
4. **Provider connection.** Configure the selected provider app and connect the
   intended mailbox with reviewed permissions. Decide HTTPS/push delivery and
   any model provider here. Test the bounded requested behavior; do not send or
   alter messages as an installation smoke check.
5. **Future mail partner.** Qualify MCP OAuth/client support and resource scope
   directly, then prepare a project-scoped connection. Fail closed while pending;
   no global registration or blanket access across projects.

Before first start, rollback is discarding only prepared Inbox Zero files. After
start, stop only its exact services and preserve volumes and encryption keys;
removing containers is not a database rollback. Back up data before migrations
or upgrades. Restoring an older app image may require restoring the matching
database backup. Provider consent/token revocation is a separate step after an
account is connected. Never use project-wide `down`, `--remove-orphans`, volume
deletion or a system prune for this integration.

The repository's
[setup guard](../.agents/skills/mcp-stack-setup-guard/SKILL.md) governs each
concrete installation/lifecycle checkpoint. The user's latest request authorizes
this bounded Option B/shared-PG container foundation. Provider consent, model
calls and future harness registration are separate from that authorization.
