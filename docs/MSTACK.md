# mstack: start with the work

The everyday channels are **Codex/Claude, Anytype, and Windmill**. mstack is the
small project configuration and skill layer connecting them. The default selects the qualified shared Graphify, Headroom, Anytype and Windmill
routing. Use tools when relevant; selection does not run a pipeline.

**[Configuration diagrams and the one-field project config](MSTACK-CONFIG.md)**
explain defaults, credentials, harness discovery and runtime connections.
The Docker Compose namespace is now `mstack`; stable container/data names remain.

## Daily presets

| Preset | Use |
| --- | --- |
| `daily` | Current direct shared workflow: Headroom, Graphify, Anytype and Windmill; gstack browser available |
| `build` | Harness plus the existing gstack browser |
| `notes` | This project's qualified Anytype channel/key |
| `automate` | A reviewed Windmill job |
| `proof` | Explicit configuration, gstack, Headroom, Graphify, Windmill and Anytype proof |

Create projects outside this infrastructure repository:

```sh
/home/developer/workspace/mstack/mstack init /home/developer/workspace/my-project --preset daily
cd /home/developer/workspace/my-project
/home/developer/workspace/mstack/mstack discover --project .
```

The default `.mstack/stack.json` is just `{"project":"my-project"}`.
New projects must register and qualify their own grants; `doctor` reports missing
bindings until then. Use `solo` for a deliberately harness-only task.

`AGENTS.md` points to the project's `.agents/skills/mstack/SKILL.md`.
`.mstack/stack.json` chooses capabilities; `.mstack/state.json` records
qualified connections. Init only creates files. `plan`, `discover` and `doctor`
make no remote calls and never install or start services. Direct projects do not
need the gateway registry or another project's files.

## Tool delivery

Use an actual harness-provided capability when present. Otherwise, use a shared
containerized backend with a project tenant. A skill alone is not an engine.
Existing Headroom and Serena helpers are preserved in the harness; gstack provides
installed work skills/browser. Graphify's native MCP runs in `mstack-graphify`:
each project gets a separate index and authenticated session. Anytype uses
`mstack-anytype-mcp` with a separate channel credential per tenant. Additional
projects do not create additional tool containers. CodeGraph is ignored for now.
Headroom now also has a shared `mstack-headroom` service with separate tenant
caches; projects select it through their own qualified binding. Existing global helpers remain.
See [shared services and tenant onboarding](../infra/services/README.md).
For the technical connection flow and optional-memory/gateway decision, read
[how the harness reaches your tools](HARNESS-CONNECTIONS.md).

```sh
./mstack services status
./mstack tenant list
./mstack services stop graphify
./mstack services start graphify
```

Stopping a shared service affects all its tenants; data and credentials remain.
Tenant registration does not automatically index, start services or grant access.

[gstack](https://github.com/garrytan/gstack) supplies planning, review, browser QA,
documentation and shipping skills. **mstack chooses project tools and access;
gstack supplies a work method; the harness performs the work.** Headroom compresses
selected output and can retrieve the original; it does not automatically compact
an entire chat.

## Example retirement

The user requested retiring the examples on October 16. Their local projects,
shared tenants, Anytype grant and Windmill workspace/tokens are removed. See the
[retirement record](../infra/maintenance/config-retirement/README.md) for verified status.
Historical qualification receipts describe past checks, not a currently runnable demo.
Create a real independent project when there is a concrete task.

## Background operation

Use APIs, containers and isolated headless browsers while the user uses the Mac.
Native setup requires an explicitly arranged quiet window. Ordinary qualified
Anytype reads/writes use the background API. No automatic memory mirror or schedule.

## Retained infrastructure

Graphify, Headroom and Anytype MCP remain shared reusable containers in the
`mstack` Compose group. Each new project needs its own explicitly qualified tenant.
CodeGraph remains ignored; its absent historical container was not restored.

`mstack-anytype-mcp` runs the official Node-based MCP adapter. The harness
starts its stdio process through `docker exec`; between connections its container
is idle. It calls the native Anytype app's existing local API on port 31009, and
publishes no HTTP port or separate document database. The app remains the backend.

Garage was found stopped and resumed in the same container on October 16. Its
S3 endpoint is Mac loopback `http://127.0.0.1:53900`, or
`http://mcp-stack-garage:3900` on the existing client networks. Health and signed
read-only S3 checks pass. Application storage requires an explicit bucket/key
binding; removing examples does not remove shared Garage storage.
See [Garage's resume receipt](../infra/garage/resume-20261016.json).

Magpie, Llama.app, PostgreSQL + pgvector, WhoDB, Garage and other retained
non-mail components are preserved. OrbStack and mise remain protected. Windmill's
existing server and worker were resumed for this exercise; no database was reset.
The shared Graphify and Anytype MCP containers reuse pinned images. Service
definitions and lifecycle notes are in [the shared service guide](../infra/services/README.md).
`stack` remains a compatibility alias; operational paths remain stable and the
Compose name is `mstack`. OpenCodex was removed on October 21; Claude Desktop
uses Magpie and Codex integration stays pending. DeepSeek provider is a model API;
DeepSeek Harness is a separate application.
