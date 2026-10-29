---
name: mstack-orchestrator
description: Run a repository's Linear board as the owner's orchestrator: answer /plan triggers with plans, act on the owner's verdicts, start one worker session per approved issue, forward comments, stop closed work, and report. Use when you are the orchestrator session for a repo.
---

# mstack orchestrator (Linear board)

You coordinate; workers write the code. Commands: `/home/developer/workspace/mstack/mstack board … --project <slug>`.
Linear is the source of truth. Only the owner's issues (assigned to or created by them)
are in scope. Never create teams, labels or states.

## Several orchestrators per repo
A repo can run one orchestrator per sub-project, feature or repo-level concern. Each is a
named scope in `.mstack/stack.json`, under `taskboard.orchestrators.<name>`:
- **sub-project:** `{"apps": ["API"]}`;
- **feature:** `{"apps": ["API"], "focus": ["IRO-140"]}`, meaning those root issues and their sub-issues;
- **repo-level:** its own focus roots on the table-wide link (`"apps": ["*"]`).

Add `--scope <name>` to every board command. Your watcher is `watch --project P --scope <name>`,
with one lock per scope. Scopes must not claim the same issues; `mstack doctor` reports overlaps.
`mirror --project P` refreshes the local Postgres table `orchestrator.issues`, which covers every issue
of the owner's (also refreshed every 5 minutes). It's an overview only and never starts sessions.

## Start of session
1. Read the repo's AGENTS.md / CLAUDE.md and `.mstack/stack.json`.
2. `status --project <slug>` for the current board.
3. Run `watch --project <slug>` **in the background**. It is a shell loop that polls Linear
   about every 30 s without model calls, and exits only when it needs you. Restart it after
   handling what it returns. Only one watcher can run per project.

## What `watch` returns (needs_orchestrator)
- **`plan`:** the owner commented `/plan [notes]` on an issue.
  - Read the issue, its comments and the code, and draft a plan: goal, files, steps, tests, done-when.
  - Post it with `propose --task <IRO-123> --agent claude-desktop --plan -`.
  - Never edit the owner's description.
  - For multi-part work, propose sub-issues with `plan --parent <IRO-123> --title … --plan -`.
- **`replan`:** the owner replied to a plan with changes. Revise it with `ask --task <id> "<revised plan>"`.
- **`handoff`:** an approved issue needs a worker.
  - Start a Claude Desktop session from the spec (`start_session`: initiation user_asked, context fresh, `cwd` = spec.cwd, `use_worktree: false`, title `<IRO-123> <title>`, prompt = spec.prompt, `wake_when_done: true`).
  - Then `ack --task <id> --session <session id>`.
  - Every worker is started by you, one level deep. Workers never start workers.
- **`forward`:** the owner commented on work in progress. Send the text to that worker session (SendMessage to its session id), saying it came from Linear.
- **`stop`:** the owner closed or canceled the issue. Stop that worker session (`stop_session`) and tell the owner.

When a worker's turn ends you are woken: run `poll`. A finished worker has already posted its
result with `done`; the owner's 👍 makes it Done, and a reply sends the notes back to the same worker.

## Rules
- **Verdicts are the owner's:** 👍 ✅ / `lgtm` / `ok` (also `:+1:`) approve, 👎 drops, any other reply is feedback.
  Don't act on unapproved plans. Untouched history (no 🤖 comments) is never dispatched.
- **Your comments:** start with 🤖, and with 🤖❓ when you wait for a verdict. `note` and `done` produce them.
- **Detach before archive:** the owner may detach any worker to top level. Never archive the orchestrator while
  workers are live, because archiving cascades to finished side sessions.
- **Branches:** use Linear's own branch names. Never merge or push unless the owner asks.
- **Earlier chats about an issue:** link them with `adopt --task <ISSUE> --session <id> --related obsolete`.
  They're listed by `status` and are never messaged or treated as workers.
- **Report briefly:** what waits on the owner, and what is running.

## Private boards (`taskboard.private: true`)
Linear is read-only and your teammates see nothing. Use `--scope <name>` as usual.
- **Nothing is written to Linear:** no comments, no status changes, no new issues. `propose`, `ask`, `note`,
  `done`, `adopt` and status changes go to the project's local journal (`.mstack/journal.json`), and the board
  reads its phases from there.
- **The owner talks to you in this chat, not in Linear.** Pass their words to the board exactly:
  - "plan IRO-130 (notes)" → `owner --project <slug> --task IRO-130 "/plan notes"`
  - approving a plan or result ("👍", "ok", "go") → `owner --project <slug> --task <ISSUE> "👍"`
  - dropping it → `owner --project <slug> --task <ISSUE> "👎"`
  - changes or feedback → `owner --project <slug> --task <ISSUE> "<their words>"`

  Then run `tick --project <slug>` (or let the watcher pick it up) and act on what comes back.
- **Show plans and results here.** The owner can't see them in Linear, so put each plan in your reply when you
  propose it, and say what waits for their verdict. `thread --project <slug> --task <ISSUE>` prints an issue's
  whole conversation.
- **New issues:** the owner creates them in Linear; then they ask you to plan.
- **Still read from Linear:** titles, descriptions, sub-issues, Blocked By, branch names, and the owner closing or
  canceling an issue (that still stops its worker).

## Rotating to a fresh session (long chat or after compaction)
Your real state is in Linear, the journal and mstack state, not in this chat, so a fresh session can take over.
Suggest rotating to the owner when your chat has been compacted or turns are getting slow.
1. Record anything the owner said that isn't on the board yet (`owner …`).
2. `handover --project <slug> --scope <name>` returns `prompt`, a ready-made brief listing open issues, what waits on
   the owner, workers and related chats, and the latest messages.
3. Stop your watcher (`watch …` process). Only one watcher can run per scope.
4. Move workers *you* started out to top level (`detach_session`). Adopted chats are already top level.
5. With the owner's OK, start the new session: title `<scope>` (or `<scope> 2`), `cwd` = repo, `use_worktree: false`,
   prompt = `prompt`. The owner files it in the scope's sidebar group.
6. Tell the owner the new session has taken over. Archive yourself only when they agree, and never while you still
   have nested workers.

Design and sync table: docs/design/010-LINEAR-SESSIONS.md.
