# Deferred work

## Remaining functional phase — n8n + harness integration

Latest direction on 2026-10-01: official n8n without a paid license, guided setup, no Assistant/privileged Assistant sandbox/SearXNG. Integrate both Codex and official DeepSeek Harness, separately qualified; OpenCode is optional, MiMo excluded. Runtime configuration belongs in `infra/`; reusable source/tests/portable workflows in `integrations/`. Recommended order: [database-only approval](N8N-DATABASE-PROPOSAL.md) → application/external Code-node runner proposal → manual/model-free dry-run router → scoped read-only gateway connection → project-local Codex and DeepSeek integrations → useful checkpoint tools → Basic Memory text-search connection. See [scope and staged plan](N8N-HARNESS-PLAN.md). No install, DB provision, workflow import or registration is approved yet. Model/semantic-search deferrals, optional delayed PKM, backup/restore readiness and the final standalone workflow-skill TODO remain intact.

### Latest final-step checklist

- [ ] n8n prerequisite: database-only step still awaits approval; then independently approve networking, application/ordinary task runner and workflow imports.
- [ ] Codex IDE: already installed per user; qualify project-local graph/n8n MCP connections, no reinstall/global registration. Resolve native `.codex/config.toml` discovery while canonical settings stay in `infra/`.
- [ ] DeepSeek CLI: existing Ubuntu global `@deepseek-ai/dsh` 0.1.0-rc.7, bundled MCP client 0.1.0-rc.8. Reuse through a version-checked project launcher with project-local `DSH_HOME`, profiles, secrets, permissions/privacy review and resume. Do not install another copy or upgrade fnm/Node/global config automatically.
- [ ] Basic Memory integration: returned to the plan by this request; start with installed PG/text search, separately approve connection/tests. Embeddings, models and unrelated tests stay deferred. No automatic capture of every response.
- [ ] PKM (can delay): Notion MCP connection/use and separately AppFlowy service installation plus maintained/pinned MCP integration. Test approved page access first; writes and attachments independently gated.
- [x] Generate [working operations runbook](OPERATIONS-RUNBOOK.md): project/session identity, major n8n workflows, startup, monitoring/logging, notes/docs locations, manual bidirectional memory↔PKM sync and export/clean/migration flow. This is documentation, not completed runtime integration.
- [ ] Qualify runbook commands/end-to-end workflows as each component is installed. Check conflict/retry/deletion/privacy behavior before any automatic sync, and prove backup restore before stack-complete status.

This latest checklist supersedes earlier blanket Basic Memory harness-integration deferral. PKM can wait; model/semantic-search deferral and every per-step approval remain intact.

## Optional n8n/AI add-ons — not installed or approved

- **n8n Assistant + its sandbox:** reconsider only if AI-assisted workflow building becomes useful. Requires a separately selected model provider, permission/resource review and installation approval. The latest decision excludes it now; neither Ollama nor Qdrant is a prerequisite.
- **Ollama:** consider for a concrete local-model workload. Review model license, multilingual quality, disk/RAM/battery cost and macOS native versus container inference before choosing a deployment domain. Do not download models or change Basic Memory during its deferral.
- **Qdrant:** consider only for a workflow needing its vector-store API/features. Existing pgvector is another option, not a drop-in replacement. Propose independent persistence/backup/resources/ports; no bundled PG downgrade or second database stack by default.
- **AI starter kit examples:** learning references only, not a deployment target. Its bundled services are unnecessary for the current model-free router. [Official starter kit](https://docs.n8n.io/deploy/host-n8n/deploy-with-the-ai-starter-kit).

## Evaluate retiring the OrbStack Ubuntu development machine

After the local `mcp-stack` is stable and backed up, evaluate migrating the development workflow from the OrbStack Ubuntu machine to macOS-native tooling managed with macOS `mise`.

Expected benefits:

- One filesystem path instead of translated macOS/Ubuntu paths.
- Direct access to OrbStack's Docker and Compose commands.
- One system-level toolchain and fewer socket/permission boundaries.
- Simpler selected-harness (OpenCode, a DeepSeek harness, or Codex), MCP, backup, and service configuration.

This is intentionally deferred. Do not begin the migration until the current stack has documented versions, backups, restore steps, and a tested cutover/rollback plan.

### Assessment (2026-09-30)

Decision: do not retire `devbox` yet. A project-scoped macOS `mise.toml` can make CLI versions reproducible, but `mise` is a tool/version manager rather than a filesystem, process, package, or service isolation boundary.

Observed dependencies and risks:

- `devbox` currently reports 47.7 GB of disk usage.
- Important apparent-size areas include `/home/developer/workspace` (17 GB), `/home/developer/.local` (12 GB), `/home/developer/.codex` (5.4 GB), and `/home/developer/.cache` (21 GB). These figures must not be added directly because filesystem accounting, caches, and copy-on-write data can overlap or compress differently.
- The active `{{mstack:CLIENT_REPO}}` Supabase stack bind-mounts files from `/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/{{mstack:CLIENT_REPO}}`. Deleting the machine before migrating those paths would break affected containers even though database and storage data use Docker volumes.
- The active `backend-db-1` Compose project records a working directory inside `devbox`.
- Codex configuration/history and several development tool homes currently live under the Linux home directory.
- The new `mcp-stack` repository is currently inside `devbox` and has not yet been committed.

Estimated migration effort: roughly 2-4 active working days, followed by a 2-7 day non-destructive soak period before deleting anything.

Migration phases:

1. Inventory Linux packages, repositories, credentials/config references, services, scheduled jobs, and all Docker bind mounts.
2. Export `devbox` and back up every relevant Docker volume before cutover.
3. Move repositories and intentional persistent files to stable macOS paths; do not bulk-copy disposable caches.
4. Keep the intentional global iOS tools (`gh` and `xcbeautify`); declare Node and other project runtimes in project-level `mise.toml` files and verify each repository independently.
5. Recreate container bind mounts from macOS paths and verify `{{mstack:CLIENT_REPO}}` without changing its data or ports.
6. Run Codex and the MCP stack natively on macOS, then test startup, backup, restore, upgrades, and rollback.
7. Stop—but do not delete—`devbox` for the soak period. Delete it only after all workflows and restores pass.

Storage-cleanliness controls needed after migration:

- Keep stateful services in explicitly named OrbStack Docker volumes and export them regularly.
- Keep repository configuration in version-controlled project files; keep secrets in ignored local files or the system keychain.
- Pin project tool versions; keep only the intentional `gh` and `xcbeautify` global selections for native iOS development.
- Document the location and cleanup method for macOS `mise` installs, caches, Codex state, package caches, and application data.
- Consider a dedicated macOS user if strong separation from the personal home directory remains a requirement; `mise` alone does not provide that separation.

### Updated preferences and open questions (2026-10-01)

- macOS global `gh = "latest"` and `xcbeautify = "3.2.1"` remain for native iOS development; the Node declaration has been removed. Existing Node installations are retained.
- Other current projects remain in `devbox`. Occasional, documented user-level caches on macOS are acceptable, so a dedicated macOS user is optional and VM retirement has lower priority.
- Supabase CLI `2.118.0` was installed and verified, but is no longer selected by the root mise config: the current database uses PostgreSQL + pgvector through Compose. Retain Supabase as a deferred option with separate approval and ports.
- npm's default Unix cache is `~/.npm`. Its cache can be cleared with `npm cache clean --force` or relocated with the `cache` setting. Inspect custom contents before removing an entire `.npm` directory; user configuration and credentials in `.npmrc` are separate from the cache. Removing the global Node declaration does not remove Node binaries or npm caches.

Open migration questions:

- Do any iOS repository scripts or editor integrations require Node? If so, declare it in that repository before relying on it there.
- Is there enough operational benefit to moving the harness or `mcp-stack` to macOS while leaving existing projects in `devbox`?
- Which caches, application state, and persistent data would move to macOS, and how will each be located, backed up, or cleaned?
- Can VM-dependent bind mounts in existing services be eliminated without interrupting those projects? This needs separate authorization from their owners before migration work.

References: [mise configuration](https://mise.jdx.dev/configuration.html), [npm cache](https://docs.npmjs.com/cli/v11/commands/npm-cache/), [Supabase CLI 2.118.0](https://github.com/supabase/cli/releases/tag/v2.118.0).

## Deferred Supabase extension

Retain `infra/supabase/config.toml` only as a starting point. Evaluate Auth, Storage, Realtime, API, or Studio services when a concrete need appears. Plan data migration and isolated ports before enabling it; the Compose database volume must not be repurposed silently. The installed Supabase CLI is retained; its removal is outside the current cleanup.

For AppFlowy, evaluate its current self-host distribution/license and S3-compatible image storage at the PKM step. Its official template currently uses PG16; test PG18 compatibility before sharing the new database instance. Prefer per-component databases/roles over schema-only isolation unless each application's migrations explicitly support the latter. Supabase Storage remains an optional evaluated provider, not a prerequisite. See [assessment](DATABASE-AND-STORAGE.md).

## Next memory steps

- Optional future battery review: [measured workload and cleanup report](RESOURCE-ASSESSMENT.md). User confirmed caffeinate is deliberate to keep AI running with the lid closed; preserve it, do not treat it as unwanted or kill/reconfigure it. Focus any later review on sustained whole-OrbStack/desktop load and explicitly approved power profiles; A/B service shutdown, health-check or CPU/RAM changes need separate approval. Basic Memory stays deferred; image cleanup does not eliminate running-service power use.
- Completed: [explicitly requested macOS global tmux removal](TMUX-GLOBAL-REMOVAL.md). Global gh/xcbeautify retained; no tmux configs/processes found. Ignored config/cache backup retained, no Ubuntu mise/config change.
- Completed: [gateway session qualification correction/retry](CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md), approved with “continue”. Both graph endpoints live; full connected suites, eight in-memory/cold replay denials and CodeGraph 32-session cleanup passed. Graphify authenticated same-route token resumption after DELETE confirmed, not permanent revocation; auth/tool/project gates unchanged. Gateway alone recreated, all other containers/data/indexes/host configs/caffeinate preserved. Earlier rolled-back retry remains historical. Next: n8n foundation and separately approved Codex + official DeepSeek Harness integrations, including Ubuntu-to-macOS networking and credentials kept out of versioned config. No install/global registration or Basic Memory integration authorized yet.
- Completed: [persistent CodeGraph backend A](CODEGRAPH-GATEWAY-CONNECTION-PROPOSAL.md), approved with “approve”; internal-only running `mcp-stack-codegraph-http`, exact qualified image/read-only engine/index/adapter/key, complete direct and Graphify/gateway regression checks passed. All 20 prior containers/268 protected hashes/10 additional files and fresh macOS configs unchanged; no watcher/writer/re-index/download/global/harness/gateway mutation or Basic Memory call. Next: [CodeGraph gateway connection B](CODEGRAPH-GATEWAY-B-PROPOSAL.md) requires separate approval and briefly recreates only the gateway; no backend restart or profile/harness registration included.
- Completed: [CodeGraph temporary HTTP direct qualification](CODEGRAPH-HTTP-SETUP-PROPOSAL.md), approved with “continue test”. Pinned existing image/Node built-ins only, native read-only engine/per-client sessions, exactly three read-only source files/index; all direct positive/negative/useful-source/concurrent-session/capacity checks passed, 20 prior containers/267 prior protected hashes unchanged. New separate key/hash config, source and empty internal network retained; temporary container removed. No indexing/writer/watcher/download/global config/gateway/harness change or Basic Memory call. Next: separately approve [persistent CodeGraph backend A](CODEGRAPH-GATEWAY-CONNECTION-PROPOSAL.md), then exact gateway connection B; neither is approved by the temporary test. See runbook for the prior inspection SHM side effect, corrected relative-path assertion and historical macOS Codex baseline limitation.
- Completed: [persistent Graphify HTTP backend A](GRAPHIFY-GATEWAY-CONNECTION-PROPOSAL.md), authorized with “Continue”. Internal-only running container, existing exact image/index/adapter/key, no host port/downloads; all direct tests passed. 19 prior container snapshots/267 protected hashes and checked macOS configs unchanged. [Gateway connection B](GRAPHIFY-GATEWAY-B-PROPOSAL.md) is now separately approved/completed: seven tools, auth separation, scoped denial and actual concurrent sessions passed; original keys/config/data intact. Record the malformed unprefixed resource URI HTTP 500 as a routing-error limitation, not authorization success; assess upstream error mapping separately, no automatic patch/upgrade. Next: prepare a separate CodeGraph HTTP/direct transport proposal preserving the scoped index and single-writer boundary; do not start/register/index it yet. Basic Memory remains deferred.
- Gateway decision (2026-10-01): **agentgateway replaces MetaMCP**. The [assessment and staged plan](AGENTGATEWAY-SETUP-PROPOSAL.md) records official v1.5.0 ARM64 image metadata, aggregation/authorization capabilities and the recommended file-configured, database-free foundation. Product selection is not install approval. MetaMCP was never installed; its [version/source correction](METAMCP-SETUP-PROPOSAL.md) remains historical research, not an active patch/fork task.
- Completed: [Basic Memory 0.23.2](BASIC-MEMORY-SETUP-PROPOSAL.md) on PG18.6, verified migrations, direct MCP note workflow, and application container re-creation persistence.
- Accepted on 2026-10-01: [task-profile memory routing](MEMORY-ROUTING.md), with per-step tool selection instead of mandatory memory calls on every input/output. Gateway enforcement is not implemented yet.
- Completed: [CodeGraph 1.6.1 isolated container/direct MCP tests](CODEGRAPH-SETUP-PROPOSAL.md), with a narrow 3-file Python projection and retained SQLite index; no host installs or harness registration. Watcher and full-repository indexing are not completed.
- Completed: [Graphify 0.9.72 container/direct MCP tests](GRAPHIFY-SETUP-PROPOSAL.md), 3 files/37 nodes/48 edges/6 communities, zero LLM tokens, seven-tool pre-dispatch gate, read-only reconnect and unchanged existing services. {{mstack:CLIENT_REPO_TITLE}}'s pre-existing Ubuntu user-level Graphify 0.9.39 remains untouched; do not relocate/remove/upgrade it here.
- Completed: [gateway-only foundation and network correction](AGENTGATEWAY-NETWORK-CORRECTION.md), approved with “Do” then “Continue!”. Official v1.5.0 running at macOS `127.0.0.1:58080`, strict API-key HTTP/route tests passed, original key/config preserved, existing resources/data unchanged. Normal project bridge permits outbound connectivity; no backend/model configured. Root Compose/mise unchanged. No real MCP server or harness registration; Basic Memory remains deferred and Helm ignored.
- Completed: [synthetic gateway qualification after approved Host correction](AGENTGATEWAY-SYNTHETIC-HOST-CORRECTION.md). All eight matrix checks passed, including actual concurrent sessions, direct-call denial/counter checks and outage/recovery. Both temporary containers removed; 19 existing snapshots/260 protected hashes and checked macOS configs unchanged; live foundation verifier passed. Config/source and empty test network retained; no downloads/global changes/real memory calls. Initial 421 failure retained in history. Next: prepare exact Graphify HTTP transport/direct-test proposal preserving the seven-tool gate and existing read-only corpus/index; obtain approval, report, then separately qualify its gateway connection. CodeGraph transport/connection follows independently with scoped index and one-writer constraints. No auto-install, watcher, indexing expansion or harness registration. Do not enable Basic Memory integration while deferred.
- Completed: [Graphify HTTP direct qualification](GRAPHIFY-HTTP-SETUP-PROPOSAL.md), approved with “Approve”. Existing exact image, unchanged seven-tool gate/read-only index; missing/wrong/duplicate auth, all tools/resources, PR/foreign-project/URI gates, Host/Origin, reconnect/concurrent-read checks passed. Temporary container removed; new private backend key/hash config/source and empty internal network retained. 19 existing snapshots/260 existing protected hashes and checked macOS configs unchanged; one new hash-config entry (261 total); live foundation checks passed. Next: exact persistent-service/network/backend-auth/gateway connection proposal and separate approval, before restarting Graphify/editing live gateway; no harness registration. CodeGraph follows independently with one-writer/scoped-index constraints. Basic Memory remains deferred.
- Remaining functional phase: n8n foundation/workflow POC first, then separately approved project-scoped profiles for selected harness options: **OpenCode directly, a DeepSeek harness, or Codex**. Follow [the staged n8n/harness plan](N8N-HARNESS-PLAN.md), not a requirement to intercept every interactive message. Xiaomi MiMo Code is excluded. Resolve the exact DeepSeek harness and verify each chosen distribution/version/configuration before integration; do not equate a DeepSeek model provider with a separate harness or install all candidates by default. Keep templates/config under `infra/`, separate client credentials/sessions, test the Ubuntu/macOS route and concurrent sessions where applicable, and preserve CodeGraph's single-writer constraint. No harness install/registration is approved by recording this preference. Validate each server directly before gateway registration; do not auto-index unrelated repositories, broaden corpus, enable watchers or semantic/LLM extraction without an explicit scope/provider proposal.
- Team/repository portability: follow [versioned setup and reviewed knowledge separation](TEAM-MEMORY-AND-REPRODUCIBILITY.md). Current files are versionable but still untracked; commit/push only when requested. Parameterized paths/UIDs, non-OrbStack Docker, other architectures, secret-free per-project harness templates and reproducible index source-revision metadata are not yet implemented. Do not publish ignored personal notes or migrate {{mstack:CLIENT_REPO}} as part of this work.
- Deferred at the user's request on 2026-10-01: Basic Memory model selection/downloads, multilingual embedding/semantic-search setup and tests, further usage tests, and harness/PKM integration. The user will investigate models in the app first. Preserve the installed Basic Memory service, database and notes; do not uninstall or stop them. Model experiments in the app do not imply an embedding-provider change in the stack.
- Implement project-scoped database and Markdown/config backups and exercise restoration before declaring the stack stable. Named volumes are not backups.

## Final step only — extract a standalone OrbStack + macOS workflow skill

Requested on 2026-10-01. Keep this as the last implementation step, after the MCP stack is working and its operating procedure has been verified. Do not create, install, activate, or execute this standalone skill now. These future requirements do not authorize Ubuntu mise configuration, new machines, SSH changes, harness installation, or cleanup in the current project.

Planned scope:

- Create an OrbStack development machine with a selectable Linux distribution; use Ubuntu by default. Inventory existing host and machine tools before proposing installs.
- Prefer mise for supported development tools in the chosen execution domain. Bootstrap requirements and OS-provided tools must be handled explicitly; preserve macOS Xcode/Command Line Tools Git and existing OrbStack Docker/Compose unless a deliberate replacement is approved.
- Provide a small global baseline: Git and GitHub CLI (`gh`). Candidate additions are `ripgrep` (`rg`), `jq`, `fd`, and `fzf`, because they are general-purpose search, JSON, and navigation utilities. Treat this as a proposed baseline, not an install list. Prefer tools already supplied by the OS and avoid redundant copies.
- Use project `mise.toml` files for Node, Python, Go, package managers, service CLIs, and other project dependencies; allow project-level overrides of global tool versions when the project needs them. Record resolved versions, installs, caches, and state locations.
- Keep existing native iOS development needs separate: macOS global `gh` and `xcbeautify` remain intentional selections.
- Support both **one project per machine** and **multiple projects per machine**, with clear ownership of repositories, user homes, ports, Docker volumes, credentials, and per-project config. Provide a choice between stronger separation and lower machine-management overhead.
- Include 瘦身 (slimming): inventory size and usage, identify redundant tool installations, obsolete versions, package caches, build artifacts, and unused machine data; propose exact removals and verify recoverability. Never treat existing databases, credentials, repositories, or Docker volumes as disposable cache.
- Include macOS SSH connection configuration, OrbStack's built-in SSH support, key/agent handling, and stable machine aliases. Document where host and guest configuration belongs; do not copy private keys unnecessarily.
- Include host-to-machine connections for Codex, Claude Code, and other selected harnesses. Verify each harness's supported connection method and account/authentication requirements at implementation time. Document working directory, environment, persistence, MCP configuration, and reconnect behavior.
- Include backup/export, restore, update, cleanup, and uninstall workflows, plus the per-step before/after reporting requested by the user.

Completion gate: the actual `mcp-stack` workflow is stable, backups/restores have been tested, and all preceding setup steps are complete. Only then generalize the demonstrated workflow into the standalone skill with separately approved setup actions.
