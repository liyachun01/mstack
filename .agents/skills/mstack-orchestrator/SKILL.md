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

Add `--scope <name>` to every board command. Your watcher is `watch --project P --scope <name>`,
with one lock per scope. Scopes must not claim the same issues; `mstack doctor` reports overlaps.
While the hub watcher runs and your scope is registered, your watcher leaves Linear to the hub (`left_to_hub`
in its tick line) and the hub's events wake you. It polls Linear itself only as the fallback when there is no hub.
`rate_limited` means Linear is throttling the key. Every process waits it out on its own, so don't restart anything.
`mirror --project P` refreshes the local Postgres table `orchestrator.issues`, which covers every issue
of the owner's (also refreshed every 5 minutes). It's an overview only and never starts sessions.
- **Carving a tree out of a scope:** give the new scope `focus: [ROOT]` and add `ROOT` to the old scope's `exclude`.
  Never replace a scope with a fixed list of roots; new issues would then belong to no scope.

## Start of session
1. Read the repo's AGENTS.md / CLAUDE.md and `.mstack/stack.json`.
2. `status --project <slug>` for the current board.
3. Run `watch --project <slug>` **in the background**. It is a shell loop that polls Linear
   about every 30 s without model calls, and exits only when it needs you. Restart it after
   handling what it returns. Only one watcher can run per project.
4. Register with the event hub: `/home/developer/workspace/mstack/mstack orchestrators register --project <slug>
   [--scope <name>] --session <your session id>`. Re-run it whenever your session changes (handover).

## What `watch` returns (needs_orchestrator)
- **`plan`:** the owner commented `/plan [notes]` on an issue.
  - Read the issue, its comments and the code, and draft a plan: goal, files, steps, tests, done-when.
  - Post it with `propose --task <IRO-123> --agent claude-desktop --plan -`.
  - Never edit the owner's description.
  - For multi-part work, propose sub-issues with `plan --parent <IRO-123> --title … --plan -`.
- **`replan`:** the owner replied to a plan with changes. Revise it with `ask --task <id> "<revised plan>"`.
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
   `--verify "what is left"`: the issue stays In Review with that note.

`status` flags issues whose branch is merged into main but aren't Done (`merged_not_done`), and the watcher raises
a `merged` event once for each.

## Events (design 011)
Everything that needs you is also an event in the hub queue. Each `needs_orchestrator` item carries its `event` id,
and messages from the mstack hub list events as `event N [kind] ISSUE: …` (same kinds as above, plus `verdict`,
for your information). After acting on one, resolve it: `/home/developer/workspace/mstack/mstack events resolve
--id N`. An unresolved event is resent every few minutes, and a duplicate of one you've handled is just resolved.

When a worker's turn ends you are woken: run `poll`. A finished worker has already posted its
result with `done`; the owner's 👍 makes it Done, and a reply sends the notes back to the same worker.

## Board tools added from sparks (2026-10-29)
- **Verdicts:**
  - "Approve", "go" or "do it", optionally followed by instructions, approve the plan, and the instructions travel
    to the worker as notes.
  - 👍 followed by more text also approves, unless the text hedges ("but", "actually", "instead", "wait", a
    question). Then it's feedback.
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
3. Stop your watcher (`watch …` process). Only one watcher can run per scope.
4. Move workers *you* started out to top level (`detach_session`). Adopted chats are already top level.
5. With the owner's OK, start the new session: title `<scope>` (or `<scope> 2`), `cwd` = repo, `use_worktree: false`,
   prompt = `prompt`. The owner files it in the scope's sidebar group.
6. The new session registers itself (`orchestrators register`, same project and scope), which replaces your route.
   Tell the owner the new session has taken over. Archive yourself only when they agree, and never while you still
   have nested workers.

Design and sync table: docs/design/010-LINEAR-SESSIONS.md.
