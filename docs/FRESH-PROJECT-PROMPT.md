# Fresh project — three channels

Copy the prompt below into a fresh project/chat and replace the first line.
The inventory after it stays here as reference; it is not startup context.
The toolkit is now named [mstack](MSTACK.md). `daily` is its default preset.

## Copyable prompt

```text
The outcome I want to finish is: [describe one concrete deliverable].

Treat this as a fresh project. My priority is completing useful work with a
small, stable workflow. I have spent too long assembling infrastructure.
Do not resume the old MCP-stack setup backlog or import its entire history.
If this project uses mstack, read .mstack/stack.json and its mstack skill;
generated records live in .mstack/state.json. The old configs and demos
are retired;
use the daily defaults: shared Headroom, Graphify, Anytype and Windmill, with
the existing gstack browser available. Use only relevant tools for the task.
The intent can be just {"project":"my-project"}; grants remain project-specific.
Keep the new project outside the mstack infrastructure repository. Its own
AGENTS.md/skill/config should describe the explicit connection to mstack.

Use three channels:
1. WORK — Codex or Claude for thinking, writing, building, and checking results.
   Use the current harness and provider. Either harness can do a task; involving
   both is optional. Code and executable scripts stay in the project files.
2. DOCUMENTS — Anytype for durable personal context, the project brief, useful
   decisions, and results. Keep one short “How to work with me” note and one
   project note containing objective, current state, and next action. Save useful
   conclusions, not every conversation. Read back any document you update.
3. AUTOMATION — Windmill when a proven task needs repetition or a schedule.
   Define inputs, outputs, and failure reporting; verify a manual run before
   scheduling. Ordinary interactive work does not require a Windmill job.

My working preferences:
- Prefer the smallest solution using what is already available.
- I am using the computer: use background APIs, containers and isolated headless
  browsers. Do not take over app focus, mouse, keyboard or display settings.
  Arrange a quiet slot for onboarding that genuinely requires visible UI.
- Complete and verify a concrete result before expanding infrastructure.
- Progress autonomously on ordinary reversible work within the requested task.
- Ask only for information or authorization actually needed to proceed.
- Keep personal preferences separate from project-specific details. Do not
  assume automatic memory across projects or infer a biography from old chats.

At project start, use the personal note and relevant project brief if I supply
them. If Anytype access is unavailable, work from pasted text and produce a
short note I can save; do not claim it was saved remotely. Missing connectors
must not block work that can be completed without them. Existing connections
belong to their authorized projects; do not inherit another project's access.

Keep the existing harnesses, Anytype, Windmill, Magpie,
Llama.app, PostgreSQL + pgvector, WhoDB, and Garage. OrbStack and mise are protected
system foundations: do not remove them. This retained infrastructure does not
need to be configured or used by every project. Keep existing Headroom, Serena,
and gstack support available; select relevant capabilities for the task. An
explicit shared Headroom binding takes precedence over a duplicate global helper;
its project cache expires originals after one hour and is not personal memory.
Reuse capabilities the harness actually supplies. If a selected tool is missing,
use a shared containerized backend with this project's own tenant/index/grant.
Do not create a tool container per project. A skill alone is not an engine or
index. Graphify is available when needed; ignore CodeGraph for now.

Agent gateways, graph indexes, extra memory databases, alternate harnesses,
and additional workflow engines remain available only when a task needs them.
Existing tool/skill availability does not make using it a project requirement.
Reintroduce a tool only for a concrete requirement in this project: explain the
gap and smallest useful addition, then verify it within the authorized scope.
Do not start a cleanup, installation, migration, or global reconfiguration just
to make this project “ready.” Preserve existing services, data, and credentials.
AI mail integrations and OpenCodex were explicitly removed; do not restore them.
Claude Desktop uses Magpie; Codex integration remains pending explicit request.

Start by identifying the smallest useful deliverable and working on it. If the
outcome above is missing or materially ambiguous, ask one focused question.
End a work session with: result, verification, and next action.
```

## Tool inventory — reference only

Retention decisions updated **2026-10-21, Asia/Shanghai**, using existing recorded
installation evidence. This is the stack's component
inventory, not a fresh uptime audit or a list of every CLI/available plugin.
“Parked” means outside the new project's default workflow; it does not mean stopped
or uninstalled. Selecting a tool does not establish a new project's connection.

| Place | Tools introduced | Recorded state / boundary |
| --- | --- | --- |
| Work channel | **Codex; Claude Desktop** | Codex retains its current route. Claude Desktop is configured for Magpie → official DeepSeek; protocol checks passed, native UI not opened. Codex/Magpie integration awaits explicit request; no Claude Code CLI installation. |
| Document channel | **Anytype** | Local-only chosen. Clock and kase have separately scoped access evidence; a new project gets no inherited grant. Root remains unbound. |
| Automation channel | **Windmill** | Server/worker deployed with shared PostgreSQL; a native project job still needs acceptance when required. |
| Keep: model support | Magpie; official DeepSeek provider | Magpie manages the current Claude Desktop route. OpenCodex and its dedicated data/configuration are removed. Codex/Magpie integration stays pending. DeepSeek provider is a model-service connection, separate from DeepSeek Harness. |
| Parked routing | agentgateway; repo-local `stack` CLI | Existing gateway/config tooling. Neither is required to start a new project. |
| Keep available: code context | Graphify; CodeGraph | Shared `mstack-graphify` runs Graphify 0.9.72 with separate authenticated project indexes. Earlier example and temporary-tenant checks verified isolation; those tenants are now retired. CodeGraph is ignored for now; its retained source/index stay preserved. Skills do not replace engines/indexes. |
| Parked memory | Basic Memory; ai-memory | Retained secondary/experimental stores. No default mirror, transcript capture, or universal personal-memory binding. |
| Parked workflows | n8n | Existing optional workflow engine; Windmill is the selected automation channel. |
| Parked alternate harness | DeepSeek Harness | Installed profile and dependencies preserved; retained-profile startup/inference was not verified by the latest migration. |
| Keep: local inference | Llama.app with its llama.cpp engine | Preserve the macOS app and configuration; weights/inference remain pending. The former standalone llama.cpp installation was retired. |
| Removed: AI mail | Inbox Zero; TimeCyber/email-mcp | Removal is complete. Do not reinstall, reconnect, restore account profiles, or resume onboarding. |
| Keep: storage/admin | PostgreSQL + pgvector; Garage S3; WhoDB | Preserve existing services/data/configuration. Each project uses these only if needed and authorized. The removed mail-specific Redis/HTTP bridge is not a retained foundation. |
| Keep available: harness helpers | Headroom; Serena; gstack skills/browser tooling | Existing add-ons, not inherent features of every harness. Shared Headroom 0.34.0 now offers separate authenticated project caches; existing global helpers remain. No per-project reinstall is needed merely to start work. Choose relevant skills and project scope; project-local installs are an option when needed. |
| Protect: system/runtime foundation | OrbStack Ubuntu/macOS; Docker Compose; mise; Node/Python/Bun/pnpm; uv application environments; macctl | Never remove OrbStack or mise. Reuse existing project runtimes. Docker runs on macOS; Ubuntu and macOS remain separate domains. No migration/startup procedure is inherited. |
| Connector preparation only | Slack; Linear; Figma; optional Notion | Stack registry references/placeholders do not establish live provider grants. Notion is not the chosen document store. Separate app plugins are independent of these bindings. |
| Considered, not adopted here | OpenCode; OpenWiki; LM Studio; this stack's Supabase option | No new-project requirement or installation claim. The unrelated {{mstack:CLIENT_REPO_CAMEL}} Supabase resources are preserved. |
| Retired / superseded / excluded | Activepieces trial; old Windmill trial; standalone llama.cpp; MetaMCP; AppFlowy | Preserve remaining history and unrelated data; do not restore them as setup steps. MetaMCP was superseded rather than installed. |

Use this shelf only after a real requirement appears. Detailed maintenance evidence
remains in [HANDOVER.md](HANDOVER.md) and each component's `infra/` documentation;
the fresh project does not need to read them at startup.

Packaging references: [Graphify skill + CLI](https://github.com/Graphify-Labs/graphify),
[CodeGraph CLI/MCP](https://github.com/colbymchenry/codegraph),
[Headroom MCP](https://headroomlabs-ai.github.io/headroom/mcp/),
[Serena](https://github.com/oraios/serena), and
[gstack](https://github.com/garrytan/gstack). These describe available approaches;
no tool upgrade, backend conversion, or global registration was performed.
