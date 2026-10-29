# WhoDB viewer installation — 2026-10-05

## Retained-state recovery — 2026-10-09

The user requested restoring the absent container/image. The same pinned version
was pulled and only `whodb` recreated, reusing the retained data volume and
encryption key after an offline backup. Health, UI and three assets pass; no
PostgreSQL login or grants were added. See [the recovery report](SERVICE-RECOVERY-2026-10-09.md).

## Completed on retry — 2026-10-05

User explicitly requested continuation in the side chat. The same pinned0.134.0
ARM64 image downloaded successfully; container `mcp-stack-whodb` is healthy in
Compose project `mcp-stack` at http://127.0.0.1:58091/. UI and two local JavaScript
assets return200. All24 other containers retain baseline metadata. Existing DB
permissions and services unchanged. New session volume/key prepared as specified.
No PostgreSQL login or application data access performed. Evidence:
`infra/whodb/state/resume-result.json`. The earlier network failure below is
historical. An initial asset check incorrectly required absolute paths; adjusted
verification to resolve the application's relative asset URLs, without app changes.
Rollback remains the scoped stop/remove commands below, preserving data/key.


User explicitly requested “install whodb first” after selecting the proposed
containerized viewer. Scope: viewer only on existing macOS OrbStack Docker via
`macctl run`; no DB roles/grants, credential reuse, model calls or registrations.

## Qualified target

Official `clidey/whodb:0.134.0`, GitHub release2026-09-30, source tree
`e8693ecf4c3b8b81cd005d01beec349526ea0c57`. Registry metadata verified:

- Image index `sha256:040e47c5d3c5b7616d731771af90ce3594a3e92786ba01ef30b3aa12088e321f`.
- ARM64 manifest `sha256:7b005cd883de0de7ab74efd958fcc13c972eac41bd221ef6c31c6169c513e9c2`.
- ARM64 compressed layers67,407,161 bytes; actual storage larger.

Tagged `core/Dockerfile` uses Alpine, starts `/core`, and declares `/data` for
session persistence. Tagged session-key code accepts a64-hex-character env key.
Some metadata HTTP requests stalled/failed; these performed no installation and
were stopped. Registry manifest and tagged source checks subsequently succeeded;
no vulnerability scan or external database authentication claim.

## Files, port, state and commands

- `infra/whodb/compose.yaml`; Compose project `mcp-stack`, service `whodb`,
  container `mcp-stack-whodb`; port `127.0.0.1:58091:8080`.
- Volume `mcp-stack-whodb-data` at `/data`;64MiB tmpfs at `/tmp`.
- Private generated key in `infra/whodb/state/runtime.env`0600, parent0700;
  variable `MCP_STACK_WHODB_ENCRYPTION_KEY` becomes `WHODB_ENCRYPTION_KEY`.
  It is a session-encryption key, not a PostgreSQL password.
- Existing external `mcp-stack-memory` network; DB reachable as
  `mcp-stack-postgres-1:5432`. This also grants network reachability to existing
  services there, not database authorization. No database credentials preloaded.
- Read-only root filesystem, capabilities dropped, no-new-privileges, no host
  bind mounts or Docker socket;512MiB/0.5CPU ceilings and bounded logs.
- `PORT=8080`, `WHODB_LOG_LEVEL=info`, `WHODB_DATA_DIR=/data`,
  `WHODB_DISABLE_UPDATE_CHECK=true`, `WHODB_DISABLE_MOCK_DATA_GENERATION=true`.
  No AI/cloud configuration. Plain loopback HTTP; Secure-cookie flag unset.

```sh
macctl run docker pull --platform linux/arm64 clidey/whodb:0.134.0@sha256:040e47c5d3c5b7616d731771af90ce3594a3e92786ba01ef30b3aa12088e321f
macctl run docker compose -p mcp-stack --env-file infra/whodb/state/runtime.env -f infra/whodb/compose.yaml config --quiet
macctl run docker compose -p mcp-stack --env-file infra/whodb/state/runtime.env -f infra/whodb/compose.yaml up -d --no-deps --pull never whodb
```

Preflight: fresh container/volume/key paths, no port58091 listener, exact cached
or pulled image identity, record all existing container and volume metadata.
Qualification: health, UI/assets, expected mounts/port/network, private key mode,
new session store and unchanged unrelated resources. No owner login or DB data
read is necessary for this viewer deployment. Stop on errors rather than broad
cleanup, silently changing image, or granting new privileges.

Scoped rollback if requested:

```sh
macctl run docker stop mcp-stack-whodb
macctl run docker rm mcp-stack-whodb
```

Preserve volume/key to resume with the same sessions. Full removal can delete only
`mcp-stack-whodb-data` and its private key after explicit data-deletion approval;
this would invalidate sessions, not remove any PostgreSQL database. Never use
project-wide `down`, `--remove-orphans` or a Docker prune.

Sources: [release](https://github.com/clidey/whodb/releases/tag/0.134.0),
[tagged Dockerfile](https://github.com/clidey/whodb/blob/0.134.0/core/Dockerfile),
[installation docs](https://docs.whodb.com/installation).

## Initial failed attempt — historical, superseded by completed retry above

**At this initial attempt, installation was blocked at image download.** Two bounded Docker
pull attempts failed while fetching image data from
`production.cloudfront.docker.com` (EOF). An independent macOS curl request to the
same official CDN failed TLS negotiation (exit35); a direct Ubuntu probe also
failed. The official release publishing workflow offers Docker Hub and no
alternate release container archive was found. No mirror/substitute image or
system proxy/security configuration was used.

Compose validation with a synthetic key passed. All24 existing containers and
all existing volumes match the pre-attempt metadata. No WhoDB container/volume,
encryption key, database account or credentials were created. Docker may retain
partial download cache; no broad image/cache cleanup was performed.

Private evidence: `infra/whodb/state/install-aq47cj4d/`, including redacted-scope
metadata, pull error and result JSON. Some error logs include temporary public
registry download URLs; do not publish raw logs. The first failed pull was not
captured; the second failure is recorded.

To resume, first verify the macOS Docker engine can download from Docker Hub's
layer CDN, then retry the same pinned image under the existing user authorization.
Recheck port/name collisions before generating a fresh64-hex session key in
`infra/whodb/state/runtime.env`0600 (directory0700) under the variable named above,
then run the scoped validation/start commands. Never run Compose without the
required generated secret or assume this record proves UI availability.

Stop at a healthy viewer and report its URL; PostgreSQL login/grants and user
project setup remain separate. The user may run the JSON-only project runbook
while the registry download is unavailable.
