# mstack project configuration

Each project edits `.mstack/stack.json`; `{"project":"my-project"}` selects daily.
Generated records live together in `.mstack/state.json`. Private credentials
live under project `.mstack/secrets/`. The older project config/binding/tenant/runtime
files are retired. See [field reference and diagrams](../../docs/MSTACK-CONFIG.md).

```sh
./mstack init /path/to/my-project
./mstack plan --project /path/to/my-project
./mstack doctor --project /path/to/my-project
./mstack run --project /path/to/my-project --inspect
```

Init is file-only and grants no access. Daily selects shared Headroom, Graphify,
Anytype and Windmill with existing gstack browse. It does not invoke them all.
Use solo/build/notes/automate for explicit smaller selections. CodeGraph is ignored.

| Shared file | Purpose |
| --- | --- |
| `presets.json` | Available tool/workflow defaults |
| `models.json` | Existing model routes and qualification status |
| `helpers.json` | Installed helper locations, without auto-installation |
| `connections.json` | Optional gateway connector catalog |
| `project-index.json` | Registered gateway project paths |
| `state/` | Private gateway reconciliation ledger |

These files belong to the shared infrastructure repository. New projects do not
copy them or other projects' credentials. Project state sections are `bindings`,
`tenants`, `documents`, `runtime`, `launch`, and `proofs`. Tenant registration and
qualification maintain them; the intent file contains no observed object IDs.

## Optional gateway path

Direct daily projects do not consult the gateway registry. Their `apply` only
maintains local state; `run` builds invocation settings without global edits.
A project selecting `tools.<provider>.connection` opts into gateway reconciliation.
Gateway `projects.json` is a generated compatibility snapshot; `projects.bindings.json`
records shared gateway qualification. Neither is a second project intent.

Named connections support Slack, Linear, Figma, optional Notion and Anytype.
Advanced `url`, `credential_file`, `input`, `space` and `access` overrides require
qualified scopes. Gateway credentials remain in this stack repository’s existing `.secrets/`.
Top-level direct `anytype`/`windmill` credential references are relative
to the consumer project. Unknown fields and inline credentials are rejected.

Gateway `apply` resolves registered project intents, preserves other projects and
owner UI additions, generates missing caller credentials, and updates `launch` in
project state. Provider OAuth/grants are never provisioned automatically. Changed
runtime config recreates only the existing agentgateway service, with a private
backup, verification and rollback. Pending providers stay closed. Unchanged apply
is a no-op. Never use project-wide down or orphan removal.

Owner UI edits cause drift. Review `plan`, then use `adopt` for supported logging
and separate owner listeners, or explicitly `apply --drift restore` for a reviewed
config restoration. Do not edit the owner UI concurrently with apply. The gateway
is currently retained but stopped; routine daily work does not start it.

The retired examples and their credentials must not be restored from historical
backups. See [retirement evidence](../maintenance/config-retirement/README.md).
Model/provider calls and global harness registration remain separate operations.
