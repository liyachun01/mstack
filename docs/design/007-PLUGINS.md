# 007 — Plugins: drop-in joints for the orchestrator

Status 2026-10-28: **manifest format, registry and contracts implemented.** The agent
joint runs entirely through manifests. Board and link use existing code through
manifests. **compress (Headroom)** has an adapter, is selected per project through
`joints` and is given to workers as per-run MCP. Its contract kit passes against a
stand-in server and, on 2026-10-28, live against test-market's own tenant (4/4). Memory, gateway and docs are listed but marked `adapter-pending`.

## Joints

```
                 owner ── board (source of truth) ── link (Linear, …)
                              │
                       orchestrator agent
                              │ dispatch
     ┌────────────────────────┼─────────────────────────┐
   agent host            agent host                agent host        ← agent
     │  worker session tools (worker-mcp):                               
     ├─ memory.instant  (task/session scratch)                         
     ├─ memory.long     (RAG / graph over the project corpus)          
     ├─ compress        (large output → summary + handle)              
     └─ docs            (project documents, read-back)                 
   all traffic optionally through ── gateway (routes, policy, capture)
```

| Joint | Contract (short) | Built-in today | Drop-in candidates |
|---|---|---|---|
| `agent` | start in worktree, see binding, report via board | codex, claude, opencode, echo (argv); claude-desktop, codex-desktop (handoff) | aider, goose, gemini-cli (argv); `opencode serve` / `codex app-server` (server) |
| `board` | tables, tasks, discussions, reactions | anytype-board (shared type + collection per project) | Linear-only, GitHub Projects, plain SQLite |
| `link` | `sync` pull/push/full, mine/label | linear | Jira, GitHub Issues; Composio as a generic link |
| `memory.instant` | put/get/recent/clear by scope, TTL | ai-memory *(pending)* | Redis, SQLite, files in `.mstack/cache` |
| `memory.long` | index/query/forget with sources | graphify *(pending)* | Basic Memory, pgvector RAG, CodeGraph |
| `compress` | compress → summary + handle; expand | headroom (implemented) | LLMLingua, a summariser model |
| `gateway` | routes, apply (approval), turn events | agentgateway (implemented: keyed project route + stdio bridge) | LiteLLM, Magpie, direct |
| `docs` | list/read/write with read-back | anytype-docs *(pending)* | Notion, markdown in `docs/` |

Full operation lists are in [contracts.md](../../integrations/plugins/contracts.md).

## Plugin = folder + manifest

```
integrations/plugins/builtin/<name>/plugin.json     # shipped with mstack
<project>/.mstack/plugins/<name>/plugin.json        # the project's own (local, not in git)
```

[Schema](../../integrations/plugins/schemas/plugin.schema.json) fields:
- **`joint`** and **`status`**: `adapter-pending` plugins are never selected.
- **`transport`**, one of:
  - `argv`: a command template with `{python} {brief} {cwd} {notify} {plugin_dir}`
  - `handoff`: `via` start_session or owner
  - `python`
  - `jsonrpc-stdio`: any language, one JSON request per line
  - `mcp` / `http`
- **`requires`**: binaries, services, credentials. The registry only checks for them; it never installs.
- **`capabilities`**, `expose` (orchestrator and/or worker-mcp) and a JSON Schema for `settings`.

Example: adding a new CLI agent takes only a manifest, with no mstack code.

```json
{"name": "aider", "version": "0.1.0", "joint": "agent", "status": "implemented",
 "transport": "argv", "requires": {"binaries": ["aider"]},
 "command": ["aider", "--yes", "--message", "{brief}"]}
```

Then list it in the project's `taskboard.workers`. The test
`test_project_agent_plugin_is_used_without_code_changes` does exactly this with
a project-local plugin and runs it through `dispatch` → `work` → review.

## Rules every plugin follows

- **Scope:** every call carries `{project, task, session}`, and a plugin must
  never return another project's data. Shared services keep per-project tenants
  (see `infra/services`).
- **Board is the bus:** agents report through `mstack board note/done`; other joints
  never move task status themselves.
- **No silent side effects:** discovery is read-only. Indexing, gateway route
  changes and installs are explicit, owner-approved steps under the setup guard.
- **Credentials:** only through settings that point at `.mstack/secrets/`; values never go into argv or logs.
- **Project plugins** can't take a built-in's name. A project only uses a plugin
  it names in its config.

## Commands

```sh
mstack plugin list [--project P] [--joint agent]   # with live availability
mstack plugin validate [--project P]
```

## Selecting joints and wiring workers (implemented)

```json
"joints": {"compress": "headroom"}
```

At `dispatch`, each selected plugin that exposes `worker-mcp`, and is available for
this project (its tenant registered), becomes an MCP server for that one run.
The host's `mcp_style` decides how:

| `mcp_style` | Hosts | How |
|---|---|---|
| `codex-config` | codex | `-c mcp_servers.<name>.command/args` on the run (`{mcp}` placeholder) |
| `mcp-json` | claude, claude-desktop | untracked `.mcp.json` in the worktree, enabled in the worktree's `.claude/settings.local.json`; only with local visibility (`/.mcp.json` is excluded) and never if the team tracks its own `.mcp.json` |
| `none` | opencode, echo, codex-desktop | skipped, with the reason in the dispatch result |

Each wired tool's `mcp.hint` goes into the worker's brief. Nothing is registered
globally, and a skipped tool never blocks the task.

## Next steps (not done)

1. ~~Joint selection in config.~~ ~~worker-mcp wiring.~~ Done for compress; the same path serves future joints.
2. ~~Live Headroom check for test-market.~~ Done 2026-10-28; see below.
3. Adapters and test kits for memory.long (Graphify), memory.instant, gateway and docs.
4. Server agent hosts (`opencode serve`, `codex app-server`), once verified.

## Live compress check — 2026-10-28

With the owner's approval, `mstack-headroom` was started (pinned image, no network,
read-only) and test-market was registered as its tenant (0600 token in its
`.mstack/secrets/`, hash only on the server). `joints.compress: headroom` was then set
in test-market's config. Results are in test-market's `.mstack/evidence/headroom-compress-live.json`:

| Input | Tokens before → after | Notes |
|---|---|---|
| 400-line plain text log | 7,206 → 7,206 | passed through unchanged, no saving |
| 400-row JSON API result | 24,962 → 12,582 (~50%) | all 5 error rows kept in the summary |

Both round-trip exactly. So Headroom helps with structured tool output, not prose
or plain logs; the worker hint should say "large JSON/tool output". Cross-tenant isolation was
checked afterwards with a second tenant (the mstack project): each tenant gets "content not found" for
the other's handles and reads its own exactly.
Stopping the service affects every tenant; the cache survives within the one-hour TTL.
