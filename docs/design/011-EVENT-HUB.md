# 011 — Event hub: Windmill polling, a Postgres queue, one mstack hub chat (planned, 2026-10-29)

Status: agreed design, not built. Claude Desktop workflow only.

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
