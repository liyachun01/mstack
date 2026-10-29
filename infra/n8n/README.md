# Official local n8n app

Runtime: **macOS OrbStack Docker**, context `orbstack`. Ubuntu `devbox` contains
project definitions/source only, not a Docker installation. Use `macctl run`
from Ubuntu to invoke macOS Docker/Compose; use ordinary `docker` on macOS.

The approved app is official **2.41.6**, digest-pinned in [compose.yaml](compose.yaml).
**2026-10-04: app healthy, zero restarts; HTTP foundation qualified.** Private
secret volume and64MiB node-owned cache tmpfs fix the initial permissions/cache
omissions. Readiness/root/setup/main JS asset all return200 on macOS. Source keys,
all21 other containers, DB owners/ACLs/role flags and DeepSeek home preserved;
only approved Compose changes among protected files. Do not rerun installers.
[Completed checks, private backup/evidence and limits](../../docs/N8N-STATIC-CACHE-PROPOSAL.md).

Open **http://127.0.0.1:5678/** on macOS. Owner account/login is now user-reported;
use that existing account privately, do not give the agent your password or activate a
paid license/provider just to complete setup. No Assistant/sandbox or AI starter kit.

The [first portable router and approved UI handoff](../../integrations/n8n/workflows/README.md)
are ready; four synthetic checks run with one manual click after import. Edge
blocks automation, so import/editor acceptance is still unverified. Built-in nodes need no Code
runner or new installation. [Secrets inventory and recovery plan](../../docs/SECRETS-INVENTORY.md)
contain names/metadata only; no secret hardening/export performed.

## Persistence and isolation

- Existing PG18: separate restricted `n8n` database/login, unchanged memory DB.
- Dedicated internal `mcp-stack-n8n-db` bridge, alias `n8n-postgres`; PG also keeps
  its original memory network. Attachment does not restart PG. Future PG lifecycle
  uses the matching definition in `../postgres/compose.yaml`, not an ad-hoc second PG.
- App named volume `mcp-stack-n8n-data` → `/home/node/.n8n`. Private password,
  encryption key and broker token originals under ignored repository `.secrets/`.
  Runtime copies: `mcp-stack-n8n-secrets` → read-only `/run/secrets`, UID/GID1000,
  directory0700/files0600; never rotate/repopulate or export automatically.
- Private baseline/backups under `backups/n8n-app-before-…`; operational logs and
  qualification under this directory's ignored `state/` (0700/0600). Never publish
  evaluated config, secret contents or raw logs without reviewing/redacting them.
- Ephemeral `/home/node/.cache` tmpfs:64MiB, UID/GID1000,mode0700; static editor
  cache regenerates on start. Observed46.8MiB used. Remeasure on upgrades; do not
  silently expand limits. Existing `/tmp` remains128MiB; rootfs stays read-only.
- App: read-only rootfs plus writable named volume/tmpfs, official non-root user,
  no added capabilities, no privilege escalation or Docker socket. UI only publishes
  `127.0.0.1:5678`; broker5679 remains unpublished. No Basic Memory/{{mstack:CLIENT_REPO}}/graph-backend
  network membership. The former Compose bind-secret delivery was unreadable and
  is no longer active; the private named volume is not a vault or encrypted store.
  Docker administrators remain trusted. Original host keys retain UID501/0600.
- External Code runner mode only. **The runner is not installed by this app step**;
  do not expect Code nodes to execute or switch to internal mode as a workaround.
  No workflow definitions/imports/schedules or harness connections are activated.

## Safe checks

From Ubuntu, these do not start/restart containers or invoke memory/model tools:

```sh
macctl run docker ps -a --filter name=mcp-stack-n8n-1 \
  --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
macctl run curl --noproxy '*' --fail --silent --show-error \
  --max-time 5 http://127.0.0.1:5678/healthz/readiness
macctl run docker stats --no-stream mcp-stack-n8n-1 mcp-stack-postgres-1
```

UI shell/readiness and migrations do not prove browser rendering, account setup,
workflow execution, runner health or recreation/restore persistence. The 1CPU/1GiB
cap and an idle sample are not a battery budget. The app's `unless-stopped` policy
is explicit long-running behavior, not authorization for the agent to restart
existing services or retry a failed deployment blindly.

## One-shot deployment and rollback

`install-app.sh` delegates to reusable `integrations/n8n/app_setup.py`. Its
`--approved-app-2.41.6` flag is a guard, not user consent. The completed operation
must not be rerun: prepare rejects existing app resources/keys and activation
refuses collisions. Preparation saves the baseline and original PG/ignore files;
only after that are the exact approved definitions applied with `apply_patch`.

[Exact scope, commands and outcome](../../docs/N8N-APP-SETUP-PROPOSAL.md).
Later lifecycle changes require their own current-identity/impact/rollback approval.
Stopping just `mcp-stack-n8n-1` preserves its DB/volume/keys; never use broad Compose
down, remove-orphans, volume deletion, a whole metadata restore or PG restart.

Offline checks (existing Python/PyYAML and existing Node for router tests; no install):

```sh
bash -n infra/n8n/install-app.sh infra/n8n/provision-database.sh
python3 -I -B -m unittest discover -s integrations/n8n/tests -v
```

Stop after the already-approved manual UI import and one-click four-case test.
Owner login is user-reported; do not re-request the same approval or change browser
security settings to automate it. [Start here](../../docs/START-HERE.md). External
Code runner, Basic Memory, Codex, PKM and n8n↔harness connections remain deferred,
not automatic next setup steps.
