# WhoDB, Windmill and Garage recovery — 2026-10-09

The user explicitly requested restoring these three components on the existing
macOS OrbStack Docker engine. At discovery their four containers and three
images were absent. All five application volumes, original secrets and
Windmill's shared PostgreSQL database remained. Shared PostgreSQL was already
healthy following the earlier Inbox Zero foundation recovery.

## Scope and status

| Component | Original version | Local macOS endpoint | Recovery status |
| --- | --- | --- | --- |
| WhoDB | 0.134.0 | `http://127.0.0.1:58091/` | Healthy; UI and three assets return 200 |
| Windmill | CE1.823.1 | `http://127.0.0.1:58090/` | Healthy server; one recent worker; UI/version/assets return 200 |
| Garage | 2.3.0 | `http://127.0.0.1:53900` | Healthy; S3 endpoint, not a web UI |

These are the original digest-pinned images. Windmill's current definition now
pins the original ARM64 manifest instead of its parent multi-platform index;
this is the same release and executable layers qualified on October 5.
No version upgrade, host tool installation, database provisioning, bucket/key
creation, owner login or unrelated application startup is part of this recovery.

Public completion receipt: `infra/maintenance/service-recovery/qualification.json`.
All four recovered containers run with zero automatic restarts. All 19 containers
present before this recovery retained their IDs, start times, status, mounts,
networks and restart counts, including PostgreSQL and all 12 {{mstack:CLIENT_REPO_CAMEL}} containers.
The subsequent authorized Inbox Zero OAuth preparation recreated only its web
container to select a shared localhost origin; that is a separate change.

## Windmill image recovery

Ordinary macOS Docker pulls failed with transient not-found responses, TLS/EOF
errors and truncated blobs. Direct registry checks confirmed the original
immutable index and ARM64 manifest still exist. A resumable download through the
Ubuntu VM verified the raw original manifests/config and all 37 compressed
executable layers (**1,467,974,956 bytes**) by their SHA256 digests. Docker's index
import additionally required provenance attachments; their download also failed.

The verified ARM64 manifest and layers were therefore imported as a platform
archive with the supported `docker image load --platform linux/arm64` command.
See [Docker's load documentation](https://docs.docker.com/reference/cli/docker/image/load/).
`infra/windmill/compose.yaml` now pins
`sha256:a0c7f7ea7db229cabd05d06615b961d1700e6755ad9489b62aff27739735b362`,
the same ARM64 manifest recorded in the original installation proposal. Its
config is `sha256:30d84f9d9a687b665067625091ac0ed1d4733ad2e9713e60d970ea6ecd4dc601`;
Docker's imported filesystem-layer chain matches that original config exactly.
The former index pin and untouched definition are backed up privately. Historical
trial/standalone Compose sources remain unchanged. No mirror image, source build,
upgrade, host proxy change or global registry login was used.
After runtime verification, only the 39 newly staged image-layer/archive files
were deleted from the VM, reclaiming about 2.94 GB. The actual Docker image,
original immutable manifest/config metadata, checks, application backups and
secret backups remain; no Docker prune or unrelated cache cleanup was run.

## Protected state and backups

Private recovery state is under
`infra/maintenance/service-recovery/20261009T130328Z/.secrets/`, directory 0700
and files 0600, ignored by Git. It contains the original container/volume
inventory, secret-file copies, expanded private Compose definitions, checks and:

- Offline archive of `mcp-stack-whodb-data`, `mcp-stack-garage-meta`,
  `mcp-stack-garage-data`, `mcp-stack-windmill-worker-cache`, and
  `mcp-stack-windmill-worker-logs`: **86,891,137 bytes**, 13,637 entries,
  SHA256 `0d9704e8a61b4a9e3a8840de7374c928d6e1bff62e108dbba4db6298e13e7037`.
  All five volumes were unmounted before the archive; the helper mounted them
  read-only with networking disabled. The full gzip CRC and tar enumeration pass.
- Existing `windmill` database export: **801,054 bytes**, SHA256
  `066e22a5175a1dc468f43f35d01682d3430ecfdb64e7a5f305e1ae8012ce63a0`.
  `pg_restore --list` reads all 1,746 TOC lines successfully. This is a logical
  backup, not a completed restore drill.
- Original WhoDB encryption env, Garage RPC secret/env, Windmill database URL
  and password copies. The active credentials were reused, never regenerated.

Windmill preflight: the original credential authenticates to the original
database. It has 673 successful migrations, zero workspace-user rows (`usr`), one workspace, zero
queued jobs and zero enabled schedules. No owner account is being reset.

## Commands and configuration

WhoDB and Windmill use the existing external `mcp-stack-memory` network.
Only Garage's missing external network `mcp-stack-n8n-local` was recreated;
this does not recreate or start n8n. The Garage bind mount was checked against
the real mapped macOS `infra/garage/garage.toml` before startup.

Commands are run from the Ubuntu repository root through `macctl`; each
component's original pinned image is pulled with `--platform linux/arm64`.
Expanded Compose configuration contains secrets and must not be printed.

```sh
macctl run docker compose -p mcp-stack \
  --project-directory /home/developer/workspace/mcp-stack \
  --env-file infra/whodb/state/runtime.env -f infra/whodb/compose.yaml \
  up -d --no-deps --no-build --pull never --wait --wait-timeout 120 whodb

macctl run docker compose -p mcp-stack \
  --project-directory /home/developer/workspace/mcp-stack \
  --env-file infra/windmill/state/shared.env -f infra/windmill/compose.yaml \
  up -d --no-deps --no-build --pull never --wait --wait-timeout 180 \
  windmill-server windmill-worker

macctl run docker compose -p mcp-stack \
  --project-directory /home/developer/workspace/mcp-stack/infra/garage \
  --env-file infra/garage/state/runtime.env -f infra/garage/compose.yaml \
  up -d --no-deps --no-build --pull never --wait --wait-timeout 120 garage
```

Preflight must confirm the existing named volumes, matching credential files,
database health and free ports before any future recreation. Do not silently
create fresh state when retained state is missing. Do not run old trial Compose
files, provisioning SQL, Garage layout initialization or the mutating smoke test.

## Verification

WhoDB: same version/digest, retained data volume and encryption key, healthy
container, UI plus three local assets return HTTP 200. PostgreSQL credentials
are not preloaded; viewer deployment does not grant database access.

Garage: one healthy assigned node running 2.3.0, original node identity,
original `project-mcp-stack-demo-artifacts` bucket dated October 5, and both
original service keys. Both keys independently pass signed GET object-list
requests with HTTP 200; the retained demo bucket is empty. Anonymous macOS
requests return 403, as expected. No objects, keys or buckets were created or
deleted, and no application S3 credential was re-imported.

Windmill: healthy server, running non-privileged worker, version endpoint reports
`CE v1.823.1`, UI and three assets return 200, and one worker has a database
heartbeat within 60 seconds. All retained database counts match preflight:
673 successful migrations, zero workspace-user rows, one workspace, no queued
jobs or enabled schedules. No script or workflow was submitted as a health test.

## What is known about removal

Existing qualification records show healthy components on October 5. At this
October 9 recovery preflight, all four containers and their three images were
absent, while the original persistent data and credentials remained. Earlier
authorized cleanup removed the old Windmill **trial** and Activepieces test
runtime, not these current service definitions.

The Docker daemon returned only its last 256 retained events, covering
2026-10-09 13:02:52–13:03:59 UTC. Those contain no target removal events and
cannot explain the preceding four days. Targeted checks of macOS and Ubuntu
zsh history found no matching removal command. The usual macOS OrbStack log
directory was absent. These records do not identify a removal time, actor or
command; none is claimed.

The overlays share Compose project `mcp-stack`. Operate exact services only;
project-wide `down`, `--remove-orphans` and Docker prune conflict with preserving
the separately managed applications. Compose's orphan warning during targeted
startup is informational and must not be followed as a cleanup instruction.
There is no evidence that such a command caused this particular disappearance.

## Data-preserving rollback

If rollback is requested, stop/remove only the restored containers, without
`-v`, preserving all named volumes, private keys and shared PostgreSQL. Do not
delete the recreated client network while Garage or another client uses it.
Recreate with the same definitions/secrets when resuming. A failed state recovery
must be diagnosed against the protected backups; never replay an offline archive
over live volumes or reset shared PostgreSQL.
