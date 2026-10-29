# 009 — Live tests for the retained services (proposal, 2026-10-28)

State at discovery: Headroom and the Anytype adapter are running; agentgateway,
Graphify, Garage, shared PostgreSQL, WhoDB, Windmill and ai-memory are stopped,
with their data volumes and credentials preserved. Each step below is a separate
setup-guard approval. No step installs anything, pulls an image or touches {{mstack:CLIENT_REPO}}.

## 1. Graphify: the `memory.long` joint
- Start `mstack-graphify` (pinned image, `network_mode: none`, read-only).
- Index test-market once in a throwaway container: source mounted read-only, no
  network, AST extraction only (no model). Output is `graph.json` under its `.mstack/`.
- `mstack tenant add --project test-market --tool graphify --graph <graph.json>`.
- Write the `memory.long` adapter (`query`, plus `index` only as an explicit command),
  a contract kit, and select it with `joints.memory.long: graphify`. Test it live, and
  test that a worker gets it as MCP.

## 2. agentgateway: what it adds beyond capture
Capture now works through the board and hooks. What the gateway uniquely adds:
- **One authenticated MCP endpoint per project** (federation). Workers get one URL
  and one key instead of a stdio launcher per tool. The tool allowlist and rate
  limits are enforced at the gateway, not just written in a brief.
- **Policy at the boundary:** CEL rules such as "workers may call `headroom_*` and
  `query_graph`, never write tools", plus per-project JWT/API keys. The project-side
  `.mcp.json` / `-c` wiring shrinks to one entry.
- **OpenAPI → MCP:** expose internal HTTP APIs (Windmill jobs, Garage, the board
  itself) as MCP tools without writing servers.
- **Audit and traces:** an access log / OTel record of every tool call, with
  `x-mstack-task`, as evidence on the issue.
- **Model gateway (later):** one OpenAI-compatible endpoint across providers, with
  token accounting per task. Budgets and failover need confirming against the
  pinned version first.

Test proposal: start the gateway, add one route `/mcp/test-market` that federates
test-market's Headroom (and Graphify, if step 1 is approved) with a test-market-only
key and a read-only tool allowlist. Turn on JSON access logs with the task header.
Check:
- a call with the key works;
- the wrong key → 401;
- a denied tool → refused;
- the log shows the task ID.

Then add a `gateway` plugin so dispatch can wire workers to that one endpoint.

## 3. Garage: S3 for internal tools
Use: durable artifacts the board shouldn't hold, such as worker run logs, briefs,
large outputs and evidence files, plus Windmill job results.

Proposal: start Garage, then create bucket `mstack-artifacts-test-market` with a key
scoped to that bucket only. Add an `artifacts` step to `finish` that uploads the run
log and links it on the issue. Test put/get with the key, and check that the key is
denied on another bucket.

## 4. Windmill: scheduler and runner
Honest fit:
- **Good for:** scheduled jobs that need no Mac-desktop access, such as nightly
  Linear sync, artifact cleanup, digest notes, and spawn-host workers.
- **Not good for:** starting Claude Desktop sessions (only a Desktop agent can). It
  also can't reach the Anytype API on Mac loopback without a qualified bridge.

Proposal: start shared PostgreSQL and the Windmill server and worker, then create
workspace `mstack` with a scoped token. That needs your admin login, or a token you
create. Run one script and one schedule (a heartbeat that writes to the Garage
bucket), check the run history, then stop or keep it as you choose.

## 5. PostgreSQL + WhoDB for internal tools
**Recommendation: one shared PostgreSQL 18 instance, with a separate database and
login role per internal tool.** That is the pattern Windmill already uses. It means one backup and
upgrade path, pgvector available to all, and isolation through roles.

Use a **separate instance** only when a tool needs:
- a different major version or extensions that can't be shared;
- heavy or bursty load that could starve others;
- a different backup or retention lifecycle;
- hostile-tenant isolation.

None applies to the orchestrator or plugins today.

Proposal: start the shared PostgreSQL instance and WhoDB, then create database
`mstack_orchestrator` with owner role `mstack_orchestrator` and a read-only role
`mstack_viewer` for WhoDB. Move the orchestrator's run/event log from the JSON file
into it later, as a separate change. Check the viewer can read but can't write.

## Results — 2026-10-28

**Graphify (approved):** `mstack-graphify` started. test-market's committed `master` was
indexed offline (29 nodes, 36 edges, 8 communities) and its tenant registered. The `memory.long`
adapter passes 4/4 live. Naming another project or calling a write tool is refused.
`joints.memory.long: graphify` is selected, so workers get Headroom and Graphify. Evidence:
test-market `.mstack/evidence/graphify-memory-long-live.json`.

**Windmill (approved, initial admin login):** shared Postgres and Windmill CE 1.823.1
started. Workspace `mstack` and non-admin user `orchestrator` were created. The token is
in `infra/windmill/state/mstack-token` and is refused on `admins`. A script ran on demand,
and a minute schedule ran twice and was then disabled. A non-admin can't write to folder
`f/mstack` (row-level security), so the user namespace is used. Evidence:
`infra/windmill/state/mstack-test-20261028.json`.

**Waiting for approval on the board:** agentgateway (high priority), Garage, Postgres + WhoDB.
**Linear:** a Todo waits for a team and an API key.

**Postgres + WhoDB (approved on the board, 2026-10-29):** this uses the shared PG18 instance.
Database `mstack_orchestrator` has its own owner role, and CONNECT is revoked from PUBLIC.
`orchestrator.events` is ready for the run/event log. Read-only role `mstack_viewer` can read but
can't insert, create tables or reach other apps' databases. WhoDB runs at 127.0.0.1:58091.
Passwords are in `.secrets/postgres/` (0600). Evidence: `infra/postgres/state/mstack-orchestrator-20261029.json`.

**Linear (entry 1):** test-market is linked to workspace `yyyymmdd`, team Y, in pull mode, with the key
verified live. The first pull found no issues. The pull/push round trip waits on network access to
api.linear.app (TLS timeouts from the dev machine). The board loop now isolates and rate-limits
Linear sync, so an outage can't stop it.

**Linear round trip (entry 1, 2026-10-29):** issue Y-10 created in Linear was pulled into
test-market's table as Backlog (source linear). Anytype task "mstack link test: push to Linear"
was pushed as Y-11 with the scope label; marking it Done in Anytype moved Y-11 to completed in
Linear. Network: all traffic goes through the Clash TUN (fake-IP DNS), and TLS handshakes take 3–5 s
and sometimes stall, so Linear calls now retry network errors three times with backoff.

**agentgateway, option B (approved, 2026-10-29):** the pinned gateway was started in place.
Route `/mcp/projects/test-market` → Windmill MCP (`mstack` workspace, an MCP-only token for the non-admin
`orchestrator` user). The project key is stored hashed; the plaintext is only in test-market's secrets.
Checks: no or wrong key → 401; another project → 404; 10 of 43 Windmill tools exposed; createScript
and the arbitrary-code preview are refused; rate limit 30/min (30 pass, 10 refused, reported as JSON-RPC
errors in HTTP 200); the access log tags project, task, tool and target.

From the dev machine the gateway is at `host.orb.internal:58080`. Its DNS-rebinding protection rejects
that Host. Relaxing the protection was refused as a security weakening, so it stays on, and workers use
`integrations/gateway/stdio_bridge.py`, which sends the published Host plus the project key. The
`agentgateway` plugin (joint `gateway`, worker MCP `mstack_gateway`) is selected for test-market.
Evidence and rollback: `infra/agentgateway/state/projects/test-market-route-20261029.json`.
Not done: Headroom and Graphify behind the gateway (option A). Decide later, per tool.
