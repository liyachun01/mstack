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
                                       hub watcher step (every 3 min) or `mstack status-table sync`
                                                        │ one way, upsert by <board>/<issue>
                                                        ▼
                         Anytype channel mstack-taskboard-test ▸ collection "My tasks" (type "My Task")
```

- **Source:** the hub's Postgres. `orchestrator.issues` (the local Linear issue table that `mstack board mirror`
  keeps: every issue assigned to or created by the owner, private boards included) gives title, state, URL and
  last update. Board state adds the worker session and scope (`runs`, latest dispatch per issue; `task_tables`) and
  which boards are private (`tables` → each project's `taskboard.private`). Before each pass, any Linear board whose
  issue table is older than 5 minutes is mirrored first, so boards without a registered orchestrator (mstack itself)
  stay current too.
- **Sink:** a new collection "My tasks" of a dedicated type "My Task" (`mstack_my_task`) with its own properties
  (`my_task_*`), in the existing `mstack-taskboard-test` channel. It goes through the same macOS bridge
  (`anytype_taskboard.py api`) and key (`.mstack/secrets/anytype-taskboard-test.key`) as the old board: no new
  grant, space or service. The old per-project collections and the `agent_task` objects are never read or written.
  The collection gets a Table view (first), a Board view grouped by status, and a sidebar widget.
- **What the table remembers:** board_state key `status_table` holds the collection and widget ids, the object id
  and a fingerprint per row, and the pass times. With `hub.store: postgres` it lives in Postgres like the rest.

## Columns

| Column | From |
|---|---|
| Name | `<issue> <title>` |
| Issue | Linear identifier (MST-40, IRO-104, YEL-407 …) |
| Project | board name (`mstack`, `{{mstack:CLIENT_REPO}}`, `{{mstack:CLIENT_C_FOLDER}}`) |
| Scope | the orchestrator scope that dispatched or adopted it, else the scope that planned it, else the mirror's focus scopes |
| Status | closed in Linear → Done / Canceled; else the board's phase for managed issues (Awaiting Approval, In Review …); else the Linear state if it is one of Backlog, Todo, In Progress, In Review; else its state type |
| Worker session | the `local_…` id of the latest worker session on it |
| Last update | Linear `updatedAt` |
| Link | the Linear URL, only for public boards. Private boards ({{mstack:CLIENT_REPO}}, {{mstack:CLIENT_C_SITE}}) and boards whose config can't be read get none |

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

- **Hub watcher:** `mstack board watch --hub` (and `tick --hub`) runs a pass every 3 minutes after ticking the
  boards. A failure (Anytype closed, Postgres down) is reported as `status_table_error` in the tick output and on
  the watcher's tick line, and never stops the watcher; the next try waits the same 3 minutes. Rows written before
  a failure are remembered, so a retry never builds a second "My tasks".
- **By hand:** `mstack status-table sync [--full]` runs one pass; `mstack status-table show` gives the switch, the
  row count and the last pass.
- **Off switch:** `"hub": {"status_table": false}` in mstack's `.mstack/stack.json` (schema
  `project.schema.json` → `hub.status_table`, default on). Off stops the watcher step and makes `sync` refuse.
- The first pass creates every row (about 260 bridge calls for 131 rows). Run it once by hand so the hub's first
  tick isn't slowed down.
- Tests never reach Anytype or Postgres: only the real state file feeds the table from the watcher, and the tests
  drive it with a fake Anytype client and a fake `psql`.

## Not in scope

Writing back to Postgres or Linear, per-project tables, new Anytype spaces or grants.

## Not done

- No live pass yet: on 2026-10-30 the Anytype app on the Mac wasn't running (the local API at 127.0.0.1:31009
  refused the connection), and opening it is the owner's call. The first `mstack status-table sync` after it is
  open creates the collection; check the property and view requests then, since they were only run against the fake.

## Questions resolved

- **Source of titles and states:** the plan named board_state `tasks`; that key only holds the 2026-10-28 seed demo
  tasks. The real per-issue data is `orchestrator.issues` (mirror), which the hub already keeps, so the table reads
  that plus `runs`/`task_tables`/`tables`.
- **Own type instead of `agent_task`:** that shared type was retired on 2026-10-28; a separate "My Task" type keeps
  the view apart from the archive.
- **"Overwritten on the next pass"** became "within the hour": rewriting all ~130 rows every 3 minutes through the
  rate-limited bridge is too heavy, so changed rows go at once and everything is rewritten hourly.
