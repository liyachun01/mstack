# WhoDB viewer

Definition: `compose.yaml`, Compose project `mstack`, service `whodb`.
Use [the installation record](../../docs/WHODB-INSTALL-RECORD.md) for actual status.
Recovered and verified 2026-10-09 using its original data/key and pinned image;
see [the recovery report](../../docs/SERVICE-RECOVERY-2026-10-09.md).
Do not use bare Compose, project-wide `down`, or `--remove-orphans`.

Resumed again on 2026-10-16 at the user's request, in the original container.
Container health, the UI and its JavaScript asset pass; the original data volume
and encryption configuration are preserved. No database connection was added.
See [the resume receipt](resume-20261016.json).

The UI is intended at macOS `http://127.0.0.1:58091/`. PostgreSQL connection fields
inside this Docker deployment are:

- Type: PostgreSQL
- Host: `mcp-stack-postgres-1`
- Port: `5432` (container port, not the macOS published55322)
- Database: the specific existing database you intend to inspect
- User/password: a database login authorized for that database, entered privately

WhoDB does not grant database access itself. No PostgreSQL credentials are
preloaded and no read-only inspection login has been provisioned by this viewer
installation. Read-only access requires a scoped PostgreSQL role; do not assume
a UI connection made with an application owner/superuser is read-only.
The runbook's mock project uses JSON, so its proposed database does not yet exist.

Session state is held in `mcp-stack-whodb-data`; the encryption key comes from
ignored `state/runtime.env`0600. Preserve both across upgrades. Neither is a
backup by itself. An offline volume/key backup was verified during October 9
recovery; restore into an isolated target remains untested. No AI provider/cloud
discovery/MCP integration is configured.
