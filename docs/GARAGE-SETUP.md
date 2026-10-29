# Garage deployment and service connections

Installed2026-10-05 after user approval; [verification and deviations](GARAGE-INSTALL-RECORD.md).
Garage and demo bucket/service keys are healthy and container-tested. Application
credential is registered in n8n; Windmill's resource awaits workspace authentication.
See [application binding status](GARAGE-S3-BINDINGS.md). The original proposal
below has been corrected to the actual runtime commands; do not rerun key/bucket
provisioning or recreate private state. All25 existing containers were preserved.

## Deployment

Target: existing macOS OrbStack Docker through `macctl run`, not Ubuntu Docker.
Official image: `dxflrs/garage:v2.3.0`, pinned to its native Linux ARM64 manifest
`sha256:2d3f94a89a8a02dc49fa75594d6df67ed9c6ffe08fe55ed023d0c9776f71a9bd`.
The manifest was verified with `docker manifest inspect`, without pulling it.
Garage was absent before this install; the deployed port53900 is now occupied by
this service. Re-inventory targets before any later lifecycle action.

Files: `infra/garage/compose.yaml`, `infra/garage/garage.toml`,
`infra/garage/README.md`, this guide, plus the private-state ignore rule.
The root Compose entry point and existing client definitions are unchanged.

One container `mcp-stack-garage`, Compose service `garage`, project `mcp-stack`.
Limits: 1CPU, 768MiB, 128processes; read-only root, dropped capabilities,
no-new-privileges. Two explicitly named volumes persist Garage metadata and
objects: `mcp-stack-garage-meta`, `mcp-stack-garage-data`.
Garage uses its own SQLite metadata, not PostgreSQL.

Only S3 is published: `127.0.0.1:53900` on macOS -> container3900.
RPC3901 binds container loopback; no admin/web endpoints are configured.
Garage joins existing `mcp-stack-memory` and `mcp-stack-n8n-local` networks.
Windmill and n8n can therefore reach `http://mcp-stack-garage:3900` without
restarts. Other containers on these networks also have network reachability,
but bucket access requires a key. No global credentials/environment injection.
Existing PostgreSQL, WhoDB, graph tools, memory, gateway and Supabase remain
unchanged. No existing files or database data are migrated.

This is a local, single-node deployment with no redundant data copy. Named
volumes and fsync do not replace an independent backup.

## Installation commands (record; already completed)

From the Ubuntu repo root, create ONLY the new private RPC file, refusing overwrite:

```sh
python3 - <<'PY'
from pathlib import Path
import os, secrets
state = Path('infra/garage/state')
state.mkdir(mode=0o700, exist_ok=True)
if state.is_symlink():
    raise SystemExit('Refusing symlink state directory')
os.chmod(state, 0o700)
with os.fdopen(os.open(state / 'rpc-secret', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
    f.write(secrets.token_hex(32) + '\n')
with os.fdopen(os.open(state / 'runtime.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
    f.write('GARAGE_RPC_SECRET=' + (state / 'rpc-secret').read_text().strip() + '\n')
PY
macctl run docker pull --platform linux/arm64 dxflrs/garage:v2.3.0@sha256:2d3f94a89a8a02dc49fa75594d6df67ed9c6ffe08fe55ed023d0c9776f71a9bd
macctl run docker compose -p mcp-stack --env-file infra/garage/state/runtime.env -f infra/garage/compose.yaml config --quiet
macctl run docker compose -p mcp-stack --env-file infra/garage/state/runtime.env -f infra/garage/compose.yaml up -d --no-deps --pull never garage
macctl run docker exec mcp-stack-garage ./garage status
macctl run docker exec mcp-stack-garage ./garage --version
```

No new host CLI/package is needed. The private env file supplies only
`GARAGE_RPC_SECRET`; do not print evaluated Compose configuration. `macctl` translates
the working directory for macOS; Docker bind paths must resolve there. Verify the
resolved Compose mount sources before starting. Do not use a Ubuntu absolute
path inside an embedded shell argument and assume macctl translates it.
Capture pre/post container IDs, start times, networks and mounts privately to
verify that every existing service, including stopped Supabase resources, is
unchanged. Health must show one assigned healthy node runningv2.3.0.

## Project buckets and service keys

Use one bucket per real project: `project-<project-id>-artifacts`. Both Windmill
and n8n access that project's bucket using different keys. Different projects
get different buckets AND keys; object prefixes alone are not an access boundary.
Example below uses only the `mcp-stack-demo` project. It does not provision the
runbook's `portfolio-research` project or all future namespaces automatically.

Pinned CLI help was inspected before provisioning. Completed commands below
are a record; do not rerun them. Through macctl, use relative `./garage` so it does
not translate a container executable path into a host path:

```sh
macctl run docker exec mcp-stack-garage ./garage bucket create project-mcp-stack-demo-artifacts
macctl run docker exec mcp-stack-garage ./garage key create mcp-stack-demo-windmill
macctl run docker exec mcp-stack-garage ./garage key create mcp-stack-demo-n8n
macctl run docker exec mcp-stack-garage ./garage bucket allow --read --write project-mcp-stack-demo-artifacts --key mcp-stack-demo-windmill
macctl run docker exec mcp-stack-garage ./garage bucket allow --read --write project-mcp-stack-demo-artifacts --key mcp-stack-demo-n8n
```

**Key creation prints secrets.** During installation capture its output directly
to exclusive0600 files in ignored `infra/garage/state/`, through a Python subprocess
or equivalent private redirection. Do not display it in tool/chat output. Prepare
private Windmill resource and n8n credential JSON in that directory from those
results. Keys get read/write only, no owner or create-bucket permissions.
Garage CLI administration remains local; there is no shared S3 superuser key.

## Windmill connection

Using an authenticated workspace, create a private resource of type `s3`, named
for the project, for example `f/mcp_stack_demo/garage`. Use:

| Field | Value |
| --- | --- |
| bucket | `project-mcp-stack-demo-artifacts` |
| region | `garage` |
| endPoint | `http://mcp-stack-garage:3900` |
| useSSL | `false` |
| pathStyle | `true` |
| accessKey / secretKey | The Windmill key, entered privately |

The live resource type's endpoint convention must be checked with the pinned
Windmill version: SDKs may expect a full URL or a hostname depending on the
script; use the full URL for boto3 and never prepend `http://` twice.
Use scripts/flows with this explicit resource. Generic S3 resource access is
available without paid instance cache/log storage features. Do not enable
instance S3 log/cache storage or assume current online workspace convenience
features exist in the pinned Windmillv1.823.1.

Resource creation needs workspace authorization. Do not read owner passwords,
bypass UI authentication or modify Windmill's application tables directly.
If no scoped API credential is available, complete the resource through the
existing UI; report it as pending, not connected.

## n8n connection

The **generic S3 credential** `mcp-stack-demo / Garage S3` is already registered;
do not create a duplicate. Its endpoint is `http://mcp-stack-garage:3900`, region
`garage`, with the n8n key, Force Path Style enabled and Ignore SSL Issues disabled.
Select it on the
generic S3 node. Use bucket `project-mcp-stack-demo-artifacts` explicitly.
No n8n restart is required to create a workflow credential.

This is workflow artifact access, not changing n8n's internal binary-data
backend to S3. Preserve its existing local data configuration. Do not substitute
AWS-specific credentials, decrypt unrelated credentials, bypass authentication,
or edit n8n's internal database tables.

## Acceptance and cleanup

1. Confirm resolved image, mounts, loopback-only port and healthy single node.
2. From the Windmill worker's existing interpreter, PUT a tiny unique synthetic
   object using the Windmill key; GET it from n8n using its key and compare bytes.
3. Verify LIST and deletion; always clean only this test's exact object keys.
4. Provision a second synthetic project bucket/key pair, verify each project's
   key gets403 for the other bucket, then revoke/remove ONLY the synthetic pair.
5. Verify unauthenticated reads are denied; existing container snapshots match.
6. Execute a reviewed synthetic Windmill script and n8n S3-node workflow through
   authenticated app interfaces. Direct container smoke tests alone do not prove
   application resources/workflows are configured.

Use existing runtimes; do not install a host AWS CLI merely for verification.
No scheduled workflows, model calls, finance data or old-data migration.

## Rollback, backup and upgrades

Rollback this new service only (stop first and preserve data):

```sh
macctl run docker stop mcp-stack-garage
macctl run docker rm mcp-stack-garage
```

Keep both named volumes, the RPC secret and private connection records.
Remove application bindings only if they were actually created for this install;
never run project-wide down or remove-orphans. Volume deletion is a distinct
destructive cleanup, not an automatic rollback step.

For backups, quiesce client writes and stop only Garage. Capture both metadata
and data volumes plus the RPC secret/config into a private, independent backup.
Treat metadata backups as secret-bearing (keys are stored there). Backup/restore
commands and any helper image must be qualified separately; no unpinned helper
containers or automatic backup jobs. Restore both volumes together, restore the
secret, start the same pinned release, and validate object content/access controls
before reconnecting clients. Restore has not yet been tested.

An upgrade needs a new pinned image and the official upgrade instructions.
Do not downgrade metadata created/migrated by a newer major release; restore the
matched backup if rollback needs an older release.

## Sources

- [Official Garage quick start and image](https://garagehq.deuxfleurs.fr/documentation/quick-start/)
- [Garage configuration](https://garagehq.deuxfleurs.fr/documentation/reference-manual/configuration/)
- [Garage upgrades](https://garagehq.deuxfleurs.fr/documentation/operations/upgrading/)
- [Windmill S3 resource fields](https://www.windmill.dev/docs/integrations/s3)
- [n8n generic S3 credentials](https://docs.n8n.io/integrations/builtin/credentials/s3/)
