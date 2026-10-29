# Remaining functional phase: n8n + Codex/DeepSeek Harness

Latest decision on2026-10-01: official self-hosted n8n without a paid license, guided setup, **no n8n Assistant or Assistant sandbox**. Codex and official DeepSeek Harness requested. **2026-10-04: n8n2.41.6 app foundation completed**, healthy/zero restarts, macOS UI **http://127.0.0.1:5678/**; readiness/editor/setup/JS asset200, isolated PG18.6 DB/142 public tables, private secret volume and64MiB cache tmpfs, read-only non-root runtime. [Qualification/limits](N8N-STATIC-CACHE-PROPOSAL.md). Owner login is user-reported; first router source/in-memory tests are complete, while import/editor acceptance, ordinary external Code runner and live integrations remain pending. No model/Assistant/paid license or automatic memory use. Native DeepSeek graph registration completed on2026-10-03; older harness research below is historical. Do not repeat installers.

2026-10-04 workflow update: owner login is user-reported. The [portable dry-run router](../integrations/n8n/workflows/README.md) now exists; 90 policy cases and four bundled examples pass installed VM/Edit Fields/Split Out implementations. Import/manual test is **approved**, but Edge blocks browser JavaScript automation, so the existing UI handoff is required; saved/editor acceptance remains unverified. **Built-in-node workflows do not need the external Code runner.** The user requests no more automatic setup steps; stop after this bounded workflow. Remaining approval sequence below is a deferred roadmap, not a request to continue. No imports, credentials, models, graph calls or schedules activated by authoring/testing.

Latest final-step request returns Basic Memory harness integration to the plan, initially using existing text search/PostgreSQL and separately approved connection/tests. Models, semantic search and unrelated usage tests remain deferred; PKM installation/integration can wait. Preserve its service/database/notes, {{mstack:CLIENT_REPO}}, stopped containers, deliberate caffeinate and graph indexes. Backup/restore qualification remains necessary; the standalone OrbStack/macOS workflow skill stays the last generalization step. The [operations runbook](OPERATIONS-RUNBOOK.md) records session startup, major workflows and proposed manual bidirectional PKM sync.

## Current scope

- Use official n8n without a paid license. “Community” is its default self-hosted license tier, not a third-party fork. Guided setup explains and gates each step; the user creates the owner account in the UI without sharing its password. [Edition comparison](https://docs.n8n.io/deploy/host-n8n/community-edition-features.md).
- Existing macOS OrbStack Docker/Compose through `macctl run`; no Ubuntu mise, host Node/npm, duplicate Docker, Helm or public tunnel. Runtime configuration belongs in `infra/`.
- Proposed app scope: n8n plus a matched-version **ordinary external Code-node task runner**, without privilege escalation or Docker socket. This is not the Assistant sandbox or a Codex/DeepSeek execution bridge. No `sandbox-certs`, `sandbox-api`, privileged `sandbox-runner-1`, SearXNG, local models, Redis/queue workers or community-node packages. Use official artifacts/configuration, not patched binaries. [Task runners](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-task-runners).
- Reuse PostgreSQL **18.6**, separate database/login `n8n`. No Basic Memory schema/credentials, PG downgrade, Supabase setup or second PG container. [PG18 support and permissions](https://docs.n8n.io/deploy/host-n8n/configure-n8n/choose-n8ns-database).
- Proposed UI: macOS `127.0.0.1:5678`; recheck listeners and all retained container bindings before allocating. Broker internal only. Persist `/home/node/.n8n` and retain an independent encryption key. Exports/logs are not automatically secret-free.
- DB-only provision needs no network/service change. For the later app proposal, investigate a dedicated n8n DB bridge attached to the existing PG container without a restart, with matching Compose declaration and persistence qualification. Avoid joining the memory network: Basic Memory there is unauthenticated and deferred. No graph-backend network membership; later graph requests use the gateway. These network changes are not implemented or approved.
- No model/provider keys, paid calls, schedules, gateway connection or agent jobs in the foundation. Use bounded manual execution, retention/log caps, measured CPU/RAM; limits are not battery measurements.

## Read-only artifact discovery — no installation

Inspected on 2026-10-01; revalidate before the app proposal. Stable release inspected: [n8n 2.41.5](https://github.com/n8n-io/n8n/releases/tag/n8n%402.41.5).

| Official image | Version | Multi-platform manifest digest | ARM64 compressed layers |
| --- | --- | --- | --- |
| `n8nio/n8n` | `2.41.5` | `sha256:6f532d3b819cfe66c6a13c5375228f312c53df1abaa11a377eb8c3d3f105c363` | 269,098,636 bytes |
| `ghcr.io/n8n-io/runners` | `2.41.5` | `sha256:32619142405e7f4a02eedffe8584214c7e0b9b09d3753094e4212aee5f4d0045` | 187,959,886 bytes |

Both manifests contain Linux ARM64. Metadata-only inspection: no image pull, runtime qualification or vulnerability scan. Compressed bytes are not final disk/RAM use. The later proposal must verify advisories, secrets, users/permissions, runner readiness, resources and topology. No runnable Compose file created.

## Future add-ons

Recorded independently in [TODO](TODO.md), not a mandatory bundle:

- **Assistant:** optional AI-assisted workflow building. Needs a chosen model provider and a sandbox, not Ollama/Qdrant specifically. Ordinary workflows do not depend on it. Review model cost, privileges and resources separately before activation. [Requirements](https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-n8n-assistant).
- **Ollama:** optional local inference for a concrete workload; no automatic model downloads or Basic Memory reconfiguration.
- **Qdrant:** optional vector-store API/features for a concrete workflow. Existing pgvector is another option, not a drop-in API replacement.
- **AI starter kit:** learning examples only, not deployment. It bundles n8n/Ollama/Qdrant/PG; do not duplicate services or import demo credentials/workflows automatically. [Official kit](https://docs.n8n.io/deploy/host-n8n/deploy-with-the-ai-starter-kit).

## Harnesses and source placement

Both **Codex** and official **[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)** are selected. This is not simply choosing a DeepSeek model in another client. OpenCode remains optional, MiMo excluded. Integrating both does not authorize concurrent agents or model calls.

- `integrations/`: reusable adapters, contracts, tests and secret-free portable workflow definitions. Create concrete files at their implementation step, not empty scaffolding. Versionable placement is not commit/push approval.
- `infra/n8n/`: DB/service definitions and runtime settings.
- `infra/harnesses/`: project-local launch/profile/endpoint configuration; future secret-bearing state must be ignored/restricted. No global MCP registration or copies of home-directory auth stores.
- Agent instructions/skills stay in project discovery locations.

The user reports Codex IDE already installed; no reinstall is needed. Prior read-only discovery found CLI **0.159.2** in Ubuntu. IDE and CLI support native project discovery through `.codex/config.toml`; CLI `-c` overrides do not configure IDE sessions. Keeping canonical config in `infra/` may require a separately approved/tested `.codex/config.toml` discovery pointer, not global edits. No pointer, registration or job created. [Official MCP configuration](https://learn.chatgpt.com/docs/extend/mcp).

Official DeepSeek Harness is a developer preview. Local metadata now confirms an existing Ubuntu global `@deepseek-ai/dsh` **0.1.0-rc.7**, bundled MCP client **0.1.0-rc.8**, installed under fnm Node **24.19.0**. These existing versions were not installed by this step. Reuse them through a proposed project launcher: explicit Node/runtime version checks, `DSH_HOME` under ignored `infra/harnesses/deepseek/state/`, reviewed profiles/patches and session resume, no `npx`/plugin auto-install or changes to `~/.dsh`. The temporary fnm multishell path is not a stable pin. Local boot source supports `DSH_HOME`; first profile boot can create files/symlinks, so it was not executed. Do not run config dumps that may expose inherited keys. Verify permissions, uploads, instruction discovery and HTTP MCP against the installed version before booting real source. Source commit `639ed015397290b3745d163aafe02ffee4aa3f84` remains upstream research, not the local installed package's proven commit.

Harness: interactive interface. Gateway: authenticated MCP routing. Graphify/CodeGraph: scoped read-only context. n8n: explicit task/checkpoint orchestration, not automatic interception of every message/tool call.

## First acceptance workflow

Manual, **model-free dry-run router**:

1. Accept `task`, explicit known `profile`, approved repository/corpus identifier and `dry_run=true`.
2. Reject unknown/missing profiles/scopes; no guessing, installs or indexing.
3. Coding: propose CodeGraph, Graphify only for relevant broader relationships. Documentation/research: relevant approved Graphify corpus, CodeGraph only for implementation questions. PKM/personal: no CodeGraph; report Basic Memory deferred without calling it.
4. Return structured next actions and mutation approval flags. No model, graph call, memory write or agent job.

Next separately qualify one authenticated read-only gateway request: initialization/discovery/query/cleanup, prefixes/session semantics, timeouts, auth/scope/failure tests. MCP Client Tool is an AI-agent subnode, not proof of model-free general-purpose MCP support; qualify a suitable native HTTP flow/client before promising interoperability.

Initial interactive direction: harness calls a selected authenticated checkpoint workflow/tool. MCP Server Trigger supports HTTP/SSE, not stdio; qualify each client. Automated n8n-to-harness jobs need a separately approved bounded bridge, not arbitrary shell, home/repository/Docker socket mounts or a harness inside n8n.

## Approval sequence

1. **Database only — completed 2026-10-04:** [outcome](N8N-DATABASE-PROPOSAL.md), restricted new DB/login, global-metadata backup, transactional probe and cross-database denials. No image/service/network change. Do not rerun provisioning.
2. **App/network — completed2026-10-04:** official pinned2.41.6 healthy, readiness/UI HTTP foundation, non-root/read-only/security/volume/key/cache/isolation checks passed; [evidence](N8N-STATIC-CACHE-PROPOSAL.md). Ordinary external Code runner remains a separate future proposal when needed, not a prerequisite to the built-in-node router. Never repeat installers or start all Compose dependencies.
3. **Guided owner setup/remaining qualification:** user chooses UI credentials privately; browser rendering and later restore/persistence/resource checks. Migrations/readiness already passed; no model key needed.
4. **Dry-run router**, then independent **read-only gateway connection**; portable exports under `integrations/`, schedules/providers disabled.
5. **Codex IDE**, then independently **existing DeepSeek CLI**, project-local config and qualified permissions/MCP/auth/networking; no reinstall by default. Basic Memory connection is a separate step.
6. **Checkpoint tools**, then only a concretely useful bounded job bridge. Actual model calls require separate approval.
7. **Basic Memory connection**, existing text-search baseline, scoped read acceptance and explicit write approval; no embeddings/models automatically.
8. **Optional delayed PKM:** Notion connection, AppFlowy installation then qualified MCP, each separately approved. Manual sync preview before any write/schedule. Complete the runbook's restore/export checks and useful end-to-end tasks before claiming the final steps done.

Follow the [setup guard](../.agents/skills/mcp-stack-setup-guard/SKILL.md): before-report, explicit approval, after-report and pause before the next component. Rollback targets newly approved resources only; never broad `down`, orphan cleanup, volume deletion or existing DB permission changes.
