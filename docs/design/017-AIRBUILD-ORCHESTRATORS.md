# 017 — Orchestrators hosted in {{mstack:CLIENT_C_APP}} (MST-66, 2026-10-30)

Status: investigation and plan. {{mstack:CLIENT_C_APP}} is treated as **a product mstack uses**, not as code (owner, 2026-10-30:
"Don't read {{mstack:CLIENT_C_APP}} Repo, I have {{mstack:CLIENT_C_APP}} desktop app"). An earlier draft drew on the {{mstack:CLIENT_C_APP}} source; it was
withdrawn, and nothing from it is used here. Sources are only:
- the public site (`{{mstack:CLIENT_C_SITE}}`, `{{mstack:CLIENT_C_SITE}}/docs/mcp/`);
- what the installed **{{mstack:CLIENT_C_APP}} for Mac 1.3** app bundle exposes (Info.plist, App Intents metadata, the bundled
  local-environment tools and skills), read without opening or driving the app;
- product facts from the {{mstack:CLIENT_C_SITE}} orchestrator.

Nothing in {{mstack:CLIENT_C_APP}} was changed or called, and no paid model ran. Steps marked ★ need the owner's OK, and an
OAuth sign-in or driving the app's UI is one of them. {{mstack:CLIENT_C_APP}} product asks go to YEL through the {{mstack:CLIENT_C_SITE}}
orchestrator.

Builds on [011](011-EVENT-HUB.md) (Postgres hub queue), [014](014-STATUS-TABLE.md) ("My tasks"),
[015](015-MULTI-HARNESS.md) (runner plugins) and 016 (DeepSeek orchestrators: mailbox, conductor, action block,
long-running loop; on the MST-64 branch, `docs/design/016-DEEPSEEK-ORCHESTRATORS.md`).

Owner (2026-10-30): "Aside from deepseek harness, I believe {{mstack:CLIENT_C_APP}} itself can do the job right? … Try build this
flow using {{mstack:CLIENT_C_APP}} production app: make orchestrators live in {{mstack:CLIENT_C_APP}}."

## Short answer

- **Very likely yes, through {{mstack:CLIENT_C_APP}}'s public MCP server.** `https://mcp.{{mstack:CLIENT_C_SITE}}/mcp` (OAuth, "nothing to
  install and no key to copy") lets an outside client act as the owner. It can talk to Agents, catch up on a
  Project, run the Team ("hire or edit Agents") and share files. It **waits for replies** ("Agents can take a few
  minutes, and the assistant keeps waiting"). That is exactly a wake-and-collect channel.
- **mstack's conductor (016) becomes an MCP client of {{mstack:CLIENT_C_APP}}.** For each mailbox batch it sends a message to the
  orchestrator Agent and waits for the reply. The Agent ends its turn with 016's `mstack-actions` block, and the
  conductor validates and runs it with `mstack board` here. Linear keys, git and Postgres stay on this machine,
  and nothing on the VM is exposed.
- **The owner's console is the {{mstack:CLIENT_C_APP}} app** (Mac, iPhone, iPad): chat with the orchestrator, see its work, and
  give verdicts. A Mac fallback for waking exists without any token: the app's **Shortcuts actions** "Send
  Message" and "Send Files" (`shortcuts run`).
- **Agent-to-agent messaging stays in the hub mailbox** (016), so an {{mstack:CLIENT_C_APP}} orchestrator can talk to Claude
  Desktop or dsh workers.
- **Phase 1** starts with a read-only qualification ★: connect an MCP client, list its tools and send one test
  message. Then one Agent, `@mstack-orch`, runs mstack's own board in shadow mode, then live. Workers stay on this
  machine.
- **What still needs the owner's answer** is listed in section 6 (models, Agent instructions, outbound HTTP,
  state, stop, cost).

## 1. What {{mstack:CLIENT_C_APP}} offers, as a user sees it

### From the public site (`{{mstack:CLIENT_C_SITE}}`)

| Topic | What it says |
|---|---|
| Agents | "AI agents to build your app and handle App Review", covering product, design, engineering, growth and marketing. They "submit, respond, fix, and resubmit". |
| Where they run | "Teams can run on a Mac or in the cloud … Switch anytime. The same brief and project context move with you." |
| Plans | **Free** $0: 1 cloud VM hour a month, BYOK ("provider usage is billed by your AI provider"). **Pro** $20: 40 VM hours, included tokens. **Max** $200: 480 VM hours, more tokens, projects in parallel. **Enterprise** $2,000: custom hours and token pool, shared seats, self-hosted backend. |
| Models | No model names on the site. Included tokens on Pro and Max; BYOK on every plan. |
| MCP server (`/docs/mcp/`) | URL `https://mcp.{{mstack:CLIENT_C_SITE}}/mcp`. OAuth sign-in in the browser. Clients: Claude (web, desktop, Claude Code), ChatGPT, Cursor, Codex, and any remote-MCP-over-HTTP client with OAuth. It acts **as you**, in the Teams you belong to; owner-only acts stay owner-only. Messages sent through it "are yours". It waits for replies. Reading never marks a chat as read. Deletes happen only on explicit request. You disconnect it under "Connected apps" on {{mstack:CLIENT_C_SITE}}. "The connection is free. Work your Agents do counts against your {{mstack:CLIENT_C_APP}} plan." The page lists capabilities, not tool names: talking to Agents, catching up on a Project, running the Team ("Hire a designer Agent and add it to the Recipes project"), sharing files. Nothing about stopping or pausing an Agent. |

### From the installed Mac app (bundle only, app not opened)

| Surface | What is there | Use for mstack |
|---|---|---|
| URL scheme | `{{mstack:CLIENT_C_FOLDER}}://` | Possibly deep links to a chat for "My tasks" (paths unknown; question). |
| **App Intents (Shortcuts)** | `Send Message` (text, agent, files), `Send Files` (files, agent, text), `Open Chat` (agent) | A token-free way to wake an Agent from the Mac with `shortcuts run`. The owner makes one shortcut ★. It is one-way: there is no "read reply" intent, and the app must be on the Mac. |
| Local environment | The app bundles the environment that runs a **local Team** on the Mac, with tools for Agents: `git`, `gh` (with a credential helper and GitHub token script), `jq`, `browser` (cloud browser), `workers` (AirHost and the app products), `password-book`, `artifact` publishing, `runbuild`, `simulator`, `asc`, `imagegen`, `audiogen`, `videogen`, `modelgen`, `website`, `storeshot` | Agents can use git and GitHub themselves, and some kind of credential store exists (`password-book`; what it holds is a question). |
| System skills | 21, mostly app building (iOS, AirHost backends, analytics, purchases, App Store). One, `daily-report`, mentions "your daily **Schedule** comes due". | Agents seem to support **scheduled turns** (question). |

### From the {{mstack:CLIENT_C_SITE}} orchestrator (product knowledge, unverified)

- Local and cloud Agents both exist in production (open YEL bugs refer to each).
- Custom Agents exist (YEL bugs about their avatars). A broader "add custom agent" item is still in YEL's Backlog.
- It knows of no per-Team skills, no custom MCP servers per Agent, and no outbound hook when an Agent replies. It
  doesn't know whether cloud Agents can reach any HTTPS host.

## 2. Design: mstack orchestrators as {{mstack:CLIENT_C_APP}} Agents

```
Linear ──(hub tick, MST-41/60)──▶ Postgres mailbox (016: orchestrator.queue + orchestrator.agents)
                                          │
                     conductor (016), one adapter per harness
                     ├─ dsh adapter:      dsh --session-id …                       (016)
                     └─ {{mstack:CLIENT_C_FOLDER}} adapter: MCP client of https://mcp.{{mstack:CLIENT_C_SITE}}/mcp (OAuth as the account)
                                                   │  "send a message to @mstack-orch" (wakes it)
                                                   ▼
                                     {{mstack:CLIENT_C_APP}} Team ── Agent @mstack-orch (cloud or local)
                                                   │  reply ending in ```mstack-actions```
                     ◀──── "wait for the reply" ───┘
   validate → `mstack board propose|ask|dispatch|forward|stop|note|…` → mail to other agents → resolve events
```

### 2.1 The `{{mstack:CLIENT_C_FOLDER}}` host and runner plugin

A third host kind beside `spawn` (argv) and `handoff` (Claude Desktop), with transport `mcp-client`.

```json
{"name": "{{mstack:CLIENT_C_FOLDER}}", "joint": "agent", "transport": "mcp-client", "status": "planned",
 "summary": "{{mstack:CLIENT_C_APP}} Agent, woken and read through {{mstack:CLIENT_C_APP}}'s public MCP server",
 "endpoint": "https://mcp.{{mstack:CLIENT_C_SITE}}/mcp", "auth": {"oauth": ".mstack/secrets/{{mstack:CLIENT_C_FOLDER}}-oauth.json"},
 "capabilities": ["resume", "actions-block", "owner-chat"],
 "requires": {"settings": ["team", "agent"]}}
```

- **Code:** the manifest goes in `integrations/plugins/builtin/{{mstack:CLIENT_C_FOLDER}}/plugin.json`. The client goes in
  `integrations/orchestrator/{{mstack:CLIENT_C_FOLDER}}.py`; it reuses `integrations/plugins/mcp_client.py` and adds streamable-HTTP
  and OAuth (dynamic registration + PKCE, refresh). It maps the adapter's four needs (send, wait, read recent,
  attach a file) onto whatever tool names `tools/list` returns. Those names are pinned in config after
  qualification (P1), not guessed in code.
- **Config:** `taskboard.orchestrators.<scope>.agent` gets `{"harness": "{{mstack:CLIENT_C_FOLDER}}", "team": "…", "agent":
  "mstack-orch"}`. The mailbox address stays `orch:mstack`; the native session is `{{mstack:CLIENT_C_FOLDER}}:<team>/<agent>` in
  `orchestrator.agents`.
- **Secrets:** `.mstack/secrets/{{mstack:CLIENT_C_FOLDER}}-oauth.json` (0600) holds the client registration and tokens. Only the
  conductor (under `conductor.lock`) refreshes, since refresh tokens usually rotate.
- **`runners.py`:** `kind('{{mstack:CLIENT_C_FOLDER}}') == 'mcp-client'`. `dispatch` refuses it as a *worker* host in phase 1.
  `sandboxed` is true: the Agent can't run `mstack board` or commit here.
- **Fallback transport `shortcuts`** (Mac only): wake via `macctl run shortcuts run "mstack → {{mstack:CLIENT_C_APP}}"` with the
  batch as input. Replies then come back only through the owner's app, or through 2.3 phase B. Keep it for the case
  where the MCP sign-in can't be used for automation.
- **"My tasks" (014):** the orchestrator row gets `session_agent: {{mstack:CLIENT_C_FOLDER}}` (a new value) and an `{{mstack:CLIENT_C_FOLDER}}://`
  link if one exists, else the conductor's turn log.

### 2.2 How the hub wakes the Agent

1. The hub tick (unchanged) writes events; 016's mailbox gives each a recipient (`orch:mstack`).
2. The conductor takes one batch per recipient (one turn at a time, `batch_wait` 30 s, cap 20) and renders one
   message:
   - a first line `mstack hub · batch 7f3c · events 412, 413`, because MCP messages "are yours", so the Agent
     can't otherwise tell hub mail from the owner typing;
   - per event: kind, issue, title, status, the owner's words and the thread excerpt the action needs;
   - a `.md` file through the MCP "share files" tools when the context is large.
3. It waits through the MCP server for the Agent's reply, up to `max_turn_seconds`. The Agent may write several
   messages (an acknowledgement, progress). The turn ends at the message holding an `mstack-actions` block. If the
   wait ends without one, the conductor asks once ("your turn ended without an actions block"); after three
   failed attempts it sends `wake_failed` to the owner and pauses the Agent.
4. A retried send must not post twice. If the send tool takes an idempotency key, use
   `sha256(address, event ids)`; if it doesn't, the conductor reads the chat first and skips a batch header it
   already sent.

### 2.3 How the Agent runs `mstack board` actions

The Agent can't reach this machine's git, Linear keys or Postgres, and shouldn't.

**Phase A: action block in the reply (phase 1, nothing exposed).** The same contract as 016, so one parser and one
validator serve dsh and {{mstack:CLIENT_C_APP}}:

````
```mstack-actions
[{"do": "propose", "task": "MST-70", "size": "small", "agent": "claude", "plan": "…"},
 {"do": "send", "to": "worker:MST-68", "text": "…"},
 {"do": "resolve", "events": [412, 413]}]
```
````

- The conductor validates each action (schema, scope, the role's allowlist, shadow-mode gate), records
  `(event ids, action hash)` before running it, and runs it with `mstack board`.
- It reports refused actions in the next batch ("action 2 refused: task not in scope"). It reacts ✅/⚠️ on the
  Agent's message if the MCP server offers reactions.
- Read needs are prefetched: `board thread`, `tree` and `status` for the batch's issues go into the message. More
  is asked for with `{"do": "fetch", …}` and comes in the next message (one extra turn).

**Phase B: a narrow mstack agent API (later, owner's OK ★, only if Agents can make outbound HTTPS calls).** It is
the same action set over HTTP, called by the Agent mid-turn (curl from its shell), served by the conductor and
published through the existing agentgateway (a new route, a hashed per-agent key, an allowlist, rate limits,
access logs) plus a tunnel. The key would go in the Agent's credential store, if `password-book` is one, never in
chat. The action block stays as the fallback.

**Local-Team variant (option, not the default).** A local Team runs on the owner's Mac. If its Agents' shell can
reach the VM, they could call `mstack board` (or a narrow wrapper) directly, with no exposure. But it works only
while the {{mstack:CLIENT_C_APP}} app is open on the Mac, the same weakness as today's chats.

### 2.4 Agent-to-agent messaging through the hub

- **The channel is 016's mailbox**, with addresses `orch:<project>[/<scope>]`, `worker:<ISSUE>`, `owner` and
  `dock`. Each harness is an adapter: MCP for {{mstack:CLIENT_C_APP}}, `--session-id` resume for dsh, and the dock or hub chat for
  Claude Desktop.
- A `send` action becomes a mailbox row. A worker's `worker_report` reaches `orch:mstack` in its next batch.
- **Not {{mstack:CLIENT_C_APP}} group chats between agents.** That skips mstack's ordering, dedupe, ack and audit, and only works
  inside one Team. It could be added later as an optimisation for agents in the same Team, still mirrored to the
  mailbox.
- **The owner** can message the Agent in the app. Messages without the `mstack hub` header are the owner's:
  requests, private-mode verdicts, "merge MST-70". The Agent's resulting actions still go through the conductor,
  which also reads recent messages in that chat on each wake ("catch up"), so owner messages typed while the
  Agent was idle are seen.

### 2.5 Which account and Team

| Option | Pros | Cons |
|---|---|---|
| **(a) A dedicated mstack {{mstack:CLIENT_C_APP}} account** with its own Team, the owner invited ★ | Hub mail shows as "mstack", the owner's messages as the owner. The MCP sign-in can't reach the owner's product Team. Separate plan and usage. | A second account and plan; the owner switches Teams in the app. |
| (b) An Agent in the owner's current Team | No new account. | The MCP connection acts as the owner everywhere, including App Store work. Hub messages look like the owner's. It mixes with the product Agents. |
| (c) A local Team on the Mac | Uses the Mac, not VM hours. | Online only while the app is open. |

**Recommendation: (a)**, if the plan allows a second account. Otherwise (b) with the hub header.

### 2.6 The orchestrator's playbook inside {{mstack:CLIENT_C_APP}}

- **Instructions:** custom Agents exist; how long their instructions may be is a question. They get a short role
  card (013: plans and dispatches, never does the work), the action-block contract, the scope, and the hub-header
  rule.
- **Long material** (the condensed `mstack-orchestrator` skill without the Claude Desktop tool parts) is sent as a
  `PLAYBOOK.md` file in the first message and re-sent when its hash changes, until {{mstack:CLIENT_C_APP}} offers per-Team skills.
- **Memory:** whatever the Agent keeps (question). Linear and the journal stay the truth, and the conductor
  prefetches them every wake, so the Agent needs little memory.
- **Rotation:** after `rotate_at_tokens`, the conductor asks for a handover note and replaces the Agent (or resets
  its chat, if possible), seeding it with `board handover`.

### 2.7 Cost guardrails (016's, adapted)

- No wake without mail. Batching (30 s, 20 items). Prefetched context, so turns are short.
- Caps per agent: `max_turn_seconds`, a daily turn cap, `budget_day`.
- {{mstack:CLIENT_C_APP}}'s cost is the plan's VM hours plus tokens, or BYOK provider billing. How a woken cloud Agent consumes VM
  hours (per turn, or a minimum hold) decides whether a busy day fits in Pro's 40 hours (question).

## 3. Gaps

### mstack work (this repo)

| # | Work | Notes |
|---|---|---|
| M1 | 016's mailbox and conductor core (`orchestrator.agents`, recipient and sender, new kinds, turn loop, validator, execute-once log) | Shared with the dsh path; schema migration ★. |
| M2 | MCP client: streamable HTTP + OAuth (DCR, PKCE, refresh) in `mcp_client.py`; `{{mstack:CLIENT_C_FOLDER}}.py` adapter | Tests against a fake MCP server; no {{mstack:CLIENT_C_APP}} calls in tests. |
| M3 | `mstack {{mstack:CLIENT_C_FOLDER}} login` (one-time browser sign-in) and `mstack {{mstack:CLIENT_C_FOLDER}} qualify` (list tools, send one test message, wait, save a receipt) | Owner signs in ★. |
| M4 | Rendering (batch → message + file), playbook delivery by hash, hub header | |
| M5 | Shadow mode: actions logged, not run; daily comparison with the Claude orchestrator | As 016 M2. |
| M6 | "My tasks" `session_agent: {{mstack:CLIENT_C_FOLDER}}`, `mstack agents list/log/pause` | 014 / 016. |
| M7 | Skills: `mstack-orchestrator` ({{mstack:CLIENT_C_APP}} role card variant), `mstack-models` ({{mstack:CLIENT_C_FOLDER}} row), `mstack-hub` (retired once the conductor runs) | |
| M8 | Shortcuts fallback transport | Only if P1 shows the MCP path can't be automated. |
| M9 | Phase B agent API + gateway route + tunnel | Later; setup guard ★. |

### {{mstack:CLIENT_C_APP}} product asks (for YEL, through the {{mstack:CLIENT_C_SITE}} orchestrator; mstack never edits these repos)

Filed only once P1 shows which are real.

| # | Ask | Why |
|---|---|---|
| A1 | Scoped connections: limit an MCP connection to one Team or one Agent | Least privilege for automation |
| A2 | Mark messages sent through a connection as such, visibly, to Agents | The hub header is a convention, not a guarantee |
| A3 | Per-Team skills or long Agent instructions | The playbook without a file in chat |
| A4 | Stop, cancel or reset an Agent's turn or session, through MCP | Stuck turns, rotation |
| A5 | A turn-finished signal in the wait tool | Cleaner than the actions block plus a timeout |
| A6 | Per-Agent secrets and outbound HTTP to an allowlisted host, or custom MCP servers per Agent | Phase B |
| A7 | A documented `{{mstack:CLIENT_C_FOLDER}}://` deep link to an Agent's chat | "My tasks" link |
| A8 | A "read latest reply" Shortcuts action | Makes the Mac fallback two-way |

## 4. Phase-1 build plan: one {{mstack:CLIENT_C_APP}}-hosted orchestrator for mstack's own board

| Step | What | Exit check | Rollback |
|---|---|---|---|
| P0 | Owner verdict on this doc; section 6 answered | answers in the thread | — |
| P1 ★ | **Qualify the MCP path**, read-only plus one test message: build M2 + M3; the owner signs in; `tools/list`; send "ping" to a test Agent and wait for the reply; record tool names, limits and timings in a receipt | receipt saved; the adapter's four needs are covered by real tools | revoke under Connected apps |
| P2 | M1 + M4 in code against a fake MCP server built from the P1 receipt | tests green; `conductor run --dry-run` on the live queue with `--peek` | don't start it |
| P3 ★ | Account and Team (2.5), hire `@mstack-orch` (model per question 2), send the playbook | the owner sees the Agent in the app | remove the Agent |
| P4 ★ | **Shadow mode** for `orch:mstack`: real batches, actions logged, not run; the Claude orchestrator keeps acting | 20 events or a week; plan quality and cost per event compared | stop the conductor |
| P5 ★ | **Live** on mstack's board; workers still Claude Desktop or dsh | a full `/plan → propose → 👍 → dispatch → done → review` cycle with no Claude orchestrator turn | `agents pause orch:mstack`; re-register the Claude chat |
| P6 | Decide phase B, a second scope, and {{mstack:CLIENT_C_APP}}-hosted workers (Agents have `git` and `gh`) | owner verdict | — |

Not in phase 1: other projects' boards, {{mstack:CLIENT_C_APP}} workers, phase B, any {{mstack:CLIENT_C_APP}} product change.

## 5. Risks

- **Unknown tool contract.** The MCP page doesn't list tool names. P1 fixes that before any code depends on it,
  and the adapter maps names from config.
- **Automation on a personal sign-in.** The connection acts as a person. Option (a) keeps that person a dedicated
  account.
- **Output contract.** Agents talk to people. Shadow mode measures how reliably the actions block comes.
- **Production dependency.** When {{mstack:CLIENT_C_APP}} is down, mail waits in the mailbox, and rollback to a Claude chat is
  one registry change.
- **Data placement.** Batches put issue text into {{mstack:CLIENT_C_APP}}'s chat history. That is fine for mstack's own board; a
  client's private board would need its own decision before P6.
- **Cost visibility.** VM hours and tokens are seen in {{mstack:CLIENT_C_APP}}, not by mstack, until there is a usage readout.

## 6. Questions for the owner

About the product (what the app and the docs don't say):
1. Can a script use the MCP server unattended after one sign-in (does the connection refresh, and how long does
   it last)? And what are its tool names (or may mstack sign in once to list them, ★ P1)?
2. **Models:** which models can an Agent run, can each Agent have its own, and does BYOK accept DeepSeek's API?
3. **Custom Agents:** can one be given long instructions (a few KB)? Do Agents keep memory or their chat session
   between wakes, and for how long?
4. **Outbound:** can a cloud Agent call an HTTPS endpoint or an MCP server of ours? What is `password-book` (a
   secret store Agents can read)?
5. **Stop and schedule:** can an Agent's turn be stopped or its session reset? Do Agents have Schedules (the
   daily-report skill mentions one)?
6. **Cost:** how does a woken cloud Agent use VM hours (per turn, or a minimum)? Which plan is this on?

About the plan:
7. **Account:** a dedicated mstack account and Team (recommended), or an Agent in your current Team?
8. **May mstack do P1:** sign in to `mcp.{{mstack:CLIENT_C_SITE}}` once (you approve in the browser), list the tools and send one
   test message?
9. **Console:** is the {{mstack:CLIENT_C_APP}} app enough as your orchestrator console, or should a Claude chat stay as a relay?
10. **dsh path:** keep MST-62 parked as the fallback adapter (it shares the conductor), or stop it?
