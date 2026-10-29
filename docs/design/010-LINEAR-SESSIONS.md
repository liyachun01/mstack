# 010 — Linear issues ↔ Claude sessions (built, 2026-10-29)

Linear is the source of truth for tasks: your own issues, assigned to or created by you.
Claude Desktop sessions do the work. Anytype is no longer a task board; its tables stay
only as an archive. There are no webhooks (they need a public endpoint): the watcher polls.

## Who's who

| Thing | Lives in | Holds |
|---|---|---|
| Issue (status, plan, discussion, verdicts) | Linear | the truth |
| Orchestrator session (one per repo, e.g. {{mstack:CLIENT_REPO}}) | Claude Desktop, top level | coordination; you talk to it |
| Worker session (one per issue it works on) | Claude Desktop, started by the orchestrator | the conversation doing the work |
| Worktree + branch (Linear's `branchName`) | the repo, `.mstack/worktrees/<id>` | the code |
| Runs (issue → session id, worktree, host) | mstack state | the links between them |

## Session layout: flat under one orchestrator, detach any time

What Claude Desktop does today (checked against its session tools):
- **Nesting:** a session the orchestrator starts is a **side session**, nested under it. The orchestrator is woken whenever that session's turn ends.
- **Detaching:** **Detach to top level** moves a side session out, either from the sidebar (by you) or by its parent. The conversation, folder and settings are unchanged, but it's one-way, and the orchestrator stops getting its turn notifications.
- **Archiving cascades:** archiving the orchestrator also archives its finished side sessions. This happened today with IRO-104 and IRO-128; both were restored and lost nothing.

The design:
1. **Flat, one level.** The orchestrator starts every worker, including sub-issues. Workers never start workers, so every wake-up and verdict goes through one coordinator.
2. **Linear holds the hierarchy.** It's expressed by:
   - titles: `IRO-123 Payments` and `IRO-123 ↳ IRO-130 Refund webhook`;
   - optional sidebar groups per parent issue;
   - Blocked By ordering: dependants start with their blockers' branches merged in.
   - Deep nesting (sub-chats of sub-chats) is avoided, because notifications only reach the direct parent and archiving cascades.
3. **Detach whenever you want to own a worker yourself.** A long conversation, or one that should outlive the orchestrator, can be detached. It keeps its binding (worktree marker), so it still updates its Linear issue. The orchestrator keeps track through Linear polling instead of turn notifications.
4. **Never archive an orchestrator with live workers.** Detach them first, or archive only after their issues are Done.

## Linear → sessions (polling, about every 30 s per link)

The rate budget is roughly 120 queries per hour per key, against Linear's limit of 1,500.

| You do in Linear | Orchestrator does |
|---|---|
| Comment `/plan [notes]` (or `@agent plan`) on one of your issues | Reads the issue and code, posts the plan as a 🤖❓ comment. The issue becomes managed. Your description is never overwritten. |
| 👍 / `lgtm` on a 🤖❓ plan | Moves it to Todo and starts a worker (if `auto`), or queues it |
| A reply on a 🤖❓ plan | Revises the plan and asks again |
| 👎 | Drops it (Canceled) |
| Any comment on an **In Progress** issue | Forwards it to that issue's worker session, so you can talk to the worker from Linear |
| 👍 / reply on a 🤖❓ result | Done / sends the worker your notes in the **same** session |
| You close or cancel the issue | Tells the worker to stop; the run ends |
| Nothing (old issues) | Nothing. Unmanaged history is never polled or dispatched. |

## Sessions → Linear

- **Worker:** posts `note` for decisions or scope changes and `done` with a summary. These are comments starting with 🤖. Status follows Linear's standard states.
- **Turn-by-turn capture is off in Linear mode,** because it would flood the issue. The worker's own notes, plus your direct chat in the session, are enough.
- **Branches use Linear's branch name,** so Linear links commits and PRs to the issue by itself.
- **Nothing is created in your workspaces:** no labels, states or teams. Phases live in the orchestrator's comments; kind comes from labels that already exist.

## Sub-issues

- `plan --parent IRO-123` creates a Linear sub-issue.
- Each sub-issue gets its own worker (still flat under the orchestrator).
- The parent is an epic: the orchestrator posts a roll-up and asks to close it when all its children are Done.

## Repos and links

| Board | Linear | Key |
|---|---|---|
| mstack (private) | yyyymmdd / MST | entry 1 |
| {{mstack:CLIENT_REPO}} `[API]` (clientapp-api) | {{mstack:CLIENT_ORG_A}} / {{mstack:CLIENT_ORG_B_UPPER}} (IRO) | entry 2 |
| {{mstack:CLIENT_REPO}} other apps | {{mstack:CLIENT_ORG_B}} / {{mstack:CLIENT_BRAND}} | entry 3 (not verifiable yet: TLS errors) |

## Built vs to do

- **Built and tested (fake Linear):**
  - the Linear board adapter (plan → approve → dispatch → done → accept, all by comment);
  - Linear branch names;
  - a guarantee that untouched history is never dispatched.
- **Built afterwards (same day):** all of the following, tested against the fake Linear (46 orchestrator tests). The original to-do list:
  1. the `🤖 plan` trigger;
  2. forwarding your comments to the worker session;
  3. stopping the worker when you close the issue;
  4. `--parent` sub-issues;
  5. a 30 s poll interval for Linear boards;
  6. switching {{mstack:CLIENT_REPO}} and mstack to `backend: linear` (moving mstack's Anytype tasks into MST);
  7. starting the new {{mstack:CLIENT_REPO}} orchestrator;
  8. writing the four skills (`mstack-setup`, `mstack-orchestrator`, `mstack-worker`, `mstack-ops`), which the new orchestrator then uses.

## Packaging as agent skills (added 2026-10-29)

The `mstack` CLI stays the single engine. The procedures around it become skills,
which any agent host can load, so a new session doesn't depend on this conversation:

| Skill | For | Covers |
|---|---|---|
| `mstack-setup` | bringing a repo in | `init --local` (`--allow-protected` when owner-authorised), app codes, `source: project` team tools vs mstack tenants, `board link --entry N --team T [--app CODE]`, `doctor` |
| `mstack-orchestrator` | one session per repo | Linear board loop: `🤖 plan` trigger, verdicts, flat workers, Blocked By, detach and archive rules, roll-ups, the watcher |
| `mstack-worker` | every dispatched session | worktree and branch, the brief, `note`/`done`, no merge or push, comment etiquette |
| `mstack-ops` | maintenance | services, tenants, gateway routes, plugins; always under the setup guard |

Skills live in `.agents/skills/` (Codex) and are mirrored for Claude Code. Each is short, links
to `docs/design/*` for the why, and is checked by a dry run on a fresh session. They can be bundled
as a Claude Code plugin when the workflow is promoted to the team. The existing
`.agents/skills/orchestrator` is rewritten as `mstack-orchestrator` for the Linear design.

## Live state (2026-10-29)

| Board | Linear | Key | Notes |
|---|---|---|---|
| mstack | yyyymmdd / MST | entry 1 | its 15 Anytype tasks moved in (MST-1…15), with their history as a transcript; `auto: false` |
| {{mstack:CLIENT_REPO}} `[API]` | {{mstack:CLIENT_ORG_A_SHORT}} / IRO | entry 2 | `auto: true`; nothing starts without `/plan` and approval |
| {{mstack:CLIENT_REPO}} other apps | {{mstack:CLIENT_ORG_B}} / CAN | entry 3 | table-wide link |

- **Trigger:** `/plan`, not `🤖 plan`. 🤖 marks the orchestrator's own comments, so yours would be mistaken for its.
- **Linear query limits:** Linear rejects queries above complexity 10,000. The team query is narrowed (`first: 1`, `labels(first: 100)`).
- **Proxy:** every call goes through the Clash proxy. TLS handshakes take 2–7 s and connections sometimes drop, so Linear calls retry 5× with backoff.
- **Watchers:** one per orchestrator (`watch --project P`, lock per project). The all-tables watcher in the mstack setup session was stopped.
- **{{mstack:CLIENT_REPO}} orchestrator:** a new session, "{{mstack:CLIENT_REPO}} orchestrator (Linear)", runs the board using the `mstack-orchestrator` skill. The skills are linked into {{mstack:CLIENT_REPO}} locally and kept out of git.
- **Anytype tables** (mstack, test-market, {{mstack:CLIENT_REPO}}) are left untouched as an archive.

## Orchestrator scopes and the local issue table (2026-10-29)

- **Scopes:** `taskboard.orchestrators.<name> = {apps: [CODE|"*"], focus: [ROOT-ISSUES]}`. One orchestrator
  session per scope (sub-project, feature or repo-level), with `--scope <name>` on board commands and
  one watcher lock per scope. Scopes must be disjoint (same app only with disjoint focus roots);
  `mstack doctor` blocks overlaps.
- **{{mstack:CLIENT_REPO}} today:** three top-level sessions.
  - "{{mstack:CLIENT_REPO}} orchestrator": the original session, kept as the repo-level coordinator (status, mirror,
    setting up new scopes, doctor). It runs no watcher and owns no issues.
  - `customer-api`: apps API → {{mstack:CLIENT_ORG_A_SHORT}}/IRO; its own watcher.
  - `staff-web`: apps * → {{mstack:CLIENT_ORG_B}}/CAN; its own watcher. CAN-187 "staff-web: Sync feature performance polish" waits for `/plan`.
- **Local table:** Postgres `mstack_orchestrator.orchestrator.issues` mirrors every issue assigned to or
  created by the owner, per board, with focus and scope flags (111 rows at creation). The watcher refreshes
  it every 5 minutes; `mstack board mirror --project P` refreshes it on demand. Viewable read-only in WhoDB
  (`mstack_viewer`). It is never a source of truth and never starts sessions.
- **Adopted sessions:** IRO-104 (Done), IRO-126 (In Review) and IRO-128 are adopted into `customer-api` with
  `mstack board adopt --scope customer-api`. Adopting never moves an issue to Todo and never dispatches a second worker;
  Linear's own status is left as it is. IRO-127 is Canceled and has no session.
- **Query complexity:** Linear's limit (10,000) is a per-query cost score computed from the requested page
  sizes, not an issue count. Queries are sized to stay under it.

## Private mode (2026-10-29)

Before the workflow is shown to the team, {{mstack:CLIENT_REPO}} runs with `taskboard.private: true`. IRO and CAN are team
workspaces, so anything the board writes there is visible to everyone.
- **Linear is read-only for the board:** no comments, no status changes, no issue creation.
- **Local journal:** the orchestrator's messages and phase changes, plus the owner's words, go to the project's
  `.mstack/journal.json` (0600, gitignored with the rest of `.mstack/`). Phases are read from the journal
  alongside the orchestrator's earlier Linear comments.
- **Owner ↔ orchestrator in chat:** the owner tells the orchestrator session "plan IRO-130", "👍" or feedback,
  and the orchestrator records it with `mstack board owner --task … "<words>"`. Teammates' Linear comments are
  ignored, so nobody else can trigger or approve work.
- **Still read from Linear:** titles, descriptions, hierarchy, Blocked By, branch names, and the owner closing
  an issue, which still stops its worker.
- **`mstack board thread --task …`** prints an issue's whole conversation.
- **Comments posted before private mode** (the three "Tracked by" notes on IRO-104, IRO-126 and IRO-128) are
  kept, as the owner decided.
- **Private files:** in {{mstack:CLIENT_REPO}} every mstack file (`.mstack/`, the `mstack-*` skill links, `CLAUDE.local.md`,
  `.claude/settings.local.json`) is excluded through `.git/info/exclude`, which is never committed. The mstack
  repo itself has no remote.

## Related sessions (2026-10-29)

`mstack board adopt … --related NOTE` lists an older chat with its issue without making it the worker:
nothing is posted, and `status` shows it under `related`. Claude Desktop can't move an existing chat under
another session, so this link and the chat's title prefix are what tie it to its orchestrator.
- **IRO-104 (customer-api):** two related chats, both marked obsolete: "[OBSOLETE] Client App progressive prod
  merge plan" and "[OBSOLETE] Portal Web Client App Auth 接入 (fork)".
- **CAN-187 (staff-web):** worker is the owner's existing chat, renamed "CAN-187: {{mstack:CLIENT_BRAND}} staff-web Sync 维护开发".
- **Linear:** the duplicate "Tracked by" comments on IRO-104, IRO-126 and IRO-128 were deleted; one remains on each.

## Rotating an orchestrator (2026-10-29)

`mstack board handover --project P --scope S` prints a brief for a fresh orchestrator session. It covers:
- open and tracked issues, and what waits on the owner;
- workers and related chats, plus the latest messages on each open issue;
- whether the old watcher still holds the scope's lock;
- a ready-made `prompt` for the new session.

The skill's "Rotating to a fresh session" section has the steps. Tests stub `psql`, so `tick` never writes to the real
issue table, and psql calls now time out after 60 s. This was the cause of an intermittent test hang.

## Projects follow mstack updates (2026-10-29)

`mstack sync --project P | --all [--check]` (`integrations/stack/sync.py`) updates what mstack owns inside each
project. It's idempotent and never touches team files or commits. It handles:
- versioned config migrations;
- `.mstack/.gitignore` rules;
- the mstack skill-group links: new skills linked, dropped ones removed;
- the generated project skill, while unedited;
- the local `.git/info/exclude` block.

Each project records `runtime.mstack_sync` (version, mstack commit, skill digest) in `.mstack/state.json`.
Projects are found through mstack's `.mstack/projects.json` (written by `init`, `skills` and `sync`) plus board
tables. `doctor` reports pending updates as `mstack_updates`.

A running watcher checks mstack's code fingerprint before each tick. When it changes, the watcher syncs its
project and re-executes itself in place: same PID and command line, with the lock released and taken again.
`sync --hook` would install post-commit/post-merge hooks in mstack that run `sync --all`. It isn't installed yet.

## Multi-repo workspaces (2026-10-29)

A project can be a folder of git repos with `.mstack/` at its root, outside every repo, so it stays private.
`taskboard.repos` maps each repo name to its path and base branch.
- The root needs no git: dispatch creates `.mstack/worktrees/<issue>/` and, inside it, one worktree per repo the
  task touches, all on the issue's Linear branch.
- Repos are named at `propose --repos`; workers add more with `board worktree`.
- `done` reports commits per repo.

First user: {{mstack:CLIENT_C_SITE}}, a folder on the Mac that the dev VM sees at the same path. Its single orchestrator scope is
`{{mstack:CLIENT_C_SITE}}`, linked to {{mstack:CLIENT_ORG_A_SHORT}}/YEL in private mode. Sessions run on the VM; Xcode runs on the Mac through `macctl`.
