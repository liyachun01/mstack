# 014 — "My tasks": the owner's table of sessions and issues in Anytype, fed from the hub (MST-40, 2026-10-30)

Status: built and live (MST-40). Code `integrations/orchestrator/status_table.py`, wired in
`integrations/orchestrator/cli.py` (`status-table`, `sessions`), tests `integrations/orchestrator/tests/test_status_table.py`,
hub playbook `.agents/skills/mstack-hub`.

## Why

Following Linear across three projects (mstack, {{mstack:CLIENT_REPO}}, {{mstack:CLIENT_C_SITE}}), several teams and private boards is awkward.
The owner wants one table to glance at, and to tidy up sessions from it: every orchestrator and worker chat,
what it last reported, whether it is still open, and a CTA to continue, archive or delete it. It isn't a second
board: the earlier Linear-synced Anytype tables (design 005/006) were dropped, and nothing flows back to Linear.

## Shape

```
Linear ──(mirror, every 5 min per board)──▶ Postgres mstack_orchestrator
                                            orchestrator.issues  +  board_state runs / task_tables / tables
                                                        │
   + runs / related / orchestrators / roles     hub watcher step (every minute, automatic)
   + sessions_seen (from the hub chat)                  │ upsert by session/<id> or <board>/<issue>
                                                        ▼        ▲ CTA (owner-set), one search per pass
                 Anytype channel "mstack" (was mstack-taskboard-test) ▸ "My tasks" (type Agent Task)
                                                        │ CTAs and "observe sessions" wake the hub chat
                                                        ▼
                     hub chat: list_sessions → `sessions observe`; archive / delete / continue → `sessions done`
```

- **Source:** the hub's Postgres. `orchestrator.issues` (the local Linear issue table that `mstack board mirror`
  keeps: every issue assigned to or created by the owner, private boards included) gives title, state, URL and
  last update. Board state adds the sessions: workers (`runs`), earlier chats on an issue (`related`), orchestrators
  (`orchestrators` and each project's role registry, which also lists helpers), their reports (`runs[…].report`,
  written by `board done`/`note`) and their app state (`sessions_seen`, from the hub chat). `tables` says which boards
  are private (each project's `taskboard.private`). Before each pass, any Linear board whose
  issue table is older than 5 minutes is mirrored first, so boards without a registered orchestrator (mstack itself)
  stay current too.
- **Sink:** a new collection "My tasks" in the board's existing channel, whose rows are objects of the existing
  "Agent Task" type (`agent_task`, `infra/taskboard/schema.json`). The type is brought up to date on the first
  pass: schema properties the channel lacks are created (new: `task_scope` and the `session_*` properties), and the
  table's columns the type doesn't carry yet are added to it. No second type. A layout version (`LAYOUT`) upgrades
  an existing table in place when columns change. Everything goes through the same macOS bridge
  (`anytype_taskboard.py api`) and key (`.mstack/secrets/anytype-taskboard-test.key`) as the old board: no new
  grant, space or service. The old per-project collections and their objects are never read or written.
  The collection gets a Table view (first), a Board view grouped by status, and a sidebar widget.
- **Channel name:** the owner runs mstack as a one-person team that pushes changes directly, so the channel drops
  its "-test" name. `mstack status-table rename --to NAME` renames the granted space (the bridge's `api` now takes
  `.` as "the channel itself"); then `channel` in `infra/taskboard/schema.json` is set to match. The key is bound to
  the space, not its name, so it keeps working.
- **What the table remembers:** board_state key `status_table` holds the collection and widget ids, the object id
  and a fingerprint per row, and the pass times. With `hub.store: postgres` it lives in Postgres like the rest.

## Rows

One row per session, keyed `session/<id>`:
- **worker**: every session in `runs` (the newest run when a session was adopted for several issues), with its
  issue's columns; earlier chats on an issue (`adopt --related`) too, reported as such — usually ones to archive;
- **orchestrator**: every session in the hub registry or a project's role registry (orchestrator, sub-orchestrator);
- **helper**: from the role registries, with its worker's issue.

An issue nobody works on keeps an issue row (`<board>/<issue>`): every open issue, plus closed ones the board handled,
that changed in the last 30 days, or that are already in the table. When an issue gets its first session, its issue
row becomes that session's row (same object, no orphan); an issue row its sessions make redundant is removed. Other
rows are never deleted: closed issues stay as Done/Canceled. On 2026-10-30: 165 rows, 22 of them sessions.

## Columns

| Column (Agent Task property) | From |
|---|---|
| Name | `<issue> <title>`; `Orchestrator <project>/<scope>`; `Helper: …` |
| Issue (`linear_identifier`) | Linear identifier (MST-40, IRO-104, YEL-407 …) |
| Project (`task_project`) | board name (`mstack`, `{{mstack:CLIENT_REPO}}`, `{{mstack:CLIENT_C_FOLDER}}`) |
| Scope (`task_scope`) | the session's orchestrator scope, else the scope that planned the issue, else the mirror's focus scopes |
| Status (`task_status`) | closed in Linear → Done / Canceled; else the board's phase for managed issues (Awaiting Approval, In Review …); else the Linear state if it is one of ours; else its state type |
| Link (`linear_url`) | the Linear URL, only for public boards. Private boards ({{mstack:CLIENT_REPO}}, {{mstack:CLIENT_C_SITE}}) and unreadable configs get none |
| Last update (`linear_updated_at`) | Linear `updatedAt` |
| Session (`agent_session`) | the `local_…` id |
| Session Type (`session_type`) | orchestrator, worker, helper |
| Agent (`session_agent`) | claude, codex, deepseek, other (from the run's runner; orchestrators and helpers are Claude sessions) |
| Parent Session (`session_parent`) | the orchestrator a worker or helper reports to: its scope's, else the project's; blank for orchestrators |
| Session State (`session_state`) | archived or deleted only when the hub chat saw it so; every other session is active (owner rule, 2026-10-30; `board ack`/`adopt` also record active) |
| Session Report (`session_report`) | the latest `board done` summary or `board note` (600 characters); free text |
| CTA (`session_cta`) | set by the owner: noop (default), continue, archive, delete, forbidden |
| Last Action (`session_action`) | what the last CTA did, with its time |

## Written by the hub, except CTA

Each pass skips rows whose fingerprint hasn't changed. Once an hour, and on `mstack status-table sync --full`, every
row is written again, so a hand edit in any other column lasts at most an hour. CTA is never written by a pass:
it's the owner's column, and only the hub resets it (to noop, after acting).

## CTAs

- **Read:** after each pass, one search over the Agent Task type with `fields: [session_cta]` (paged, ~2 calls)
  returns every row's CTA. A CTA on an issue row (no session) is reset to noop.
- **forbidden:** the session is protected (`status_table.protected`): never archived, deleted or messaged through
  the table, and it never shows up in `sessions todo`. Setting the CTA back to noop lifts it.
- **continue, archive, delete:** wait in `status_table.ctas`. The hub watcher exits with `hub_work` when one waits
  (or when session states are older than 15 minutes), which wakes the hub chat. `mstack sessions todo` hands them
  out (again after `hub.resend_minutes` if not done) and refuses archive/delete of an orchestrator that still has
  active workers (recorded as the Last Action, CTA reset). The hub chat carries them out with its session tools —
  continue: SendMessage "Continue: the owner asked from My tasks."; archive: archive_session; delete:
  delete_session, which the app always confirms with the owner — then reports with
  `mstack sessions done --session <id> --result "…" [--state archived|deleted]`. That resets the CTA to noop at once
  and the next pass shows the Last Action and the new state. Setting a waiting CTA back to noop cancels it.
- **Session states:** the hub chat runs list_sessions (`include_archived`, `limit: 200`) and pipes it to
  `mstack sessions observe --complete --self <hub id>`. Listed → active or archived; with `--complete`, a row's
  session missing from the list → deleted. list_sessions only shows sessions on the hub's own connection, which is
  where mstack's sessions run.
- `mstack sessions list` shows waiting CTAs, protected sessions and the last states.

## Running it

Nobody runs it by hand: the table follows the work by itself.

- **Hub watcher:** the always-running `mstack board watch --hub` (and `tick --hub`) runs a pass every minute after
  ticking the boards. A pass with nothing changed costs one Postgres read and no Anytype calls. A pass writes at
  most 40 rows; while rows are still waiting (the first build of ~131 rows, the hourly rewrite) the next pass comes
  15 seconds later, so neither stalls event delivery. The watcher reloads itself when mstack's code changes, so the
  step starts on its own after merge.
- **One writer:** only the hub watcher runs the step (`tick --hub`; the per-scope watchers return before it), and
  every pass holds `.mstack/evidence/status-table.lock`. A pass that finds it taken (a manual `sync` during the
  hub's pass) is skipped, not run in parallel, so a row is never created twice.
- **Failures** (Anytype closed, Postgres down) show as `status_table_error` in the tick output and on the watcher's
  tick line and never stop the watcher; the next try is a minute later. Rows written before a failure are
  remembered, so a retry never builds a second "My tasks".
- **Off switch:** `"hub": {"status_table": false}` in mstack's `.mstack/stack.json` (schema
  `project.schema.json` → `hub.status_table`, default on). Off stops the watcher step and makes `sync` refuse.
- **For diagnosis only:** `mstack status-table show` (switch, rows, rows waiting, last pass), `sync [--full]` (one
  unbatched pass now) and `rename --to NAME` (the channel).
- Tests never reach Anytype or Postgres: only the real state file feeds the table from the watcher, and the tests
  drive it with a fake Anytype client and a fake `psql`.

## Not in scope

Writing back to Linear, per-project tables, new Anytype spaces or grants; CTAs carried out without the hub chat
(Windmill can't reach Claude Desktop sessions).

## Live setup (2026-10-30)

With the owner's OK the worker started the Anytype app in the background and, through the API with the existing key:
- renamed the channel `mstack-taskboard-test` → `mstack` (`infra/taskboard/schema.json` `channel` updated);
- added the new `task_scope` property to the Agent Task type (every other column was already on it);
- created "My tasks" (Table and Board views, sidebar widget) and wrote 156 rows: mstack 40 issues after a fresh
  mirror, plus {{mstack:CLIENT_REPO}} and {{mstack:CLIENT_C_SITE}}. Every row was read back from the collection. Public rows carry their Linear
  link and private ones don't.
- A second pass with nothing changed made no Anytype calls (0.4 s).

The table's state (`status_table` in board_state) is in Postgres. Until this branch is merged, the running hub
watcher has older code and doesn't update the table; after merge it reloads itself and takes over.
The live API returns a type's properties under `type_settings.property_definitions`; the fake in the tests now
returns that shape.

Sessions and CTAs (same day): the 7 `session_*` properties were created and added to the type and the views; 13
issue rows became their worker's session rows and 9 session rows were added (165 rows, 22 sessions, nothing removed);
every row's CTA set to noop. A first look at the sessions (52 listed) gave every session row a state except two old
"obsolete" chats, left blank until the hub's first `--complete` look. Reports fill in from each worker's next
`board done`/`note`; earlier reports live only on the issues.

## Questions resolved

- **Source of titles and states:** the plan named board_state `tasks`; that key only holds the 2026-10-28 seed demo
  tasks. The real per-issue data is `orchestrator.issues` (mirror), which the hub already keeps, so the table reads
  that plus `runs`/`task_tables`/`tables`.
- **Type:** first built with a separate "My Task" type; the owner then asked to reuse the existing Agent Task type
  with the necessary updates (2026-10-30), so the rows are Agent Tasks and only Scope is new.
- **Channel:** keep the existing one and rename it, since mstack is a one-person team pushing directly (owner,
  2026-10-30). Renamed to `mstack` on 2026-10-30 (the owner confirmed `mstack`, not `mastack`).
- **Who changes Anytype:** the worker, through the API with the existing key, not the owner in the UI.
- **Where it runs (owner, 2026-10-30: "we don't run sync by ourselves"):** in the hub watcher, which is always
  running and already reads the same Postgres, with batched passes so no manual first run is needed. Postgres
  alone can't do it: it has no way to call Anytype's API. Windmill (design 011 phase 2) would keep running when
  the hub chat is closed, but its worker is a container that can't reach the Anytype API (Mac loopback only) or the
  key without a new route and a copy of the key into Windmill. That counts as a grant change under the setup guard,
  so it's a later option for the owner, not part of MST-40. The step is a plain function
  (`status_table_pass`), so a Windmill job could call the same code if that is approved.
- **Sessions and actions (owner, 2026-10-30):** one row per session (orchestrators, workers, helpers), issue rows
  only for issues without one; the hub chat carries out CTAs, since only a Claude chat can archive, delete or message
  sessions; forbidden = protected; the report column is the latest `board done`/`note` text.
- **"Overwritten on the next pass"** became "within the hour": rewriting all ~130 rows every minute through the
  rate-limited bridge is too heavy, so changed rows go at once and everything is rewritten hourly.
