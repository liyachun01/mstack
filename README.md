# mstack

Current default: [one-field project config and routing diagrams](docs/MSTACK-CONFIG.md).
Docker Compose group: **mstack**. [Migration evidence](docs/MSTACK-NAMESPACE.md).

**2026-10-16: [Start with mstack](docs/MSTACK.md).** Each project edits only
`.mstack/stack.json`; generated records live in `.mstack/state.json`. The old
configuration and example projects are retired. [Cleanup status](infra/maintenance/config-retirement/README.md).
Use `./mstack`; `./stack` remains compatible. The directory/project identity stays
`mcp-stack`; Docker Compose uses `mstack`. The everyday workflow is Codex/Claude,
Anytype, and Windmill. Retained shared infrastructure stays available.

Graphify, Anytype MCP and Headroom use [one shared container per tool with project tenants](infra/services/README.md).
New projects require their own qualified grants. CodeGraph remains ignored.
WhoDB is resumed and healthy. [How the harness connects](docs/HARNESS-CONNECTIONS.md)
explains project MCP bindings and why ai-memory/agentgateway remain optional.

The dated entries below are engineering history, not a required startup sequence
or a current service-health report.

**2026-10-15:** the approved Ubuntu mise migration is active. New shells use
repo-owned pinned profiles; {{mstack:CLIENT_REPO_CAMEL}} keeps its project Node selection. Twelve
duplicate apt CLIs and unused standalone Bun files were retired with rollback
copies. The later authorized helper drain also migrated 146 Python environments
and DeepSeek profile dependencies, reconnected MCPs and retired old fnm/uv Python
paths. Application data and private rollback copies remain preserved.
[Migration details](docs/ORB-DEVBOX-MISE-MIGRATION-2026-10-15.md).

**2026-10-08:** unified project config is implemented. Start with `./stack init`,
then `plan/apply/doctor --project <directory>`. Edit project `.mstack/stack.json` and
shared `infra/stack/connections.json`; the gateway registry is generated.
[Config contract](infra/stack/README.md). Owner UI remains editable; apply detects
drift and preserves unrelated projects/keys. Historical inventory below is not
current runtime evidence; use the canonical handover.

Local proof of concept and long-running personal MCP stack. Provider/service provisioning remains separate from project config reconciliation.

**Canonical handover: [status, operating steps, data flow and message flow](docs/HANDOVER.md).**
Keep returning to that same file as integrations progress. It reconciles the
2026-10-05 side-chat results; older status and next-step statements below are historical.

2026-10-06: Anytype is sole PKM, initially local-only; Basic Memory secondary.
ai-memory 2.5.2 installed as an optional working-memory candidate, with no
capture hooks/model keys/registrations. All 26 pre-existing containers are stopped
and were preserved. Model routing and llama.cpp remain pending/later. Current
architecture and credentials are documented in the handover.

**Start working: [small-by-default guide](docs/START-HERE.md).** Updated
2026-10-05: Codex primary; Windmill primary workflows; agentgateway selected/current proxy;
Graphify and Basic Memory retained. Other harnesses, n8n, CodeGraph and OpenWiki
are optional; PKM integrations are later. Preserve `infra/` and engineering history.
[Component catalog](docs/COMPONENT-CATALOG.md) separates desired roles from actual
runtime. [Windmill shared-PG replacement](docs/WINDMILL-SHARED-PG-PROPOSAL.md) is
completed; Activepieces test runtime/data also removed. Use the
[Windmill runbook](docs/WINDMILL-RUNBOOK.md). Older status/next-step statements below are historical
and do not override this decision or authorize follow-on setup.

The repository is `/home/developer/workspace/mstack` inside the OrbStack Ubuntu machine (`devbox`). It is a real directory. From macOS, use `/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack`.

## Current status

- Root `compose.yaml` includes `infra/postgres/compose.yaml` to run isolated PostgreSQL **18.6** + pgvector **0.8.6**, with the image pinned by digest, a named volume, separate administrator/application passwords, and macOS `127.0.0.1:55322` publication.
- First startup, health, authenticated application writes, vector distance queries, correct PG18 persistence mount, and unchanged `{{mstack:CLIENT_REPO}}` inventory are verified. See the [database runbook](docs/DATABASE-START-PROPOSAL.md).
- Supabase is a [disabled future option](infra/supabase/README.md). Its previously installed CLI remains on macOS, but this project's `infra/mise.toml` does not select it.
- macOS global `gh` and `xcbeautify` remain selected. [Global tmux was removed as requested](docs/TMUX-GLOBAL-REMOVAL.md), with config/cache recovery material kept locally. Node is project-specific. Docker/Compose remain OrbStack-provided. The separately approved Ubuntu mise migration is documented above; no duplicate Docker installation was added.
- Basic Memory **0.23.2** is running against PostgreSQL, with 21 MCP tools verified at macOS `http://127.0.0.1:58000/mcp`. Read/write/text search and note persistence across container re-creation passed. Its opt-in overlay is `infra/basic-memory/compose.yaml`; see the [runbook](docs/BASIC-MEMORY-SETUP-PROPOSAL.md). Semantic search is not yet enabled. Basic Memory gateway/harness integration, n8n, semantic search and PKM connections remain deferred or later steps.
- Accepted: [task-profile memory routing](docs/MEMORY-ROUTING.md), with tools used only when relevant. Basic Memory text-search harness integration is now a requested final step, still awaiting concrete connection/test approval. Models/semantic search/unrelated tests stay deferred; PKM can wait. The installed service/database stay unchanged.
- CodeGraph **1.6.1** and Graphify **0.9.72** are installed in separate project-only images and their narrow source-projection/direct MCP tests passed. Graphify's graph has 3 files, 37 nodes, 48 edges and 6 communities, with seven permitted query tools and no model/API use. Config/state are under `infra/codegraph/` and `infra/graphify/`; no host/global install, backend ports, persistent watcher or harness registration. See the [CodeGraph runbook](docs/CODEGRAPH-SETUP-PROPOSAL.md) and [Graphify runbook](docs/GRAPHIFY-SETUP-PROPOSAL.md). {{mstack:CLIENT_REPO_TITLE}}'s pre-existing Graphify remains untouched. Gateway foundation, synthetic qualification and both separately approved graph gateway connections are complete, including [CodeGraph session qualification](docs/CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md).
- Gateway: **agentgateway v1.5.0**, official pinned ARM64 image, **installed/running at macOS `127.0.0.1:58080`**. Strict API-key authentication and HTTP foundation tests passed after the separately approved [network correction](docs/AGENTGATEWAY-NETWORK-CORRECTION.md). Configuration under `infra/agentgateway/`; dedicated normal bridge plus two separate internal graph networks. `/mcp/graphify` exposes seven authenticated query tools; `/mcp/codegraph` exposes one `codegraph_codegraph_explore` tool; bare `/mcp` remains 503. Current Compose recipe is base gateway + CodeGraph overlay only, not both integration overlays. No model provider or harness registration. See the [operating notes](infra/agentgateway/README.md). MetaMCP was never installed; its patch/fork plan is superseded.
- Harnesses: **Codex + official DeepSeek Harness** (`deepseek-ai/deepseek-harness`). Existing DeepSeek CLI updated to0.2.0-rc.2; retained-home Web3080 and forwarder58081/native graph registration/discovery passed. No model/tool-job acceptance implied. Codex stack registration is pending; OpenCode optional, Xiaomi MiMo excluded. [Current runbook](docs/OPERATIONS-RUNBOOK.md).
- n8n: official **2.41.6 installed and healthy** on macOS OrbStack at127.0.0.1:5678, isolated PG18.6 DB/login, private named secret volume, read-only non-root app and bounded cache tmpfs. No paid license, Assistant/sandbox, models or starter kit. [Foundation outcome](docs/N8N-STATIC-CACHE-PROPOSAL.md). Built-in-node router passed25 tests,90 policy cases and4 bundled examples; [approved manual import handoff](integrations/n8n/workflows/README.md), no Code runner required. Future connections/add-ons are deferred, not a mandatory installation chain.
- Latest final steps: use existing Codex IDE and Ubuntu global DeepSeek CLI; qualify Basic Memory text-search integration separately, leave models deferred and PKM optional. The [start-work/operations runbook](docs/OPERATIONS-RUNBOOK.md) includes major n8n workflows, docs/notes locations and proposed manual bidirectional PKM sync. No connections/schedules enabled by documenting them.
- [Synthetic gateway qualification completed](docs/AGENTGATEWAY-SYNTHETIC-HOST-CORRECTION.md): all eight checks passed after the separately approved fixture Host correction, including aggregation, discovery/direct-call enforcement, missing-claim denial, concurrent session/replay checks and fail-closed outage/recovery. Both temporary containers removed; live services/config/key/protected files unchanged. No real MCP server connected. Subsequent Graphify direct transport qualification is recorded below; gateway integration B is now separately completed below. CodeGraph follows independently and Basic Memory stays deferred.
- [Restricted Graphify HTTP direct qualification completed](docs/GRAPHIFY-HTTP-SETUP-PROPOSAL.md): authenticated wrapper reuses installed image/unchanged seven-tool gate/read-only three-file index; all tool/resource/scope/auth/Host/Origin/reconnect/concurrency checks passed. Temporary container removed; private backend credential/hash config/source and empty internal network retained. No downloads, persistent service or gateway/harness registration. Subsequent persistent service A and gateway connection B are completed below; CodeGraph follows independently, Basic Memory deferred.
- [Persistent Graphify HTTP setup A completed](docs/GRAPHIFY-GATEWAY-CONNECTION-PROPOSAL.md): `mcp-stack-graphify-http` is running, internal-only with no host port, reusing the pinned image/adapter/index/key. All direct tests passed; 19 pre-existing containers/267 protected hashes and checked macOS configs unchanged. HTTP is a local transport adapter, not an external provider. [Gateway connection B](docs/GRAPHIFY-GATEWAY-B-PROPOSAL.md) is now approved/completed: seven tools, authentication separation, strict valid-request denials and concurrent sessions verified. Known limitation: malformed unprefixed resource URI returns HTTP 500 before dispatch, not an authorization pass.

Tool/service definitions and application configuration belong under `infra/`. Reusable harness integration source, tests and portable workflow definitions live under `integrations/`. Root Compose is an entry point only; project mise config is `infra/mise.toml`, with a root discovery symlink. Linux shared/CLI/Python profiles are under `infra/toolchains/`; macOS selections remain separate and unchanged. Home shell/command links are discovery plumbing, not independent tool declarations. Markdown lives at `knowledge/main`; Basic Memory's ignored config/log state is `infra/basic-memory/state`.

[CodeGraph session qualification correction/retry](docs/CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md) is approved/completed: both graph endpoints now live, all connected suites and eight in-memory/cold route-replay denials passed. CodeGraph DELETE/reuse 404 and full native 32-session cleanup passed. Stateless Graphify permits authenticated same-route resumption after DELETE; this is not permanent token revocation. Only the gateway was recreated; all 20 other containers, data/indexes, keys, host configs and deliberate caffeinate unchanged. Earlier failed attempts remain in the history. Next: separately scoped project-local harness integration; Basic Memory stays deferred.

## Documents

- [Start-work and operations runbook](docs/OPERATIONS-RUNBOOK.md)
- [Remaining functional phase: n8n + harness integration](docs/N8N-HARNESS-PLAN.md)
- [Setup status](docs/SETUP-STATUS.md)
- [Database start, verification, and rollback](docs/DATABASE-START-PROPOSAL.md)
- [Basic Memory setup, verification, and rollback](docs/BASIC-MEMORY-SETUP-PROPOSAL.md)
- [Accepted memory routing and Basic Memory deferral](docs/MEMORY-ROUTING.md)
- [CodeGraph setup, verified scope and repeatable tests](docs/CODEGRAPH-SETUP-PROPOSAL.md)
- [CodeGraph HTTP direct qualification and next backend approval](docs/CODEGRAPH-HTTP-SETUP-PROPOSAL.md)
- [Graphify setup, verified scope and repeatable tests](docs/GRAPHIFY-SETUP-PROPOSAL.md)
- [Agentgateway assessment and staged plan — foundation installed, integration pending](docs/AGENTGATEWAY-SETUP-PROPOSAL.md)
- [Agentgateway foundation — installed, HTTP checks passed](docs/AGENTGATEWAY-FOUNDATION-PROPOSAL.md)
- [Gateway correction and completion report](docs/AGENTGATEWAY-NETWORK-CORRECTION.md)
- [Historical MetaMCP source assessment — superseded](docs/METAMCP-SETUP-PROPOSAL.md)
- [Sharing setup and team knowledge without publishing private memory](docs/TEAM-MEMORY-AND-REPRODUCIBILITY.md)
- [Database sharing and future AppFlowy/Supabase storage](docs/DATABASE-AND-STORAGE.md)
- [Deferred work and final standalone-skill TODO](docs/TODO.md)
- [Agent instructions](AGENTS.md)
- [Project setup guard](.agents/skills/mcp-stack-setup-guard/SKILL.md)

Existing `{{mstack:CLIENT_REPO}}` Supabase resources are out of scope. Never run broad Docker cleanup or remove data volumes without explicit direction.
