# 015 — Multi-harness workers: DeepSeek Harness first, OpenCode second (MST-54, 2026-10-30)

Status: investigation and plan. Nothing was installed, started, logged in or called. Every setup step below is a
proposal that goes through `.agents/skills/mcp-stack-setup-guard/SKILL.md` with the owner's explicit OK.

## Goal

Run mstack's normal loop (Linear issue → plan → owner verdict → worker in its own worktree → `board note/done` →
review → merge) with workers that aren't Claude Code, mainly on DeepSeek models. Later, one UI that manages sessions
the way Claude Desktop does and dispatches to Claude, DeepSeek and ChatGPT.

## Short answer

- **DeepSeek Harness (`dsh`) fits mstack's existing `argv` worker joint today.** Its `headless` profile runs one task
  per process, prints a JSON event stream, resumes a session by id, reads `AGENTS.md`/`CLAUDE.md` and
  `.agents/skills/` natively, and defaults to official DeepSeek V4 Flash. A worker needs a manifest, not new
  machinery.
- **mstack's spawn path has four gaps** that block any non-Claude worker. They're the same for dsh and OpenCode:
  (1) spawn runs record no session id, so they never show in "My tasks"; (2) owner comments (`forward`) and
  `stop` events address a chat session, which a CLI process doesn't have; (3) `work` posts its own review ask
  after the process exits, so a worker that also ran `board done` reports twice; (4) the harness sandbox has to
  allow `git commit` in a worktree (it writes to the main checkout's `.git`) and the `mstack board` calls.
- **OpenCode is the stronger second option**, and the better base for a session UI: a real HTTP server with a
  sessions API (create, prompt async, abort, fork, SSE events), DeepSeek as a built-in provider, MCP, and the same
  instruction and skill folders. It isn't installed.
- **Session UI:** see [Session-manager UIs](#session-manager-uis). Recommendation in short: keep Claude Desktop as
  the hub, add an ACP-capable UI only after phase 1 proves headless workers.

## What mstack already has (read locally)

| Piece | State |
|---|---|
| `dsh` 0.2.0-rc.2 (`~/.local/bin/dsh`, mise Node 24.19.0) | Installed. Web profile was used in October; headless/ACP/SDK profiles never started. `~/.dsh` holds settings, credentials and older sessions. |
| `infra/harnesses/deepseek/` | Pinned toolchain, MCP overlay (`mcp-stack.cordis.yml`, Streamable HTTP to the gateway through the 58081 forwarder), no-vision overlay. Native MCP activation still awaits approval. |
| `integrations/agents/deepseek_launch.py` | Repo launcher; refuses missing tools, reads the explicit credential. |
| `integrations/plugins/builtin/opencode` | `argv` manifest `opencode run {brief}`; binary absent, so `mstack plugin list` shows it unavailable. No dsh manifest. |
| `integrations/orchestrator/runners.py` | Two host kinds: `spawn` (argv, detached `cli.py work`) and `handoff` (desktop `start_session`). The brief is the whole instruction; MCP servers can be injected per run (`mcp_style`). |
| `cli.py work` | Runs the argv once, captures output, then `finish()` posts the review ask and sets In Review. |
| `status_table.py` | Builds worker rows only from runs that carry a `session`; `agent_of()` knows claude/codex/deepseek, else `other`. Spawn runs have `pid`, no `session`. |
| Magpie (Mac, `127.0.0.1:3425`) | Claude Desktop → official DeepSeek Flash. App-wide profile switch; loopback-only; trusts any local caller. |
| `mstack-models` skill | Already describes the route table; says `dsh` is "later". |

## DeepSeek Harness

Sources: the installed package READMEs (`@deepseek-ai/dsh`, `dsh-headless`, `dsh-acp-app`, `dsh-sdk-app`,
`dsh-agent-instructions`, `dsh-skill-filesystem`, `dsh-hooks-claude-code`, `dsh-mcp-client`, `dsh-base`) and the
[repo](https://github.com/deepseek-ai/deepseek-harness) / [releases](https://github.com/deepseek-ai/deepseek-harness/releases).

### Entry modes

| Mode | Use for mstack |
|---|---|
| `dsh --profile headless "task"` | **Worker.** One task, then exit 0/1. `--json` gives NDJSON events (`session`, `status`, `text`, `thinking`, `tool_call`, `tool_result`, `final`, `error`). `--session-id <id>` continues a persisted session (refused if the cwd differs or the session is live elsewhere). No port. |
| `dsh --profile acp` | **Session UI / long-lived worker.** Standard ACP v1 over stdio: `session/new` with absolute `cwd` and MCP declarations, `session/prompt`, `session/list`, `session/resume` (reconnects, no history replay), `session/close`, permission requests; no `session/load` or fork. Any ACP client (Zed and others) can drive it. Default route `deepseek-official` / `deepseek-v4-flash`. |
| `dsh --profile sdk` | JSON-RPC stdio for the TS/Python SDKs; resume support since 0.2.1-alpha.3, operation-approval callbacks in 0.2.2-alpha.2. |
| `dsh web` | The browser UI used in October. |

### What a worker gets for free

- **Instructions:** `AGENTS.md` and `CLAUDE.md` (plus `*.local.md`) from the project root down to the cwd, 64 KiB
  budget, nearest `.git` ancestor as the root. A worktree's `.git` is a file, not a folder — check it counts as
  the marker (phase-1 qualification item).
- **Skills:** `<root>/.dsh/skills` and `<root>/.agents/skills` are scanned, so `mstack-worker` is visible as is.
- **Hooks:** `dsh-hooks-claude-code` runs an existing Claude Code `hooks.json` (SessionStart, UserPromptSubmit,
  PreToolUse, Stop…) unchanged. mstack's capture hook could be reused later; not needed for phase 1.
- **MCP:** `dsh-mcp-client` rows, `stdio` or `streamable-http`, added per launch with `--patch <overlay>`. This
  matches mstack's per-run `mcp` wiring (Headroom/Graphify stdio bridges) — a new `mcp_style: dsh-patch` would
  write a temporary overlay into `.mstack/cache/`.
- **Credentials:** since 0.2.1-alpha.3 headless reads keys from env and `.env` only, not saved keys — good for a
  worker-scoped key. On 0.2.0-rc.2 this is unverified.

### Risks found

- **Version:** installed 0.2.0-rc.2; upstream is at 0.2.1-rc.5 / 0.2.2-alpha.2 (all pre-releases, weekly). The
  headless env-only key rule and SDK resume are newer than ours. Update = setup-guard proposal.
- **Approvals in headless:** the base policy "confines file writes to your workspace and asks before risky
  actions". The README doesn't say what "ask" does with no UI (likely abort or deny). 0.2.2-alpha.2 adds an
  experimental auto-review for headless. Must be qualified on a throwaway task before any real issue.
- **Writes outside the worktree:** `git commit` in a worktree writes to the main checkout's
  `.git/worktrees/<name>` and object store; `mstack board note/done` writes the state file under the main
  checkout and calls `psql`. The sandbox needs a narrow profile patch for those paths, or `done`/commit run by
  `cli.py work` after the agent exits (see phase 1).
- **Telemetry:** base enables OTel upload in `FEEDBACK_ONLY` mode and a default-on DeepSeek session-log
  contributor. A worker profile should set OTel `DISABLED` and review the contributor before private repos.
- **Profile state:** `~/.dsh` holds the retained web profile and its fnm-linked packages (AGENTS.md history). A
  worker should use its own `DSH_HOME` under `infra/harnesses/deepseek/` so nothing retained is touched.

## OpenCode (comparison)

Sources: [CLI](https://opencode.ai/docs/cli/), [server](https://opencode.ai/docs/server/),
[permissions](https://opencode.ai/docs/permissions/), [providers](https://opencode.ai/docs/providers/),
[rules](https://opencode.ai/docs/rules/), [skills](https://opencode.ai/docs/skills/),
[MCP](https://opencode.ai/docs/mcp-servers/).

| Question | DeepSeek Harness | OpenCode |
|---|---|---|
| One-shot worker | `--profile headless`, `--json` | `opencode run --format json`, `--model provider/model`, `--agent`, `--dir` |
| Resume | `--session-id <id>` | `run --session <id>` / `--continue`, `--fork` |
| Long-lived server | ACP / SDK over stdio only | `opencode serve` HTTP + SSE (`/session`, `/session/:id/prompt_async`, `/session/:id/abort`, `/fork`, `/event`), basic auth by env; `--attach` lets `run` reuse it; also `opencode acp` |
| Stop | SIGTERM/SIGINT drain (ACP/SDK documented); headless exits on its own | `POST /session/:id/abort`, or signal the `run` process |
| Unattended approvals | Unclear (see risks) | `--auto` approves everything not explicitly denied; per-tool and bash-pattern `permission` rules; `external_directory` defaults to ask |
| DeepSeek | Native default (V4 Flash) | Built-in provider via `/connect`; any OpenAI-compatible `baseURL` |
| MCP | `--patch` overlay rows, stdio/HTTP | `mcp` in `opencode.json`, local/remote; per-run config via `OPENCODE_CONFIG` (verify) |
| AGENTS.md / skills | AGENTS.md + CLAUDE.md; `.agents/skills`, `.dsh/skills` | AGENTS.md (CLAUDE.md fallback); `.opencode/`, `.claude/`, `.agents/skills` |
| Claude-style hooks | Yes, bridge package | Own plugin system (JS), no Claude hook bridge |
| Install state here | Installed, not qualified | Not installed (and was removed with other tools once; reinstall needs a request) |

OpenCode is ahead on the server/session API and on unattended permission control; dsh is ahead on being already
installed, DeepSeek-native, and running Claude hooks. For phase 1, dsh. OpenCode becomes phase 2 if headless
approvals in dsh don't qualify, or when a UI needs a session server.

## Fit with mstack

### Runner plugin per harness

`integrations/plugins/builtin/dsh/plugin.json` (the MST-54 sketch; the built manifest adds `{resume}` and a `stream` block, see "as built" below):

```json
{"name": "dsh", "joint": "agent", "transport": "argv", "status": "planned",
 "summary": "DeepSeek Harness headless, one task per process",
 "command": ["dsh", "--profile", "headless", "{mcp}", "--json", "{brief}"],
 "requires": {"binaries": ["dsh"]}, "mcp_style": "dsh-patch",
 "capabilities": ["resume", "json-events"]}
```

The real command goes through `deepseek_launch.py` so `DSH_HOME`, the key file and the toolchain are pinned there.
`opencode` gets `--format json --dir {cwd}` and `--auto` with a deny list (no push, no merge).

### Session ids, forwarding and stop (the four gaps)

1. **Session id.** `cli.py work` reads the first `session` event of the JSON stream and stores
   `run.session = "dsh:<id>"` (or `opencode:<id>`), plus `run.log`. "My tasks" then shows the worker; `agent_of()`
   maps `dsh` → `deepseek` and `opencode` → `other` (or the model). `source_url` points at the run log, not a chat.
2. **Forward.** A comment for a CLI worker is stored on the run. When the process has exited, `work --resume`
   starts a new turn with `--session-id` and the comment as the task. While it's still running, the comment waits
   until exit (dsh refuses a live session; OpenCode server mode could take it at once).
3. **Stop.** For `spawn` runs the orchestrator's `stop` becomes `SIGTERM` to the process group (it already starts
   with `start_new_session=True`) after `alive(pid)` and an identity check, then a note on the issue.
4. **Double report.** `work` skips `finish()` when the worker already ran `board done`, and otherwise posts its
   summary from the `final` event.

### Hub and events

No new event kinds. The hub keeps delivering to the project orchestrator chat (still Claude Desktop). For
`spawn` runs, the orchestrator handles `forward`/`stop` by running `mstack board work --resume` / `board stop`
instead of SendMessage. The `handoff` event is never raised for spawn hosts; `dispatch` starts them directly.
Plans name the model in their first line (`Model: DeepSeek V4 Flash (dsh headless)`), as the models skill says.

### Magpie and DeepSeek Flash

Magpie already gives a DeepSeek-backed **Claude Desktop** (the `claude-desktop` handoff host works unchanged) — but
it's an app-wide profile switch, so the orchestrator would also run on DeepSeek, and running both profiles at once
is unverified. Headless workers don't need Magpie: dsh and OpenCode call the official DeepSeek API directly. The
existing DeepSeek Flash credential can be reused through a worker-only key file (0600, under
`infra/harnesses/deepseek/`), which is a setup-guard step. Pointing them at Magpie's loopback gateway instead
would need it reachable from Ubuntu and gives nothing a direct key doesn't.

## Session-manager UIs

Web research on 2026-10-30, nothing installed. The owner already tried Paradev/Superset, Paseo and OpenCodex and
found them hard to use, so the bar is: drives Claude Code **and** an ACP/CLI agent like dsh **and** Codex, can be
driven by `mstack board` (start, message, stop), and adds little to learn.

| Option | Agents | Worktree per session | Outside control | Notes | Source |
|---|---|---|---|---|---|
| **Agent Deck** | Claude Code, Codex, OpenCode, Gemini, **dsh** (listed, with per-account `DSH_HOME`), custom via config | Yes | CLI (`add/launch`, `session send/start/stop/fork`, many with `--json`), local web UI | TUI + web over tmux; macOS/Linux; MIT, ~1.2k stars, active. Whether `session send` waits is unverified. | [repo](https://github.com/asheshgoplani/agent-deck) |
| **Zed** (Parallel Agents) | ACP registry (Claude Agent, Codex, OpenCode…) and custom ACP via `agent_servers` (fits `dsh --profile acp`) | Yes, per thread | None documented (UI only) | Best UI of the group; macOS/Linux; free with own keys. | [parallel agents](https://zed.dev/docs/ai/parallel-agents.md), [external agents](https://zed.dev/docs/ai/external-agents.html) |
| JetBrains Air | Claude Agent, Codex, OpenCode, Junie…; custom ACP | Yes (or Docker) | Not documented | Preview, proprietary; Anthropic-subscription use unclear. | [blog](https://blog.jetbrains.com/air/2026/07/what-s-new-air-gets-more-agents-local-models-and-java-kotlin-code-intelligence/) |
| Conductor | Claude Code, Codex, Cursor, OpenCode; no custom | Yes | REST/CLI/MCP, but for its hosted cloud workspaces (beta) | Mac only; can't run dsh. | [docs](https://www.conductor.build/docs/api) |
| Emdash | ~34 CLIs; dsh not listed | Yes (also SSH) | Not documented | Desktop, active; licence unconfirmed. | [docs](https://emdash.com/docs) |
| OpenCode app / `opencode serve` | OpenCode only (any provider) | Yes | Full HTTP API | Good if OpenCode becomes the DeepSeek worker. | [changelog](https://opencode.ai/changelog) |
| Claude Squad, cmux, Toad, Nimbalyst | various | partly | weak or none | TUI-first, Mac-only or pre-1.0. | — |
| Vibe Kanban | — | — | — | Shut down April 2026; avoid. | [notice](https://vibekanban.com/shutdown) |

Trade-offs:
- A polished UI and outside dispatch rarely come together: Zed/Air look like Claude Desktop but an orchestrator
  can't start their threads; Agent Deck is scriptable but terminal-first.
- Claude Code inside ACP clients runs through the Agent SDK adapter, so those sessions don't appear in Claude
  Desktop's sidebar — the owner would have two places to look.
- dsh's ACP server supports `session/list` and `session/resume` (no history replay) but not `session/load`, fork,
  terminals or client file operations, which limits it in every ACP client.
- Churn is high (Vibe Kanban shut down, Crystal deprecated, Air and Toad pre-1.0). Whatever is picked should sit on
  top of `mstack board`, not replace it.

**Recommendation.** Don't adopt a session UI in phase 1. Claude Desktop stays the hub for orchestrators and Claude
workers; headless DeepSeek workers show in "My tasks" (with the run log as their link) once gap 1 is fixed. If the
owner then wants to watch or steer DeepSeek sessions live, pilot **Agent Deck** first: unlike Paradev/Paseo it
isn't a replacement workflow but a CLI `mstack board` can drive, and it's the only one listing Claude Code, Codex,
OpenCode and dsh together. **Zed** is the GUI alternative for opening a single ACP session by hand. Either install
is a setup-guard proposal.

## Recommended phase-1 build plan

Each setup step (★) is its own setup-guard proposal and needs the owner's OK before it runs.

1. **Qualify dsh headless on a throwaway repo** ★ — own `DSH_HOME` under `infra/harnesses/deepseek/worker/`,
   OTel disabled, worker-only key file, current 0.2.0-rc.2 first (update to 0.2.1 only if a blocker needs it).
   Check: AGENTS.md and `.agents/skills` load in a worktree; what "ask" does headless; whether `git commit` and
   `mstack board note` work under the sandbox; `--session-id` resume; SIGTERM. A handful of cheap Flash calls.
2. **mstack code (no setup):** `dsh` manifest + `mcp_style: dsh-patch`; `work` records the session id from the
   JSON stream, supports `--resume` with a queued comment, skips a duplicate `finish()`; `board stop` for spawn runs;
   `agent_of()` and "My tasks" rows for spawn sessions; tests with a fake `dsh` (like `echo`).
3. **Skills:** `mstack-orchestrator` (forward/stop for spawn hosts), `mstack-models` (dsh row → available after
   step 1), `mstack-worker` (a short note that headless workers report with `note`/`done` and can't ask
   mid-run).
4. **First real issue** on DeepSeek: a small, low-risk mstack issue with `--agent dsh`, the owner reviews as usual.
5. **Then decide** phase 2: OpenCode (install ★) if dsh approvals or resume fall short, and the session-UI pilot.

## Phase-1 steps 2–3 as built (MST-57, 2026-10-30)

Code and skills only; no `dsh` was run and no model was called. Everything is tested with a fake `dsh`
(`integrations/orchestrator/tests/fake_dsh.py`) that speaks the event stream and the sandbox behaviour recorded in
the MST-56 qualification (see "Phase-1 qualification"), the way `echo` is tested. `DshStreamTests` parse lines
copied from that run.

| Gap / item | What mstack does now | Where |
|---|---|---|
| Manifest | `integrations/plugins/builtin/dsh/plugin.json`: `dsh --profile headless {mcp} {resume} --json {brief}`, `resume: ["--session-id", "{session}"]`, a `stream` block with the qualified field names, capabilities `resume`, `json-events`, `sandboxed`. Schema gained `resume`, `stream` and `mcp_style: dsh-patch`. | plugin schema, `registry.render` |
| `mcp_style: dsh-patch` | `runners.dsh_patch` writes `.mstack/cache/dsh-mcp.patch.yml` in the worktree (one `@deepseek-ai/dsh-mcp-client` stdio row per selected worker MCP server, JSON written as YAML) and passes `--patch <file>`. Never touches `~/.dsh`. | `runners.py` |
| 1. Session id | `work` reads the stream line by line (`runners.Stream`). The first `{"type":"session","sessionId":…}` sets `run.session = "dsh:<id>"` and `run.native_session` while the process still runs. The raw stream is kept beside the run log (`<log>.stream.log`, secrets redacted). Per-step `usage` is summed into `run.usage`. | `cli.py work` |
| Turn outcome | Decided from the stream, never the exit code: completed only on `{"type":"status","phase":"turn_end","reason":{"kind":"completed"}}`. Without it the run is **stopped** (when `board stop`/the hub recorded a stop: no report, no commit) or **incomplete** (a note on the issue, which stays In Progress; a comment resumes it). Hosts without a stream still use the exit code. | `Stream.completed`, `cmd_work` |
| Commit and report | dsh's `workspace-write` sandbox refuses `git commit` in a worktree and `mstack board`. For `sandboxed` hosts, `work` (outside the sandbox) commits each completed turn on the task branch (`.mstack`, `.mcp.json`, `.claude` excluded; multi-repo folders per repo), then posts the review ask from the `final` text and records it as the run's `done` report. The brief and every resume prompt say: don't commit or call `mstack board`; end with a summary. | `commit_turn`, `brief_for(headless=True)` |
| Refused actions | Headless "ask" fails closed. A `tool_result` whose text matches the manifest's `blocked_patterns` ("requires approval", "no approval channel", "denied under workspace-write", "Permission denied") is collected as a blocker. The turn still counts by its `turn_end`, and the review summary ends with a "Blocked …; the owner decides" list. | `Stream.blocked`, `Stream.summary` |
| 2. Forward | `board forward --task X "text"` and the hub: the comment is queued on the run. While `work` is live it becomes the next turn of the same session when the current one ends; otherwise a `work --resume` is spawned at once (same cwd, as dsh requires). A review reply (In Review → Todo) makes the next `dispatch` resume the recorded session with the updated brief. | `forward_to_cli`, `cmd_dispatch` |
| 3. Stop | `board stop --task X` and the hub: SIGTERM to the `work` process group after an identity check (`/proc/<pid>/cmdline` is `cli.py work … <task>`). The stop is recorded on the run first (the exit code won't show it), its queue is dropped, and nothing resumes it. Desktop workers are refused (they use `stop_session`). | `stop_cli` |
| 4. Double report | `board done` stamps its report with `ts`; for hosts that can call `board` (not dsh), `work` skips `finish()` when a `done` report is newer than the start of the last turn. | `cmd_work` |
| Hub | `tick` carries out `forward`/`stop` for CLI runs itself (`deliver_to_cli`) and lists them as `cli_workers`; they no longer become orchestrator events. Desktop runs are unchanged. | `tick_once` |
| My tasks | Spawned sessions get worker rows: `session_agent` `deepseek` for `dsh` (`HARNESS_AGENT`), link `file://<run log>`, state from the run (live → active, ended → idle unless In Review, stopped → archived). `sessions observe --complete` never marks a `<host>:<id>` session deleted; CTAs on them are refused with a pointer to `forward`/`stop`. | `status_table.py`, `cmd_sessions` |
| Skills | `mstack-orchestrator` (CLI workers' forward/stop), `mstack-models` (dsh row: after qualification), `mstack-worker` (headless workers don't commit or call `board`, can't ask mid-run). | `.agents/skills` |

### Still open

- **Launch environment.** The manifest calls `dsh` on PATH. The qualified launch (`env -i`, `DSH_HOME` =
  `state/worker-home`, `DEEPSEEK_API_KEY` from `.secrets/deepseek-worker.key`, telemetry off, the
  `worker/worker.cordis.yml` overlay) needs a headless launcher (`deepseek_launch.py` or a wrapper); then only
  `command[0]` changes. Whether dsh takes two `--patch` flags (worker overlay + mstack's MCP patch) is unverified.
- **Stdio MCP rows** in the patch (`transport: stdio`, `command`, `args`) were not part of the qualification.
- **User-level `~/.agents/skills`** leak into workers (MST-56); a clean `HOME` is a later choice.
- The hub chat can't act on "My tasks" CTAs for CLI sessions yet (continue = `forward`, archive = `stop` could be
  wired), and the run-log link is a `file://` path on the VM.

Out of scope for phase 1: ChatGPT/Codex workers (the `codex` manifest exists; the CLI is uninstalled), the
orchestrator itself on DeepSeek, and any UI install.
