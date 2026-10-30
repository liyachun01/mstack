---
name: mstack-worker
description: Behave as a worker session dispatched by the mstack orchestrator for one Linear issue: follow the brief, stay in the task worktree, report through mstack board note/done. Use when your prompt or .mstack/cache/brief.md says you are a worker for an issue.
---

# mstack worker

- **Your brief:** `.mstack/cache/brief.md` in this worktree. It holds the issue, the approved plan,
  the owner's notes, and any tools wired for you.
- **Multi-repo workspace:** your folder holds one worktree per repo (brief section "Workspace"). Need another repo?
  Run `mstack board worktree --task <ISSUE> --repo <name>`. Never edit the repos at the project root.
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
- **Draft in the issue, settle, then doc and consolidate (owner, 2026-10-30; replaces "docs first"):**
  - Small issue: no doc; your `done` result is the record.
  - Medium issue: work out the plan and open questions on the issue (`note`, or `ask` for the owner). Once settled,
    write the doc in the repo from the thread (`board thread`), with a short "Questions resolved" section. Then
    shrink the issue description to a few lines plus the doc link (`--doc <path>`). Keep the comments.
  - Big design: the doc comes first as its own PR; the issue links it.
  - Docs and PRs go under the issue's **Resources**, not in comments; on a private board, only when the owner asks.
  - Before `done`: the doc exists (medium and big) and the description is consolidated.
- **Ideas for mstack itself:** `mstack spark --from <project> "<idea>"`. Never edit mstack from a task.
- **Helpers and sub-issues:**
  - For a part of your issue, you may start a **helper** as your side session (one level; it never starts its own).
    Register it: `mstack role set --project <path> --session <id> --role helper --task <ISSUE> --worker <your id>`.
    Helpers report only to you, and you write the issue's record.
  - For a **sub-issue** of your issue, you may start its worker as your side session. Then ask your orchestrator to
    adopt it. It owns its own record and stays nested under you.
  - Never move them to top level.
