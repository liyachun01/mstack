# 006 — Orchestrator over the Anytype task board

Status: **working on the live test channel with the model-free `echo` worker;**
the Codex runner is wired but no paid agent run has happened yet. 2026-10-28.

## Shape

```
 owner ──goal──▶ orchestrator agent (Claude/Codex session + orchestrator skill)
                    │ mstack board plan/ask/poll/dispatch/status/sync
                    ▼
   Anytype channel "mstack-taskboard-test" ── one Agent Task type, reused ─────────
   │ collection:           │ collection:               │ collection:            │
   │ mstack tasks          │ test-market tasks         │ <next project> tasks   │
   │ (sidebar widget; Board kanban by status / Table)                           │
   │ each issue: plan body + discussion (🤖❓ asks, owner 👍 / replies)         │
   ─────────────────────────────────────────────────────────────────────────────
                    │ dispatch: one worker per approved task
          ┌─────────┼──────────┐
       codex     claude     opencode     (only if installed; echo = test)
       worktree  worktree   worktree     .mstack/worktrees/<id>, branch task/<id>
          └── results + session turns flow back to the same issue (note / capture hook)
                    ▲
   optional link ── Linear (pull | push | full; my issues or one label)
```

| Piece | Where |
|---|---|
| Toolbelt CLI (`mstack board …`) | [`integrations/orchestrator/cli.py`](../../integrations/orchestrator/cli.py) |
| Board model, verdict rules | [`board.py`](../../integrations/orchestrator/board.py) |
| Worker runners | [`runners.py`](../../integrations/orchestrator/runners.py), [`echo_worker.py`](../../integrations/orchestrator/echo_worker.py) |
| Linear link | [`linear.py`](../../integrations/orchestrator/linear.py) |
| Orchestrator playbook | [`.agents/skills/mstack-orchestrator/SKILL.md`](../../.agents/skills/mstack-orchestrator/SKILL.md) |
| Session → issue hook | [`capture_hook.py`](../../integrations/agents/capture_hook.py) |
| Mac-side API bridge | `anytype_taskboard.py api` (channel-confined, one request per call) |
| Table registry, runs | `.mstack/evidence/taskboard-test.json` (ignored) |

## Host layer: CLIs and desktops behind one contract

All communication goes through the board, never through the host. So any agent
app fits if it can (1) start in the task worktree with the brief, (2) see the task
binding (`MSTACK_TASK` or `.mstack/cache/current-task`), and (3) run
`mstack board note` / `done`. `dispatch` prepares the same things for every host:
the worktree and branch, the binding, `.mstack/cache/brief.md`, the base commit,
and the project's local hook settings.

| Host | Kind | How it starts | How it reports |
|---|---|---|---|
| `codex` | spawn | `codex exec --cd <tree>` (detached) | exit → `finish`; turns through per-run `notify` |
| `claude`, `opencode` | spawn | `claude -p`, `opencode run` | exit → `finish` (CLIs not installed today) |
| `echo` | spawn | model-free test worker | exit → `finish` |
| `claude-desktop` | handoff | the orchestrator, running in Claude Desktop, calls `start_session` with the spec's cwd, title and prompt | worker runs `done`; project hooks mirror turns; the app wakes the orchestrator when the worker's turn ends |
| `codex-desktop` | handoff | you open the worktree in Codex Desktop (spec `instructions`) | worker runs `done` / `note` |

A handed-off task counts toward `max_parallel` until it reports `done`.
Possible later hosts, unverified: Codex's experimental `codex app-server` daemon,
which Codex Desktop also uses (`codex agents`), could make `codex-desktop`
startable from a script. `opencode serve` provides an HTTP API for creating many
sessions. Each would be a new `HOSTS` entry with the same contract.

## Project config

```json
"taskboard": {
  "table": "test-market",
  "workers": ["codex", "claude", "opencode", "echo"],
  "max_parallel": 3,
  "link": {"provider": "linear", "mode": "full", "scope": "label", "label": "agents",
           "team": "MKT", "credential_file": ".mstack/secrets/linear-api-key"}
},
"capture": {"enabled": true, "sink": "anytype-taskboard", "harnesses": ["claude", "codex"]}
```

Without `link`, a table stays private to Anytype. `mode: pull` or `push` is a
partial link (one direction). `scope: label` limits it to one label, and `mine`
means issues you are assigned or created. The channel key belongs to mstack (the
board owner); a project never holds it. A Linear key, when added, is the
project's own credential.

## Verdicts on the issue

The orchestrator's key acts as the same Anytype user as you, so its lines start
with 🤖, and lines that wait for you start with 🤖❓. Anything else in a discussion
is you. The latest ask decides:

| You do | Awaiting Approval → | In Review → |
|---|---|---|
| 👍 ✅ 🚀 👌 ❤️ reaction, or reply `lgtm` / `approve` / `ok` / 👍 | Todo (queued) | Done (branch ready to merge) |
| 👎 ❌ reaction | Canceled | Todo (back to the worker) |
| Any other reply | Feedback for the orchestrator to revise; it re-asks | Todo, with your notes in the next brief |

## Reverse path

Each worker runs with its task bound: `MSTACK_TASK`, plus a marker in its worktree
and a copy of the project's local hook settings. A Claude session opened in that
worktree mirrors your prompt and its reply onto the issue. Codex workers do the
same through a per-run `notify` (never global config). Any session can post
`mstack board note --task … [--status …] "…"`. The capture hook's project-scope
and config-agreement checks still apply. A worktree session uses its main checkout's config.

## Verified 2026-10-28 (live channel)

- Two tables in one channel: the collections `mstack tasks` (5) and `test-market tasks` (3).
  Every task uses the one reusable **Agent Task** type, and a collection per project is its
  table: explicit membership, Board (kanban by status) and Table views, a sidebar widget.
  Two earlier layouts were wrong in the UI. Filtered queries over a shared type mixed
  projects and didn't appear in the sidebar. A type per project was unnecessary. The
  migration re-typed tasks in place (same IDs and discussions) and removed the old objects.
- Three test-market plans created. A simulated 👍 reaction approved one. A simulated reply
  came back as feedback and the orchestrator re-asked with a revised plan. The third
  is left for you.
- `dispatch` ran an `echo` worker detached, in `.mstack/worktrees/zpy6mbki` on
  branch `task/zpy6mbki`: one commit, issue → In Review with a 🤖❓ result ask.
- Simulated session turns from that worktree went through the real hook, and a `note`,
  appeared on the same issue. The main checkout stayed clean.
- Tests: 57 stack, 16 agents, 7 orchestrator (fake board, real git, Linear with a fake transport).

## One table per repo (2026-10-29)

One repo = one table (an Anytype collection of the shared Agent Task type). A monorepo's apps
share it and are told apart by the naming convention and two fields:

- **Titles:** `[APP][KIND] description`, e.g. `[API][BUG] Login fails on retry`. `plan --app API --kind BUG`
  sets the title and the **App** and **Kind** fields. Kinds: FEAT, BUG, CHORE, DOCS, TEST, REFACTOR, PERF, SEC, OPS.
- **Apps:** `taskboard.apps` maps codes to folders. A worker gets a worktree of the whole repo
  and starts in its app's folder; the capture hook still finds its task there.
- **Per-app Linear links:** each app may have its own `link` (own key file, workspace, team).
  Its issues arrive as `[APP]` tasks, with Kind taken from a matching Linear label. Only its tasks are
  pushed, without the board prefix. A table-wide `link` covers tasks of apps without their own.
  `mstack board link --project P --entry N --team T [--app CODE]`.

```json
"taskboard": {"table": "{{mstack:CLIENT_REPO}}", "apps": {
  "API": {"path": "apps/clientapp-api", "link": {"provider": "linear", "mode": "pull", "workspace": "{{mstack:CLIENT_ORG_A_SHORT}}",
          "team": "IRO", "key_entry": 2, "credential_file": ".mstack/secrets/linear-api-key-api"}},
  "WEB": {"path": "apps/staff-web"}}}
```

A cross-repo "All tasks" view was tried and dropped (2026-10-29): too many repos and angles to
manage in one place.

## Always-on loop (2026-10-28)

- `mstack board tick`: one pass over tables with `taskboard.auto: true`. It applies
  verdicts, dispatches approved tasks within `max_parallel` and returns
  `needs_orchestrator`: unstarted desktop handoffs (re-offered until `ack`), and
  plan feedback (surfaced once).
- `mstack board watch`: a shell loop of `tick` with no model calls. It exits only
  when an agent is needed, so a waiting Claude Desktop orchestrator wakes only for
  real work. It stops after 5 failed ticks in a row.
- Dependencies: **Blocked By** tasks wait until their blockers are Done, then start
  with the blockers' `task/*` branches merged into their own branch. A conflict
  stops that dispatch with a message.
- Desktop scheduled tasks can't be created from an SSH-host session. The watcher
  runs in the background of the orchestrator session, so it is always-on only while
  that session and the Mac are up. For headless always-on, a host scheduler or a
  Windmill schedule would run `tick`, but desktop handoffs still need a Desktop agent.
- Fixed with it: Anytype stores a typed 👍 as `:+1:`; shortcodes are now verdicts
  (a 👍 with extra text is still feedback). `status` no longer fails on handoff runs.

## Not yet

- No real Codex/Claude/OpenCode worker run. The Claude CLI and OpenCode aren't
  installed; installing either needs its own setup-guard step.
- No Linear token, so the link is tested only against a fake GraphQL transport.
- Branches aren't merged or pushed. Plan bodies aren't rewritten on replan; revised
  plans live in the discussion.
