# Windmill

Primary workflow choice as of2026-10-05. Shared-PG replacement is installed and healthy; the trial runtime/data is removed.

Restored and verified 2026-10-09 with its retained database, credentials and
cache/log volumes. Current pin is the original 1.823.1 ARM64 manifest; its
executable layers are unchanged. See [the recovery report](../../docs/SERVICE-RECOVERY-2026-10-09.md).

- [Everyday guide](../../docs/START-HERE.md)
- [Completed shared-PostgreSQL replacement](../../docs/WINDMILL-SHARED-PG-PROPOSAL.md)
- [Historical trial runbook](../../docs/WINDMILL-TRIAL-RUNBOOK.md)
- [Upstream self-host guide](https://www.windmill.dev/docs/advanced/self_host#docker)

Use [the current runbook](../../docs/WINDMILL-RUNBOOK.md).
`compose.yaml` defines the running deployment under Compose project `mcp-stack`;
`compose.shared.yaml` retains the historical standalone grouping. `provision-shared.sql`
has already been applied; do not rerun it.
`compose.trial.yaml`, downloaded `docker-compose.yml`, Caddyfile and existing
assets remain for reference. Always select a Compose file explicitly; never use
bare `docker compose up` in this directory. No root Compose inclusion was added.
