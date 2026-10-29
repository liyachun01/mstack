# Shared services, project tenants

Compose namespace: **`mstack`**. [Configuration diagrams](../../docs/MSTACK-CONFIG.md)
and [namespace migration](../../docs/MSTACK-NAMESPACE.md) are the current reference.

One service container serves multiple projects. Project configuration selects a
tenant; adding a tenant does not add, recreate or restart a container.

| Capability | Shared runtime | Project boundary |
| --- | --- | --- |
| Graphify | `mstack-graphify`, Graphify 0.9.72 | Separate graph index and authenticated session per tenant |
| Anytype MCP | `mstack-anytype-mcp`, official adapter 2.0.1 | Separate channel-only API key per tenant; native Anytype remains the backend |
| Headroom MCP | `mstack-headroom`, Headroom 0.34.0 | Separate SQLite cache/statistics and authenticated session per tenant |
| Windmill | Existing server + worker | Workspace and restricted script/API tokens |
| Garage | Existing `mcp-stack-garage` | Explicit bucket/key permissions when a project needs storage |
| PostgreSQL + pgvector | Existing shared PostgreSQL | Explicit database/role grants when needed |

Serena and gstack remain available through existing harness/tooling. Existing
Headroom helpers are preserved; a project's explicit shared binding takes
precedence when selected. No per-project installation. CodeGraph is ignored for now.
WhoDB remains an administration UI, not a tenant isolation boundary.

## Daily operation

Run from this repository:

```sh
./mstack services status
./mstack tenant list
./mstack services stop graphify
./mstack services start graphify
# The same start/stop commands accept: anytype, headroom
```

Start/stop operates only the named shared service. **Stopping it disconnects all
its tenants.** Indexes and credentials survive in ignored `state/`; Anytype
documents remain in the native app. Start reuses an existing container, or creates
the one shared service from the existing pinned image if absent. It never pulls
or builds images. Nothing automatically starts during project discovery, doctor,
or a harness session. Native Anytype must be running for its API to work.

Use [compose.yaml](compose.yaml) for these three services. Never use project-wide
`down` or `--remove-orphans` against separately managed mstack overlays.
Windmill and Garage keep their existing service-specific runbooks/lifecycle.

## Add a project when it needs a tool

First initialize the independent project with `mstack init`. Its one-field `.mstack/stack.json` inherits the daily shared
workflow; use explicit overrides only for exceptions. Then register its own data/grant:

```sh
./mstack tenant add --project /path/to/project-a --tool graphify --graph /path/to/approved/graph.json
./mstack tenant add --project /path/to/project-a --tool anytype
./mstack tenant add --project /path/to/project-a --tool headroom
```

Graphify registration imports an existing approved index without extracting code,
running a model, mounting the repository or broadening its corpus. Index creation
and refresh are explicit scoped work using the containerized engine; registration
does not provide an automatic watcher. The imported index is a snapshot. Replacing
it requires updating its registered hash and requalifying affected proof receipts.

Anytype registration requires that project's own `.mstack/stack.json` Anytype section,
`.mstack/anytype/openapi.json` and private channel credential under `.mstack/secrets/`.
It does not create channels or borrow another project's grant. Every session
verifies the native API reports exactly the registered channel, read/write access
and `all_spaces: false`. Duplicate channel registration is refused.

Headroom registration creates a private cache namespace without importing any
other session's content. Its native SQLite cache preserves originals across
connections and service restarts within the one-hour MCP TTL. The three tools
compress, retrieve and report statistics; no automatic model proxy is configured.
See [Headroom's guide and live evidence](../headroom/README.md).

Registration updates `tenants` in `.mstack/state.json` and a separate private 0600 token
per tool under project `.mstack/secrets/`, and adds `/secrets/` to
`.mstack/.gitignore` before creating credentials. Server state stores token hashes and tenant
data under `infra/services/state/<tool>/tenants/<project>/`. Keep `.mstack/secrets/` out
of Git and never paste credentials into project config, command arguments or docs.
An existing or partially registered tenant is preserved, not overwritten.

Registration alone is not a qualified harness binding. The project MCP command is:

```sh
python3 /home/developer/workspace/mstack/integrations/tenants/launch.py --project /path/to/project-a --tool graphify
```

Use `--tool anytype` for documents or `--tool headroom` for compression. Put that command/argument array in the
project's generated state `bindings.<tool>.mcp` entry with `provider: container`,
`tenancy: shared`, its project slug in `tenant`, and the shared container name.
Keep it pending until a real query/read-back and scope rejection are saved in
the project's `.mstack/evidence/`; then qualify the binding and use the normal
project-only `mstack run` workflow. Global MCP registration is unnecessary.
For Anytype/Windmill, record the current `project_state.connection_fingerprint`
with qualification. Never mark a binding qualified from registration alone.

## Access model

The launcher sends a tenant name and private token over stdin to the shared
container. A native stdio MCP process serves each connection. It is idle between
connections and publishes no HTTP port. Graphify's session is fixed to one index;
project selectors, write tools and foreign resource paths are rejected. Graphify
has no network and sees only graph tenant state. Anytype sees only its own tool's
tenant state and calls the existing desktop API. No new document backend exists.
Headroom has no network, source mounts or file-read tool; tenant state contains
its compression cache and statistics. Native SQLite initialization must succeed
before the session starts, so it cannot silently fall back to a volatile cache.

This is mstack's authenticated adapter around the pinned tools, not a claim that
upstream Graphify supplies native tenant RBAC. The local Docker owner and service
administrator are trusted: someone with Docker/filesystem control can bypass the
MCP boundary. Tenant registration changes affect new sessions; disabling a tenant
does not revoke an already established session. There are no per-tenant resource
quotas. These boundaries suit the owner's projects, not hostile public tenants.

## Verification

The former example and its tenants are retired. Dated [qualification evidence](qualification.json)
and [Headroom checks](../headroom/qualification.json) describe the earlier isolation,
readback and restart checks; they do not assert a live example still exists.
Shared containers and unrelated service data remain. See the
[retirement record](../maintenance/config-retirement/README.md).

Local regression checks:

```sh
python3 -m unittest discover -s integrations/tenants/tests -v
python3 -m unittest discover -s integrations/stack/tests -v
macctl run sh -c 'docker exec mstack-anytype-mcp node --test /integration/tests/anytype.test.mjs'
```

The retired example's live acceptance helpers are removed. Unit tests use
isolated synthetic fixtures; they do not recreate example projects or grants.
