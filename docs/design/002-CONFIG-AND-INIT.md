# Historical design — superseded 2026-10-16

The active design is [MSTACK-CONFIG.md](../MSTACK-CONFIG.md). Separate project
registries and example migrations below are historical and must not be replayed.

# Small config and project entry flow

Design paper + implemented foundation · 2026-10-07.

**2026-10-08 implementation update:** v3 adds typed `tools` overrides and shared
`infra/stack/connections.json`; project intent now derives the gateway registry.
`stack plan/apply/adopt` reconcile generated launch settings/runtime, preserve
unrelated projects, detect UI drift, and avoid writes/restarts on unchanged intent.
Credential references are supported; plaintext credentials are not. Qualification
remains separate, and Clock keeps its direct adapter. v2 is supported and source
backups preserved. See [current contract](../../infra/stack/README.md) and
[canonical handover](../HANDOVER.md). The v2 foundation below is historical where
inconsistent; it is not the current list of CLI commands.

The old Clock registry combined user choices, package pins, object IDs and setup
history. Keep its qualified binding evidence, but stop making the user edit it
for normal choices. Separate intent, bindings, and shared runtime definitions.

## Files and responsibility

| File | Owner | Content |
| --- | --- | --- |
| project `infra/stack.json` | User/harness | Six normal project choices |
| project `infra/stack.bindings.json` | Qualified adapters/harness | Resource IDs, private credential references, evidence paths |
| stack `infra/stack/presets.json` | Maintained stack config | Tool purpose/default sets and common boundaries |
| stack `infra/stack/models.json` | Maintained stack config | Model route status; no plaintext keys |
| component `infra/...` | Component setup | Versions, endpoints, runtime/Compose/launch configuration |
| `.agents/skills/stack-use/SKILL.md` | Harness workflow | Select/qualify/work/read-back/checkpoint/improve |
| `integrations/stack/` | Reusable source | CLI resolver/launcher and meaningful tests |

Clock's human config is now:

```json
{
  "version": 2,
  "project": "clock",
  "preset": "project",
  "model": "codex",
  "context": [],
  "jobs": "manual"
}
```

Change `context` to `["codegraph"]` for an actual source-structure need. This
selects the tool and makes doctor require its project binding; it does not start
containers or index code. Empty context means graph/memory candidates are off for
routine retrieval. `model: "local"` selects a model route, not model installation.
`jobs: "windmill"` introduces reviewed execution and requires a qualified binding.
Model routes are explicit: codex, local, deepseek. No paid fallback occurs silently.
The knowledge preset limits Anytype MCP to search/read/create/patch (4 tools),
reducing daily-task schema overhead; the project setup preset retains collection
operations. Codex built-in tools still contribute context and require model testing.

## CLI implemented now

Run the repo-local `./stack`; no global command or PATH/profile edit is required.
From another project, use its absolute path or invoke through the skill.

```sh
./stack init examples/new-project --preset project
./stack plan --project examples/new-project
./stack doctor --project examples/new-project
./stack run --project examples/clock --inspect
./stack run --project examples/clock
```

`init` writes config, empty project bindings, a discovered project skill and an
AGENTS reference. It preserves existing instructions and refuses existing v2
files. No service start, remote creation, credential copy, Git repository init
or model download. New Anytype projects therefore begin unbound. The stack-use
skill operates the subsequent qualification for an authorized project setup;
file initialization alone does not create a channel.

`plan` expands defaults into concrete tool purposes and proposed resource names.
`doctor` reports local binding/evidence/model-route readiness, returning 2 while
pending. It is not a health probe or proof that an app is running right now.
`run --inspect` resolves Codex's project overrides without inference; `run` launches
Codex with them for this invocation. Inherited MCP registrations are disabled
for that invocation. Global Codex settings/login and the current desktop chat
remain unchanged. Only qualified model routes can be launched.

Clock uses `legacy_registry: infra/mcpstack.config.json` in its new binding file.
This reuses its actual IDs/key/qualification without copying access to another
repo. The legacy file remains supported as runtime evidence. New project bindings
must carry their own project ID; another project's file is rejected.
The root project still has no Anytype binding and must not reuse Clock's key.

## Prompt flow

The user can say: “Use stack-use to start this project, with Anytype docs and tasks.”
The harness resolves the directory, selects `project`, performs file initialization,
shows the minimal tool selection, then creates/binds the authorized project
channel and its collections. Use the already-qualified MCP or native UI fallback;
keep the new key private and restricted to that channel. Qualify live discovery,
read/write/read-back and collection membership before marking the binding ready.
The harness does the setup; the user is not asked to type object IDs into JSON.

For “fix this small source file,” select `solo`; don't create a PKM destination
without a reason. For “use local inference for today's notes,” select `knowledge`
only after its model and tool-call round trip are qualified. Report missing
capability instead of secretly promoting the request to a paid provider.

## Isolation contract

Same project ID links separate stores; it is not itself a storage system or RBAC.
Anytype holds canonical docs; source stays in Git/files; Garage holds objects;
application DBs hold application internals; memory/graphs hold derived context.
Sharing happens through explicit references and scoped credentials, not one
writable directory mounted into every tool.

Each binding must document resource ownership and a denial test: Space grant,
workspace/resource permissions, DB login/grants, bucket credentials, and index
scope. A label/prefix-only boundary is marked as such. The loader can reject a
mislabelled binding file; it cannot make a permissive backend multi-tenant.
No broad service cleanup or project-wide Compose lifecycle is part of init.

## What remains designed, not implemented

A generic `stack bind` wizard, universal cross-tool provisioning, model downloads,
background change watching, project-wide service start/stop, billing quotas and a
container bundle are not implemented. These add operating cost and should follow
a real example. Currently Clock's direct MCP adapter is qualified; other tools
must use their reviewed setup/adapter and record evidence before selection is ready.

The practical next CLI addition is a narrow Anytype binding wizard, followed by a
model qualification command. They solve repeated friction without inventing an
all-tools deployment platform. A global `stack` shell alias is optional future
convenience and requires explicit global-config authorization.
