---
name: mcp-stack-setup-guard
description: Safely plan and operate the mcp-stack across the macOS OrbStack host and its Ubuntu development machine. Use for every install, setup, update, removal, service lifecycle action, MCP registration, database migration, or toolchain change in this repository.
---

# MCP Stack Setup Guard

## OpenCodex removal completed — 2026-10-21

The user subsequently requested removing OpenCodex. This supersedes all older
OpenCodex retention/rollback instructions in this skill. Its stopped container,
two dedicated volumes, unused image, credentials, setup files and old native
Claude profile are removed, including dedicated credential/profile backup copies
and Magpie's old applied-profile stash pointer. Do not restore or reinstall it.

Claude Desktop still uses Magpie/official DeepSeek; Codex integration is pending
explicit request. Native Codex config/auth and the active Magpie profile/provider
are unchanged. All 31 other containers present at removal and unrelated data are
preserved. The old custom Codex project routes remain unbound; no Magpie binding
is inherited. Use `integrations/models/magpie_manage.py` for local operations;
the one-time migration helper is retired. No new quiet UI window is active.
See `infra/maintenance/opencodex-retirement/README.md` for exact targets and proof.

## Magpie migration — 2026-10-21

The user explicitly authorized moving Claude from OpenCodex to Magpie, leaving
Codex integration pending until requested. Installed Claude Desktop 3.1623.0 now
uses installed Magpie 0.1.1206 and the existing official DeepSeek Flash key.
This supersedes historical Magpie exclusion and Claude-through-OpenCodex guidance.
No Claude Code CLI was installed. Mac and Ubuntu Codex config/auth are unchanged;
do not connect Codex, discover/refresh native accounts, or alter its MCP bindings.

Read `infra/magpie/README.md` and its qualification receipt. Public intent/private
Magpie state remain under `infra/`; native config/cache links discover that state.
Claude's generated profile library is a native Mac directory because OrbStack
rejects Magpie's atomic metadata writer. Its old OpenCodex profile is preserved.
The background gateway/management bind Mac loopback 3425/3430, without login
autostart. Provider keys and management login keys remain private. The gateway
caller marker is not a secret authentication boundary. No automatic fallback,
update, account discovery or request archive is enabled.

Three synthetic requests passed streaming and automatic tool/result handling.
The native window was not opened; no Desktop UI, Code/Cowork, or project MCP
qualification follows. Background-only preference remains. All 33 containers are
unchanged; OpenCodex stayed stopped with its config/volumes/credentials retained.
Use the documented launcher; migration operations and paid probes are not health
checks. No pending Codex action may be inferred from Claude's completion.

## Project folder and example retirement completed — 2026-10-16

The user requested all project-specific mstack metadata in root `.mstack/`.
The sole editable intent is `.mstack/stack.json`; generated bindings, tenants,
document IDs, runtime details, launch settings and proofs share `.mstack/state.json`.
Project credentials belong in `.mstack/secrets/`; optional schemas, evidence and
helper/browser cache also live under `.mstack/`. Its `.gitignore` protects generated
and private files. New-project init creates no `infra/` directory. Old project
configuration paths and readers are retired; do not recreate them.

This explicitly supersedes older instructions requiring consumer project config
under `infra/`. Shared infrastructure Compose/catalog/state and existing service
credentials retain their current paths. Harness discovery stays in AGENTS.md and
`.agents/skills/`; human-readable project documents stay in `docs/`. Direct apply
is file-only; explicit named gateway connections retain reconciliation. See
`docs/MSTACK-CONFIG.md` and `infra/maintenance/config-retirement/README.md`.

External mstack-example, in-repo project-a/project-b and portfolio-demo are removed,
along with their three shared tenants, example state copies and gateway placeholder
routes/keys. The Anytype example channel/documents are deleted and its key is revoked
(HTTP 401). Other Anytype grants are preserved. Following explicit permission to use
Windmill's documented initial administrator login, the example workspace and its
two matched tokens were removed. Other workspace IDs are unchanged. Follow-up
confirmed absence and session revocation (HTTP 401); temporary credential files
are removed. No example cleanup or permission request remains pending.

Keep all containers and shared infrastructure. No lifecycle operation follows from
this cleanup. The current layout passes 83 Python tests; five Node adapter tests
passed in the preceding retirement step. Historical example proof receipts do not
describe a currently runnable project. Do not recreate demos or restore revoked
credentials. OrbStack/mise, retained harnesses and unrelated data remain protected.

The quiet UI window ended after Anytype deletion/revocation. Return to background
APIs/containers/headless browsing; no further foreground permission is implied.
This section supersedes older instructions to use or preserve the example configs.


## Minimum defaults and Docker namespace — 2026-10-16

The user made the current shared routing the minimum default and requested the
Docker namespace rename. `infra/stack.json` now needs only a stable `project` ID;
omitted version/preset resolve to v3/daily. Daily selects Codex, shared Headroom,
Graphify, scoped Anytype and Windmill, with the existing gstack browser available.
Selection is not a mandatory tool sequence or provisioning. New projects still
need their own qualified tenants/grants. CodeGraph stays ignored; no memory mirror,
schedule, provider call or global harness configuration change follows.

Docker Compose project is now `mstack`, superseding older namespace instructions.
The 11 existing services were recreated with the same pinned images, credentials,
ports, persistent mounts and resource settings: nine running, ai-memory and
agentgateway stopped. All 19 unrelated containers are unchanged. Stable container,
volume and network names retain `mcp-stack` where needed for compatibility; the
repository path and project identities are unchanged. Explicit external volumes
and networks prevent replacement data allocation. PostgreSQL's obsolete reference
to the removed mail-only network was repaired through its current definition;
do not restore that network or reuse the original stale container definition.

Use `docs/MSTACK-CONFIG.md` for diagrams and `docs/MSTACK-NAMESPACE.md` for migration
evidence. The external example now has a one-field intent and its existing grants.
The infrastructure root uses explicit `solo` because it has no Anytype grant.
Use `mstack run` for direct Codex bindings; `apply` remains gateway reconciliation.
No project-wide down/remove-orphans. Historical migration helpers are not health
checks or startup commands. Only relevant work should trigger actual tool calls.


## Shared Headroom and WhoDB resumed — 2026-10-16

The user requested shared Headroom and starting WhoDB. `mstack-headroom` now
runs pinned Headroom 0.34.0 / MCP 1.29.0 with separate authenticated tenant
SQLite caches/statistics. The external example selects its shared binding;
existing global helpers/configuration remain unchanged. Native compression,
concurrent tenant isolation, foreign-hash rejection, reconnect and exact
retrieval after shared stop/start pass. Originals expire after one hour.
No network, model/provider calls, file-read tool or automatic traffic proxy.
Four example Anytype documents are saved/read-back verified, including the new
Headroom note. Other projects must register their own tenants explicitly.

WhoDB is healthy at Mac localhost:58091 after starting its original container,
preserving its volume and encryption settings. No DB connection was added.
All 28 other pre-existing containers stayed unchanged; only Headroom was added.
ai-memory and agentgateway are optional for the current direct-MCP workflow;
leave their existing state alone. CodeGraph remains ignored. See
`infra/headroom/README.md`, `infra/whodb/resume-20261016.json` and
`docs/HARNESS-CONNECTIONS.md`. Shared service stop affects all its tenants.


## Shared services and project tenants — 2026-10-16

The user requires one reusable container per tool, with project tenants inside
it, rather than `example-[tool]` containers. `mstack-graphify` and
`mstack-anytype-mcp` now serve authenticated project sessions. The external
mstack-example project is migrated; its old two containers are removed. The
Graphify index was copied byte-for-byte without reindexing. Anytype retains its
own channel/key; three documents have verified read-back. Two temporary Graphify
tenants passed concurrent isolation checks in the same running container and
were removed. Shared stop/start preserves tenant state. All 27 unrelated
containers retain IDs, start times, images and mounts.

Use `infra/services/README.md`, `infra/services/compose.yaml` and the tenant
commands. Project `infra/stack.tenants.json` selects its own private credential;
never reuse another project's grant or create a container per project. A tenant
registration is not automatic indexing or a qualified harness binding. Shared
service stop affects all tenants. The Docker owner/admin remains trusted; this
is an authenticated MCP boundary, not hostile-public-tenant isolation. Windmill
keeps its existing workspaces; Garage keeps explicit bucket/key grants. No new
S3 binding exists. Headroom/Serena/gstack and protected system tools remain.

Ignore CodeGraph for now: do not restore, install, index or convert it. This
supersedes previous per-project container guidance. No provider/model call,
automatic memory mirror, schedule or global harness configuration change ran.
The six-stage proof includes fresh shared-service/configuration checks and
explicitly carried-forward evidence for unchanged gstack/Headroom/Windmill.


## mstack and current daily policy — 2026-10-16

Use `mstack` and `.agents/skills/mstack/SKILL.md`; `stack` is compatible.
The default is daily, with build/notes/automate selected for actual requirements.
The old mstack-demo was explicitly removed, including its revoked key and deleted
Anytype channel. Its replacement is outside this repo at
`/home/developer/workspace/mstack-example`. Use actual harness capabilities first,
then dedicated containers for missing selected tools. The Graphify container and
Windmill job/MCP are qualified. The dedicated Anytype MCP 2.0.1 container and new
channel-only read/write key are qualified; both documents were saved/read back.
All six proof stages pass. No grants are copied.

The user is using the computer: background APIs, containers and isolated headless
browser only. No app activation, desktop input, window moves or display changes.
Foreground onboarding requires a user-arranged quiet slot or manual setup. The
user offered that slot on October 16, authorizing the now-completed Anytype setup
and superseding the earlier interference rejection for that setup only. Return
to background operation. Reports are saved evidence, not uptime.
No automatic Anytype memory mirror or follow-up refresh is required. The latest
three-channel policy supersedes the older memory-refresh instructions below.
Preserve operational paths/Compose names and all retained non-mail resources.


## Authorized helper drain completed — 2026-10-15

The user's later request explicitly authorized temporary fnm/uv helper downtime.
This supersedes the same-day legacy-store retention below: 16 verified MCP trees
/ 44 helpers stopped cleanly; Codex stayed running. Existing bindings reconnected
through the supported runtime reload API. Headroom/Serena are connected in all
10 loaded sessions; no global config/auth or model/provider/mailbox test changed.

146 existing Python environments now use mise Python 3.13.15, with packages
preserved and execution verified. DeepSeek's 430 profile links now target exact
project dependencies at ignored `infra/harnesses/deepseek/runtime/profile-packages/dsh`.
Its settings/auth and 96 pre-existing broken links are unchanged. No normal
profile startup, Web/forwarder or inference ran. Preserve that dependency copy.

Original fnm and old uv interpreter home paths are absent; private quarantine
and verified archives provide rollback. Zero old-runtime processes remain.
Keep uv tools/cache: these hold applications now using the mise interpreter,
not an obsolete competing runtime. Do not delete application environments as
duplicate toolchains. 64 tests pass; all 30 Docker IDs/start times and Codex
config/auth files remain unchanged. Stop/rebind/reload was explicit maintenance,
never an automatic startup/doctor action. Never replay historical PIDs.
See latest drain evidence and `docs/HANDOVER.md` for current state and rollback.

## Authorized Linux mise migration — 2026-10-15

The user's explicit migration request and continuation authorize the completed
OrbStack Ubuntu cutover, superseding earlier Linux mise deferral below. Reuse
Linux mise 2026.9.6, exact same-version declarations/locks under `infra/mise.toml`,
`infra/toolchains/` and `infra/harnesses/deepseek/mise.toml`. Root `.mise.toml`
is a discovery symlink. Home shell/command links are authorized launch plumbing,
not independent configuration. No user-global Node/Python pin was added.
New shells use root Node 24.19.0; {{mstack:CLIENT_REPO_CAMEL}} keeps its project Node 24.21.0.
uv selects mise Python 3.13.15 for new environments; OS Python stays untouched.

All 20 tool checks, 45 migration unit tests, offline Git/LFS/worktree checks and
three credential-free email MCP tests pass. Exactly 12 duplicate apt CLIs and
three unused standalone Bun paths were removed with verified archive/exact
`.deb` rollback. Preserve fnm: live editors and retained DeepSeek profile
package links still need it, even after processes exit. Preserve uv Python,
tools and cache for existing MCP/application environments. Never force an
editor/MCP restart or delete these stores to make the migration look cleaner.
DeepSeek preparation/offline composition passes; retained-profile startup and
provider execution were not activated. Email MCP uses mise Node; mailbox
connection/registration remains deferred. All 30 Docker identities/start times
are unchanged. No macOS runtime, Codex setting/auth or service/data change follows.

See `docs/ORB-DEVBOX-MISE-MIGRATION-2026-10-15.md` and the canonical handover.
Install/cutover/retirement helpers are explicit maintenance operations, never
startup/doctor actions. Missing-tool auto-install remains disabled. New tools,
versions, global registration, app dependency migration or another execution
domain still require their own authorization. User approval persists; do not
ask again for this already completed migration.

Apply these rules whenever work can change the `mcp-stack` runtime or either machine's toolchain.

## Unified configuration — 2026-10-08

The user's “go” authorizes v3 project config, shared connection catalog and scoped
plan/apply reconciliation. All config remains under repo `infra/`, integration
source under `integrations/`. `stack apply` may update/recreate only the existing
pinned agentgateway service in `mcp-stack`; no image pull, new service, provider
login, model call or global harness registration follows. Changed runtime has a
private backup, post-recreation check and rollback. Unchanged apply makes no
changes. Pending scopes stay closed. Owner UI drift stops apply unless the user
chooses adopt (non-project settings only) or explicit restore. Gateway project
registry is generated from registered project configs and shared catalog.
Clock retains its direct binding; root remains unbound. Legacy definitions and
pre-migration files are preserved. See `infra/stack/README.md`.

## Scoped connectors — 2026-10-08

The user superseded our read-only UI choice: a separate authenticated **owner UI**
at Mac loopback 58084 allows persistent configuration editing inside the same
pinned gateway/container namespace. Raw admin listeners stay off. No database or
paid call is needed. UI edits save to the writable runtime directory; render
preserves existing edits. Explicit `connections apply` backs up/replaces the
runtime from the candidate, then recreate only agentgateway with the projects
overlay if applying registry changes. Retain private keys/password. Codex
Command-click was observed rewriting the native Mac URL to forwarded port 62966;
use the Mac address bar or `macctl run open` for the native address. Registry/UI
changes do not qualify provider scopes.

The user authorized agentgateway project connections, then requested blank
input/space fields for Slack, Linear, Figma and Notion; Anytype gets a separate
project Space/collections when bound. All future persistent services belong to
the `mcp-stack` Compose project via targeted overlays. Do not confuse this grouping
with project data isolation. `infra/agentgateway/projects.json` is intent;
`projects.bindings.json` holds qualified scope evidence. Blank/unverified routes
fail closed. Keep provider credentials private, caller credentials distinct by
project/harness, and validate real resource restrictions before routing a broad
account token. Temporary synthetic tests are removed by exact owned targets.

## Latest authorized update — 2026-10-07

The user requested progressive design examples, smaller config/CLI, stack-use,
llama.cpp and OpenCodex. Repo-local init/plan/doctor/run and the discovered skill
are now implemented. Clock reuses its verified binding; the root remains unbound.
llama.cpp b11429 is installed as a project-local native macOS Metal runtime;
OpenCodex 2.79.0 is installed in its isolated mcp-stack container. This supersedes
older llama.cpp install deferral, without authorizing unrelated global settings.
The user expressly chose model weights later: no model download/inference or
local/DeepSeek tool qualification yet. Preserve native Codex auth, per-project
credentials and existing services. See docs/HANDOVER.md for current evidence.

## Latest user direction — 2026-10-06

Latest refinement: direct harness ↔ Anytype MCP is the default knowledge path.
No gateway or Windmill prerequisite. The user requests derived project-memory
refresh after Anytype updates; implement the narrow harness write/read-back/
memory-follow-up once client bindings are qualified. Background UI change watching
is not configured by a JSON instruction file. Keep the simpler profile in
`infra/mcpstack.config.json`; registrations/authenticated bindings remain pending.

Anytype is the sole PKM, initially the already-downloaded macOS client in local-only
mode. Notion/AppFlowy integrations are excluded, preserving definitions and unrelated
data. Basic Memory is retained but secondary/opt-in. Keep Graphify/CodeGraph;
never broadcast every prompt to memory services. ai-memory is an experimental
working-memory candidate; its requested pinned container installation does not
authorize hooks, automatic capture/imports, global harness configuration or new
gateway routes. Anytype project Space/auth binding still needs qualification.
Model routing/key centralization is proposed; llama.cpp installation/models are
deferred. `docs/HANDOVER.md` is the canonical current status/flow document.
Existing execution-domain, resource protection and scoped-authorization rules apply.

## Previous user direction — 2026-10-05

Product preferences below are historical where inconsistent with this update:
Codex primary; DeepSeek Harness/OpenCode optional; Windmill primary workflow
engine; n8n/alternatives optional; agentgateway selected/current proxy; MetaMCP historical; Graphify and
Basic Memory retained; CodeGraph/OpenWiki optional; Notion/AppFlowy later.
Preserve all existing infra definitions/documentation. The user approved and completed
Windmill trial cleanup and fresh integration with the existing PG instance using
a separate database/login; see `docs/WINDMILL-RUNBOOK.md`. Activepieces is excluded
and its test runtime/data was explicitly removed; definitions are retained. Do
not recreate either test environment. Optional tools remain preserved. Existing confirmation, execution-domain and resource
protection rules still apply. Do not interpret the older stopping point as a ban
on preparing this requested work, or automatically continue other components.

## Fixed boundaries

- The repository root is `/home/developer/workspace/mstack` inside the OrbStack Ubuntu machine. It is a real directory. The old `mcp-stack` compatibility symlink was removed after the approved context/container migration; see `infra/maintenance/repo-relocation/README.md`. Do not recreate it during normal startup. The old plural `workspaces` directory has been removed; never recreate it.
- Codex currently runs inside the Ubuntu development machine. The user wants both Codex and official `deepseek-ai/deepseek-harness` integrations; OpenCode is an optional alternative and Xiaomi MiMo Code is excluded. Product selection does not approve installations, model calls, harness registrations or an execution-domain change.
- Keep project tool/service definitions and application configuration under the repository's `infra/`, not in either machine's user/system config directories. Reusable integration source, contracts, tests and portable workflow definitions belong in `integrations/`; runtime settings and launch configuration remain under `infra/`. The root Compose file is an entry point including infra definitions. Project mise declarations are in `infra/mise.toml`; shared approved Linux profiles are under `infra/toolchains/`, and the root discovery link contains no separate selections. Keep Linux/macOS selections OS-scoped and separate; do not add user-global tool declarations. Agent instructions/skills remain in their project discovery paths. Keep human-readable notes at `knowledge/` and passwords in ignored `.secrets/`; secret-bearing application state under `infra/` must also be ignored and access-restricted. Harness registrations require a separately approved project-scoped approach, not edits to global Codex/Claude configuration.
- The system-level OrbStack Docker engine runs on macOS. Use the macOS OrbStack-provided `docker` and `docker compose` commands; do not install duplicate Docker clients or Compose plugins.
- On macOS, use its existing `mise` only for separately approved CLIs OrbStack does not provide. Linux uses the explicitly authorized repo profiles above. Invoke macOS commands through `macctl run`; approval does not cross execution domains.
- Declare this project's tools in `infra/mise.toml` or the approved scoped profiles, with exact versions and the correct `os = ["macos"]` or `os = ["linux"]`. Stateful services use existing OrbStack Docker/Compose, with images pinned by digest. Supabase is a deferred optional expansion, not the current database runtime.
- Keep macOS global `gh` and `xcbeautify` for native iOS development. Node must be selected by project configuration or an explicit invocation, not macOS global configuration. Preserve unrelated tool selections and the Ubuntu configuration.
- User-level caches such as `~/.npm` are acceptable when their cleanup is documented. This does not authorize cleanup or migration. Retiring `devbox` remains a deferred evaluation, not an approved action.
- The October 15 Linux migration is explicitly approved and complete. New Linux mise tools/configuration changes still require applicable user authorization; never infer that authorization from macOS permission.
- Do not install global Ubuntu tools through `apt`, `npm -g`, `pipx`, `uv tool`, Homebrew, or another manager without a separately confirmed install proposal.
- Containers belong to the macOS OrbStack Docker engine. Do not create a second Docker daemon inside Ubuntu.

## Per-install confirmation gate

Treat each component as a separate install step. This includes CLI/package installation, image pulls, `docker compose up`, `supabase start`, schema migrations, plugins, skills, MCP registrations, and persistent service configuration.

Before every install step:

1. Report the component and whether it targets macOS, Ubuntu, a container, Codex, or an external service.
2. State why it is needed, its source, exact pinned version or commit, and whether it is already present.
3. Show the exact commands, files changed, ports, persistence paths or volumes, environment variables, and secret locations.
4. Explain impact on existing services and provide verification and rollback commands.
5. Ask for explicit confirmation for that one step. Do not bundle approval for later components.

Do not execute the step until the user confirms it. Read-only discovery may continue while waiting when it cannot trigger auto-installation or mutate external state. Disable auto-install behavior during discovery where possible.

Apply explicit confirmations already given in the conversation. Do not ask again for the same authorized step; a changed version, new component, service start, or migration needs its own concrete proposal.

After every confirmed install step:

1. Report exactly what changed, where it was installed, and the resolved version.
2. Report verification results and any deviations or failures.
3. State whether rollback remains available and whether any cleanup is needed.
4. Stop before the next install step and present a new proposal.

Repository documentation or file generation explicitly requested by the user is not an install step. Still report material file changes after completing them.

## Existing-resource protection

- Treat the existing Supabase project `{{mstack:CLIENT_REPO}}` as immutable and out of scope.
- Its observed published ports include `54321`, `54322`, `54323`, `54324`, and `54327`. Re-inventory immediately before allocating ports because runtime state may change.
- Never stop, restart, reset, migrate, rename, reuse, or remove its containers, networks, or volumes.
- Never use broad commands such as `supabase stop --all`, `docker system prune`, or unscoped volume deletion.
- The new Compose project must use its own name, ports, network, volumes, migrations, credentials, and backup location. Any future Supabase stack must also be isolated from `{{mstack:CLIENT_REPO}}`.
- Resolve exact targets with read-only inspection before any lifecycle command.

## Current target architecture

- Harness integrations: Codex plus official DeepSeek Harness, each independently qualified and approved. Verify exact source/distribution version, permissions and MCP support; do not equate using a DeepSeek model in OpenCode with a separate DeepSeek Harness. OpenCode remains optional, not an install request.
- Orchestration: official self-hosted n8n, no paid license, guided setup. The latest user decision excludes n8n Assistant, its privileged sandbox/cert services and SearXNG. An ordinary external Code-node task runner is separate and may be proposed without the Assistant stack. Ollama and Qdrant remain independent deferred add-ons; neither is required for future Assistant use. See `docs/N8N-HARNESS-PLAN.md`. n8n coordinates explicit workflow checkpoints, not every harness message automatically.
- Gateway: agentgateway, selected by the user on 2026-10-01 in place of MetaMCP. See `docs/AGENTGATEWAY-SETUP-PROPOSAL.md`. Product selection is not installation approval; qualify the pinned official artifact and scoped transport/authentication proposal first. MetaMCP was never installed and its patch/fork research is historical, not an active setup task.
- Temporary code context: Graphify plus CodeGraph, unless a later harness-specific decision explicitly replaces them.
- Durable memory and PKM bridge: Basic Memory with isolated PostgreSQL + pgvector managed by Compose. Verify Basic Memory's current backend requirements before configuring its connection.
- Latest final-step request returns Basic Memory harness integration to the plan, initially using installed PostgreSQL/text search. This is not connection/test/registration approval. Models, semantic-search setup and unrelated usage tests remain deferred; preserve the running service/data. PKM integration and sync may wait. Start bidirectional sync with manual preview-and-approve; automatic schedules or external writes require separate approval. Follow `docs/OPERATIONS-RUNBOOK.md` for the remaining-work checklist and planned workflows.
- Keep `infra/supabase/` as a disabled future option; do not start Supabase for the current database setup.
- PKM destinations: Notion and preferably AppFlowy, selected and integrated through separately confirmed steps.

Do not silently substitute products, add Mem0, or drop a selected component. Present evidence and obtain a new decision first.

## Safe operating pattern

- Prefer read-only discovery before proposals.
- Pin every third-party version or source revision.
- Keep secrets in ignored files or environment variables and never print them.
- Bind local services to loopback when supported.
- Keep durable data in explicitly named project-scoped volumes or paths.
- Validate each MCP server directly before adding it to agentgateway. Aggregation does not enforce task profiles automatically; verify discovery filtering, call rejection and failure behavior. Preserve Graphify's existing adapter restrictions, CodeGraph's scoped index/single-writer boundary and Basic Memory's model deferral/unapproved connection boundary.
- Record versions, ports, persistence, backup, restore, upgrade, and rollback instructions in the repository.
- If an inspection unexpectedly triggers an installer or mutation, stop it, report it immediately, and restore the prior state before proceeding.
