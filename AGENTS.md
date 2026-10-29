# mstack agent instructions

## {{mstack:CLIENT_REPO}} orchestrators — 2026-10-29

Linear is the task source of truth (`docs/design/010-LINEAR-SESSIONS.md`). {{mstack:CLIENT_REPO}} has three
top-level Claude Desktop sessions:
- "{{mstack:CLIENT_REPO}} orchestrator": repo-level coordinator with no watcher;
- `customer-api`: API → {{mstack:CLIENT_ORG_A}}/IRO, its own watcher. It has adopted IRO-104, IRO-126 and IRO-128.
- `staff-web`: everything else → {{mstack:CLIENT_ORG_B}}/CAN, its own watcher, with CAN-187.

Scopes live in {{mstack:CLIENT_REPO}} `.mstack/stack.json` `taskboard.orchestrators`. Adopting never dispatches a second
worker. Don't archive an orchestrator while it has live workers. {{mstack:CLIENT_REPO}} runs in **private mode** (`taskboard.private: true`):
the board never writes to Linear, the orchestrator's messages go to {{mstack:CLIENT_REPO}} `.mstack/journal.json`, and the owner
gives verdicts in the orchestrator chat (`mstack board owner`). Keep the three earlier "Tracked by" comments.

## Task board, orchestrator and plugins — 2026-10-28

At the user's request: Anytype channel `mstack-taskboard-test` (native UI created; key
`.mstack/secrets/anytype-taskboard-test.key`, read/write to that channel only) holds one
reusable Agent Task type and one collection per project (`mstack tasks`, `test-market tasks`).
`mstack board` (integrations/orchestrator) plans, polls owner verdicts, dispatches workers
into git worktrees and takes reports back; `.agents/skills/mstack-orchestrator` is its playbook.
`mstack plugin` (integrations/plugins) holds joint manifests and contracts. The demo project is
`/home/developer/workspace/test-market` (local visibility). With approval, `mstack-headroom` was
started and test-market registered as its tenant; `joints.compress: headroom` passes its live
contract kit. Capture hooks are project-scoped only. No Linear token, Claude CLI or OpenCode
installed; do not install them or merge/push task branches without a request. See
docs/design/005–009. Later the same day, with approval: `mstack-graphify` started and
test-market registered (offline index); shared Postgres and Windmill started, with workspace
`mstack` and non-admin user `orchestrator` (token in infra/windmill/state, 0600). These services
are left running. On 2026-10-29, Postgres + WhoDB was approved on the board: database
`mstack_orchestrator` (own owner role, read-only `mstack_viewer`) was created and WhoDB started.
Linear keys live in `.secrets/linear.csv` (0600); `mstack board link` copies one entry per project
into its `.mstack/secrets`. The owner authorised mstack integration in ~/workspace/{{mstack:CLIENT_REPO}}
(local visibility, repo files only); its Supabase containers, networks and volumes stay untouched.
agentgateway is running (approved option B): route `/mcp/projects/test-market` → Windmill MCP with a
hashed project key, a 10-tool allowlist, a 30/min rate limit and access logs. Workers use
`integrations/gateway/stdio_bridge.py`; the gateway's DNS-rebinding protection stays on (relaxing it
was refused). Rollback steps are in `infra/agentgateway/state/projects/test-market-route-20261029.json`.
Garage stays stopped pending approval.
{{mstack:CLIENT_REPO}} (2026-10-29, owner-authorised with `init --allow-protected`, local visibility): table
"{{mstack:CLIENT_REPO}} tasks", app codes API/GO/COMM/MKTG/PORTAL/DESK/MOB/WEB, `[API]` linked to {{mstack:CLIENT_ORG_A}}/IRO
(key entry 2, pull) with 93 history issues imported, `auto: false`. Team tools (.mcp.json Headroom/Serena,
graphify-out) stay the repo's own. A Claude Desktop "{{mstack:CLIENT_REPO}} orchestrator" session waits for the
owner's call; it must not edit, commit or switch branches in the owner's checkout.
Claude may review and close its own issues on the mstack tasks board (owner delegation, 2026-10-29).
mstack's own tools (2026-10-29): project `.mcp.json` gives Claude sessions here Serena (pinned
v2.1.0 via uvx, as in {{mstack:CLIENT_REPO}}) plus mstack's own Headroom and Graphify tenants (`mcp-stack`; the
Graphify index is an offline snapshot of 489 non-ignored files: re-index after big changes). Workers
get Headroom and Graphify through `joints`. Serena's first run downloads from GitHub and needs the owner's OK.
Linear is the task board (2026-10-29, owner decision; see docs/design/010-LINEAR-SESSIONS.md). Boards:
mstack → yyyymmdd/MST (entry 1), {{mstack:CLIENT_REPO}} [API] → {{mstack:CLIENT_ORG_A_SHORT}}/IRO (entry 2), other {{mstack:CLIENT_REPO}} apps → {{mstack:CLIENT_ORG_B}}/CAN
(entry 3). Never create teams, labels or states in the owner's workspaces; phases live in 🤖 comments.
Work starts only from the owner's `/plan` comment. Skills: mstack-setup, mstack-orchestrator,
mstack-worker, mstack-ops (`.agents/skills`, mirrored in `.claude/skills`; `mstack skills --project P`
links them into a repo). The Anytype tables are an untouched archive. test-market is retired from automation.

## Back to Codex Desktop and Claude Desktop — 2026-10-27

The user found Paradev hard to use and returned to Codex Desktop (ChatGPT.app
26.1021.31345) and Claude Desktop 3.6556.2, reinstalled by the user, until a
better orchestration app appears. Do not reinstall Paradev/Superset, Paseo or
the standalone Codex/Claude CLIs unless explicitly requested.

Paradev is removed from both hosts: orb-devbox host deregistered (service and
API key revoked), apps/CLI/state, agent hooks, skills, plugins and temporary
files removed. See `infra/maintenance/paradev-retirement`. The Paradev cloud
account (org, offline host entries, user API key, Pro plan) is the user's to
close. Empty `.git` folders created for Paradev in four Mac folders and the empty
`mstack` root commit were undone. (On 2026-10-29 the owner asked for mstack's first real commit, "Initial commit: mstack stack, orchestrator and Linear board".)

The mise-managed Codex and Claude Code CLIs and `~/.local/bin/{codex,claude}`
launchers are uninstalled on both hosts; `infra/harnesses/agent-clis` is
historical. On orb-devbox `~/.local/bin/codex` again points to Codex Desktop's
managed standalone install, which its remote connection uses. Native `~/.codex`
and the Claude CLI config/history under agent-clis `state/` are retained.

Paseo is removed from both hosts; see `infra/maintenance/paseo-retirement`.
Claude Desktop and Codex Desktop were removed earlier the same day and then
restored; their native history/configuration directories were never deleted.

## OpenCodex removed — 2026-10-21

The user's subsequent explicit removal request supersedes every older OpenCodex
retention/rollback instruction below. Its stopped container, two dedicated data
volumes, unused image, proxy tokens, active setup files and obsolete Claude profile
are removed. Dedicated token/profile backup copies and the old Magpie stash pointer
were also removed. No OpenCodex rollback remains; do not restore or reinstall it.

Claude Desktop continues through Magpie and official DeepSeek Flash. Magpie's
provider/settings/key/active profile and Mac/Ubuntu Codex config/auth are unchanged.
Codex integration remains pending explicit request. The old local/deepseek project
routes are unbound with no endpoint/token; the launcher refuses them, and project
schema rejects the removed opencodex tool. No automatic Magpie route inheritance.
Use `integrations/models/magpie_manage.py` for start/stop/local verification; the
completed Magpie migration helper is retired. No paid call or foreground UI ran.

All 31 other containers present at removal are unchanged, as are unrelated volumes
and all networks. See `infra/maintenance/opencodex-retirement/README.md` and receipts.

## Claude Desktop moved to Magpie — 2026-10-21

The user explicitly selected Magpie instead of OpenCodex, Claude first, with
Codex integration pending until requested. The existing installed Claude surface
is Desktop 3.1623.0; no Claude Code CLI was installed. Installed Magpie 0.1.1206
now runs in the Mac background on loopback 3425 (gateway) and 3430 (management),
using the existing official DeepSeek Flash credential. No login autostart is
configured. Account discovery/refresh, updates, fallback and request archives
are off. Native Codex config/auth on Mac and Ubuntu are unchanged. Do not enable
Codex through Magpie until explicitly requested. This supersedes the old Magpie
removal/exclusion and Claude-through-OpenCodex selection below.

Runtime intent/state are under `infra/magpie`; native config/cache discovery links
point there. Claude's generated profile library is now a native Mac directory:
OrbStack rejected Magpie's atomic metadata writer. The old profile is retained
byte-for-byte; its repository copy is historical. See `infra/magpie/README.md`,
`infra/claude-desktop/config.json` and the fresh Magpie qualification receipt.
Three synthetic requests verified streaming and automatic tool/result handling;
management returned 401 without its key and 200 with it. The native Claude window
was not opened, so do not claim a live Desktop chat, Code/Cowork or MCP proof.

All 33 containers retained their identities, start times, states, settings and
mounts. OpenCodex stayed stopped with credentials/volumes/config preserved.
No Anytype grant, graph index, service lifecycle or global harness MCP change
follows. Background-only operation remains in force. Historical migration actions
and paid probes are not startup commands; use the documented pinned launcher.

## Repository path migration completed — 2026-10-19

The canonical checkout is `/home/developer/workspace/mstack`. The old sibling
`mcp-stack` was a compatibility symlink to this same directory and is now removed.
The repository was already renamed; no separate source copy existed. File/hash
inventory verifies retained private state, dependencies, Git metadata, skills,
project context and documentation. See `infra/maintenance/repo-relocation/README.md`.

All nine user chats use mstack, with original IDs/history bytes/archived status
preserved. ChatGPT Desktop now has one mstack project with the prior chats attached;
the merge persisted after its explicitly approved restart. DeepSeek's 430 profile
links and Serena's existing project entry use mstack. The 96 previously broken
DeepSeek targets remain unchanged. Six obsolete mise trust links are removed;
all six existing replacement grants are retained.

The six containers with old bind paths were recreated at mstack, preserving exact
images, credentials, data volumes, ports, effective resources and network choices.
All 30 containers remain stopped; the other 24 retain their identities/settings.
No service start, model call, new grant, index or schedule follows. Stable service,
volume, tenant and project IDs still use mcp-stack where required. Historical
command text and container-internal graph paths are preserved. Do not recreate
the deleted alias or rerun migration helpers as startup/health checks.

Git/Git LFS use Ubuntu `/usr/bin` after the October 18 repair; do not move them
back into mise. Native desktop work is complete; return to background operation.
No approval or migration cleanup remains pending.

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

## Live service correction — 2026-10-16

Garage was resumed in its original container after the user's service-state
report. Health and signed read-only S3 checks pass; original credentials/data
and all 28 other containers are unchanged. No new application S3 binding exists.
The example Graphify container is running and answers MCP. The older CodeGraph
container and exact image are absent, with source/configuration/index preserved;
do not claim it is running. The six-stage proof covers the selected example
workflow, not every retained service. Anytype's Node container is a stdio MCP
adapter to the native desktop API, not a second document backend or HTTP listener.
See `docs/MSTACK.md` and `infra/garage/resume-20261016.json`.

## External project and background operation — 2026-10-16

The user replaced the in-repository demo with `/home/developer/workspace/mstack-example`.
Use `docs/MSTACK.md` and its own project instructions. Actual harness capabilities
come first; missing selected capabilities need dedicated containerized backends.
A Graphify skill does not substitute for the engine. Graphify 0.9.72 now runs in
`mstack-example-graphify`, indexing only the example's two Python files, without
network/model calls. Existing Headroom/Serena/gstack are retained. Windmill's two
existing containers were resumed; its isolated example workspace/report and
restricted API/MCP tokens are qualified. Other services/data are preserved.

Use background APIs, containers and isolated headless browsers while the user
uses the Mac. Native app control requires an explicitly arranged quiet window.
The user offered that window on October 16 and authorized completing Anytype.
The new mstack-example personal channel and its read/write-only channel grant
are qualified through the dedicated Anytype MCP 2.0.1 container. All-spaces access
is off; an out-of-channel request returns space_not_granted. The brief and verified
result were saved and their contents read back. Ordinary document work now uses
background MCP/API. The old demo key is revoked (401), channel deleted and local
directory removed. No grant was borrowed. All six saved proof stages pass against
the completed external-project configuration. No automatic mirror or schedule.

Native Codex discovers the external AGENTS.md and mstack skill. Project MCP files
still require normal project trust. The explicit `mstack run` invocation is
verified without global settings/auth changes. Claude Code files are prepared,
not a qualified Claude session. No inference/provider call ran. Direct `plan`
does not consult unrelated gateway projects. `doctor` checks enabled bindings;
`proof` checks all six saved proof receipts, including the completed Anytype stage.

## Keep the infrastructure; use three everyday channels — 2026-10-16

The user explicitly retains harnesses, Anytype, Windmill, OpenCodex with its
existing setup, Llama.app, PostgreSQL + pgvector, WhoDB, and Garage. OrbStack and
mise are protected system tools: never remove them. Other remaining non-mail
components are preserved; simplification is not a removal or migration request.
The everyday workflow remains Codex/Claude, Anytype, and Windmill. Supporting
infrastructure does not become a prerequisite for every new project.

Keep existing Headroom, Serena, and gstack support available; choose relevant
capabilities for each task rather than reinstalling or invoking everything per
project. Graphify already has a skill interface; a CodeGraph CLI-backed skill
is a possible future packaging change, not completed work or approval to replace
its backend. Skills still require the underlying programs and project indexes.
No graph reindexing, helper reconfiguration, new model download or provider call
follows from this discussion. DeepSeek provider means the model API configured
in OpenCodex; DeepSeek Harness is a separate agent application.

The completed AI mail removal below remains in force. The fresh-project prompt
and reference inventory in `docs/FRESH-PROJECT-PROMPT.md` reflect this decision;
do not carry removed mail-account summaries into new project context.

## AI mail setup removed — 2026-10-15

The user explicitly cancelled all AI mail integration and requested removal of
Inbox Zero, TimeCyber/email-mcp, both Microsoft Entra apps, and both Google links.
This supersedes every earlier mail preservation, onboarding and continuation
instruction below. **Do not reinstall, reconnect, regenerate credentials, or
resume the Hotmail/Outlook/QQ setup.** Actual mailboxes/messages are untouched.

Both Entra registrations were deleted and are absent from the refreshed active
app list. Google confirmed Inbox Zero OAuth revocation (HTTP 200); the named
TimeCyber Google app password was revoked and is absent. Inbox Zero's dedicated
DB/role, three containers, Redis volume, two networks and unused image references
were removed. Both local runtimes, source clones, launch/configuration files,
credentials, caches and app-specific backups were deleted. Historical broad
container snapshots had only their mail-container environment values scrubbed.
The exact Inbox Zero Google OAuth client was also deleted; the active client
list is empty. All six requested mail cleanup items are complete.

Shared PostgreSQL, its other databases, OpenCodex/DeepSeek, {{mstack:CLIENT_REPO_CAMEL}} and all 27
unrelated containers are preserved. The mail-only PG network was detached;
`infra/postgres/compose.yaml` now directly preserves the existing external volume
and prior platform/pull settings, so the deleted mail overlay is not required.
The pre-mail shared PG recovery copy moved to `infra/postgres/.state/recovery-20261009`.
See `infra/maintenance/mail-retirement/README.md` and its evidence. The user also
requested removing stored mailboxes: the mail database/account files are absent,
and historical account connection summaries were removed from these project notes.
Do not retain mailbox identities or reconstruct their account profiles.

## Everyday workflow simplified — 2026-10-15

The user's latest direction is **Codex + Claude for interactive work, Anytype
for documents/personal context, and Windmill for repeatable automation**. Help
them complete real work with this small workflow. Use `docs/START-HERE.md` as
the everyday entry point; consult the handover for relevant maintenance/evidence,
not as a prerequisite to every task.

Agentgateway, Graphify, additional memory backends and unfinished integrations
are outside the everyday checklist. Existing Graphify availability does not
require graph retrieval. This direction supersedes older default tool-selection
and derived-memory follow-up requirements: an Anytype note does not require an
ai-memory mirror or a pending-refresh task. Use a short, curated personal note
and relevant project context; explicit read/paste is sufficient until a direct
binding is qualified. Do not claim automatic cross-project memory.

Historical non-mail setup checkpoints remain available for explicitly requested
work. Stored mail account connection summaries have been removed.
This is an operating-guidance change, not authorization to remove components,
stop services, change credentials/global registrations, or inherit another
project's Anytype access. Runtime/configuration evidence below remains dated.

## Authorized helper drain finished — 2026-10-15

The user's later request explicitly allowed temporary fnm/uv helper downtime.
Sixteen identity-checked helper trees / 44 processes stopped gracefully, without
stopping Codex or Docker. Existing bindings reconnected through the supported
MCP reload API; Headroom and Serena are connected in all 10 loaded sessions.
All helper Python/Node/language-server processes now use mise; no legacy runtime
process remains. This supersedes earlier same-day mandatory fnm/uv Python
retention below. No model/provider/mailbox call or global config/auth edit ran.

Rebound 146 same-version Python environments, preserving packages and verifying
actual execution. Keep uv tools/cache: these hold application environments now
using mise Python, rather than a competing interpreter. DeepSeek's 430 profile
links now target exact-byte project dependencies under ignored
`infra/harnesses/deepseek/runtime/profile-packages/dsh`; preserve them and user
profile/settings/credentials. Its 96 pre-existing broken links remain unchanged;
retained-profile startup/inference was not tested or started.

Original fnm and old uv Python home paths are absent; private quarantine and
verified archives remain for rollback. Do not restore/reinstall them as normal
startup. Sixty-four migration tests pass; all 30 Docker IDs/start times and
Codex config/auth files remain unchanged. See the latest drain qualification,
the migration record and `docs/HANDOVER.md`. Reusable maintenance helpers are
under `integrations/toolchains/`; never replay historical PIDs or treat these
explicit stop/rebind/reload actions as automatic health checks.

## Ubuntu mise migration completed — 2026-10-15

The user's explicit migration request supersedes the earlier Linux mise
deferral. Existing Linux mise 2026.9.6 now manages the approved same-version
toolchain. Declarations/locks stay under `infra/`: project Node/pnpm in
`infra/mise.toml`, common/CLI/Python profiles in `infra/toolchains/`, DeepSeek in
`infra/harnesses/deepseek/mise.toml`. Root `.mise.toml` is discovery only, linked
to `infra/mise.toml`. `~/.zshrc` sources the repo bootstrap; 25 command links
resolve installed tools without auto-installing. No user-global Node/Python
selection was added. Root Node is 24.19.0; {{mstack:CLIENT_REPO_CAMEL}} keeps Node 24.21.0.

Twenty exact replacements and offline Git/LFS/worktree checks pass; 45 migration
unit tests and three credential-free email MCP checks pass. Twelve duplicate
apt CLIs and three unused standalone Bun paths were removed only after exact
rollback copies/checks. Keep OS Python and PostgreSQL client. Keep the old fnm
store: active editor processes AND retained DeepSeek profile package links still
need it, even after processes drain. Keep uv-managed Python/tools/cache for live
MCP consumers. Do not force restarts or delete these stores. New uv invocation
selects mise Python 3.13.15; existing environments retain their interpreters.

Email MCP now uses mise Node 24.19.0; mailbox connection/registration remains
deferred. DeepSeek launcher/preparation and offline composition use the new
toolchain; retained-profile startup/provider calls were not tested or activated.
All 30 Docker names/IDs/start times and protected unrelated home configs are
unchanged. macOS tools, native Codex settings/auth, services and data are outside
this cutover. npm top-level pins are verified, but mise.lock does not fully lock
their transitive artifact URLs. See `docs/ORB-DEVBOX-MISE-MIGRATION-2026-10-15.md`,
the public qualification receipt and `docs/HANDOVER.md`. Do not rerun install,
cutover or retirement helpers as startup/health checks.

## Magpie removal — 2026-10-12

The user explicitly requested removing newly installed Magpie. macOS app 0.1.1206
was moved from `/Applications/magpie.app` to the owner's Trash; no provider state
or agent settings were deleted/changed. Restore from Trash only if requested.
Do not install Magpie again or add a replacement without a new request.

## Service recovery — 2026-10-09

The user explicitly requested recovery of WhoDB, Windmill and Garage. Their four
containers are restored on macOS OrbStack with original retained data/credentials
after verified offline-volume and Windmill DB backups. Only Garage's missing
`mcp-stack-n8n-local` client network was recreated. Windmill's current Compose
pin selects the original qualified 1.823.1 ARM64 manifest
`sha256:a0c7f7ea7db229cabd05d06615b961d1700e6755ad9489b62aff27739735b362`;
its executable layers are unchanged. Healthy UIs, one worker heartbeat, 673
migrations, original Garage node/bucket/keys and 19 unchanged existing containers
were qualified. No cause/time/actor for removal is established. See
`docs/SERVICE-RECOVERY-2026-10-09.md` and its public qualification receipt.
Other absent historical applications were not restored; trial/Activepieces
retirement stays in force. Use exact service overlays, not project-wide lifecycle.

## Shared PostgreSQL recovery — 2026-10-09

The original shared PG18.6 service was recovered from its retained volume after
verified offline backup. Its non-mail databases and roles remain protected.
Mail-specific data and account records were subsequently deleted at user request.
Use the current root Compose entry and `infra/postgres/compose.yaml`; the retired
mail overlay is no longer required. The pre-mail recovery copy is private under
`infra/postgres/.state/recovery-20261009`. Never reset the shared volume.

## Linux cleanup follow-up — 2026-10-09

The user's scoped removal request supersedes preservation of the unused Linux
Supabase CLI and Deno: both are removed, with dedicated residue and Deno shell
hooks. {{mstack:CLIENT_REPO_CAMEL}}'s existing Supabase mise declarations are now macOS-only.
Preserve its existing Docker containers/data. Linux Bun 1.3.14 is preserved for
gstack for now; the user asked for the dependency explanation and conditional
retention if already mise-managed. It is actually standalone, not mise-managed;
its migration remains a proposal. Do not stop unrelated helpers or alter macOS
Bun. See
`docs/ORB-DEVBOX-CLEANUP-2026-10-09.md` for evidence and private backup locations.

Native iOS compression tests already moved to the macOS media lab; preserve the
Linux clone's separate uncommitted app integration patch before retirement.
The broad Linux mise migration remains a proposal. Inbox Zero can keep config
in this VM and use the existing macOS OrbStack Docker engine; its full-container
runtime needs no host Node. The setup CLI/source path requires Node 24+, already
installed through mise. Inbox Zero runtime was installed later as documented
above; provider access remains unprovisioned.

## Unified project configuration — 2026-10-08

The user authorized single-source reconciliation. Project `infra/stack.json` v3
is authoritative intent; v2 remains supported. Shared URLs/auth methods/secret
references are in `infra/stack/connections.json`. Gateway `projects.json` is a
**generated compatibility snapshot**, not an independent strategy source.
`./stack plan/apply --project <directory>` resolves all registered project intents,
preserves unrelated routes/keys, and updates project-only harness settings.
Unchanged apply is a no-op. Changed gateway runtime uses only the existing pinned
agentgateway service in `mcp-stack`, with a private backup, verification and rollback.
No auto-install, provider login, paid call or global harness registration occurs.
`stack init` creates v3 files and a skill. Missing bindings remain closed/pending.
Root Anytype stays unbound; Clock keeps its qualified direct binding. A/B migrated
to `examples/project-a` and `examples/project-b` as placeholder configs, not real
provider grants. Owner UI drift stops default apply. `stack adopt` supports logging
and separate non-project listeners/routes; managed project/auth drift must be
expressed in intent/evidence. `--drift restore` explicitly restores reviewed config.
See `infra/stack/README.md` and `docs/HANDOVER.md` for exact scope and evidence.

## Scoped connector update — 2026-10-08

Later refinement: shared-connector projects default to agentgateway. The native
UI is enabled at Mac loopback `127.0.0.1:58084/ui` with separate Basic owner login;
owner editing is enabled and persists in the runtime directory, raw admin disabled.
This supersedes our earlier read-only choice. Render preserves existing UI edits;
explicit `connections apply` backs up/replaces runtime before targeted recreation.
Paste the native Mac address or use `macctl run open`; Codex Command-click was
observed rewriting it to the wrong forwarded port 62966. Documented JSON Schemas under
`integrations/gateway/schemas/` validate registry, bindings and UI settings through
`./stack connections validate` and before plan/render. Detailed blank project/auth
inputs remain unbound. Existing direct Clock access and file-only work are preserved.

The user requested centralized agentgateway connections and blank input/space
fields for two projects. The generated `infra/agentgateway/projects.json` contains placeholder
project-a/project-b, shared Slack/Linear/Figma account references, separate Anytype
references and optional blank Notion. This narrow Notion request supersedes its
earlier exclusion for connector preparation only; Anytype remains canonical PKM.
No live provider OAuth, external objects, or harness registration is completed.
The pinned v1.5.0 gateway is restored in the `mcp-stack` Compose namespace using
base + `infra/agentgateway/projects/compose.yaml`. Qualified project/caller auth
and synthetic concurrency/isolation tests do not qualify the real provider scopes.
Old graph configurations remain preserved; their runtime containers were absent
at discovery and their endpoints have not been restored. Root Anytype stays unbound.
Future persistent tools belong to `mcp-stack`; operate exact services only.
Use `./stack connections plan` and the canonical `docs/HANDOVER.md` for status.

For every installation, setup, update, removal, service lifecycle action, MCP registration, database migration, or toolchain change in this repository, load and follow `.agents/skills/mcp-stack-setup-guard/SKILL.md` before acting.

The macOS host and OrbStack Ubuntu development machine are separate execution domains. Never infer that approval to use macOS `mise` permits installing or configuring `mise` inside Ubuntu.

Keep project tool/service configuration under this repository's `infra/`, never in macOS or Ubuntu user/system-level configuration. Reusable integration source, contracts, tests and portable workflow definitions belong in `integrations/`; runtime settings and launch configuration still belong in `infra/`. The root Compose file is only an entry point. Project mise declarations belong in `infra/mise.toml`; target that directory explicitly with macOS mise when a separately approved CLI needs it. Agent instructions/skills stay in their project discovery locations. Do not register harness MCP servers globally without separate explicit approval.

## Progressive project workflow — 2026-10-07

Use `.agents/skills/stack-use/SKILL.md` for project initialization/continuation.
Prefer small `infra/stack.json` intent and `infra/stack.bindings.json` evidence;
shared presets/routes are under `infra/stack/`. The repo-local `./stack` provides
init/plan/doctor/run. Init is file-only, not remote provisioning. Clock's legacy
registry remains qualified runtime evidence; do not copy its bindings elsewhere.
Root Anytype remains unbound. Config does not change the current desktop tool menu.

The user reopened local-model work: llama.cpp b11429 is installed natively for
macOS Metal, with version/hash verified. OpenCodex 2.79.0 is installed as the
isolated mcp-stack-opencodex container, health/auth verified. This supersedes
llama.cpp's older installation deferral. The user chose model weights later;
no download, inference, local/DeepSeek provider/tool qualification or automatic
paid fallback. OpenCode and LM Studio are optional alternatives, not installs.
Keep Codex's native login/global settings unchanged; use project invocation
settings. See docs/HANDOVER.md and docs/design/ for current evidence and boundaries.

## Latest PKM and memory decision — 2026-10-06

Latest refinement: the default knowledge profile is **direct-anytype**. Read
`infra/mcpstack.config.json` and `.agents/skills/mcpstack-policy/SKILL.md`.
The harness calls Anytype MCP directly; gateway and Windmill are not prerequisites.
After an authorized harness write succeeds, read back that object and refresh
one derived entry through the direct ai-memory project binding. This narrow
follow-up replaces the earlier blanket no-mirroring policy for that case only.
No broad sync/capture or graph reindexing. Anytype/ai-memory project client bindings
are still pending. UI edits are refreshed on the next explicit harness read;
there is no background watcher. Config/skill instructions do not themselves
register tools or detect changes while the harness is idle. Preserve existing services.

This update supersedes older PKM/memory preferences. Anytype is the sole PKM;
Notion and AppFlowy are excluded from future integration, with existing source
and unrelated data preserved. The user downloaded the macOS client and chose
local-only mode; no sync server is requested. Exports are not lossless for chats,
discussions or member identity links; retain protected backups and verify restores.

Prefer a qualified Anytype MCP connection for relevant knowledge reads/writes in
the explicitly bound Space for the harness project. The root remains unbound.
Clock has a qualified Clock-only key, full Space ID, docs/tasks collections and
direct MCP/project CLI launcher; see its registry and `docs/HANDOVER.md`.
Do not inherit Clock access in another project. Never infer isolation from a name/Space ID
argument or expose a macOS loopback API to Docker/Ubuntu without qualification.

Basic Memory remains installed/preserved but secondary and opt-in; no automatic
Basic Memory mirror into/from Anytype. Graphify and CodeGraph remain contextual tools, not
mandatory retrieval. ai-memory 2.5.2 is installed as an experimental working-memory
candidate; no model/embedding provider, capture hooks, project import or harness/
gateway registration. Candidate data is persistent, not automatically disposable.

Choose relevant tools per step. No broadcast to every memory backend. Project
instructions guide selection; agentgateway enforces only qualified configured
routes, and Windmill sequences only reviewed workflows. A central LLM route is
still proposed; current gateway has graph MCP routes only. Model keys centralize
only for callers configured to use that LLM route. Codex provider remains unchanged.
llama.cpp is installed per the October 7 update; weights/inference remain pending. See `docs/HANDOVER.md` for
current status/flows and `infra/agents/memory-routing.json` for policy guidance,
which is not an active dispatcher. Load this setup guard before runtime changes.

## Simplification decision — 2026-10-05

This section supersedes older product preferences and stopping points below.
Codex is primary; DeepSeek Harness and OpenCode are optional. Windmill is the
primary code/workflow engine; n8n and alternatives are optional complements.
Agentgateway remains the selected and installed proxy; MetaMCP is superseded
historical research, not a pending replacement. Keep Graphify and Basic Memory; CodeGraph and OpenWiki are optional.
Its Notion/AppFlowy preference is superseded by the Anytype decision above.

Start simple tasks in Codex with ordinary file inspection/search. No mandatory
workflow, gateway, memory or graph calls. For coding, Graphify is available when
relationships help; CodeGraph is opt-in for a specific source-structure need.
OpenWiki is optional documentation generation, not a required memory service.

Preserve every existing `infra/` entry and its documentation. Catalog optional
or superseded definitions in place; do not move runtime source into Basic Memory.
Future knowledge capture uses curated notes/source links, excludes secrets/state,
and is not an automatic indexing/import request. See `docs/KNOWLEDGE-ORGANIZATION.md`.

The user approved and completed Windmill fresh shared-PG integration and trial
cleanup on2026-10-05. `docs/WINDMILL-RUNBOOK.md` is current; the new server/worker
use their own database/login on existing PG. All three trial containers/volumes,
trial network and runtime credentials are removed. Activepieces is excluded:
its four test containers, two volumes, network and runtime env are removed;
source definitions remain, cache empty. See `docs/ACTIVEPIECES-RETIREMENT.md`.
Do not recreate either test environment or rerun provisioning automatically.
Optional is not excluded: n8n, CodeGraph, DeepSeek and other preserved state are
not deletion targets. Agentgateway remains the selected/current proxy. No automatic next component, harness registration,
model work or PKM sync follows. `docs/START-HERE.md` is the everyday entry point.

Windmill's current Compose grouping is `mcp-stack`, via
`infra/windmill/compose.yaml`; use only services `windmill-server` and
`windmill-worker`. Existing cache/log volumes are external/reused. Never use
`--remove-orphans` or project-wide `down` for these separately managed overlays.
CodeGraph remains installed/running and optional: no routine calls or reindexing;
use only for a relevant source-structure need within the approved index scope.

WhoDB is the selected simple database viewer, superseding the pgAdmin proposal.
Selection does not install/connect it; see `docs/WHODB-VIEWER.md`.
Use `docs/PROJECT-SETUP-RUNBOOK.md` for new-project onboarding. The JSON policy
and repo skill are guidance, not provisioned cross-tool access isolation.

## Historical decisions (superseded where inconsistent)

## Current stopping point and user control

Updated 2026-10-04: the user approved only the prepared n8n router import and synthetic manual tests, and explicitly rejects an endless chain of next setup steps. Finish or accurately hand off this bounded task; do not automatically propose/install/register the next component. The four synthetic checks are bundled into one manual execution of one inactive workflow. If browser automation is unavailable, do not change global browser/security permissions, copy cookies, read the owner password or bypass authentication. Provide the existing UI import/run procedure and stop. Future Code runner, gateway/harness/memory/PKM connections, model work, secret hardening/export and generalized skill remain deferred until the user deliberately reopens a specific item. Use `docs/START-HERE.md` for the everyday handoff, not the historical roadmap as mandatory instructions.

## Harness preference

Updated on 2026-10-01: integrate both Codex and the official `deepseek-ai/deepseek-harness`, through separately approved steps. OpenCode remains an optional alternative, not an additional installation request; Xiaomi MiMo Code is excluded. DeepSeek Harness is distinct from selecting a DeepSeek model in another client. Verify each distribution/version, project-scoped configuration, permissions and MCP support before installation/integration. This preference approves no authentication, registration, model calls or execution-domain change; existing setup approval gates and Basic Memory's deferral remain in force.

Latest package-manager decision on 2026-10-02 supersedes npm-only: **allow existing pnpm for DeepSeek**, respecting the official `dsh plugin` wrapper's upstream choice. The user requests continuing the corrected vision-plugin update; see `docs/DEEPSEEK-VISION-UPDATE-PROPOSAL.md`. npm migration is cancelled, not implemented. Reuse existing managers, disable scripts and self-installation, keep cache/state under `infra/`, and preserve settings/credentials/sessions. Permission to use pnpm does not approve global configuration changes, manager installs/removals, wrapper-specific reconciliation, profile startup or new components; each still follows the setup guard.

## n8n decision

Latest decision on 2026-10-01 supersedes the earlier Assistant/sandbox acceptance: official self-hosted n8n without a paid license, guided setup, **no n8n Assistant, Assistant sandbox/cert services or SearXNG**. The ordinary external Code-node task runner is distinct from that privileged sandbox. Reuse PG18 with a separate n8n database/login. Ollama and Qdrant are independent deferred add-ons, not prerequisites for later Assistant use; do not deploy the AI starter kit or download models automatically. See `docs/N8N-HARNESS-PLAN.md` and the separately gated database proposal.

## Gateway decision

Updated on 2026-10-01: agentgateway replaces MetaMCP as the selected gateway. Follow [the agentgateway assessment](docs/AGENTGATEWAY-SETUP-PROPOSAL.md); MetaMCP source/patch choices are superseded historical research. Nothing is installed or registered by this decision. Prefer a qualified, pinned official standalone container and project-local file configuration, without Docker socket access or an automatic database/UI setup. Every install, transport adaptation and harness registration still requires its own concrete approval. Preserve Basic Memory's deferral and the existing graph-tool isolation.

## Accepted memory routing policy

Follow [the task-profile policy](docs/MEMORY-ROUTING.md). Select a profile for each task, retain it as a session default, and reassess when the user changes task or repository. Tool availability and installation are separate from this policy: never auto-install, auto-index another repository, or assume gateway filtering is already implemented.

- PKM/personal tasks: Basic Memory only when relevant; no CodeGraph. Graphify is optional for a relevant document corpus.
- Coding tasks: prefer CodeGraph for indexed source structure; consult Basic Memory for relevant durable decisions and Graphify for broader code/document relationships. Do not call all three by default.
- Documentation/research tasks: Basic Memory and Graphify when relevant; CodeGraph only for implementation questions in an explicitly scoped repository.
- Do not save every response. Persist explicit remember requests or approved durable decisions/checkpoints, never credentials or unconfirmed speculation as facts.
- Latest final-step request on 2026-10-01 returns Basic Memory harness integration to the plan, initially using existing PostgreSQL/text search. Each connection/registration/test still needs its own concrete approval; none has been enabled. Model selection/downloads, semantic-search setup/tests and unrelated usage tests remain deferred. Preserve the installed service, database and notes; no shutdown/removal/reconfiguration, models, paid APIs or automatic memory use are approved. Notion/AppFlowy PKM integration and bidirectional sync can wait; sync is manual preview-and-approve until independently qualified and approved.
- CodeGraph's first container test indexes only selected `scripts/` Python files and a synthetic fixture, not this entire repository. Its watcher is disabled and no harness registration exists. The separately qualified gateway now exposes only `codegraph_codegraph_explore` at `/mcp/codegraph`; Graphify exposes seven query tools at `/mcp/graphify`. See `docs/CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md` for current topology/session semantics; use the base + CodeGraph gateway overlay only. This does not enable automatic task profiles or Basic Memory use. Never claim index completeness, automatically broaden mounts or infer that absent graph results prove absent source. See `docs/CODEGRAPH-SETUP-PROPOSAL.md` for the verified scope and the `macctl` absolute-argument translation caveat.
