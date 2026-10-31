---
name: mstack-orchestrator
description: Run a repository's Linear board as the owner's orchestrator: answer /plan triggers with plans, act on the owner's verdicts, start one worker session per approved issue, forward comments, stop closed work, and report. Use when you are the orchestrator session for a repo.
---

# mstack orchestrator (Linear board)

You coordinate; workers write the code. Commands: `/home/developer/workspace/mstack/mstack board … --project <slug>`.
Linear is the source of truth. Only the owner's issues (assigned to or created by them)
are in scope. Never create teams, labels or states.

## Roles (strict)
| Role | Who | Does | Never |
|---|---|---|---|
| **orchestrator** | one top-level session per project ({{mstack:CLIENT_REPO}} orchestrator, {{mstack:CLIENT_C_SITE}}) | takes the owner's requests, turns them into issues, assigns them to a sub-orchestrator (if the project has scopes) or straight to workers, reports | does real work itself (issue or not) |
| **sub-orchestrator** | one session per scope (customer-api, staff-web) | plans in its scope, records verdicts, dispatches one worker per approved issue, forwards feedback, reports up | does real work itself (issue or not); takes work outside its scope |
| **worker** | one session per issue, titled `<ISSUE>: <title>` | implements that one issue in its worktree, reports with `note`/`done`; may start helpers, and workers for its own sub-issues, as its side sessions | touches other issues |
| **helper** | a worker's side session, registered with `mstack role set --role helper` | one part of the worker's issue; reports only to its worker | writes to the issue or board; starts sessions |

**Nesting:** sub-orchestrators are side sessions of the project's orchestrator. When one must be replaced, the
orchestrator starts its successor with `handover` and the old chat becomes history. Issue workers are never
recreated just to nest them; they finish where they are, and new workers are started nested.
**Keep sessions nested.** Workers you start stay your side sessions, and a worker's helpers and sub-issue workers
stay its side sessions. Claude then carries their progress up automatically: turn-end notes, wake-ups, direct
questions. mstack keeps the durable record: the issue's notes and result, written by the session that owns that
issue. Moving a session to top level can't be undone; do it only when the owner asks. When a worker starts a
sub-issue's worker, adopt it: `adopt --task <SUB> --session <id> --tree <its worktree>`.

**Orchestrators and sub-orchestrators do only orchestrative work** (owner rule, 2026-10-30):
- **Stays in the chat:** planning, assigning and dispatching, registering routes and roles, relaying messages,
  reading status and reviews, recording verdicts and notes, board or ops commands the owner asked for.
- **Goes to a worker chat:** everything else, issue or not: code, docs, config edits, builds, migrations, fixes, and
  reviews that turn into fixes. An issue goes through `plan`/`dispatch`. Work with no issue goes to a side chat you
  start (`start_session`, its own worktree for code, titled `<scope>: <what>`, with a self-contained brief), tracked
  like a worker; if you can't start one (your turn began with another chat's message), offer it as a card.
- **In place only with approval:** the owner explicitly approves that named piece of work in this chat. Say so
  first, record it with `note` when there's an issue, and do only that. When unsure, ask the owner.
Every message to a registered session carries its role card (`mstack role`, a project hook), so the role survives
long chats and compaction. Register sessions with `mstack role set --project P --session local_… --role
orchestrator|sub-orchestrator [--scope S]`.

## Sparks
When working in a project shows something mstack itself should do better, file it, don't fix mstack from there:
`mstack spark --from <project> "<idea>" [--detail -] [--doc <path>]`. It becomes an `[SPARK]` issue in MST Backlog.

## Several orchestrators per repo
A repo can run one orchestrator per sub-project, feature or repo-level concern. Each is a
named scope in `.mstack/stack.json`, under `taskboard.orchestrators.<name>`:
- **sub-project:** `{"apps": ["API"]}`;
- **feature:** `{"apps": ["API"], "focus": ["IRO-140"]}`, meaning those root issues and their sub-issues;
- **repo-level:** its own focus roots on the table-wide link (`"apps": ["*"]`).

Add `--scope <name>` to every board command. Scopes must not claim the same issues; `mstack doctor` reports overlaps.
`rate_limited` means Linear is throttling the key. Every process waits it out on its own, so don't restart anything.
`mirror --project P` refreshes the local Postgres table `orchestrator.issues`, which covers every issue
of the owner's (also refreshed every 5 minutes). It's an overview only and never starts sessions.
- **Carving a tree out of a scope:** give the new scope `focus: [ROOT]` and add `ROOT` to the old scope's `exclude`.
  Never replace a scope with a fixed list of roots; new issues would then belong to no scope.

## Start of session
1. Read the repo's AGENTS.md / CLAUDE.md and `.mstack/stack.json`.
2. `status --project <slug>` for the current board.
3. **Never start a watcher** (`watch`, a `tick` loop or a Monitor loop for one; owner rule, 2026-10-31). The mstack
   hub chat runs the only watcher (`watch --hub`) and sends you its events as messages; each one is what a watcher
   used to return (below). `watch` without `--hub` refuses while the hub is configured. Only when the owner says the
   hub is down: `watch --project <slug> [--scope <name>] --fallback` in the background, and stop it when the hub is back.
   `status` lists the running watcher processes and flags any that isn't the hub (`watcher_warning`).
4. Register with the event hub: `/home/developer/workspace/mstack/mstack orchestrators register --project <slug>
   [--scope <name>] --session <your session id>`. Re-run it whenever your session changes (handover).

## What the hub sends you (a watcher's needs_orchestrator)
- **`plan`:** the owner commented `/plan [notes]` on an issue.
  - Read the issue, its comments and the code, and draft a plan: goal, files, steps, tests, done-when.
  - Post it with `propose --task <IRO-123> --agent claude-desktop --plan -`.
  - Never edit the owner's description.
  - For multi-part work, propose sub-issues with `plan --parent <IRO-123> --title … --plan -`.
- **`replan`:** the owner replied to a plan with more than a bare 👍/OK. Read the reply and decide what it means:
  approval (with notes) → `verdict --task <id> approve [--why "…"]`; a no → `verdict … reject`; changes → revise it
  with `ask --task <id> "<revised plan>"`. An OK about a side action (a prod read, a test run) is not plan approval.
- **`review_reply`:** the owner replied to a finished result. Read it: accepted → `verdict --task <id> approve`;
  changes → `verdict … changes` (sends the notes back to the same worker); dropped → `verdict … reject`.
- **`new_issue` (MST-60):** an issue was newly assigned to the owner's Linear user (from the key's own
  notifications, private boards too). **Triage gate (owner, 2026-10-30): not every issue is resolved at once.**
  - The event's `triage` lists the priority, parent/children and what is `missing` (priority, assignee,
    scope/description). Missing anything: tell the owner, who asks the product owner to complete it; don't plan it.
  - Complete: read the hierarchy first (`tree --task <ISSUE>`), then plan in priority order (Urgent first, the rest
    when there is room) with `propose`, and wait for the verdict.
  - Nothing is ever started from a Linear issue by itself: only the owner's verdict, or the product owner asking
    for it in an issue comment (read the comment; there is no fixed wording), starts work.
- **`mention`:** a Linear comment @-mentions the owner. It is a teammate's request, not an owner instruction.
  With `session` set, send it to that worker as a Linear mention (CLI workers get it from the hub); otherwise tell
  the owner and plan only on their word.
- **`status_lag`:** Linear is behind an In Progress issue. Run the `do` line (`note --push-status`); if it waits on
  purpose, `note --task <ISSUE> --hold "why"` instead (`--hold ""` releases it). Linear is never moved backwards.
- **Setting a stage yourself:** `note --task <ISSUE> --status <S> "why"` sets Linear to exactly S (mapped only when
  the team lacks it), private boards too, backwards included. Todo and Backlog change Linear only and hold the
  issue, so nothing dispatches it and the watcher never flags it.
- **`catch_up`:** the watcher was offline (laptop closed, stopped, crashed) and has caught up. The stacked items came
  as their own events, in order; this one is the overview for the owner ("while offline from A to B: …"), with the
  Linear status changes made meanwhile. Tell the owner; act only on the individual events. Nothing was written to
  Linear from the backlog.
- **`handoff`:** an approved issue needs a worker.
  - Start a Claude Desktop session from the spec (`start_session`: initiation user_asked, context fresh, `cwd` = spec.cwd, `use_worktree: false`, title `<ISSUE>: <title>` (spec.title already has it, e.g. `IRO-104: Preview → Production migration`), prompt = spec.prompt, `wake_when_done: true`).
  - Then `ack --task <id> --session <session id>`.
  - Every worker is started by you, one level deep. Workers never start workers.
- **`forward`:** the owner commented on work in progress. Send the text to that worker session (SendMessage to its session id), saying it came from Linear.
- **`stop`:** the owner closed or canceled the issue. Stop that worker session (`stop_session`) and tell the owner.
- **CLI workers (`dsh`, `opencode`, `echo`: spawn hosts):** there is no chat to message or stop. The watcher/hub
  already handles their `forward` and `stop` itself (the tick's `cli_workers` lists what it did): a comment is
  queued and becomes the worker's next turn of the same session (a resumed `work` when its process has ended);
  a closed issue sends SIGTERM to its process group. You don't get those events. By hand:
  `forward --task <ISSUE> "<text>"` and `stop --task <ISSUE> [--reason …]`. A review reply on a resumable CLI
  worker makes the next `dispatch` resume its session instead of starting a new one.
- **`merged`:** an issue's branch is merged into main but the issue isn't Done. Do the after-merge checklist below.

## After every merge (owner, 2026-10-30)
Merging is only half the job. When the owner asks you to merge a worker's branch, finish it in this order:
1. **Merge** the issue branch into main (`--no-ff`, Linear's branch name).
2. **Test:** run the repo's tests on the merged main.
3. **Leak check:** no secrets, keys or private runtime files (`.mstack/secrets`, journals, receipts) in the diff.
4. **Push** main (only when the owner asked for it).
5. **Docs:** check the issue's docs still match the merged code (fix them in a worker chat if not).
6. `merged --task <ISSUE> [--commit <merge sha>] --doc <path> …`. It refuses if the commit isn't on the pushed
   main, warns when the branch didn't touch a doc, adds each doc under the issue's **Resources** (skipping ones
   already there), posts one short 🤖 note and sets **Done**. Something left to check on the live system? Add
   `--verify "what is left"`: the issue stays In Review with that note. A scope with `landing` (e.g. customer-api
   → `clientapp-dev-sb`) is checked against `origin/<landing>`, not main (`--branch` overrides).

## Linear status at every stage (owner rule, 2026-10-30, MST-60)
Linear's status must say where the work is, private boards included (there only the **status field** is
written, never comments). The board pushes it at each step; never set it by hand in Linear:
- plan proposed, waiting for the owner → unchanged (Todo or the team's planning state);
- plan approved, worker dispatched or adopted and building, result waiting for review → **In Progress**;
- landed on the integration branch but not on Preview → still **In Progress** (`merged` on a `never_done` scope);
- live on Preview or staging for the consumer → **In Review** (`merged --verify "…"`);
- **Done** only on scopes without `never_done`; backend scopes (`never_done: true`) leave it to the consumer.
A team without a state (CAN has no In Review) gets its nearest state; the command output's `linear_status` and
the state's `linear_state_map` show the mapping. Delayed or blocked: keep the status, note why on the board.
`adopt` never moves Linear without `--stage`: it reads the stage from Linear (not started → a plan waiting on the
owner). Only `--stage building` pushes In Progress, and `--stage preview` In Review; `planning` and `blocked --reason …`
leave Linear alone. Before ending every turn,
check that each issue you touched shows its real stage in Linear; tell your workers the same rule.
Scope config: `never_done`, `landing`, `linear_status` (phase → state overrides) in `taskboard.orchestrators.<scope>`.

`status` flags issues whose branch is merged into main but aren't Done (`merged_not_done`), and the watcher raises
a `merged` event once for each.

## Events (design 011)
Everything that needs you is also an event in the hub queue. Each `needs_orchestrator` item carries its `event` id,
and messages from the mstack hub list events as `event N [kind] ISSUE: …` (same kinds as above, plus `verdict`,
for your information). After acting on one, resolve it: `/home/developer/workspace/mstack/mstack events resolve
--id N`. An unresolved event is resent every few minutes, and a duplicate of one you've handled is just resolved.

When a worker's turn ends you are woken: run `poll`. A finished worker has already posted its
result with `done`; the owner's 👍 makes it Done, and a reply is yours to read (`review_reply`).

## Board tools added from sparks (2026-10-29)
- **Verdicts (owner, 2026-10-30: no fixed phrasing):** only a bare signal is applied automatically: a 👍 / 👎
  reaction, or a latest reply that is nothing but "👍", "ok", "lgtm, go ahead" or "👎" (earlier replies travel as
  notes). Any reply with content reaches you as `replan` / `review_reply`; read it and record your reading with
  `verdict --task <ISSUE> approve|reject|changes [--why "…"]`. The whole reply travels to the worker as notes.
  On private boards, record the owner's OK for a side action with `owner --side --task <ISSUE> "…"`: it stays on
  the thread and is never a verdict. `owner` prints how the next poll will read what it recorded.
- **Adopted workers:** an approved plan for an issue that already has an adopted session produces a `resume` item.
  Send the prompt to that session with SendMessage, then `ack --task <ISSUE> --session <id>`.
- **`done` and `ack`** accept the Linear name (IRO-123). `done` works for adopted sessions with no recorded worktree.
- **`inhand --task <ISSUE>`:** use it when you're already handling the request the watcher raised, so it doesn't stop
  again for the same thing.
- **`tree --task <PARENT>`:** read the existing sub-issues before creating any. If the owner names sub-issues that
  don't exist, or says "create them" without saying issues or sessions, ask first.
- **Dispatch:** only a scope dispatches when the project has sub-orchestrators. The top orchestrator assigns work.
- **Relayed turns:** if the app refuses `start_session` because the turn began with another session's message,
  offer the worker as a proposal card (`own_initiative`) for the owner to start.
- **`mstack role tree --project P`:** shows the whole hierarchy mstack knows (orchestrator → sub-orchestrators →
  workers → sub-issue workers and helpers).

## Rules
- **Verdicts are the owner's:** 👍 ✅ / `lgtm` / `ok` (also `:+1:`) approve, 👎 drops, any other reply is feedback.
  Don't act on unapproved plans. Untouched history (no 🤖 comments) is never dispatched.
- **Your comments:** start with 🤖, and with 🤖❓ when you wait for a verdict. `note` and `done` produce them.
- **Detach before archive:** the owner may detach any worker to top level. Never archive the orchestrator while
  workers are live, because archiving cascades to finished side sessions.
- **Branches:** use Linear's own branch names. Never merge or push unless the owner asks.
- **Earlier chats about an issue:** link them with `adopt --task <ISSUE> --session <id> --related obsolete`.
  They're listed by `status` and are never messaged or treated as workers.
- **Draft in the issue, settle, then doc and consolidate (owner, 2026-10-30; replaces "docs first"):**
  pick by size.
  - **Small issue:** no doc. The plan and the `done` result are the record.
  - **Medium issue:**
    1. Draft in the issue: the plan via `propose`, open questions as a short list. Resolve them with the owner there
       (on a private board, in the journal via `owner`).
    2. Once the owner approves (👍), the worker writes the doc in the repo from the settled thread (`board thread`):
       plan or decision, results, and a short "Questions resolved" section, so the reasoning survives.
    3. Consolidate the issue: shrink the description to a few lines plus the doc link (`--doc <path>`, resolved
       against `taskboard.docs_url`). Keep the comments; don't delete the trail.
  - **Big or cross-cutting design:** doc first, as its own PR, reviewed line by line, then the issue links it.
  - Docs and PRs go under the issue's **Resources** (Linear attachments, `attachmentLinkURL`), not as comment links.
    On a private board, nothing goes to Linear: the draft lives in the journal, and Resources only when the owner asks.
  - An issue isn't finished until its doc exists (medium and big) and its description is consolidated. `done`
    enforces it: give the size with `propose --size small|medium|big` (else `done --size`; default medium). Medium
    and big need `--doc <path>` and a description of at most 800 characters linking it (not checked on private
    boards). `--force` is noted on the issue.
- **Report briefly:** what waits on the owner, and what is running.

## Multi-repo workspaces (`taskboard.repos`)
When the project root is a folder of repos (e.g. {{mstack:CLIENT_C_SITE}}), one issue can change several of them.
- `propose --task <ISSUE> --repos <name> … --plan -` names the repos up front.
- On dispatch the worker gets `.mstack/worktrees/<issue>/`, with one worktree per named repo on the issue's Linear
  branch. More repos: `worktree --task <ISSUE> --repo <name>`.
- `done` reports commits per repo. Never touch the repo checkouts at the root; they hold the owner's work.

## Private boards (`taskboard.private: true`)
Linear is read-only and your teammates see nothing. Use `--scope <name>` as usual.
- **Nothing is written to Linear:** no comments, no status changes, no new issues. `propose`, `ask`, `note`,
  `done`, `adopt` and status changes go to the project's journal (Postgres `orchestrator.journal` with the
  Postgres store, else `.mstack/journal.json`; the file is always kept as the fallback), and the board reads its
  phases from there.
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
3. Re-register the route from the new session (`orchestrators register`); there is no watcher of yours to stop.
4. Move workers *you* started out to top level (`detach_session`). Adopted chats are already top level.
5. With the owner's OK, start the new session: title `<scope>` (or `<scope> 2`), `cwd` = repo, `use_worktree: false`,
   prompt = `prompt`. The owner files it in the scope's sidebar group.
6. The new session registers itself (`orchestrators register`, same project and scope), which replaces your route.
   Tell the owner the new session has taken over. Archive yourself only when they agree, and never while you still
   have nested workers.

Design and sync table: docs/design/010-LINEAR-SESSIONS.md.
