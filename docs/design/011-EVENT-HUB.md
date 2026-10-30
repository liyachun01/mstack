# 011 — Event hub: Windmill polling, a Postgres queue, one mstack hub chat (phase 1 built, 2026-10-29)

Status: phase 1 built (MST-21), off until the owner applies the schema and switches `hub.store`; phases 2–3
planned. Claude Desktop workflow only.

## Why

Today each orchestrator chat runs its own watcher as a background task. Polling stops when the chat or app closes,
or the Mac sleeps. It gives up after 5 failures in a row, which the flaky proxy causes, and its only log is inside
the chat. Windmill can poll reliably, but it can't wake a Claude Desktop chat: a chat only wakes when its own
background command finishes. Chats can wake each other with messages, so a single hub chat can carry events to the
others.

## Shape

```
Linear ──poll──▶ Windmill (every 30–60 s) ──▶ Postgres event queue (each event waits until resolved)
                                                   │
                                     mstack hub chat (the only one waiting on the queue)
                                                   │ message to the right chat
                        ┌──────────────────────────┼──────────────────────────┐
                 customer-api orch.          staff-web orch.          (any later project)
```

- **Events:** a /plan request, a verdict, feedback, a closed issue, or an approved issue that's ready for a worker.
  Each moves through `new → sent → resolved`. It's resolved only when the receiving orchestrator runs
  `mstack events resolve`. Delivery alone doesn't count, because a message between chats can be held back. The hub
  resends events left in `sent` for a few minutes. If the hub is closed, events wait.
- **Hub chat:** a fresh, small, cheap session. Code does the routing (`mstack events next` returns events grouped by
  recipient chat); the hub only delivers them with SendMessage. Planning stays with the project orchestrators.
- **Registry:** `mstack orchestrators register --project P --scope S --session ID`. The hub routes by it, and a
  handover updates it.
- **Workers:** "approved, ready for a worker" is an event; the project orchestrator runs `dispatch` itself.
  Windmill never creates worktrees in a repo.
- **Backlog alert:** Windmill flags events older than 10 minutes that are still `new` or `sent`.

## Phases

1. **Postgres foundation:** board state, journal and the event queue table in Postgres; the orchestrator registry;
   `events next` and `resolve`; the hub chat. One watcher running in the hub produces the events for now.
2. **Windmill poller:** Windmill writes the same events, and the hub's watcher becomes a cheap wait on the queue.
   This needs the owner's OK to copy the Linear keys into Windmill and to mount the repo into its worker.
3. **Retire the per-scope watchers:** project orchestrators are woken by the hub; update the skills.

## Prerequisite found

Windmill's single worker runs in a container on the Mac with no access to the repo files that hold today's board
state (`.mstack/evidence/taskboard-test.json`) and private journals. That's why phase 1 moves them into Postgres.

## Phase 1 as built (MST-21)

### Store (`integrations/orchestrator/store.py`, schema `integrations/orchestrator/schema.sql`)
`hub.store` in mstack's `.mstack/stack.json` (schema: `project.schema.json` → `hub`) picks the backend:

| | `file` (default) | `postgres` |
|---|---|---|
| Board state (tables, runs, related, task_tables, task_repos, attention_seen, orchestrators, poll timers) | `.mstack/evidence/taskboard-test.json` | `orchestrator.board_state`: one jsonb row per top-level key |
| Private journals | each project's `.mstack/journal.json` | `orchestrator.journal` (project path, issue, body, created_at) |
| Event queue | `events` in the state file | `orchestrator.queue` |

- **Fallback:** with `postgres`, the JSON files are still written on every change. When Postgres doesn't
  answer, reads come from the file and a `.pg-dirty` marker is left beside it. The next command that reaches
  Postgres pushes the file back first (it's the newer copy). The first use after the switch does the same, so
  the existing state and journals are migrated by just switching. Events queued while Postgres is down are spooled
  in the state file (`events_spool`, ids `local-N`) and moved into the queue when it's back; `events next` and
  `resolve` refuse with a clear error meanwhile, and the watcher's own output still lists the items.
- **Writes** stay serialized by the local file lock (every writer is on this machine in phase 1). Only changed
  keys are written, in one transaction. Plain reads are cached for 2 s per process; locked read-modify-writes
  always read fresh.
- **Tests never reach Postgres:** only the real state file can use it; a test that points `STATE` elsewhere
  always gets the file backend. Postgres tests drive `Store` with a fake `psql` runner.
- No driver was installed: everything goes through the `psql` client, as `mirror` already did.

### Queue and registry
- `mstack orchestrators register --project P [--scope S] --session ID` (also `list`, `remove`). Routes are
  `project/scope`; an event for a scope with no route falls back to the board's unscoped route.
- `tick` turns every `needs_orchestrator` item, and every verdict it applied, into an event, and adds the event id to
  the item (`event`). Kinds: `plan`, `replan`, `forward`, `stop`, `handoff`, `resume`, `verdict`, and since MST-60
  `new_issue`, `mention`, `status_lag`, `review_reply` (design 010, "Linear triggers"), `catch_up` (below). Items were already
  raised once by the watcher's seen-keys; handoffs and resumes repeat until acked, so each carries a dedupe key per
  dispatch. Verdicts are information only: `events next` resolves them as it hands them out.
  An event's scope is the tick's `--scope`, else the scope that planned, adopted or dispatched the task.
- `mstack events next`: hands out `new` events and `sent` ones older than `hub.resend_minutes` (5), marks them
  `sent`, and groups them by recipient session, each group with a ready-to-send `message`. Events with no route
  stay `new` and are listed under `unrouted`. `--peek` shows without marking.
- `mstack events resolve --id N [--note]`, run by the receiving orchestrator. `events list [--status]` for a look;
  `events schema [--apply]` prints or applies the schema.
- Two scopes of one board now keep separate Linear poll timers (`last_linear_poll["board/scope"]`). The hub
  replaced this with one timer per board in MST-41 (below); per-scope watchers keep theirs as the fallback.

### Hub watcher and chat
- `mstack board watch --hub` (lock `watch.hub.lock`) ticks every registered (project, scope) and exits when routable
  events wait (`events_waiting`). If the queue is unavailable it exits on the raw items, as the per-scope watchers do.
- The hub chat's playbook is `.agents/skills/mstack-hub`. The orchestrator skill now registers at start and on
  handover and resolves events; per-scope watchers keep working unchanged meanwhile, and since their items carry
  event ids, resolving them keeps the queue clean for when the hub starts.

### Review fixes (2026-10-30)
- `events next` on Postgres returned sent events with no session (a statement's main query can't see its own CTE's
  UPDATE), so everything looked unrouted. Sent rows now come from `UPDATE … RETURNING`; checked on a temp table.
- Catching up a spool inside a write took the state lock a second time and hung; the lock is now re-entrant.
- A missing state file is restored from Postgres instead of being pushed over it (which deleted every key).

### Linear rate limits (MST-41, 2026-10-30)
{{mstack:CLIENT_REPO}}'s watchers hit `HTTP 429` on many ticks, and the customer-api watcher stopped after 5 failed ticks.
**Measured:** the watcher logs held 98 ({{mstack:CLIENT_C_FOLDER}}), 100 (hub) and 137 ({{mstack:CLIENT_REPO}}) 429s. Two causes:
- {{mstack:CLIENT_REPO}}'s `API` link ({{mstack:CLIENT_ORG_A_SHORT}}/IRO) and {{mstack:CLIENT_C_FOLDER}} ({{mstack:CLIENT_ORG_A_SHORT}}/YEL) use the **same Linear key** (entry 2), and Linear
  limits per key, so both projects share one budget.
- Each due tick of a scope read the whole board three times (signals, verdict poll, dispatch), with up to 50
  comments per issue. The hub's unscoped {{mstack:CLIENT_REPO}} route and portal-web read the same boards again, and per-scope
  watchers shared the hub's per-scope timers, so whichever ran first polled. A fake-Linear replay of the live
  setup (hub with 5 routes and 3 per-scope watchers, 10 s ticks) counted **2,904 requests/h, 2,292 of them on
  the shared key**. After the change: **828/h, 708 on the shared key**. Most of what is left is parent lookups
  that the fake data forces. On the real boards those parents are the owner's own issues, which are already loaded.

**Changes:**
- **One read per board per tick.** `tick` runs inside `linear_board.shared()`. Every LinearBoard made during it
  (signals, poll, dispatch, the mirror, the "My tasks" pass, every scope) reuses one issue list per (key, team),
  and parent lookups are shared too. Any write through a link (a mutation) drops that board's copy, so dispatch
  still sees an approval the poll just wrote. Private boards write to the journal, so their copy stays valid.
- **One poll timer per board in the hub.** The first route of a board decides whether it is due this tick
  (`last_linear_poll["board"]`), and its other routes follow, so all scopes of a board poll together from one read.
  `mirror` and `sync` timers were already per board.
- **The hub owns Linear I/O.** A per-scope or per-project `tick`/`watch` skips a Linear board (`left_to_hub`)
  while `watch.hub.lock` is held and the hub has that (board, scope) registered. It still lists handoffs and
  resumes from the state file. With no hub, or for a scope the hub doesn't tick, it polls as before: this is
  the fallback.
- **Shared backoff on rate limits** (`linear.py`). A 429, a `RATELIMITED` GraphQL error, or a good answer whose
  `X-RateLimit-Requests/Complexity-Remaining` is 0 puts the key in `.mstack/cache/linear-backoff.json`. The entry
  is keyed by a hash of the key, never the key itself. The wait comes from `Retry-After`, else the
  `X-RateLimit-*-Reset` time, else 60 s, doubling for each 429 in a row (at most 1 h). Until it ends, every
  process using the key raises `RateLimited` without calling Linear. The backoff is logged once when it starts,
  and the watcher line says `rate-limited until …` once per backoff. A rate-limited board is skipped for that
  tick (`rate_limited` in the tick output) and never counts as a failed tick.
- **Counter:** the tick output has `linear_calls` (requests by team), and the watcher line prints it, so an
  hour of logs shows who calls Linear.

**Follow-up after the merge: duplicate verdict events.** In the live queue, verdict ids 11 and 15 were the same
verdict (fddd7a66, In Review → Done), and id 9 repeated id 4 (d4fc71ca) 30 minutes later.
- *11/15:* two processes applied the verdict at the same moment. Their journal rows interleave within 30 ms
  (`Done`, `Done`, `Accepted`, `Accepted`), most likely the hub and a per-scope watcher that ran while the hub
  lock was briefly free between hub restarts. `poll` had no lock and no re-read before acting. Now `poll` holds
  `poll.<board>.lock`, and before it moves a task it reads the task again past every cache (`LinearBoard.fresh`:
  Linear and the journal). It skips the task when another process got there first.
- *4 → 9:* a real second application. `done` set In Review before posting its "finished" ask, and a poll in
  between found In Review under the plan's ask. That ask already had the owner's 👍 (09:29), so the poll accepted
  it straight away. The ask then put the issue back to In Review, and the owner's next 👍 accepted it again.
  `done` now posts the ask first.
- The hub polls each board's verdicts **once per tick, board-wide** (no scope). Before, it polled once per route.
  A board-wide poll never erases the scope that planned a task (`task_tables`), and its verdict and replan events
  are routed to the task's own scope, not to the route that ran the poll.
- Verdict events carry a dedupe key `verdict:<task>:<was>:<now>:<ask id>`, so a repeat returns the existing row.
  A verdict on a new ask is a new event.

**Questions resolved:**
- *Share the board read across processes through Postgres?* No. While the hub runs, only the hub reads Linear,
  so an in-process share per tick is enough. Two fallback watchers on scopes of one board (no hub) still read
  it twice. That's acceptable for a fallback.
- *Latency:* the hub still polls each board every `LINEAR_EVERY` (30 s), so verdicts and dispatch arrive as fast
  as before. Per-scope orchestrators are woken by the hub's events instead of their own watcher's exit.
- Not in scope: webhooks, moving {{mstack:CLIENT_C_FOLDER}} or {{mstack:CLIENT_REPO}} to another key.

### Catch-up after downtime (2026-10-30, MST-60)

Owner: "I may close the computer then the watcher is off line: when it's back online, I need it to be able to view
the stacked linear updates".
- **Durable cursor:** each board keeps `notify_cursor` (the latest owner notification already read) and
  `linear_states` (each issue's last seen Linear state) in the state, so in Postgres board_state with the Postgres
  store. The hub keeps one cursor per board; a per-scope watcher keeps its own per scope, so one scope moving on
  never hides another's updates. The first read only sets the cursor (old notifications start nothing).
- **After a gap** (no poll for `CATCH_UP_GAP`, 10 min: laptop closed, watcher stopped, a crash) the next tick
  reads everything since the cursor, paged and under the MST-41 rate limits. That means new or reassigned issues
  and mentions (notifications), owner comments (`plan`, `forward`, from each issue's thread), verdicts (the normal
  poll, deduped by its keys) and Linear status changes (against the snapshot).
- **In order, once each:** the items are raised as their normal events, sorted by when they happened. The
  seen-keys and event dedupe keys mean nothing is doubled; the cursor means nothing is missed.
- **Summary:** each route also gets one `catch_up` event: "while offline from A to B: 3 new issues, 5 comments,
  2 mentions, 4 status changes". It lists the status changes ("IRO-1 Todo → Done").
- **No acting on a backlog:** catch-up never writes to Linear. Status changes are reported, and lag flags stay
  suggestions. Old verdicts go through the normal verdict path.
- **Bounded:** a catch-up reads at most `CATCH_UP_MAX` (7 days) back and `CATCH_UP_LIMIT` (500) notifications;
  when it was cut, the summary says so.
- Comments are read from each issue's last 50, as before, so an issue with more than 50 new comments while offline
  shows only the latest 50.

### Not done in phase 1
- The schema is not applied to the live database, and `hub.store` stays `file`, until the owner approves.
- The hub session isn't started; the owner decides after review.
- Concurrent writers outside this machine (Windmill, phase 2) need row-level updates instead of the local lock.
