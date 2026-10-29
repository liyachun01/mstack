# 005 — Anytype agent task board (illustration)

Status: **test channel live; capture/sync/dispatcher are design only.** 2026-10-28.

Goal: one task table in Anytype is the source of truth. One dispatcher agent
reads it, assigns work, and Claude/Codex/DeepSeek do the work. Agent turns are
logged against the task. My own Linear issues mirror into the same table.

```
            ┌──────────── Anytype channel "mstack-taskboard-test" ────────────┐
            │  Agent Task type ─ Task Board (kanban by Task Status)           │
            │  Agent Log chat  ─ one line per captured agent turn             │
            └───▲───────────────▲──────────────────────────▲──────────────────┘
                │ read/assign   │ run count + log          │ upsert by Linear ID
         ┌──────┴─────┐   ┌─────┴──────────────┐   ┌───────┴──────────────────┐
         │ dispatcher │   │ capture sink       │   │ Windmill: linear_sync    │
         │ (one agent)│   │ gateway logs/hooks │   │ assignee=me OR creator=me│
         └──────┬─────┘   └─────▲──────────────┘   └───────▲──────────────────┘
      launches  │               │ MCP + LLM traffic         │ Linear GraphQL
   ┌────────────▼─────┐  ┌──────┴───────┐            ┌──────┴──────┐
   │ claude / codex / │──│ agentgateway │            │   Linear    │
   │ deepseek workers │  └──────────────┘            └─────────────┘
```

## What exists now (verified)

| Piece | Where | State |
|---|---|---|
| Channel `mstack-taskboard-test` | Anytype (native UI created) | Live |
| Scoped key | `.mstack/secrets/anytype-taskboard-test.key` (0600, ignored) | One channel, read/write, all-spaces off — checked through `whoami` |
| Schema intent | [`infra/taskboard/schema.json`](../../infra/taskboard/schema.json) | 14 properties, `agent_task` type |
| Helper | [`integrations/agents/anytype_taskboard.py`](../../integrations/agents/anytype_taskboard.py) | provision / seed / board / capture |
| Board | Kanban + Table query, `Task Board` collection | 5 example tasks, read back |
| Agent Log | Channel chat | Example lines plus captured turns, read back |
| Object IDs | `.mstack/evidence/taskboard-test.json` (ignored) | |

Task fields: Task Status (Backlog→Todo→In Progress→In Review→Done/Canceled),
Priority, Assigned Agent, Source (anytype/linear/agent-capture), Labels, Due,
Estimate, Parent Task, Blocked By, Linear ID/URL/Updated, Agent Session, Run Count.

```sh
# All run on macOS, because the Anytype API listens on Mac loopback only.
K=.mstack/secrets/anytype-taskboard-test.key
macctl run python3 integrations/agents/anytype_taskboard.py board $K        # dispatcher view
macctl run python3 integrations/agents/anytype_taskboard.py capture $K <task-id> claude out "text"
```

Pass Anytype API paths to `macctl` without a leading `/`, because it rewrites
arguments that look like absolute paths. The helper only uses relative paths.

## 1. Capturing agent input and output

Agentgateway sees **MCP tool traffic**, and LLM traffic only on routes that go
through it. Claude Desktop currently reaches its model through Magpie, not the
gateway. Two capture points cover this:

1. **Gateway (tool calls).** Turn on agentgateway access logging or an OTel
   exporter for the MCP routes, with CEL fields for the route, tool name,
   arguments digest, status and latency. A small sink (a Windmill webhook or a
   sidecar) groups records by an `x-mstack-task` header or session ID and calls
   `capture` for each turn. Tool arguments can hold secrets, so log digests and
   names, not raw bodies.
2. **Harness hooks (prompts and replies).** Claude Code `UserPromptSubmit` and
   `Stop` hooks, and Codex `notify`, post the user prompt and final reply to the
   same sink. Hooks are project-scoped files and are not registered globally.

The sink writes **one chat line per turn plus a run-count bump**, not one task
per message. A new task is created only when the agent calls an explicit
`task.create` tool, or when a hook marks a reply as a task proposal. If every
message became a task, the board would be unusable.

### Capture proposal (2026-10-28)

What I found: the live gateway config (`state/projects/runtime/config.yaml`) has
**no MCP or model routes**, only health/UI. Logging is `filter: "false"`, and the
container is only *Created*, not running. Agentgateway 1.5 exposes `llm.prompt`,
`llm.completion`, `llm.toolCalls` and token/cost fields to access-log CEL
(`frontendPolicies.accessLog.add`), but **only for traffic on an `ai` backend**.
MCP logs give `mcp.tool` identity and post-request payloads. Today none of
your traffic reaches the gateway, so turning on logging alone would capture nothing.

**Step 1: Claude Code project hooks (registered 2026-10-28, gated).**
The hook does nothing unless **all** of these agree:
(1) the session's project directory is this repository;
(2) `.mstack/stack.json` validates and has `capture.enabled: true` for the
harness and event (schema: `capture` in `integrations/stack/schemas/project.schema.json`);
(3) the hook appears in this project's `.claude/settings.json` and in **no**
user-level `~/.claude/settings{,.local}.json` (project scope only; if it is also
registered globally, the hook stops working);
(4) a task is bound. Unit tests in `integrations/agents/tests/test_capture_hook.py`
cover each gate. Set `capture.enabled: false` to turn it off without touching the hook.

[`integrations/agents/capture_hook.py`](../../integrations/agents/capture_hook.py)
handles `UserPromptSubmit` (in) and `Stop` (out, the last reply from the event
or the transcript). It logs only while a task is bound through `$MSTACK_TASK`
or `.mstack/cache/current-task`, redacts key-shaped strings, truncates to 1800
characters, never fails the turn, and writes through a detached
`macctl … capture … -` call that reads the text from stdin. A dry run against
the test channel logged one in line and one out line, redacted a fake key, and
ignored an unbound event. Registering it means creating this project-only file:

```json
// .claude/settings.json
{"hooks": {
  "UserPromptSubmit": [{"hooks": [{"type": "command", "timeout": 5,
    "command": "python3 \"$CLAUDE_PROJECT_DIR\"/integrations/agents/capture_hook.py"}]}],
  "Stop": [{"hooks": [{"type": "command", "timeout": 5,
    "command": "python3 \"$CLAUDE_PROJECT_DIR\"/integrations/agents/capture_hook.py"}]}]}}
```

It affects Claude Code sessions opened in this repository only. There is no
global setting, service or port. Turn it on with
`echo <task-id> > .mstack/cache/current-task` and off with `rm` of that file.
To roll back, delete `.claude/settings.json`.

**Step 2: agentgateway LLM route (design; needs its own approval later).**
Add a third loopback listener (proposed `127.0.0.1:58086`) with an `ai` backend
for DeepSeek's Anthropic-compatible endpoint. Set
`accessLog.add: {task: 'request.headers["x-mstack-task"]', prompt: 'llm.prompt',
completion: 'llm.completion', tools: 'llm.toolCalls', tokens: 'llm.totalTokens'}`
and `filter: 'has(llm.requestModel)'`, with JSON logs on stdout. A sink follows
`docker logs` and calls `capture`. Then point Magpie's DeepSeek provider at
that listener. This step covers Claude Desktop/Cowork, which hooks don't, and
adds token and cost data. The trade-offs: it copies the DeepSeek key into gateway state, changes
Magpie's upstream, starts the gateway, and the exact v1.5 `ai`/`hostOverride`
syntax still has to be checked against the pinned image first. Do it only if you
need Desktop coverage or cost accounting. MCP routes can be added the same way
once workers use gateway-hosted tools.

## 2. Linear sync (only my issues)

- **Scope:** `issues(filter: { or: [{ assignee: { isMe: true } }, { creator: { isMe: true } }] })`.
- **Pull:** a Windmill scheduled script upserts by `Linear ID` and stores
  `Linear Updated`.
- **Push:** for tasks with Source = linear, Anytype changes to title, status,
  priority or due go back through `issueUpdate`. Status mapping uses the team's
  workflow state *type* (backlog/unstarted/started/completed/canceled). See
  `linear_sync` in the schema.
- **Conflicts:** the newest `updatedAt` wins for shared fields. Agent-only
  fields (Assigned Agent, Run Count, Session) never leave Anytype.
- **Anytype-only tasks** stay local unless they get a `linear` label. Then
  the push step creates the Linear issue and writes back its ID.

**Composio or direct?** I recommend calling the Linear API directly from Windmill
with a personal API key held as a Windmill secret. With one user and one
service, Composio would add a hosted OAuth broker, another account and a
third-party data path, and it gives you nothing Linear's GraphQL API doesn't
already have. Composio is worth adding later if you want the same pattern for
several SaaS tools (GitHub, Slack, Notion) behind one auth layer. The sink and
sync shapes stay the same either way.

## 3. Dispatcher loop

1. `board` → open tasks sorted by priority, skipping any with an open `Blocked By`.
2. Pick the first `Todo` whose Assigned Agent is `unassigned` or `dispatcher`.
   Choose a worker: Claude for design/writing, Codex for repo code changes,
   DeepSeek for cheap batch work.
3. Set the status to In Progress and Assigned Agent to the worker, then post a
   `dispatcher → worker` line.
4. Launch the worker (`mstack run`, or the harness CLI/session API) with the
   task body as the brief and `x-mstack-task: <id>` on its gateway connection.
5. The worker finishes and sets In Review. A human or reviewer agent moves it to
   Done. The Linear push sends the change upstream.

The dispatcher should run on demand at first, not on a schedule. Make it
scheduled only once the capture and sync steps are qualified.

## Not done / needs approval

- No agentgateway configuration change, sink, hook or service lifecycle action.
- No Linear token, Windmill script or Composio account. `DEMO-1` is a placeholder.
- The dispatcher is a read view plus a design, not an autonomous runner.
- The test channel and key are disposable: delete the channel in Anytype, revoke
  `mstack-taskboard` under API keys, then remove the key file and evidence file.
