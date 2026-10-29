# 008 — Competitive landscape for the mstack orchestrator

Researched 2026-10-28 from public pages: vendor pages, changelogs, comparison blogs
and directories. Many claims are vendor-stated or second-hand; links at the end.

## What mstack is, in one line

A **personal, local-first control plane**. The owner approves plans on issues in a
private task board (Anytype; optionally mirrored to Linear). An orchestrator agent
runs a team of agents (CLIs or desktop apps), each in its own git worktree, and all
of them report back on the same issue. Memory, compression, gateway and docs plug
in as joints.

## The five neighbouring categories

| Category | Examples | What they do | Overlap with mstack |
|---|---|---|---|
| **Tracker-native agents** | Linear for Agents (Codex, Cursor, Devin, Copilot, Factory…); GitHub Agent HQ (Copilot, Claude, Codex; Copilot coding agent GA Feb 2026) | Assign or mention an agent on an issue → cloud agent → branch/PR, with progress posted back | The closest product idea: issue as source of truth, agent reports on it |
| **Local parallel-agent workspaces** | Conductor, Superset, Claude Squad, Vibe Kanban (company shut down Apr 2026, community-maintained), Crystal → Nimbalyst | Many CLI agents in parallel, a worktree per task, diff review, PRs | Closest mechanics: worktree per task, many agent CLIs, kanban (Vibe Kanban) |
| **In-harness orchestration** | Claude Code subagents and Agent Teams (experimental, Feb 2026); Codex app with parallel cloud tasks | One harness splits work across its own agents | Usable *as hosts* by mstack rather than competitors |
| **Workspace agents** | Notion Custom Agents (Feb 2026; task database pattern, triggers, Linear connector, credits) | Autonomous agents over a docs + tasks workspace | Closest to "an Anytype-managed Linear with agents", but for knowledge work, cloud and paid |
| **Personal omni assistants** | ChatGPT agent + scheduled tasks; Grok Automations, Grok Bot (beta Aug 2026) | Broad connectors, schedules, always-on cloud agents | Same "personal agent" ambition, but chat-centred, not board/repo-centred |

## Where mstack is genuinely different

1. **Approval before work, on the issue.** Tracker agents and workspaces start on
   assignment and gate at the PR. mstack gates the *plan* (👍, 👎 or a reply) and
   again at review, and every revision stays in the issue's discussion.
2. **Private, multi-project board with an optional partial link.** A local-first PKM
   (Anytype) is the source of truth for every project, and Linear is mirrored only
   for your issues or one label. None of the others combine a private board with a
   selective mirror of an external tracker.
3. **Host-agnostic, desktop apps included.** The same contract drives headless CLIs and
   desktop sessions (Claude Desktop via handoff), and a new agent drops in as a
   manifest. Most workspaces are tied to CLIs; tracker agents are tied to their
   vendors' clouds.
4. **Two-way session ↔ issue.** Chatting directly in a worker session updates its
   issue (capture hook / notify), so the board doesn't go stale when you step
   into a session.
5. **Pluggable joints with per-project tenants.** Compression (Headroom, live),
   memory, gateway and docs are replaceable and scoped per project. Only the
   self-hosted long tail (small MCP orchestrators) tries this, and with little maturity.

## Where it is clearly behind

- **Review and merge.** There's no diff viewer, PR creation, CI gate or merge flow;
  Conductor, Superset, Vibe Kanban and every tracker agent have them. Today
  "Done" means "branch ready".
- **Always-on.** `poll`/`dispatch` run when the orchestrator is asked. ChatGPT,
  Grok and Notion run on schedules and triggers. A Windmill schedule would close this.
- **Reach.** There are no notifications or mobile surface (Anytype is in local-only
  mode), and it's single-user. Tracker agents are team products.
- **Setup weight.** OrbStack, containers, a running Anytype desktop app and a macOS
  loopback bridge, versus `npx vibe-kanban` or a Linear toggle. Anytype API v2 is
  prerelease.
- **Proof at scale.** Two real worker runs, one live plugin, one tenant pair. No
  long-running or many-agent load yet.

## Read of the market

- Teams are being served by GitHub Agent HQ and Linear's agent marketplace, with
  vendor clouds and per-seat or credit pricing. Competing there as a product is unrealistic.
- Local orchestrators are crowded and commercially fragile: Vibe Kanban's company
  shut down and Crystal was deprecated. Building another one is low-leverage.
- The open gap is the **owner-centric, privacy-first chief of staff**: one person,
  many projects, code and knowledge together, every agent accountable to one
  private board, and the owner's choice of tools and models. mstack is aimed
  right at it, and the incumbents aren't.

## Recommendations

1. Keep positioning personal; don't chase team features.
2. Treat neighbours as plugins, not rivals. Claude Code Agent Teams, the Codex app
   and Superset or Conductor sessions can all be agent hosts behind the same contract.
3. Close the three gaps that matter for daily use, in order:
   1. a review step: diff summary on the issue and an optional `gh pr create` per task;
   2. an always-on loop: a Windmill schedule for `poll` and `dispatch`;
   3. a notification channel: an Anytype chat mention, or Linear notifications via the link.
4. Make it cheaper to adopt: a one-command `mstack board init` for a new channel and
   project, and fewer moving parts on the Mac bridge.

## Sources

- Vibe Kanban: [GitHub](https://github.com/BloopAI/vibe-kanban), [site](https://www.vibekanban.com/?embed=0), [fork noting sunset](https://github.com/MrEggs/vibe-kanban-fork), [AI Engineer listing](https://www.ai.engineer/orgs/vibe-kanban)
- Linear agents: [integrations](https://linear.app/integrations/agents), [Codex in Linear](https://linear.app/integrations/codex), [Cursor agent changelog](https://linear.app/changelog/2025-08-21-cursor-agent), [How Cursor integrated](https://linear.app/blog/how-cursor-integrated-with-linear-for-agents)
- GitHub Agent HQ: [SD Times](https://sdtimes.com/ai/github-unveils-agent-hq-the-next-evolution-of-its-platform-that-focuses-on-agent-based-development/), [i-programmer: Claude and Codex join](https://www.i-programmer.info/news/105-artificial-intelligence/18651-github-adds-claude-and-codex-to-agent-hq.html), [agentpatterns](https://www.agentpatterns.ai/tools/copilot/agent-hq/), [Copilot agent GA](https://2236-io.pages.dev/en/news/github-copilot-coding-agent-ga-february-2026), [noqta](https://www.noqta.tn/en/blog/github-agent-hq-multi-ai-coding-2026), [Codex issue assignment](https://codex.danielvaughan.com/2026/03/28/codex-github-copilot-coding-agent-issue-assignment/)
- Parallel workspaces: [Conductor vs Claude Code](https://www.conductor.build/compare/claude-code), [Nimbalyst multi-agent tools](https://nimbalyst-website.pages.dev/blog/best-multi-agent-coding-tools-2026/), [Nimbalyst agent management](https://nimbalyst-website.pages.dev/blog/best-agent-management-tools-2026/), [worktree tools](https://nimbalyst-website.pages.dev/blog/best-git-worktree-tools-ai-coding-2026/), [Crystal](https://loopengineering-app.pages.dev/tools/crystal/), [Claude Squad](https://nathan-norman.vercel.app/ai-stacks/claude-squad), [Superset Show HN](https://hn.svelte.dev/item/46368739), [Superset vs Codex app](https://superset.sh/compare/superset-vs-codex-app), [Superset vs Claude Code](https://superset.sh/compare/superset-vs-claude-code)
- Claude Code teams: [Morph: Agent Teams](https://www.morphllm.com/claude-code-agent-teams), [Morph: orchestrator](https://www.morphllm.com/claude-orchestrator), [Tembo](https://www.tembo.io/blog/claude-code-multi-agent-orchestration), [prompt-shelf patterns](https://the-prompt-shelf.pages.dev/blog/claude-code-multi-agent-orchestration-patterns-2026)
- Notion agents: [Custom Agents](https://www.notion.com/product/custom-agents), [Rundown guide](https://app.therundown.ai/guides/how-to-automate-your-business-with-custom-notion-agents), [eesel review](https://eesel.ai/blog/notion-ai-review), [Vibe Coding Academy](https://www.vibecodingacademy.ai/blog/notion-custom-agents)
- Personal assistants: [Grok vs ChatGPT automations (Jul 2026)](https://andrew.ooo/answers/grok-automations-vs-cursor-automations-vs-chatgpt-scheduled-tasks-july-2026/), [toolradar ChatGPT vs Grok Bot](https://toolradar.com/compare/chatgpt-vs-grok-bot), [tooldirectory matchup](https://tooldirectory.ai/compare/chatgpt-openai-vs-grok)
- Self-hosted long tail: [Maestro](https://maestro-v2.taile3e365.ts.net/), [agent-fleet listing](https://enterprisedna.co/directories/mcp/escapeboy-agent-fleet-o), [memory MCP directory](https://mcpservers.org/category/memory?page=5)
