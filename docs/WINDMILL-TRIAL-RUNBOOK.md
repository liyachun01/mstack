# Windmill trial — use what is installed

> Retired2026-10-05: the Windmill trial containers, all three volumes, network
> and runtime credentials were deleted after successful shared-PG replacement.
> This is historical evidence; trial lifecycle commands no longer apply.
> Use [the current Windmill runbook](WINDMILL-RUNBOOK.md).

> 2026-10-05: [the simplification decision](START-HERE.md) takes precedence.
> This document preserves existing runtime/history; old product choices and
> “next steps” are not mandatory. Agentgateway remains selected; MetaMCP is superseded;
> Windmill shared-PG replacement is complete; the trial has been removed.

Installed and verified 2026-10-05 after exact user approval. Execution domain:
existing **macOS OrbStack Docker**, reached from Ubuntu using `macctl run`.
No Docker/mise/toolchain installed in Ubuntu; original downloaded assets untouched.

## Open the UI

Open [http://127.0.0.1:58090/](http://127.0.0.1:58090/) on the Mac. Follow
[official first-login instructions](https://www.windmill.dev/docs/advanced/self_host#first-time-login)
to replace the public bootstrap admin account with your own account and create
a workspace. Store your new UI password in your password manager, never Git.
No agent login or account change was performed. The generated database password
is separate from UI credentials and is not needed for normal browser use.

This is a **trusted-personal-code-only trial**. NSJAIL/PID job isolation is
disabled to avoid privileged workers. A job can access the worker environment,
trial DB credential/files and outbound network. Do not import untrusted Hub
jobs or add real external API credentials/private repository mounts. No script
execution, model calls, schedules or harness/memory/PKM connections have been
qualified or created by deployment. Editor LSP/debugger/SMTP extras are absent.

## What is running

- Official Windmill **CE v1.823.1**, server and one worker, digest-pinned ARM64.
- Isolated official PostgreSQL **18.6**, no published DB port.
- Project/network: `mcp-stack-windmill-trial`, not the shared stack network.
- Container names: `mcp-stack-windmill-trial-db`, `mcp-stack-windmill-trial-server`,
  `mcp-stack-windmill-trial-worker`.
- Ceilings: PG512MiB/0.5CPU, server768MiB/0.5CPU, worker2GiB/1CPU. Total
  3.25GiB/2CPU is a limit, not measured idle consumption or a battery guarantee.
- Only host port: `127.0.0.1:58090`; bounded Docker logs10MiB/service.

Definition: `infra/windmill/compose.trial.yaml`. The root Compose entry point
does not include Windmill. **Never use bare `docker compose up` in
`infra/windmill/`**: it could select the original, broader upstream setup.

## Read-only status

From `/home/developer/workspace/mcp-stack` in Ubuntu:

```sh
macctl run docker ps -a --filter label=com.docker.compose.project=mcp-stack-windmill-trial --format '{{.Names}} {{.Status}} {{.Ports}}'
macctl run curl --noproxy '*' --fail --silent --show-error http://127.0.0.1:58090/api/version
```

PG and server have healthchecks. The worker's running state is not proof of job
execution. The owner can inspect worker status in the UI after logging in.
No permanent monitoring agent/recurring task was installed. Docker logs may
contain application data; inspect locally and redact before sharing them.
Do not print rendered Compose or inspect container environment for diagnostics.

## Stop and resume only this trial

These commands are **instructions, not actions already performed**. The owner
may choose when to run them; an agent must obtain scoped lifecycle approval.
Stop preserves all trial data and does not stop any other stack service:

```sh
macctl run docker stop mcp-stack-windmill-trial-worker mcp-stack-windmill-trial-server mcp-stack-windmill-trial-db
```

Resume existing containers without pulling, recreating or migrating:

```sh
macctl run docker start mcp-stack-windmill-trial-db
macctl run docker inspect --format '{{.State.Health.Status}}' mcp-stack-windmill-trial-db
# Run the next command only after the new trial DB reports healthy:
macctl run docker start mcp-stack-windmill-trial-server mcp-stack-windmill-trial-worker
```

Do not rerun `integrations/windmill/trial_setup.py`: it is a one-shot install
helper and refuses existing credentials/resources. No cleanup is required.
No volume/image pruning or `down -v`; removal needs an exact data-retention choice.

## Data, credentials and evidence

- New durable DB volume: `mcp-stack-windmill-trial-postgres-data`.
- New cache/log volumes: `mcp-stack-windmill-trial-worker-cache` and
  `mcp-stack-windmill-trial-worker-logs`.
- Original generated DB secret: `.secrets/windmill_trial_password`0600.
- Runtime URL: `infra/windmill/state/trial.env`0600, state directory0700,
  ignored by Git. Docker admins can inspect environment credentials; not a vault.
- Private install/verification evidence:
  `infra/windmill/state/install-li4tytgf/qualification.json` and private logs.
- All22 pre-existing containers retained their complete metadata. The first
  verifier falsely flagged unordered mount arrays; canonical comparison was
  corrected, regression-tested and reverified read-only. No reinstall/restart.
- 14 offline contract tests pass; UI/versionHTTP200; three processes running
  with zero restarts, PG/server healthy. No owner login or real jobs performed.

Named volumes are persistence, **not a backup**. Export/restore, version upgrades
and future shared-PG consolidation require separately scoped work. Existing
stack DB/{{mstack:CLIENT_REPO}} credentials, schemas and volumes were not reused or changed.

There is no next automatic setup step. Trial deployment is complete; use the UI
or stop it when you choose. [Approved scope/pins](WINDMILL-TRIAL-PROPOSAL.md).
