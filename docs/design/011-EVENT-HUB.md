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
  the item (`event`). Kinds: `plan`, `replan`, `forward`, `stop`, `handoff`, `verdict`. Items were already raised
  once by the watcher's seen-keys; handoffs repeat until acked, so each carries a dedupe key per dispatch.
  An event's scope is the tick's `--scope`, else the scope that planned, adopted or dispatched the task.
- `mstack events next`: hands out `new` events and `sent` ones older than `hub.resend_minutes` (5), marks them
  `sent`, and groups them by recipient session, each group with a ready-to-send `message`. Events with no route
  stay `new` and are listed under `unrouted`. `--peek` shows without marking.
- `mstack events resolve --id N [--note]`, run by the receiving orchestrator. `events list [--status]` for a look;
  `events schema [--apply]` prints or applies the schema.
- Two scopes of one board now keep separate Linear poll timers (`last_linear_poll["board/scope"]`).

### Hub watcher and chat
- `mstack board watch --hub` (lock `watch.hub.lock`) ticks every registered (project, scope) and exits when routable
  events wait (`events_waiting`). If the queue is unavailable it exits on the raw items, as the per-scope watchers do.
- The hub chat's playbook is `.agents/skills/mstack-hub`. The orchestrator skill now registers at start and on
  handover and resolves events; per-scope watchers keep working unchanged meanwhile, and since their items carry
  event ids, resolving them keeps the queue clean for when the hub starts.

### Not done in phase 1
- The schema is not applied to the live database, and `hub.store` stays `file`, until the owner approves.
- The hub session isn't started; the owner decides after review.
- Concurrent writers outside this machine (Windmill, phase 2) need row-level updates instead of the local lock.
