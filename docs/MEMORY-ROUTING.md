# Accepted memory routing policy

Updated 2026-10-06: Anytype is the sole PKM, local-only initially; Basic Memory
is secondary/opt-in. ai-memory is an installed experimental working-memory
candidate. Keep Graphify/CodeGraph without automatic retrieval fan-out.
[Canonical handover and flow](HANDOVER.md),
[machine-readable instruction policy](../infra/agents/memory-routing.json).
This policy does not configure a gateway dispatcher or register harness tools.

Latest refinement: `direct-anytype` uses harness → Anytype MCP directly, then
one changed-object ai-memory refresh after a successful authorized harness write.
No gateway/Windmill prerequisite. Read the project `.mstack/stack.json` and
project skill. Source edits and memory updates are reported separately; client
bindings remain pending. App/UI edits are refreshed on the next explicit harness
read; no background watcher is configured. This is a narrowly scoped follow-up,
not a full workspace mirror or transcript capture.

## Distinct responsibilities

| Component | Responsibility | Skip when |
| --- | --- | --- |
| Anytype | Canonical personal/project knowledge in the bound Space, via its local API/MCP | Knowledge irrelevant or authenticated project binding absent |
| ai-memory | Experimental working context/checkpoints and cross-harness handoffs | No explicit evaluation request/project binding; automatic capture remains off |
| Basic Memory | Secondary existing Markdown notes and legacy durable context | Anytype satisfies the need, prior Markdown irrelevant, or connection deferred |
| CodeGraph | Source symbols, callers/callees, dependencies and impact in an approved indexed repository | No implementation question, no relevant index, or repository outside the approved scope |
| Graphify | Broader relationships across code, documents, schemas and selected media | No relevant corpus or no relationship question; ordinary symbol/call-path lookup can use CodeGraph instead |

Embeddings are an optional Basic Memory retrieval enhancement, not a replacement for either structural graph. A multilingual model can support cross-language retrieval; test actual languages and cross-language queries before selecting it. No model has been selected or downloaded for this stack. Graph indexes are persistent, rebuildable derived context, not the agent's conversation history. No automatic CodeGraph-to-Graphify graph merge is promised.

## Task profiles, with per-step tool selection

| Profile | Candidate tools | Selection rule |
| --- | --- | --- |
| PKM/personal | Anytype in the bound project Space | Basic Memory only for relevant existing notes; Graphify only for an approved relationship question. No CodeGraph. |
| Coding/debugging | Direct source/search first; one relevant contextual tool | Graphify for relationships; CodeGraph opt-in for source structure; ai-memory opt-in for prior work/handoff. Anytype for durable project decisions; Basic Memory secondary. |
| Documentation/research | Anytype; conditional Graphify | Basic Memory for a named legacy note; CodeGraph only for approved implementation scope; ai-memory for an explicit checkpoint. |

At task entry, establish the profile, repository/corpus scope and whether memory writes are authorized. The session profile is only a default: reassess on a material task or repository change. Within a task, choose tools only when useful. Do not perform mandatory three-tool retrieval on every input or save every output.

Start with zero retrieval calls when local context suffices; otherwise select one
backend for that step. Add another only to resolve a named unanswered question.
Windmill can encode this sequence in a reviewed workflow. Interactive harness
calls need not traverse Windmill. Gateway tool filtering/call enforcement needs
runtime qualification; instructions alone do not dynamically hide all unused tools.
MCP calls do not inherently use model tokens. Definitions and results included in
model requests do, as do optional backend LLM/embedding passes. See the measured
schema example and citations in the handover; no paid inference test was performed.

If the relevant tool/index is unavailable or stale, report the limitation and use approved direct inspection where appropriate. Do not silently index, broaden filesystem access, install dependencies or treat inferred graph links as source facts. Do not run automatic vendor hooks that force duplicate Graphify/CodeGraph calls; review their instructions against this policy during each setup proposal.

## Instructions versus enforcement

- Project instructions and tool descriptions guide the agent. They are not a security boundary.
- Hard restrictions require a verified harness/gateway tool allowlist and filesystem/database access boundaries. Hiding a tool from discovery alone is insufficient if it can still be called through another exposed route.
- Future profile configurations belong under `infra/`; agent discovery instructions remain in `AGENTS.md` and project skill locations. Do not use global harness configuration.
- Agentgateway is the selected/current proxy. MetaMCP is historical, not a pending replacement. Aggregation by itself does not classify tasks or guarantee profile enforcement. Its documented MCP authorization filters discovery and authorizes calls; verify the pinned runtime's rejection/failure behavior before relying on profiles. Scope tools by configured endpoint/identity, not a user-supplied claim that a task is non-code. See the [assessment](AGENTGATEWAY-SETUP-PROPOSAL.md).

For interactive harness work, use the project policy directly. n8n does not automatically intercept Codex messages or MCP calls. For automated jobs, the selected Windmill engine (or optional n8n) may select the profile and scoped toolset before the agent step and choose subsequent workflow steps. That launcher/tool-control integration must be verified separately; it is not implemented now.

## Memory writes and index lifecycle

- Save explicit remember requests and approved durable decisions/checkpoints, not every agent answer.
- Never save credentials, secret-bearing tool output, or unconfirmed speculation as established facts.
- Keep live source indexes fresh through an approved watcher or scoped sync, not by rebuilding on every user prompt. Refresh a Graphify corpus only when its relevant source material changes.
- Reference source paths and index freshness when graph evidence affects a coding decision. Index misses are not proof that a symbol or relationship does not exist.

## Current integration scope and model deferral

Basic Memory 0.23.2 and PostgreSQL are already installed; prior direct MCP smoke tests and application-container persistence tests passed. Preserve that completed baseline without repeating tests during this deferral.

The latest final-step request on 2026-10-01 returns Basic Memory harness integration to the plan, initially using the installed PostgreSQL/text-search baseline. Each connection, registration and scoped acceptance test still needs a concrete approval; none is enabled yet. Local embedding model selection/downloads, multilingual semantic-search setup/tests and unrelated usage tests remain deferred. No service shutdown/removal/reconfiguration, paid model use or automatic memory use is authorized. Model exploration inside the app does not itself configure the embedding provider. PKM integration may wait; [the runbook](OPERATIONS-RUNBOOK.md) defines proposed manual preview-and-approve bidirectional sync, not a currently running sync service.

CodeGraph's and Graphify's separately approved container/direct MCP test steps are complete; each covers only a narrow source projection, not a full repository or registered harness server. Agentgateway's [HTTP foundation](AGENTGATEWAY-NETWORK-CORRECTION.md), [synthetic aggregation/authorization qualification](AGENTGATEWAY-SYNTHETIC-HOST-CORRECTION.md) and both persistent backend/gateway connections are complete. [Latest combined qualification](CODEGRAPH-GATEWAY-SESSION-QUALIFICATION-PROPOSAL.md) passed: `/mcp/graphify` exposes seven query tools and `/mcp/codegraph` one explore tool through separate exact tool allowlists; bare `/mcp` remains 503. Current Compose recipe is base gateway + CodeGraph overlay only. Eight in-memory/cold cross-route replay tests were denied, and CodeGraph deletion/native capacity passed. Stateless Graphify supports authenticated same-route token resumption after DELETE, not permanent revocation. Its malformed-resource-URI HTTP 500 limitation is not an authorization pass. Endpoint restrictions do **not** implement automatic task-profile selection/filtering or automatic memory use. The user clarified on 2026-10-05 that agentgateway remains selected; MetaMCP is superseded. Harness, n8n and Basic Memory connections each require independent approval. Backup/restore validation remains required before declaring the stack stable, but is not pulled into this step.

## Upstream references

- [CodeGraph source and agent tool guidance](https://github.com/colbymchenry/codegraph#agent-tool-guidance)
- [Graphify capabilities](https://github.com/Graphify-Labs/graphify#what-it-does)
- [n8n Tools Agent system message](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/tools-agent#system-message)
