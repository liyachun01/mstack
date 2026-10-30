# 014 — "My tasks": a personal read-only status table in Anytype, fed from the hub (MST-40, 2026-10-30)

Status: built (MST-40). Code `integrations/orchestrator/status_table.py`, wired in `integrations/orchestrator/cli.py`,
tests `integrations/orchestrator/tests/test_status_table.py`. Not yet run against the live Anytype app (see
"Not done").

## Why

Following Linear across three projects (mstack, {{mstack:CLIENT_REPO}}, {{mstack:CLIENT_C_SITE}}), several teams and private boards is awkward.
The owner wants one table to glance at. It's a view, not a second board: the earlier Linear-synced Anytype tables
(design 005/006) were dropped, and nothing flows back.

## Shape

```
Linear ──(mirror, every 5 min per board)──▶ Postgres mstack_orchestrator
                                            orchestrator.issues  +  board_state runs / task_tables / tables
                                                        │
                                       hub watcher step (every minute, automatic)
                                                        │ one way, upsert by <board>/<issue>
                                                        ▼
                 Anytype channel "mstack" (was mstack-taskboard-test) ▸ "My tasks" (type Agent Task)
```

- **Source:** the hub's Postgres. `orchestrator.issues` (the local Linear issue table that `mstack board mirror`
  keeps: every issue assigned to or created by the owner, private boards included) gives title, state, URL and
  last update. Board state adds the worker session and scope (`runs`, latest dispatch per issue; `task_tables`) and
  which boards are private (`tables` → each project's `taskboard.private`). Before each pass, any Linear board whose
  issue table is older than 5 minutes is mirrored first, so boards without a registered orchestrator (mstack itself)
  stay current too.
- **Sink:** a new collection "My tasks" in the board's existing channel, whose rows are objects of the existing
  "Agent Task" type (`agent_task`, `infra/taskboard/schema.json`). The type is brought up to date on the first
  pass: schema properties the channel lacks are created (new: `task_scope`, "Scope"), and the table's columns the
  type doesn't carry yet are added to it. No second type. Everything goes through the same macOS bridge
  (`anytype_taskboard.py api`) and key (`.mstack/secrets/anytype-taskboard-test.key`) as the old board: no new
  grant, space or service. The old per-project collections and their objects are never read or written.
  The collection gets a Table view (first), a Board view grouped by status, and a sidebar widget.
- **Channel name:** the owner runs mstack as a one-person team that pushes changes directly, so the channel drops
  its "-test" name. `mstack status-table rename --to NAME` renames the granted space (the bridge's `api` now takes
  `.` as "the channel itself"); then `channel` in `infra/taskboard/schema.json` is set to match. The key is bound to
  the space, not its name, so it keeps working.
- **What the table remembers:** board_state key `status_table` holds the collection and widget ids, the object id
  and a fingerprint per row, and the pass times. With `hub.store: postgres` it lives in Postgres like the rest.

## Columns

| Column (Agent Task property) | From |
|---|---|
| Name | `<issue> <title>` |
| Issue (`linear_identifier`) | Linear identifier (MST-40, IRO-104, YEL-407 …) |
| Project (`task_project`) | board name (`mstack`, `{{mstack:CLIENT_REPO}}`, `{{mstack:CLIENT_C_FOLDER}}`) |
| Scope (`task_scope`, new) | the orchestrator scope that dispatched or adopted it, else the scope that planned it, else the mirror's focus scopes |
| Status (`task_status`) | closed in Linear → Done / Canceled; else the board's phase for managed issues (Awaiting Approval, In Review …); else the Linear state if it is one of Backlog, Todo, In Progress, In Review; else its state type |
| Worker session (`agent_session`) | the `local_…` id of the latest worker session on it |
| Last update (`linear_updated_at`) | Linear `updatedAt` |
| Link (`linear_url`) | the Linear URL, only for public boards. Private boards ({{mstack:CLIENT_REPO}}, {{mstack:CLIENT_C_SITE}}) and boards whose config can't be read get none |

## Which rows

Every open issue in the issue table. Closed issues are shown when the board handled them (managed or had a worker),
when they changed in the last 30 days, or when they are already in the table. Rows are never deleted: a closed issue
stays as Done/Canceled, and an issue that leaves the source keeps its last values. On the live data of 2026-10-30
that is 131 of 141 issues.

## Read-only

One way only. Each pass skips rows whose fingerprint hasn't changed (no Anytype calls at all when nothing changed).
Once an hour, and on `mstack status-table sync --full`, every row is written again, so a hand edit in Anytype lasts
at most an hour. Each row's body says it is written by the hub.

## Running it

Nobody runs it by hand: the table follows the work by itself.

- **Hub watcher:** the always-running `mstack board watch --hub` (and `tick --hub`) runs a pass every minute after
  ticking the boards. A pass with nothing changed costs one Postgres read and no Anytype calls. A pass writes at
  most 40 rows; while rows are still waiting (the first build of ~131 rows, the hourly rewrite) the next pass comes
  15 seconds later, so neither stalls event delivery. The watcher reloads itself when mstack's code changes, so the
  step starts on its own after merge.
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

Writing back to Postgres or Linear, per-project tables, new Anytype spaces or grants.

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
- **"Overwritten on the next pass"** became "within the hour": rewriting all ~130 rows every minute through the
  rate-limited bridge is too heavy, so changed rows go at once and everything is rewritten hourly.
