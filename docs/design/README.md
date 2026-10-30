# Progressive stack design papers

2026-10-07. These documents distinguish installed/qualified work from designs.
For changing live status, use [the canonical handover](../HANDOVER.md).

1. [Scenarios at different scales](001-PROGRESSIVE-SCENARIOS.md): files-only work,
   Clock-style project docs, daily local PKM, source investigation, repeatable jobs,
   events and concurrent paper research.
2. [Small config and stack init](002-CONFIG-AND-INIT.md): the implemented six-field
   project config, binding separation, CLI/prompt flow and isolation limitations.
3. [Local models, proxy and effort](003-LOCAL-MODELS-AND-PROXY.md): installed versions,
   message/key flow, OpenCode/LM Studio comparison, model candidate and time estimates.
4. [Focused next improvements](004-NEXT-IMPROVEMENTS.md): a short priority list that
   improves the existing workflow before adding another platform.
5. [Anytype agent task board](005-AGENT-TASK-BOARD.md): live `mstack-taskboard-test`
   channel with an Agent Task schema, kanban board and Agent Log chat; designs for
   gateway capture, Linear sync (my issues only) and a single dispatcher agent.
6. [Orchestrator over the task board](006-ORCHESTRATOR.md): one table per project in
   the shared channel, owner verdicts by reaction/reply on the issue, parallel workers
   in git worktrees, session → issue updates, optional Linear link; `test-market` demo.
7. [Plugins](007-PLUGINS.md): one manifest format for every joint (agent, board, link,
   instant/long-term memory, compression, gateway, docs); agents already drop in by manifest.
8. [Competitive landscape](008-COMPETITIVE-LANDSCAPE.md): tracker-native agents, local parallel
   workspaces, in-harness teams, workspace agents and personal assistants versus mstack (2026-10-28).
9. [Live service tests](009-SERVICE-TESTS.md): Graphify, Windmill, Postgres + WhoDB, agentgateway and
   Linear link results, with evidence locations.
10. [Linear issues ↔ Claude sessions](010-LINEAR-SESSIONS.md): Linear as the board (polling, comment verdicts,
   `/plan` triggers), a flat orchestrator → worker session layout, and the four mstack skills.
11. [Event hub](011-EVENT-HUB.md) (planned): Windmill polls Linear into a Postgres event queue, and one small
   mstack hub chat delivers each event to the right project orchestrator.
12. [Product vs runtime](012-PRODUCT-VS-RUNTIME.md): what is mstack itself and what is this installation's
   records, the `runtime/` folder, and the MST-22 migration.
13. [Roles and sparks](013-ROLES-AND-SPARKS.md): strict orchestrator, sub-orchestrator and worker roles with
    role cards on every message, plus `mstack spark` for reporting ideas back to mstack.
