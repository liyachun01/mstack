# 013 — Session roles that stick, and sparks back to mstack (built, 2026-10-29)

## Problem

The owner gives work to the top-level {{mstack:CLIENT_REPO}} orchestrator, but it didn't stay in its role: it didn't pass work
on to the sub-orchestrator or a worker. The customer-api sub-orchestrator didn't either. Each session's role
lived only in its first prompt, which fades in a long chat and is summarized away on compaction.

## Roles (strict)

| Role | Does | Never |
|---|---|---|
| **orchestrator** (one per project, top level) | takes requests, makes issues, assigns to sub-orchestrators or workers, reports | issue work |
| **sub-orchestrator** (one per scope) | plans, verdicts, dispatches workers, forwards feedback, reports up | issue work; work outside its scope |
| **worker** (one per issue, `<ISSUE>: <title>`) | implements its one issue in its worktree | starting sessions, other issues |

Exception: the owner explicitly approves, in the chat, that an orchestrator or sub-orchestrator does a named issue
itself. It says so, records it with `note`, and does only that issue.

## Role cards

- Every Claude Desktop session exposes its id as `$CLAUDE_CODE_HOST_SESSION_ID`.
- A project-scoped hook (`UserPromptSubmit` and `SessionStart`, in the project's personal
  `.claude/settings.local.json`) runs `integrations/agents/roles.py hook`. It looks the session up and adds a short
  role card to the context on every message, so the role survives long chats and compaction.
- **Registered roles:** `mstack role set` stores them in the project's private `.mstack/state.json`
  (`runtime.roles`).
- **Inferred roles:** workers and adopted sessions come from the board's runs, and related chats from `related`.
- An unknown session gets nothing.
- `mstack sync` installs the hook in every project that has a board. `mstack role card` shows a session's card.

Limit: Claude Code reads hooks when a session starts. A session that was already running gets cards only once it
restarts, or a new session is started; until then it was sent its card once by message.

## Sparks (reverse reports to mstack)

`mstack spark --from <project> "<idea>" [--detail -] [--doc <path>]` files an `[SPARK]` issue in MST Backlog, assigned
to the owner. It records the source project and session. The owner triages it; `/plan` starts work. Every role card
and the worker skill mention it, so ideas from project work reach mstack without anyone editing mstack from inside
a project.

## Helpers and nested sub-issue workers (2026-10-29)

The IRO-104 worker started workers for its sub-issues (IRO-111, IRO-112 and IRO-113) as its own side sessions. Their
progress reached it automatically through Claude Desktop's side-session link: turn-end notes, wake-ups and
direct questions. The owner liked that, so mstack now supports it:
- **Two layers:** Claude carries live coordination along the nesting; mstack keeps the durable record. Each issue's
  record is written only by the session that owns that issue.
- **Helper** (`mstack role set --role helper --task <ISSUE> --worker <id>`): the worker's side session for one part
  of the same issue. It reports only to its worker and never writes to the board. It starts no sessions; one
  level only.
- **Sub-issue worker:** may be started by the parent issue's worker as a side session, and is then adopted by the
  orchestrator. It owns its sub-issue's record. Runs now store `parent`, so cards show the link both ways: the
  parent worker lists its sub-issue workers, and a sub-issue worker names its parent's worker.
- **Nesting is kept:** orchestrators don't move workers to top level, because that can't be undone and drops the
  automatic notes. Sidebar groups and the board still track chats that were already moved.
