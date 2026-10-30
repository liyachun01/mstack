# 017 — Orchestrators hosted in {{mstack:CLIENT_C_APP}} (MST-66, 2026-10-30)

Status: investigation and plan. Nothing in {{mstack:CLIENT_C_APP}} production, its repos or its accounts was changed, and no paid
model was called. {{mstack:CLIENT_C_APP}} was read only from the {{mstack:CLIENT_C_FOLDER}} workspace checkouts (`backend`, `worker-platform`,
`{{mstack:CLIENT_C_SITE}}`, `{{mstack:CLIENT_C_APP}}`). Every step marked ★ needs the owner's OK. Steps that touch {{mstack:CLIENT_C_APP}} accounts also go
through the setup guard. {{mstack:CLIENT_C_APP}} product work goes to the YEL board through the {{mstack:CLIENT_C_SITE}} orchestrator.

Builds on [011](011-EVENT-HUB.md) (Postgres hub queue), [014](014-STATUS-TABLE.md) ("My tasks"),
[015](015-MULTI-HARNESS.md) (runner plugins) and 016 (DeepSeek orchestrators: mailbox, conductor, action block,
long-running loop; on the MST-64 branch, `docs/design/016-DEEPSEEK-ORCHESTRATORS.md`).

Owner (2026-10-30): "Aside from deepseek harness, I believe {{mstack:CLIENT_C_APP}} itself can do the job right? … Try build this
flow using {{mstack:CLIENT_C_APP}} production app: make orchestrators live in {{mstack:CLIENT_C_APP}}."

## Short answer

- **Yes, {{mstack:CLIENT_C_APP}} can host the orchestrator today, with no {{mstack:CLIENT_C_APP}} product change.** An {{mstack:CLIENT_C_APP}} Team Agent is a
  long-lived, cloud-hosted agent. It wakes when a message arrives in its channel, keeps its session and `MEMORY.md`
  on a persistent volume, has Bash, git and the network inside a gVisor sandbox, and runs any catalog model. That
  includes cheap ones and the owner's own key (`byok:custom`, e.g. DeepSeek's official API).
- **The hub wakes it by sending a chat message.** {{mstack:CLIENT_C_APP}}'s user API token (the MCP connector's
  `{{mstack:CLIENT_C_FOLDER}}-api-v1` token, built in the backend) can send to a channel and long-poll for replies
  (`POST …/messages/wait`). A message sent with it wakes Agents "exactly as one typed in the app". mstack adds an
  **{{mstack:CLIENT_C_APP}} adapter** to 016's conductor. The adapter posts each mailbox batch to the orchestrator Agent's DM and
  reads its replies back.
- **The Agent never touches this machine.** It gets the context it needs inside the message (and in attachments
  when large). It ends its turn with 016's `mstack-actions` block. The conductor, on this machine, validates every
  action and runs it with `mstack board`. Linear keys, Postgres and git stay here, and nothing on the VM is exposed
  to the internet in phase 1.
- **The owner gets an orchestrator console for free:** the {{mstack:CLIENT_C_APP}} app on iPhone, iPad and Mac. They can chat
  with the orchestrator, get push alerts when it finishes (`chat.settled`), and see one thread per orchestrator.
- **Agent-to-agent messaging stays in the hub mailbox** (016), not in {{mstack:CLIENT_C_APP}} channels. So an {{mstack:CLIENT_C_APP}}
  orchestrator can talk to a Claude Desktop or dsh worker, and the other way round.
- **Phase 1:** one Agent, `@mstack-orch`, runs mstack's own board, first in shadow mode, then live. Workers stay
  on this machine (Claude Desktop or dsh) because they need its git worktrees.

## 1. What {{mstack:CLIENT_C_APP}} offers today

Sources: `backend/AGENTS.md`, `backend/docs/{agent-team-sandbox,chat,mcp,byok,default-model,billing,token-usage,
environment-local,team-workers}.md`, `backend/team/models.json`, plus the other repos' docs (summarised below).

### Agents, sandboxes and models

| Topic | What exists |
|---|---|
| Agent | A **Team member** (`team_members` row) made from a template. Owners can hire a `custom` Agent with their own name, role, bio and instructions (`POST /api/teams/:teamID/members` with overrides). Its `agentID` is its @handle. The model is chosen per member or from the account default. |
| Runtime | The **{{mstack:CLIENT_C_APP}}Environment** program, one per Team. Each enabled Agent is a KWWK bot worker process (a Swift agent loop) with read, write, edit, grep, find, ls, Bash and sub-agents, plus `bot_*` chat tools (cards, `ask_question`, status). The bundled CLIs are `git` (works on the volumes), `runbuild`, `simulator`, `asc`, `imagegen`, `modelgen`, `website` and `storeshot`. |
| Sandbox | **Cloud Team:** one GKE Autopilot Pod per Team under gVisor, created on demand (warm pool, seconds to wake). Agents run as a shared unprivileged uid; there are no GCP or K8s credentials inside. **Local Team:** the same Environment as a child process of the owner's Mac app, running as the owner's user with no isolation. It is online only while the app runs. |
| Persistence | JuiceFS volumes: one Team state volume (each Agent's workspace, `MEMORY.md`, KWWK session store and notification cursor) and one volume per Project (`/projects/<id>`, a normal git working copy). Memory and processes can be thrown away; the volumes are the only state. |
| Lifetime | Decided by heartbeats. The Pod stays up while an Agent is busy (`self/activity`) or the app is in the foreground (`presence`), then 300 s more. A message to a stopped Team starts the Pod (wake outbox, retried, "wake never lost"). |
| Models | `team/models.json`: Grok 4.6/4.7, GPT-5.6/6.x (Luna from $0.10/$0.50 per M tokens), Claude Sonnet/Opus 5/5.5 and Fable, Kimi K3, GLM 5.2/5.3 (5.3 Flash $0.075/$0.25). They are served through the backend's OpenRouter proxy. BYOK (`byok:` prefix) sends traffic straight to the provider with the account's own login, and `byok:custom` points at any OpenAI- or Anthropic-compatible endpoint (one per account). DeepSeek isn't in the catalog; `byok:custom` with DeepSeek's API key covers it. |
| Search | Exa search and contents through the backend (`/api/llm/v1/search`, `/contents`). |

### Create, message, resume, stop

| Action | API | Auth |
|---|---|---|
| List Teams, channels, members | `GET /api/teams`, `GET /api/chat/teams/{t}/channels`, `…/members` | user session or user API token |
| Create an Agent | `POST /api/teams/{t}/members` (template + overrides; the `custom` template for our own) | owner; opened to the API token in MCP phase 1b ("hire and edit Agents") |
| Edit instructions or model | member override routes, phase 1b | owner |
| **Message (wake)** | `POST /api/chat/teams/{t}/channels/{c}/messages` with an `Idempotency-Key`. A DM (`dm.<agentID>`) wakes that Agent without the Selector. A Project channel runs the Selector (an extra LLM call); the host and @mentions always get it. | user session or API token |
| Read replies | `GET …/channels/{c}/messages?after=…` | same |
| **Wait for replies** | `POST /api/chat/teams/{t}/messages/wait`: up to 20 channels, each from its own sequence, ≤30 s per call, ignores the caller's own messages | same |
| Resume | Nothing to do: the session lives on the volume, so the next message continues it. A Pod restart is a cold start that reloads the session. | — |
| Stop | No "cancel this turn" for users. Remove the Agent (`DELETE …/members/{agentID}`); enable or disable only in the admin surface. Not sending is how you pause. | owner |
| Turn finished | Agents keep a 👀 status that lasts 10 s and is renewed while they work. When it clears, the channel is *settled* and the owner gets a `chat.settled` push. | members sync |

The user API token (`{{mstack:CLIENT_C_FOLDER}}-api-v1.`, 1 h access + 30-day rotating refresh) comes from OAuth 2.1 with PKCE at
`https://{{mstack:CLIENT_C_SITE}}/oauth/*`. It is open to dynamic client registration. It acts as the user who granted it, in
every Team they belong to, on an allowlist of routes. It never moves read cursors, and it is revoked on its own.
The backend has the principal, the OAuth server and the wait service (`ChatMessageWaitService`), and about 70
routes accept the token. Whether `mcp.{{mstack:CLIENT_C_SITE}}` and the OAuth pages are live in production is to be confirmed
(question 1 below).

### Tools, MCP, outbound network

- **No custom MCP servers per Agent.** The runtime has its own tool set. Skills are **global**: `team/sync.sh`
  publishes them to every Team, and production needs `--allow-production`. A per-Team or per-Agent skill doesn't
  exist. The way to give an Agent a playbook today is its instructions (`role_prompt` override), files it keeps
  in its workspace, and the messages it receives.
- **Network out:** Agents install dependencies and fetch from the web inside the sandbox. Reaching an arbitrary
  HTTPS host from a cloud Team, for example an mstack API behind a tunnel, is still to be confirmed (question 5).
- **{{mstack:CLIENT_C_APP}}'s own MCP connector** (`{{mstack:CLIENT_C_FOLDER}}-mcp` Worker at `mcp.{{mstack:CLIENT_C_SITE}}`) goes the other way: it lets an
  *outside* agent (Claude, Grok …) use {{mstack:CLIENT_C_APP}} chats as the user. mstack can use the same API without MCP.

### Triggers and the worker platform

- **No external triggers besides chat.** There are no user-defined inbound webhooks and no scheduled or proactive
  Agent turns; the backend's crons are system tasks. Posting a message with the user API token is the only way an
  outside system starts a turn.
- **worker-platform (`apps.{{mstack:CLIENT_C_SITE}}`)** is Cloudflare Workers for Platforms: plain ESM JS apps with D1, a public
  `fetch` handler (so it can receive webhooks), and crons (one minute at least, 60 s per run, at most once,
  missed runs not caught up). It has no resident processes and no per-worker secret store yet
  (`workers env set` is on its roadmap). It **can't host the conductor**: the conductor needs this machine's git,
  Linear keys and Postgres, and a long-running loop. AirRouter (its metered AI proxy) has DeepSeek V4.1 Flash only
  as a free-preset fallback, not for Agents.
- The app's own ExecPlans include `TeamIssueDelivery` (Claude sessions delivering YEL issues from Linear). It is
  the closest product precedent and worth a look by the {{mstack:CLIENT_C_SITE}} orchestrator before A-items are filed.

### Auth and cost

- The admin surface (`/api/admin`, behind Cloudflare Zero Trust) is out of bounds for mstack. Its service token
  is for {{mstack:CLIENT_C_APP}}'s own maintenance, and mstack never uses it.
- **Billing** is per user: per-feature plan quotas plus a prepaid credit balance in micro-USD. Platform inference
  is metered at upstream cost times a multiplier. BYOK traffic never charges credits. Token usage per Team, Agent
  and model is readable at `GET /api/teams/{t}/token-usage`.
- **A wake costs** one agent turn (KWWK system prompt + role + the message; the prefix stays stable, so it is
  cached), plus a Pod held for the turn and 300 s after it. A DM has no Selector call; a Project-channel message
  adds one.

## 2. Design: mstack orchestrators as {{mstack:CLIENT_C_APP}} Agents

```
Linear ──(hub tick, MST-41/60)──▶ Postgres mailbox (016: orchestrator.queue + orchestrator.agents)
                                          │
                     conductor (016), adapter per harness
                     ├─ dsh adapter: dsh --session-id …            (016)
                     └─ {{mstack:CLIENT_C_FOLDER}} adapter ──HTTPS, user API token──▶ {{mstack:CLIENT_C_APP}} backend
                                                   │  POST dm.mstack-orch messages (wakes the Agent)
                                                   ▼
                                         {{mstack:CLIENT_C_APP}} Team "mstack" ── Agent @mstack-orch (cloud Pod)
                                                   │  reply ending in ```mstack-actions```
                     ◀──── messages/wait ──────────┘
   validate → `mstack board propose|ask|dispatch|forward|stop|note|…` → mail to other agents → resolve events
```

### 2.1 The `{{mstack:CLIENT_C_FOLDER}}` host and runner plugin

A third host kind beside `spawn` (argv) and `handoff` (Claude Desktop), with transport `chat`.

```json
{"name": "{{mstack:CLIENT_C_FOLDER}}", "joint": "agent", "transport": "chat", "status": "planned",
 "summary": "{{mstack:CLIENT_C_APP}} Team Agent, woken by a DM, replies read by the conductor",
 "endpoint": "https://server.{{mstack:CLIENT_C_SITE}}", "auth": {"secret": ".mstack/secrets/{{mstack:CLIENT_C_FOLDER}}.json"},
 "capabilities": ["resume", "actions-block", "owner-chat"],
 "requires": {"settings": ["team", "agent"]}}
```

- **Where it lives:** `integrations/plugins/builtin/{{mstack:CLIENT_C_FOLDER}}/plugin.json`, and a client in
  `integrations/orchestrator/{{mstack:CLIENT_C_FOLDER}}.py` (send, wait, read, attachment upload, token refresh). No new dependency:
  plain `urllib`, like `linear.py`.
- **Config:** `taskboard.orchestrators.<scope>.agent` gets `{"harness": "{{mstack:CLIENT_C_FOLDER}}", "team": "<team id>",
  "agent": "mstack-orch", "model": "…"}`. The address stays `orch:mstack`; the native session is
  `{{mstack:CLIENT_C_FOLDER}}:<team>/<agentID>` in `orchestrator.agents`.
- **Secrets:** `.mstack/secrets/{{mstack:CLIENT_C_FOLDER}}.json` (0600) holds the OAuth client id, refresh token and access token.
  The refresh token rotates, and the file is rewritten atomically on each refresh. A reused refresh token revokes
  the grant, so only one process (the conductor, under `conductor.lock`) ever refreshes.
- **`runners.py`:** `kind('{{mstack:CLIENT_C_FOLDER}}') == 'chat'`. `dispatch` refuses it as a *worker* host in phase 1 (workers
  need local worktrees). `can_resume` is true, and `sandboxed` is true (no `mstack board`, no git here).
- **"My tasks" (014):** the orchestrator row gets `session_agent: {{mstack:CLIENT_C_FOLDER}}` (a new value beside claude, codex,
  deepseek, other). Its link is the {{mstack:CLIENT_C_APP}} DM, if the app has a deep link (question for YEL), else the
  conductor's turn log.

### 2.2 How the hub wakes the Agent

1. The hub tick (unchanged) writes events. 016's mailbox gives each one a recipient (`orch:mstack`).
2. The conductor takes the batch for `orch:mstack` (one turn at a time, `batch_wait` 30 s, cap 20) and renders
   one message:
   - a first line `mstack hub · batch 7f3c · events 412, 413`, so the Agent and the owner can tell hub mail from
     the owner's own messages (`content.via` is recorded but not shown to Agents);
   - per event: kind, issue, title, status, the owner's words, and the thread excerpt the action needs;
   - when the context is over about 8 KB: the full threads as a `.md` attachment (`create_attachment_upload` →
     `PUT` → `complete`), referenced in the text. Agents download attachments themselves.
3. It sends the message with `Idempotency-Key = sha256(address, event ids)`, so a retry never double-sends. A 202
   (Pod cold-starting) counts as delivered. A 503 `chat_wake_failed` puts the batch back in the queue with an
   attempt count.
4. It waits with `messages/wait` on `dm.mstack-orch` from the sequence of its own message. It collects the
   Agent's messages until one holds an `mstack-actions` block, or until the Agent's status has cleared and no
   new message has come for 60 s, or `max_turn_seconds` passes (see 2.3).

The Agent's KWWK base prompt makes it say a line first and a line per milestone. That is fine: the owner sees
progress in the app, and the conductor reads only the block.

### 2.3 How the Agent runs `mstack board` actions

The Agent can't reach this machine's git, Linear keys or Postgres, and it shouldn't. Two steps:

**Phase A: action block in the reply (phase 1, nothing exposed).** The same contract as 016, so one parser and one
validator serve dsh and {{mstack:CLIENT_C_APP}}:

````
```mstack-actions
[{"do": "propose", "task": "MST-70", "size": "small", "agent": "claude", "plan": "…"},
 {"do": "send", "to": "worker:MST-68", "text": "…"},
 {"do": "resolve", "events": [412, 413]}]
```
````

- The conductor validates each action (schema, the agent's scope, the role's allowlist, milestone gates such as
  shadow mode). It stores `(event ids, action hash)` before running, and runs it with `mstack board`.
- After running, it reacts on the Agent's message (`PUT …/messages/{seq}/reactions`): ✅ all ran, ⚠️ some were
  refused. The refusals go into the next batch ("your action 2 was refused: task not in scope").
- A turn that ends without a block gets one follow-up in the same DM ("your turn ended without an actions block").
  If that also fails, the batch goes back with an attempt count; after 3 attempts, `wake_failed` goes to the
  owner and the Agent is paused.
- **Read tools in phase A** are prefetched: the conductor puts `board thread`, `tree` and `status` output for
  the batch's issues into the message or attachment. If the Agent needs more, it asks with
  `{"do": "fetch", "what": "thread", "task": "MST-70"}`, and the conductor answers in the next message (one extra
  turn).

**Phase B: a narrow mstack agent API (later, owner's OK ★).** It is the same action set as HTTP tools the Agent
calls from Bash with `curl` mid-turn, so it can look things up without an extra turn:

- `POST /agents/v1/{address}/actions` and `GET /agents/v1/{address}/{thread|tree|status|mail}`. It is served by
  the conductor and published through the existing agentgateway: a new route, a hashed per-agent key, an
  allowlist, rate limits and access logs, as for `/mcp/projects/…`. A Cloudflare tunnel publishes it, because the
  sandbox is on GKE, not on this network. The key sits in the Agent's workspace (a 0600 file the Agent reads), is
  bound to one address and its scope, and is rotatable.
- It needs: outbound HTTPS from the cloud sandbox to that host (question 5), a public route to the VM (a new
  exposure, setup guard), and a way to give the Agent its key without putting it in chat history (the workspace
  file is written once by the Agent from a one-time message, which is weak; see gap A4).
- The action block stays as the fallback.

**Rejected for phase 1:** a local Team on the owner's Mac, where Bash runs as the owner and could reach the VM
(`orb run …/mstack board`). It needs no exposure, but it is online only while the {{mstack:CLIENT_C_APP}} app is open on the
Mac (the same failure as today's chats) and runs a model with the owner's full shell. Keep it as the fallback if
cloud networking or cost blocks phase B.

**Also rejected:** running the conductor on worker-platform, with a cron posting mail through the token. It has no
long-running loop and no secret store, and it can't reach this machine anyway.

### 2.4 Agent-to-agent messaging through the hub

- **The channel is 016's mailbox**, with addresses `orch:<project>[/<scope>]`, `worker:<ISSUE>`, `owner` and
  `dock`. Every harness is just an adapter: the {{mstack:CLIENT_C_APP}} adapter for {{mstack:CLIENT_C_APP}} Agents, dsh resume for dsh, and the
  Claude dock or hub chat for Claude Desktop sessions.
- An {{mstack:CLIENT_C_APP}} orchestrator's `send` action becomes a mailbox row. A worker's `worker_report` (its turn ended or
  `done`) becomes a mailbox row for `orch:mstack`, so it reaches the {{mstack:CLIENT_C_APP}} Agent in its next batch.
- **Not {{mstack:CLIENT_C_APP}} channels between agents.** Two mstack orchestrators as Agents in one {{mstack:CLIENT_C_APP}} Project channel
  could @mention each other. But that skips mstack's ordering, dedupe, ack and audit, costs a Selector call, and
  only works inside one Team. Allow it later only as an optimisation for agents in the same Team, still mirrored
  to the mailbox.
- **The owner** can message the Agent directly in the app. The Agent treats any message without the
  `mstack hub` first line as the owner's: requests, private-mode verdicts and "merge MST-70". Its actions still go
  through the conductor, so an owner verdict typed in the app becomes `board owner …` run by the conductor, as in
  016's `mstack chat`.
  - The conductor must also read the owner's messages in that DM: the wait call ignores the caller's own
    messages, and the caller is the owner. It does this by also reading `messages?after=` on each wake. That
    stays sound once a separate mstack account sends (A1).

### 2.5 Which account and Team

| Option | Pros | Cons |
|---|---|---|
| **(a) A dedicated `mstack` {{mstack:CLIENT_C_APP}} account** owning its own cloud Team "mstack", with the owner invited as a member ★ | Hub mail shows as "mstack", the owner's own messages as the owner. The token can't reach the owner's product Team or Apple accounts. Billing and usage are separate. The Team roster is only orchestrators. | A new account (an invite if registration is gated), a second plan or credit balance, and the owner joins a second Team in the app. |
| (b) A custom Agent in the owner's existing cloud Team | No new account. | The token acts as the owner everywhere, including App Store tools. Hub messages look like the owner's. It mixes with the product Agents (default roster and host rules). A cloud Team is limited to one per user. |
| (c) A local Team on the Mac | No Pod cost; can reach the VM | See 2.3 (offline with the app, no isolation). |

**Recommendation: (a).** It is the only option where a leaked mstack token can't touch the owner's product
work.

### 2.6 The orchestrator's playbook inside {{mstack:CLIENT_C_APP}}

- **Instructions** (`custom` template overrides, set with the hire/edit routes): a short role card (013: an
  orchestrator plans and dispatches, never does the work), the action-block contract, the scope, and "hub mail
  first line vs the owner". The judgment rules from `.agents/skills/mstack-orchestrator` go in **condensed**,
  without the Claude Desktop tool parts (SendMessage, start_session), which the conductor replaces.
- **Longer material** (the full skill, Linear status rules, size rules): a `PLAYBOOK.md` attachment in the first
  message. The Agent saves it to its workspace and refers to it, and the conductor re-sends it when its hash
  changes. This is a stopgap until per-Team skills exist (gap A2).
- **Memory:** the Agent's own `MEMORY.md` on the Team volume. Linear and the journal stay the truth; the conductor
  prefetches them every wake.
- **Rotation:** when usage passes `rotate_at_tokens`, the conductor asks for a handover note (an action), removes
  and re-hires the Agent with the same handle, and seeds it with `board handover` plus the note. That stays
  manual until {{mstack:CLIENT_C_APP}} has a "reset session" (gap A3).

### 2.7 Cost guardrails (016's, adapted)

- No wake without mail. Batching (30 s, 20 items). Context prefetched, so turns are short. DM, not a Project
  channel, so there is no Selector call.
- Model per scope in config. The default for phase 1 is the owner's choice (question 3).
- The conductor's own budget: `max_turn_seconds`, a daily turn cap and `budget_day`, computed from {{mstack:CLIENT_C_APP}}'s
  token usage (`GET /api/teams/{t}/token-usage`, read after each turn) and the catalog prices. Over budget, the
  mail is `held` and the owner is told once. {{mstack:CLIENT_C_APP}}'s credit balance is the hard stop for platform models.
- Pod time: one turn plus 300 s. Bursts are batched, so a busy day holds the Pod for minutes, not hours.

## 3. Gaps

### mstack work (this repo)

| # | Work | Notes |
|---|---|---|
| M1 | 016's mailbox and conductor core (`orchestrator.agents`, recipient and sender columns, `message`, `owner_message`, `worker_report`, `wake_failed` kinds, the turn loop, action validator, execute-once log) | Shared with the dsh path; needs the schema migration ★. |
| M2 | `{{mstack:CLIENT_C_FOLDER}}` plugin + `{{mstack:CLIENT_C_FOLDER}}.py` client (send, wait, read, attachments, reactions, token refresh) | Tests against a fake {{mstack:CLIENT_C_APP}} server; never production in tests. |
| M3 | OAuth bootstrap: `mstack {{mstack:CLIENT_C_FOLDER}} login` runs DCR + PKCE once in the owner's browser and stores the refresh token | Owner signs in and approves ★. |
| M4 | Rendering: batch → message (+ attachment), playbook delivery by hash | |
| M5 | Shadow mode: actions logged, not run; daily compare with the Claude orchestrator's actions | As 016 M2. |
| M6 | "My tasks" `session_agent: {{mstack:CLIENT_C_FOLDER}}`, `mstack agents list/log/pause` | 014 / 016. |
| M7 | Skills: `mstack-orchestrator` (an {{mstack:CLIENT_C_APP}} variant of the role card), `mstack-models` (an {{mstack:CLIENT_C_FOLDER}} row), `mstack-hub` (hub chat retired once the conductor runs) | |
| M8 | Phase B agent API + gateway route + tunnel | Later; setup guard ★. |

### {{mstack:CLIENT_C_APP}} product work (for YEL, through the {{mstack:CLIENT_C_SITE}} orchestrator; mstack never edits these repos)

| # | Ask | Why | Workaround until then |
|---|---|---|---|
| A1 | **Scoped API tokens**: one Team or one channel, no App Store, Simulator or management | Least privilege for automation | A dedicated account (2.5 a) |
| A2 | **Per-Team (or per-Agent) skills**, published by the Team owner | The playbook without global `team/sync.sh` | Instructions + `PLAYBOOK.md` attachment |
| A3 | **Turn control for owners and tokens**: cancel the current run, reset or compact the session | Stuck turns, rotation | Remove and re-hire the Agent |
| A4 | **Per-Agent secrets** (a value the Agent's tools can read, never shown in chat) | Phase B key | Workspace file from a one-time message |
| A5 | **Outbound allowlist or egress per Team** (or a confirmed answer that egress is open) | Phase B calls to mstack | Phase A only |
| A6 | **A turn-end signal for token clients**: a "run finished" event in `messages/wait` or a webhook on `chat.settled` | Cleaner than the actions block plus a timeout | Actions block + status timeout |
| A7 | **Custom MCP servers per Agent** (remote, streamable HTTP, with a per-Agent header) | Phase B as real tools instead of curl | curl from Bash |
| A8 | **A deep link to an Agent's DM** | "My tasks" row link | The conductor's turn log |
| A9 | Confirm whether `mcp.{{mstack:CLIENT_C_SITE}}` / OAuth / `messages/wait` are live in production, and the plan and credit setup for an automation account | Phase 1 depends on it | Staging (`staging-server.{{mstack:CLIENT_C_SITE}}`) for the dry run ★ |

## 4. Phase-1 build plan: one {{mstack:CLIENT_C_APP}}-hosted orchestrator for mstack's own board

| Step | What | Exit check | Rollback |
|---|---|---|---|
| P0 | Owner verdict on this doc. Questions 1–6 answered; A9 confirmed through the {{mstack:CLIENT_C_SITE}} orchestrator | answers in the thread | — |
| P1 | M1 + M2 + M4 in code with a **fake {{mstack:CLIENT_C_APP}} server** and fake board; no network | tests green; `conductor run --dry-run` against the live queue with `--peek` | don't start it |
| P2 ★ | Account and Team: create the `mstack` account (or use option b), its cloud Team, hire `@mstack-orch` (custom, model per question 3), invite the owner; `mstack {{mstack:CLIENT_C_FOLDER}} login` | the owner sees the Agent in the app; the token can list exactly that Team | remove the Agent; revoke the grant |
| P3 ★ | **Shadow mode** for `orch:mstack`: real mailbox batches go to the Agent, its actions are logged, not run; the Claude orchestrator chat keeps acting | 20 events or a week; plan quality and cost per event compared | stop the conductor |
| P4 ★ | **Live** for mstack's own board: actions run; workers still Claude Desktop (via the dock or hub chat) or dsh | a full cycle `/plan → propose → 👍 → dispatch → done → review` with no Claude orchestrator turn | `agents pause orch:mstack`; re-register the Claude chat |
| P5 | Decide phase B (agent API), a second scope, and {{mstack:CLIENT_C_APP}}-hosted *workers* (Project volume + git push credentials) | owner verdict | — |

What phase 1 does not include: other projects' boards, {{mstack:CLIENT_C_APP}} workers, phase B, and any {{mstack:CLIENT_C_APP}} product change.
Product asks go to YEL as separate issues.

## 5. Risks

- **Production dependency.** The orchestrator stops when {{mstack:CLIENT_C_APP}} is down or a runtime release breaks the KWWK
  loop. The mailbox holds mail, and rollback to a Claude chat is one registry change.
- **Output contract.** The Agent writes chat messages in a register the base prompt sets for people. The actions
  block competes with that style. Shadow mode measures how reliably it comes.
- **Selector and host rules** don't apply in a DM, but a Team needs a host Agent. In option (a) the orchestrator
  is the Team's host, so any Project channel created later wakes it. Don't create Projects in that Team.
- **Token power.** Even option (a)'s token can hire Agents and invite people in its Team. Until A1, keep the
  account empty of anything else.
- **Cost visibility** lags: token usage is rolled up each minute. Budgets use the rolled-up numbers plus a safety
  margin.
- **Chat history holds board context** (issue text, threads) in {{mstack:CLIENT_C_APP}}'s database. mstack's own board is fine.
  A client board (private mode) would put client data into {{mstack:CLIENT_C_APP}}. Decide per board before P5.

## 6. Questions for the owner

1. **Account:** a dedicated `mstack` {{mstack:CLIENT_C_APP}} account and Team (recommended), or a custom Agent in your current
   Team?
2. **Staging first?** Run P2–P3 against `staging-server.{{mstack:CLIENT_C_SITE}}`, then production, or go straight to production?
3. **Model** for `@mstack-orch`: a cheap platform model (GLM 5.3 Flash, GPT-6 Luna), Claude Sonnet 5.5 for plan
   quality, or `byok:custom` with the DeepSeek key? That key is one endpoint per account, which favours a
   dedicated account.
4. **Budget:** a daily cap for the orchestrator, and who pays: credits on the mstack account, or BYOK.
5. **Console:** is the {{mstack:CLIENT_C_APP}} app enough as your orchestrator console (chat, verdicts, push), or should a
   Claude chat stay as a relay?
6. **dsh path:** keep MST-62 parked as the fallback adapter (it shares the conductor), or stop it?
