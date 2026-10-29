# WhoDB — selected database viewer

User selection2026-10-05 supersedes the pgAdmin recommendation. WhoDB is selected
for straightforward database browsing. Installed on retry2026-10-05: healthy at
http://127.0.0.1:58091/. Database login/inspection is not yet configured.

Reviewed [official installation guidance](https://docs.whodb.com/installation):
WhoDB supports Docker, binaries and desktop use. The Docker web service listens
on8080. Current documentation describes encrypted login sessions stored in SQLite
under its data directory, with `/data` persistence and a stable encryption key.
This is WhoDB's UI/session state, not a new PostgreSQL instance.

## Intended fit in this stack

- One container in Compose project `mcp-stack`; definition under `infra/whodb/`.
- Qualify/pin a specific official `clidey/whodb` version and ARM64 digest before
  installation. Do not copy upstream's mutable `latest` command into deployment.
- Bind a freshly checked macOS loopback port, not all interfaces. No host Docker
  socket, source-directory mounts or automatic connection to unrelated projects.
- Connect through an explicitly selected Docker network to the existing PG
  service using its internal hostname/port5432. `localhost` inside WhoDB means
  WhoDB's container, not PostgreSQL or the macOS host.
- Own session-data volume; encryption key in ignored, restricted runtime config.
  WhoDB can retain encrypted DB credentials, so treat its session data/key as
  sensitive. Credentials do not belong in the project policy or documentation.
- Start with a dedicated read-only database role. A viewer UI does not itself
  prohibit SQL writes: enforce grants in PostgreSQL. Do not automatically use
  administrator credentials or expose {{mstack:CLIENT_REPO}}/application secrets.
- No AI provider, cloud discovery, MCP registration or model setup needed to browse.

These choices were qualified for the completed deployment. The viewer image,
port, session volume and encryption key are installed; no database role or
authenticated connection was created.
The current project mock uses JSON artifacts and needs no DB viewer. Once a real
project database exists, a scoped WhoDB connection can inspect it independently
of Windmill. Use [the project runbook](PROJECT-SETUP-RUNBOOK.md) first.

## Initial installation attempt — historical, 2026-10-05

The initial attempt prepared the pinned0.134.0 Compose definition, but Docker Hub
layer-CDN downloads failed from the macOS engine and no runtime was created then.
See [installation record](WHODB-INSTALL-RECORD.md) for both attempts.

Installation completed on explicit retry; see the current result at the top of
[the installation record](WHODB-INSTALL-RECORD.md). Earlier failure notes are historical.
