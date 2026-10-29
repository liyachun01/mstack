# Start work and operate mcp-stack

**Current handover: [status, operating steps and flows in one file](HANDOVER.md).**
Use that same file as work progresses. The dated qualification records and
historical next-step sections below are retained as detailed references.

> 2026-10-05: [the simplification decision](START-HERE.md) takes precedence.
> This document preserves existing runtime/history; old product choices and
> “next steps” are not mandatory. Agentgateway remains selected; MetaMCP is superseded;
> Windmill shared-PG replacement is complete; its trial and Activepieces test runtime/data were removed.

**Everyday entry point: [Start here — no setup chain](START-HERE.md).** The user
approved the router import/synthetic test on 2026-10-04 and requested a stopping
point, not another sequence of setup approvals. Four synthetic cases are now
bundled into one manual run. Edge blocks Apple Events JavaScript automation;
the agent has not imported/executed the saved workflow or changed that setting.
Use the already-approved UI handoff. Remaining integrations below are a deferred
roadmap, not instructions to continue installing components.

Working runbook, updated2026-10-04. **DeepSeek native graph initial registration/discovery passed on2026-10-03; n8n2.41.6 is healthy on macOS OrbStack at http://127.0.0.1:5678/, with zero restarts and readiness/editor/setup/JS HTTP200.** [Completed app qualification](N8N-STATIC-CACHE-PROPOSAL.md). Owner account/login is user-reported. The [first manual router](../integrations/n8n/workflows/README.md) is built and in-memory qualified, not imported into n8n yet. Ordinary external Code runner, saved/editor workflow qualification, graph tool/model execution and long-idle recovery, Codex stack registration, memory connection and PKM/sync remain implementation targets. Do not rerun installers. No command here grants permission to install, start/stop/reconfigure services, register MCP, copy private data or run model jobs.

Follow the [setup guard](../.agents/skills/mcp-stack-setup-guard/SKILL.md): before-report with exact target/version/files/impact/verification/rollback, explicit approval, after-report, then stop before the next component. Preserve {{mstack:CLIENT_REPO}}, all stopped containers and deliberate caffeinate. Never use broad Compose `up/down`, `--remove-orphans`, unscoped pruning or volume deletion.

## 1. Remaining work and exit criteria

| Step | Current state | Done when |
| --- | --- | --- |
| n8n foundation and orchestration | Official2.41.6 healthy at macOS5678; owner login user-reported; router source and 90 synthetic cases qualified in memory, import/UI pending; runner absent | Guided router import/manual test, persistence/restore checks; separately install a Code runner only when a Code-node workload needs it |
| Codex IDE connection | Installed per user; stack MCP not registered | Correct execution domain, project-local discovery/auth, graph scope and n8n checkpoint tested without global config edits |
| DeepSeek connection | Retained-home Web3080, forwarder58081, both native graph entries active; [7+1 discovery qualification](DEEPSEEK-LOOPBACK-MCP-ACTIVATION-PROPOSAL.md) | Scoped tool/model usage, long-idle recovery, permissions/privacy/session resume and later n8n integration pass |
| Basic Memory integration | 0.23.2/PG/text search running; connection not enabled | Explicitly approved scoped read/search, write confirmation and cross-project denial tests; no model download required |
| PKM | Can delay; no integration performed | Notion scope/auth and AppFlowy deployment/storage/MCP independently qualified; manual sync tests pass |
| Operations | This runbook created; recovery not proven | Safe startup/log checks, useful sessions, export/isolated restore and documented rollback tested |

No Assistant, privileged Assistant sandbox, SearXNG, Ollama or Qdrant in the initial scope. Model/embedding/semantic-search work remains deferred. PKM completion is not necessary to start coding sessions. The standalone generalized OrbStack/macOS skill remains the last later step, not replaced by this runbook.

## 2. Identify project, task and session before work

Open the actual target repository, not just the infrastructure repository. For this project:

- Ubuntu: `/home/developer/workspace/mstack`, machine `devbox`.
- macOS mirror: `/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack`.
- Docker/Compose run on macOS through `macctl run`; an Ubuntu `127.0.0.1` is not automatically macOS loopback. Existing verifiers use host-side curl. Determine where the IDE's MCP client actually runs before choosing its URL; do not widen port bindings or open tunnels by assumption.
- Config/services: `infra/`; reusable integration source/tests/workflows: `integrations/`; credentials: ignored `.secrets/`; personal notes: ignored `knowledge/`.

At session entry, record this proposed envelope in the session/checkpoint, not global harness configuration:

```json
{
  "project_id": "mcp-stack",
  "repository": "/home/developer/workspace/mstack",
  "execution_domain": "ubuntu-devbox",
  "session_id": "new-unique-stack-session-id",
  "harness": "codex-ide",
  "harness_session_id": "client-native-id-if-available",
  "task_id": "new-unique-task-id",
  "task": "Synthetic task description; never include credentials",
  "task_profile": "coding",
  "memory_project": "main",
  "index_scope": "approved-three-file-projection",
  "memory_writes": "explicit-confirmation",
  "pkm_sync": "off",
  "dry_run": true,
  "implementation_question": true,
  "broader_relationships": false,
  "durable_decisions": false
}
```

The portable router v1 validates the relevant subset of this envelope, not a currently registered API. Its exact profiles are `coding`, `documentation-research`, `pkm-personal`; harness labels are `codex-ide`, `deepseek-harness`. See the [router contract](../integrations/n8n/workflows/README.md#contract-v1-and-scope). Native harness IDs and `memory_project` are not forwarded or authorized by this first preview. `main` is Basic Memory's existing project, not a synonym for this code repository. Its future use for a task must be explicit. Switching repository/task requires reassessing profile and scope. Unknown repositories fail closed; do not auto-index them. Existing graph indexes cover only three selected files each, not the whole repo. A profile/session ID is not access control.

Use one stack correlation ID across harness/n8n operations, but keep each harness's native session ID separate. Switching Codex↔DeepSeek transfers an approved checkpoint, not their private conversation state or credentials. Resume only after checking project/profile/permissions/index freshness again. A session ID is not an authorization token.

## 3. Start-work checklist

1. Confirm execution domain, repository and envelope; read project instructions.
2. Inspect required services without starting anything. Coding may need gateway/CodeGraph, Graphify only for relevant relationships; PKM tasks never need CodeGraph. Basic Memory is used only after its connection approval and only when relevant.
3. If a required service is stopped/unhealthy, report exact state and propose its own scoped action. Do not restart healthy services or turn on all tools. Do not touch {{mstack:CLIENT_REPO}}/stopped unrelated projects.
4. Run an appropriate bounded graph/gateway verifier when qualifying a new connection or after an approved lifecycle change. Running containers and version-only health checks are not proof of working MCP.
5. Choose the existing harness. Until integrations are qualified, work using ordinary repository inspection; do not pretend missing n8n/MCP features are connected.
6. After n8n is installed, invoke the task-router dry run at task start or material checkpoints—not every message. Review proposed next steps before actions.
7. At session end, offer a durable checkpoint only when requested/useful and approved. Optionally preview selected PKM sync after that integration exists; never synchronize every response.

### Read-only inventory now

From Ubuntu:

```sh
macctl run docker ps -a --filter label=com.docker.compose.project=mcp-stack \
  --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
macctl run docker stats --no-stream mcp-stack-postgres-1 \
  mcp-stack-basic-memory-1 mcp-stack-agentgateway-1 \
  mcp-stack-codegraph-http mcp-stack-graphify-http mcp-stack-n8n-1
macctl run docker exec mcp-stack-postgres-1 pg_isready -U postgres -d postgres
```

These checks start no services and call no Basic Memory tools. Last observed baseline is six running stack containers including n8n and 16 stopped unrelated containers. PostgreSQL, Basic Memory and n8n have Docker health checks; Basic Memory's check is only a version check. Graph adapters/gateway lack equivalent Docker MCP-health proof. Re-inventory rather than treating this baseline as permanent.

### Other-service startup workflow — approval required, not run now

Inspect exact container identity, image, mounts, networks, published ports and saved configuration first (avoid full env/secret dumps). If an **existing** required container is merely stopped and its definition still matches the qualified configuration, a separately approved `docker start` preserves the container instead of recreating it:

```sh
# Execute only the individually approved target, only if currently stopped.
macctl run docker start mcp-stack-postgres-1
macctl run docker start mcp-stack-codegraph-http
macctl run docker start mcp-stack-graphify-http
macctl run docker start mcp-stack-agentgateway-1
```

These are separate alternatives/steps, not a batch to run. Start only needed graph backends before the gateway. PostgreSQL is required for future n8n/Basic Memory, not for graph queries alone. Preserve the running Basic Memory baseline; if it later needs lifecycle recovery, obtain its separate approval rather than starting/stopping it incidentally. Missing containers/images/networks require a new install/recovery proposal, not this shortcut.

If gateway re-creation is needed, the qualified recipe is **base `infra/agentgateway/compose.yaml` + `infra/agentgateway/codegraph/compose.yaml` only**. Do not combine Graphify and CodeGraph overlays, use base alone, or run root Compose to start the entire stack. Use the exact [combined lifecycle recipe](../infra/agentgateway/codegraph/README.md) only after approval. Other service definitions remain in their individual runbooks.

Existing bounded graph checks, when relevant:

```sh
python3 infra/agentgateway/verify.py
python3 infra/agentgateway/codegraph/verify.py
python3 infra/agentgateway/graphify/verify.py --codegraph-connected
```

Authentication is supplied by these verifiers without printing keys. Graphify same-route resumption after DELETE is supported, not permanent session revocation. CodeGraph DELETE/reuse returns 404. An index miss is not proof of missing code.

## 4. Harness startup and connection design

### Codex IDE — reuse installation

No reinstall. Establish whether the IDE/client runs on macOS or in the Ubuntu remote workspace, its actual version, trusted repository and credential source. Native project MCP discovery uses `.codex/config.toml`; CLI overrides do not configure IDE sessions. Proposed canonical settings live in `infra/harnesses/codex/`, with a small `.codex/config.toml` discovery pointer only if separately approved and tested. **No pointer/config is created by this runbook.** Do not redirect `CODEX_HOME`, copy `auth.json` or run global `codex mcp add`. [Official project discovery/configuration](https://learn.chatgpt.com/docs/config-file/config-advanced), [MCP configuration/auth/tool selection](https://learn.chatgpt.com/docs/extend/mcp).

Qualify authenticated graph routes independently, profile-appropriate tool allowlists, wrong-key/scope failures and session cleanup before adding n8n or Basic Memory. Environment/header-helper auth must work in the IDE's actual process environment; a terminal export does not automatically reach it. Keep plaintext credentials out of TOML, command arguments and logs.

### DeepSeek — official MCP plugin with a project overlay

Latest native activation (2026-10-03): Web **127.0.0.1:3080**, recorded PID **414648**, uses two actual loopback URLs through forwarder **127.0.0.1:58081**, recorded PID **402899**. Both official MCP plugin entries are enabled/**active**; installed SDK discovered Graphify **7 tools / 2025-11-25** and CodeGraph **1 tool / 2025-06-18**, with diagnostic sessions cleaned. No tools/call or model request. **23 Python + 10 forwarder + 2 offline SDK** cases and native contracts pass; complete home/key/global packages/38 other protected artifacts/all21 containers unchanged. [Completed root-cause/activation record and exact launch](DEEPSEEK-LOOPBACK-MCP-ACTIVATION-PROPOSAL.md). Native fetch discards custom Host overrides, so those were removed and actual loopback URL authorities used. Do not repeat old failed registration/Host-correction steps or act on stale recorded PIDs.

Manual entry now: open macOS **http://127.0.0.1:3080/** with an existing valid browser cookie. A 401 means authentication is required, not that MCP failed: privately open the current `dsh web:` token-bearing launch URL from `infra/harnesses/deepseek/state/loopback-mcp-20261003-hads2zul/server.log`. Never paste/share that token/log. Select a session and verify repository/task scope before any user-initiated model/tool use; native active-entry evidence is not a completed model/tool-execution acceptance test. Graph/gateway/BM protocol endpoints are not separate task GUIs; use OrbStack Containers for manual service status/logs, without restarting healthy services.

Forwarder is on-demand, not auto-started. Before any approved start/stop, confirm exact domain/executable/PID/start identity/listener and keep private logs in `infra/`. 32-client cap, 5-second connection/DNS bound, 10-minute idle expiry, 5-second shutdown drain; a changed OrbStack address fails closed. One idle process sample was ~63 MiB RSS/0.0% CPU, not a battery estimate. Live restart/shutdown/capacity and indefinite MCP idle-recovery behavior are not qualified. Web's graph initial connection is now qualified, vision remains disabled; tool/model execution is separate. Do not edit watched YAML live.

Historical Host correction (2026-10-02), superseded by the successful activation above: old Web **402276** was online with both MCP entries failed403 because native fetch discarded the custom Host. Python HEAD was the wrong end-to-end acceptance client. [Failure evidence/backups](DEEPSEEK-MCP-HOST-CORRECTION.md) remains for audit, not a pending retry. Earlier preparation/foundation notes below are historical and must not be treated as current runtime state.

Native integration preparation on 2026-10-02: [infra configuration](../infra/harnesses/deepseek/README.md) and [exact relaunch/connection proposal](DEEPSEEK-NATIVE-MCP-PROPOSAL.md). Installed official MCP client **0.2.0-rc.2** needs no additional package. `mcp-stack.cordis.yml` is an opt-in `--patch` overlay for the existing Graphify/CodeGraph gateway endpoints, reached from Ubuntu via `host.orb.internal:58080`; Ubuntu localhost does not reach that macOS listener. Key-file expression remains unevaluated until separately approved activation. **22** offline tests and installed native parser/composer/Config schema checks pass, not a live MCP pass. Existing user-started `dsh web` at 3080 is running independently; it has not loaded our overlay and is not restarted by preparation. Optional `no-vision.cordis.yml` is for first connection qualification only, not an uninstall or saved-profile change. No Basic Memory row, global config, new package or custom MCP bridge.

Latest finding (2026-10-02): the packaged browser shell supplies React **18.3.1**, JSX runtime and primitives required by vision's native client factory; no extra React installation is indicated. [Static proof and first attempt](DEEPSEEK-WEB-SMOKE-PROPOSAL.md); the first unauthenticated client timed out, then the [separately approved correction/retry passed](DEEPSEEK-WEB-AUTH-CORRECTION.md). **16** synthetic/helper tests passed; one credential-free isolated base+web retry confirmed native readiness, unauthenticated 401, temporary-token 303/cookie exchange, authenticated page 200 and React shell asset 200. Owned server stopped, no test process remains, retained home/global/source identities and all 21 container snapshots unchanged. Private fixtures/logs and original-helper rollback copy retained under ignored `infra/`. Existing vision Python cache remains unexecuted; full vision mount may install/clean its runtime. This is isolated Web foundation qualification, **not** browser rendering/vision qualification or permission to start the retained profile.

Approved existing-global CLI update completed: **0.2.0-rc.2**, retaining `/home/developer/.dsh` configuration/credentials/sessions, not initializing a new home. [Completion, exact commands and private backup location](DEEPSEEK-CLI-UPDATE-PROPOSAL.md). Version-only smoke check passed; no profile/model/MCP test. Latest user decision on 2026-10-02 accepts upstream pnpm and requests continuing the fix: [vision plugin 0.1.46 update completed](DEEPSEEK-VISION-UPDATE-PROPOSAL.md), scripts disabled, existing managers, recovered exact pin after pnpm retained a caret range, lock integrity/snapshots/direct dependencies/bundle list checked. Old node_modules retained intact in the restricted backup; protected home/global identity/all 21 containers unchanged. All DeepSeek-related peers accept the installation-owned packages, but React is not a standalone installed peer: frontend/runtime resolution remains unqualified; do not auto-install it. npm migration cancelled, no npm lock created. `dsh plugin ...` uses pnpm; accepting it does not approve wrapper reconciliation or profile startup automatically. The project-home launcher below remains an earlier design option, not permission to relocate/reset configuration. The next launcher design must retain the user's chosen existing home unless relocation is separately approved.

Current verified runtime (2026-10-01):

- Ubuntu `@deepseek-ai/dsh` **0.2.0-rc.2**.
- Bundled `@deepseek-ai/dsh-mcp-client` **0.2.0-rc.2**, so an additional MCP plugin install is not automatically necessary.
- Existing fnm Node **24.19.0**, verified by version command; CLI source at `/home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/@deepseek-ai/dsh/lib/bin.js`.
- Local boot source supports `DSH_HOME` and profile/patch flags. Initial profile boot can create files/symlinks. The isolated test server is stopped; the separately approved retained-home Web is now running with the two project overlays, without modifying retained home content.

Preferred runtime interface is now the official CLI's `--patch` mechanism, not a required custom launcher/plugin. Any future `check`/`web`/`resume` convenience wrapper is optional, **not implemented or required for MCP**. Reuse the existing executable, check actual Node/CLI/plugin versions, reject mismatches; never pin a transient `/run/user/.../fnm_multishells/...` path or auto-install via `npx`. Retain the user's existing `/home/developer/.dsh` for normal launches unless relocation is separately approved; only disposable test homes belong under ignored/restricted `infra/harnesses/deepseek/state/`. Reviewed project launch settings/patch templates belong under `infra/harnesses/deepseek/`, reusable source/tests under `integrations/deepseek/`. No global aliases, shell-profile or retained-home edits.

Set `DSH_HOME` in the launching process, not a `.env` file: installed boot resolves it before reading env layers. It also reads invoking-directory `.env`; the launcher must review/filter inherited/project credentials without printing them or copying another project's secrets. Explicit project/model/permissions, uploads disabled unless approved, verified project-instruction loading and independent native session resume are required. `cwd` and a new home directory are not shell sandboxes. No shell escapes, headless agent job or paid request is authorized by selecting a profile. Prefer foreground TUI initially; Web UI is optional, loopback-only, with port/authentication reviewed before start. [Official source/product](https://github.com/deepseek-ai/deepseek-harness).

## 5. Major n8n workflows

**`task-start-router` is authored and in-memory qualified, not imported/published; all other names remain planned.** Official2.41.6 is healthy on macOS OrbStack; HTTP foundation qualified. Do not repeat completed installers. Portable definitions/tests go in `integrations/n8n/`; runtime settings/credentials stay in `infra/`/ignored secrets.

### What to do in the interface now

1. On macOS, open **http://127.0.0.1:5678/** and use your existing owner login
   (created/logged in per your report). Never send the agent its password. Store
   human passwords in your password manager, not a project file; see the
   [metadata-only secrets inventory/recovery proposal](SECRETS-INVENTORY.md).
2. The workflow import/manual synthetic test is already approved. Import from
   `integrations/n8n/workflows/task-start-router.json`. Follow the
   [bounded UI handoff and exact macOS file-chooser path](../integrations/n8n/workflows/README.md#complete-the-approved-ui-action).
   Edge blocks automation; no browser setting was changed. It will not appear in
   your workflow list until imported/saved. No API token or password handoff needed.
3. This router uses built-in Manual Trigger and Edit Fields only. **No Code runner
   installation is needed for it.** The ordinary external runner remains absent;
   defer its separate proposal until a real Code-node workflow needs it. Do not
   switch to internal runners or add an Assistant sandbox.
4. For the approved manual test, leave the bundled fixed synthetic JSON in
   **Task input** unchanged, choose **Execute Workflow** once, then inspect
   **Route preview → Output → JSON**. Expect four items: coding, documentation,
   PKM and an intentional `dry_run=false` rejection. No four separate runs needed.
   Verify `status`, candidates, deferred tools and `actions_executed: []`.
   `status="rejected"` is a refused envelope even if the node is green.
   Keep unpublished; no schedules, credentials or provider/model calls.

For non-mutating host checks from Ubuntu:

```sh
macctl run docker ps -a --filter name=mcp-stack-n8n-1 \
  --format '{{.Names}} {{.Status}} {{.Ports}}'
macctl run curl --noproxy '*' --fail --silent --show-error \
  --max-time 5 http://127.0.0.1:5678/healthz/readiness
```

Only app port5678 is published, on loopback; task broker5679 is internal. Runtime
definition is `infra/n8n/compose.yaml`, not a second Docker installation in Ubuntu.
DB/app/secret volumes persist; cache is a64MiB tmpfs and regenerates on start.
Sample cache use46.8MiB, app544.3MiB/0.01%CPU; not a whole-machine battery guarantee.
Recheck cache headroom on upgrades. Review logs privately; they may contain
personal execution data. Never print evaluated Compose/env or credential files.

| Workflow / state | Trigger / purpose | Safety boundary |
| --- | --- | --- |
| `task-start-router` — approved, manual UI import pending | Manual at task/session start or profile change; one-click four-case check supplied | Dry run: no model/tools/writes/install/indexing; 90 policy + 4 bundled cases passed installed VM/Set/Split Out, not editor qualification |
| `context-read` | Explicit checkpoint; choose scoped CodeGraph/Graphify and later relevant Basic Memory | No mandatory all-tool calls; report stale/partial/unavailable indexes, no memory write |
| `checkpoint-plan` | Task milestone, failure or harness handoff; return next step/approval requirement | Does not start Codex/DeepSeek or change services automatically |
| `memory-capture` | Explicit remember request or approved durable checkpoint | Preview note/source/project, require write approval; no secrets or speculative facts |
| `pkm-sync-preview` | Manual before pulling PKM changes or publishing selected notes | Read approved scopes, produce diff/conflicts/loss report; no remote/local note writes |
| `pkm-sync-apply` | Manual approval of a specific still-current preview | Approved IDs/versions/direction only; durable ledger, idempotency, verification |
| `stack-health` | Manual; later optional low-frequency monitoring after approval | Metadata/readiness only, no auto-restart or Basic Memory usage test while deferred |
| `data-export-plan` | Before cleanup/upgrade/move; enumerate targets and backup requirements | Planning first; actual export/restore/delete individually approved |

Basic Memory read/capture workflows are enabled only after its connection step. Initial graph/n8n/harness integration does not expose Basic Memory automatically. MCP Server Trigger and client interoperability must be tested against pinned versions. Automated n8n→harness execution needs a separately approved bounded bridge; ordinary Code-node runners are not that bridge. No Docker socket, home/repository mounts or arbitrary shell node as a shortcut.

## 6. Where to read Basic Memory docs and your notes

- Product documentation: [official docs](https://docs.basicmemory.com/), [Knowledge Format](https://docs.basicmemory.com/concepts/knowledge-format), [MCP tools reference](https://docs.basicmemory.com/reference/mcp-tools-reference), [Postgres backend](https://docs.basicmemory.com/local/postgres-and-milvus). Read the local/open-source sections; Cloud/web-app examples do not mean those paid/hosted features are installed here. Recheck syntax against pinned **0.23.2** before changes.
- This stack's installation/verification/history: [Basic Memory runbook](BASIC-MEMORY-SETUP-PROPOSAL.md); behavior/approval rules: [memory routing](MEMORY-ROUTING.md).
- Your human-readable documents: Ubuntu `/home/developer/workspace/mstack/knowledge/main`; macOS `/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack/knowledge/main`. Open Markdown in an existing editor; no new PKM app required. Notes remain private/gitignored.
- PostgreSQL holds indexed application data, not the only copy of the Markdown. `/mcp` at macOS port `58000` is the existing MCP endpoint, **not a claimed notes browser/editor UI**. Gateway has no Basic Memory route today. Once approved, use scoped MCP read/text search through the qualified connection, not direct SQL edits.
- Editing Markdown, Basic Memory's file→index synchronization, and memory↔PKM synchronization are separate operations. Before direct-file edits are integrated, verify the pinned service's indexing behavior; do not assume its database updates instantly or start an extra watcher. No editing/test is performed by this document.

## 7. Bidirectional memory ↔ PKM sync

Recommendation: **manual preview-and-approve first; scheduled bidirectional writes off**. Sync is a separate curated export/import, not Basic Memory embeddings, model memory, CodeGraph/Graphify refresh or Basic Memory Cloud sync. There is no implemented Notion/AppFlowy sync pipeline yet.

### Where and when to trigger

| Direction | When useful | Where / initial action |
| --- | --- | --- |
| PKM → Basic Memory | Before a task when approved PKM notes have changed | n8n `pkm-sync-preview`, `direction=pull`, selected project/page IDs; then approve `pkm-sync-apply` |
| Basic Memory → PKM | After approving a durable checkpoint or finishing a note you want in PKM | Same preview workflow, `direction=push`, selected notes and one destination; approve apply separately |
| Bidirectional reconciliation | Periodic housekeeping or after edits on both sides | Preview `direction=both`; resolve conflicts before apply, not last-write-wins |
| Automatic later | Only after safe manual cycles and restore/conflict/retry tests | Separately approved n8n Schedule Trigger or qualified events, timezone `Asia/Shanghai`, explicitly published; no schedules now |

During implementation/testing use the n8n editor's manual trigger. Later expose a small authenticated harness tool for **preview/status** so Codex/DeepSeek can offer a sync at session start/end. It must not publish all notes or grant write approval by itself. Apply requires the user's reviewed plan approval. Notion/AppFlowy UI edits are upstream changes, not proof that n8n was triggered.

An automatic phase should start with scheduled **previews** and meaningful-change/failure notices. Automatic apply is a further decision, limited to nonconflicting changes in a specific allowlist; conflict/deletion/loss always escalates. Do not make every agent message a sync event, add host cron/launch agents or enable public webhooks/tunnels just for sync. [n8n schedule publication/timezone requirements](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/).

### Data contract and conflict rules to implement

1. Explicitly allowlist local notes/folders and remote workspace/page/document IDs. No whole personal knowledge base by default. Start with one synthetic fixture and one provider before enabling both.
2. Treat Markdown as the durable portable representation; a mapped PKM document can also originate edits. Sync only supported fields/content. App-specific blocks, relations, comments and attachment/object URLs need conversion rules; unsupported/lossy conversion stops for review rather than silently stripping data. Imported text is untrusted content, not agent instructions.
3. Keep a restricted durable mapping/ledger under ignored project `infra/` state: project/provider, stable note ID/permalink/path, remote ID, last-synced normalized content/base hashes, remote revision metadata, operation ID and outcome. Exact backing store requires its own proposal; do not modify n8n core DB tables or assume workflow static data is a safe concurrent ledger.
4. Compare **local and remote changes against the last common base**, not clocks alone. One side changed: propose transfer; both changed: merge preview/conflict review; neither changed: no-op. Remote IDs/path mappings prevent rename-based duplication and cross-project writes.
5. Bind approval to a preview ID, scope, content hashes/versions and short validity window. Re-read before apply; stale plans abort. Verify provider concurrency controls rather than promising atomic compare-and-set where unsupported. No automatic overwrites until race behavior is qualified; local serialization does not prevent human remote edits.
6. Single writer per mapped pair/project, bounded batches/timeouts, provider rate-limit handling, durable checkpoints and idempotent retries. If a create/write timed out, reconcile actual remote state before retrying; never create duplicates blindly. Do not advance a cursor/base hash until the write/read-back is verified.
7. Apply approved Basic Memory writes through its qualified API/MCP path, not PG table edits. Verify note readability and text-search/index consistency. File-based import needs separately tested index synchronization, not silent extra processes.
8. No automatic deletion propagation. Missing/archived/deleted items become tombstones/conflicts for review; preserve both sides until approved. First sync is a bootstrap preview with explicit pairing/direction, not a forced overwrite.
9. Disable reverse-loop echo using origin/operation IDs and normalized hashes. Separate Notion and AppFlowy mappings: do not relay one provider's changes into the other automatically. A→B→A must settle to no-op.
10. Log redacted IDs/hash/outcome counts, not full note bodies/tokens. Preview/apply authorization, offline recovery and partial-attachment failure must be tested. Back up affected documents/attachments before applying changes; expose per-provider pause and resumable status.

Acceptance: no-op repeat, both directions, conflicts, rename, deletion, attachment/loss reporting, rejected unknown IDs, stale approval, offline/rate-limit/timeout retry, failed read-back, concurrent edits and no infinite echo. A dry-run does not qualify write correctness.

### PKM choices — delayed

- **Notion:** prefer its official MCP connection after a separate scope/auth review. Notion tools act with the user's existing permissions; a project/page allowlist is not automatically an upstream account-security restriction. Start read-only; preview/approve every external write until a narrower policy is verified. No Notion pages read/written by this runbook. [Notion permissions guidance](https://www.notion.com/help/notion-mcp).
- **AppFlowy:** independently review official server deployment, image/storage/auth requirements, PG18 compatibility, ports and resources. Installation is separate from choosing/qualifying a maintained MCP connector and supported operations. Do not assume an official MCP endpoint is included just because the app is installed. Preserve Supabase as an optional evaluated expansion, not a prerequisite or an excuse to alter {{mstack:CLIENT_REPO}}. [Official server source](https://github.com/AppFlowy-IO/AppFlowy-Cloud), [existing storage assessment](DATABASE-AND-STORAGE.md).

## 8. Monitoring and logging

Start with manual bounded checks, not another monitoring stack. Inspect container state/restarts, authenticated gateway readiness, DB readiness, resource use and disk/backup age. MCP functional checks are separate from process health. No watchdog automatically restarts/recreates/re-indexes services.

Example local diagnostics, without full environment dumps:

```sh
macctl run docker inspect mcp-stack-agentgateway-1 \
  --format '{{.Id}} {{.State.Status}} restarts={{.RestartCount}} started={{.State.StartedAt}}'
macctl run docker logs --since 15m --tail 100 mcp-stack-agentgateway-1
```

Logs may contain paths, prompts, payloads or credentials: review locally/redact before sharing. Do not print `.secrets`, rendered state configs, database URLs, OAuth tokens, `.env` files or unfiltered harness config dumps. Container engine logs live in OrbStack; current graph/gateway caps are two 5 MB files per container. PG/Basic Memory log limits are not claimed configured; changing them is an independent proposal.

Proposed harness/audit logs under ignored `infra/harnesses/.../state/` and sync logs under ignored `infra/pkm/state/`; create/ignore/restrict only at the approved setup step. Record UTC timestamp plus display timezone, project/session/task/workflow/operation ID, version/scope, duration, result and approval reference. Keep long agent transcripts private and distinct from reviewed durable notes. Versionable workflow exports must not embed secrets or live execution data.

For future periodic monitoring, qualify a metadata-only workflow, interval/retention and notification channel first. Stay quiet when unchanged; notify on failures, actionable changes or approval needs. Service recovery remains an explicit scoped action. Preserve caffeinate; idle service limits do not measure whole-machine battery use.

## 9. Export, cleanup, restore and migration flow

**Plan → approve scoped backup/export → verify manifests/isolated restore → approve change → verify → retain rollback.** No export, private-file copy, cleanup or migration performed now.

| Data class | Export/preserve | Important boundary |
| --- | --- | --- |
| Basic Memory | Markdown + DB dump + restricted runtime config + credential recovery material | Notes and DB/index represent different pieces; never assume a DB dump contains Markdown |
| n8n, once installed | DB + persistent app volume + encryption key + secret-free portable workflow definitions | Workflow exports alone are not full credential/state backups |
| Graphify/CodeGraph | Approved source-scope manifest, tool/runtime pins, adapter config and retained index/checksum | Rebuildable does not mean safe to delete before rebuild/restore proof |
| Gateway/harness | Versioned templates/source + protected keys/rendered settings + private session IDs/checkpoints if needed | Do not publish or copy whole home directories/auth stores |
| PKM | Approved document/block exports, ID mapping/ledger, attachment/object data and destination references | Database metadata does not contain remote or object-store files |

Use PG18's existing container tools for future per-service `pg_dump -Fc`; global roles require separate protected metadata capture. `pg_dump` gives a consistent single-DB dump, not a synchronized Markdown/attachment snapshot. Coordinate writers or define a tested consistent checkpoint before a multi-part backup. Basic Memory lifecycle/write pauses themselves need approval while deferred. [PostgreSQL dump/restore](https://www.postgresql.org/docs/18/app-pgdump.html), [global objects](https://www.postgresql.org/docs/18/backup-dump.html).

Store backups in ignored restricted `backups/<unique operation>/`, never overwrite previous backups. Record application/DB/extension versions, source scope, timestamps and checksums; use approved encrypted/off-machine storage for private content/credential recovery. Restore into a separately approved **isolated** DB/project/storage target; prove notes/attachments/credentials/workflow behavior before replacing anything live. No wholesale global-role restore over shared PG, PG major-version tag swaps, `--clean` restore against live databases or volume repurposing.

Cleanup: enumerate exact targets/owners/restart references, inspect age and recoverability, back up first, obtain deletion approval, report removals/recovery. Expired previews/logs may be candidates, not durable notes, stopped containers, restart images or entire tool homes. “Derived index” is not permission to delete it. Bulk personal-memory/export publication is never automatic.

Migration: map project/session IDs, paths, roles/permissions, tool versions, PKM mappings and object URLs; pause only separately approved writers/sync; restore into isolated destination, test one scoped project, then approve cutover and a rollback window. Keep originals until restore and real tasks pass. Retiring devbox or enabling Supabase stays a later separate decision.

## 10. Session completion / next work

Record a secret-free outcome: completed task, unresolved issue, index/scope limitations, approvals used and next proposed action. Capture durable memory only with an explicit remember request or approved checkpoint. Optional PKM push is preview-first after integration, not a mandatory session teardown. Closing a harness session need not stop long-running services; any battery-mode shutdown needs separate approval.

DeepSeek CLI/plugin updates, Web foundation, forwarder and native graph registration are completed; retained-home Web/forwarder remain running, vision disabled. The npm migration is cancelled. n8n app foundation completed2026-10-04: healthy at macOS5678, read-only root, private secret volume and bounded cache tmpfs; [evidence/limits](N8N-STATIC-CACHE-PROPOSAL.md). Owner login user-reported; router source, 90 policy cases and four bundled checks passed installed-node in-memory qualification. Import/test is already approved but requires the manual UI handoff because Edge automation is disabled. **Stop after this bounded workflow; no automatic next setup proposal.** Code runner, Basic Memory/PKM/Codex and other integrations stay deferred until explicitly reopened. No automatic model/tool call, schedule or integration. Do not repeat installers or claim saved/editor acceptance without evidence.
