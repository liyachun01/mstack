# Docker namespace migration to mstack — 2026-10-16

Completed at the user's request. Docker Compose now reports one **`mstack`**
project containing 11 retained services: **nine running, two stopped**. The old
`mcp-stack` group has no containers. All 19 unrelated containers retain their
IDs, start times, images, mounts, running states and restart counts.

| Service | Container name retained | State |
| --- | --- | --- |
| PostgreSQL + pgvector | `mcp-stack-postgres-1` | Running, healthy |
| Windmill server | `mcp-stack-windmill-server` | Running, healthy |
| Windmill worker | `mcp-stack-windmill-worker` | Running; fresh heartbeat and report verified |
| WhoDB | `mcp-stack-whodb` | Running, healthy |
| Garage | `mcp-stack-garage` | Running, healthy |
| OpenCodex | `mcp-stack-opencodex` | Running, healthy |
| Graphify | `mstack-graphify` | Running; native project MCP verified |
| Anytype MCP | `mstack-anytype-mcp` | Running; four documents read back |
| Headroom | `mstack-headroom` | Running; native compression/retrieval verified |
| agentgateway | `mcp-stack-agentgateway-1` | Stopped; Docker reports `Created` because it was not started |
| ai-memory | `mcp-stack-ai-memory` | Stopped; Docker reports `Created` because it was not started |

## What changed and what was retained

Compose definitions now select `name: mstack`; gateway lifecycle commands use
`-p mstack`. Containers had to be recreated to acquire the new Compose project
label. Original stopped instances were retained through verification, then
removed by exact ID without `-v`. No volume, network or image was removed.

Every replacement uses the original image ID, environment values (including
credentials), ports, persistent mounts, resource limits, security settings,
restart policy and network aliases. Existing named volumes and networks are now
explicitly external in the active definitions. Their old names and labels are
retained; they are stable data/network identities, not the displayed service group.
PostgreSQL and agentgateway also have explicit stable container names.

The repository stays `/home/developer/workspace/mcp-stack`. Project IDs, tenant
tokens, Anytype grants, Windmill workspace/script grants, Garage keys, WhoDB
settings and OpenCodex provider state are unchanged. This operation made no model
call, created no schedule, indexed no source and changed no global harness config.
WhoDB still has no newly configured database connection. No new Garage binding
was added to the external example.

## Corrections during the migration

The first replacement inspection passed a leading-slash container name through
`macctl`, which interpreted it as a host path. Inspection now strips that slash,
and recovery handles a replacement created before its ID was recorded.

The attempted restart of the original PostgreSQL container revealed that its
Docker `NetworkMode` still named the mail-only network deleted during the earlier
mail cleanup. That reference was stale despite the container already being
attached to the retained database networks. The current Compose definition was
used to recreate PostgreSQL on `mcp-stack-memory` and `mcp-stack-n8n-db`, preserving
its original data volume, roles, credentials and aliases. The retired network was
not recreated. PostgreSQL and the original Windmill services were recovered and
verified before the rest of the migration resumed.

Automatic approval review rejected a general retry while that recovery was
incomplete. The journal was preserved, PostgreSQL recovered as a scoped operation,
and health/configuration checked before continuing one service at a time.

The comparison also detected different implicit shared-memory limits on a newly
created service. Active definitions now pin each original runtime's exact limit.
Docker's empty-list/null representations for default DNS settings are normalized;
actual DNS changes still fail comparison. These checks have regression tests.

## Verification

- 11 replacements passed operational-equivalence checks; 19 unrelated containers
  are unchanged. Nine are running; the two optional services remain stopped.
- Private PostgreSQL logical copies before/after preserve the same database/role
  definitions. Windmill has a current worker heartbeat and a fresh successful
  restricted MCP report returning 90 minutes. An outside script was denied.
- Graphify queried the original 17-node/23-edge project index without reindexing.
  Concurrent temporary tenants verified index isolation and were removed.
- Anytype returned the existing four project documents, with its original single
  channel grant; an outside channel request was denied. No document was rewritten.
- Shared Headroom compressed the fresh tool evidence, saving 139 tokens (17.9%),
  and returned the exact original after reconnect. File reads and tenant overrides
  remained denied. Originals retain their one-hour TTL.
- WhoDB, Windmill and OpenCodex returned HTTP 200. Existing Garage credentials
  passed signed read-only S3 checks through the retained client network.
- Native Codex discovered the external project's mstack skill. Explicit
  `mstack run --inspect` selected all four project MCP bindings. Automatic native
  project loading still requires normal trust; no global trust setting was changed.
- 42 unit/regression tests passed. All six example proof stages pass against its
  compact config. Five stages were checked live; unchanged gstack browser evidence
  was carried forward after checking prior source dependencies and artifact hashes.

Public receipt: [namespace-mstack-20261016.json](../infra/services/namespace-mstack-20261016.json).
The private recovery snapshots, logical database copies, config backups, journal
and diagnostics are ignored under `infra/services/state/namespace-mstack-20261016/`.
They can contain credentials and must never be published.

## Operating from here

Use the [configuration guide and diagrams](MSTACK-CONFIG.md). Shared tool commands:

```sh
./mstack services status
./mstack services stop graphify
./mstack services start graphify
```

Other services keep their service-specific Compose files and env files, with
project `mstack`. Use exact services; no project-wide `down`, `--remove-orphans`,
volume reset, image rebuild or pull is needed for routine operation.

The one-time helper is `integrations/maintenance/namespace_mstack.py`. Do not replay
its prepare/apply/recovery/finish stages as startup or health checks. Original
containers have been retired. Any future reversal must use the current corrected
Compose definitions and preserved volumes, with the same stop-before-start rule;
restarting the old PostgreSQL definition would restore its stale network bug.
