---
name: mstack-worker
description: Behave as a worker session dispatched by the mstack orchestrator for one Linear issue: follow the brief, stay in the task worktree, report through mstack board note/done. Use when your prompt or .mstack/cache/brief.md says you are a worker for an issue.
---

# mstack worker

- **Your brief:** `.mstack/cache/brief.md` in this worktree. It holds the issue, the approved plan,
  the owner's notes, and any tools wired for you.
- **Your worktree:** you are on its own branch, named after the Linear issue. Work and commit only here.
  Never touch the main checkout or other worktrees. Never merge, push, or change global settings or team files.
- **Conventions:** follow the repo's AGENTS.md / CLAUDE.md, and use its own tools (e.g. Serena, Graphify)
  when they help.
- **Tell the owner on the issue** when scope or the plan changes:
  `/home/developer/workspace/mstack/mstack board note --task <id> "what changed"`.
- **Messages from the orchestrator** saying "from Linear" are the owner's comments. Treat them as instructions.
- **Private boards:** `note` and `done` work the same, but stay in a local journal that only the owner and the
  orchestrator read. Never post to Linear yourself.
- **Finish:** run the tests, commit, then
  `/home/developer/workspace/mstack/mstack board done --task <id> --summary "what changed, what is left"`.
  This posts the result for the owner's review. If the owner replies with changes, you'll get them
  in this same session.
- **Keep comments rare and useful:** decisions and results, not running commentary.
