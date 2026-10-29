# Progressive mcp-stack scenarios

Design paper · 2026-10-07 · Personal setup, not a product platform.

Use the smallest preset that finishes the work. Scale here means the number of
execution domains and independently authenticated systems involved, not a ladder
of tools everyone must eventually install. Only Clock is a completed application
exercise. The scenes below are designs; initialization does not deploy them.

| Scale | Scene | Preset | Tools actually needed | Graduation trigger |
| --- | --- | --- | --- | --- |
| 0 | Small code patch / one-off clock change | solo | Codex + files | Durable shared project docs become useful |
| 1 | App with project knowledge, like Clock | project | Codex + direct Anytype | Repetition requires execution outside a chat |
| 1 | Daily notes and object housekeeping | knowledge | Codex + small local model through OpenCodex + Anytype | A measured model limitation, not tool availability |
| 2 | Explain a source change and its impact | research | Harness + Anytype; one selected graph | Approved corpus too complex for ordinary search |
| 3 | Weekly CSV/report processing | jobs | Harness + Windmill + scoped Garage artifacts + Anytype | External app events need a connector |
| 4 | Intake event → reviewed report → project record | events | Previous scene + n8n | Multiple callers need shared policy/quotas |
| 5 | Concurrent research jobs / paper investment analysis | explicit expansion | Relevant earlier tools; optional agentgateway + project DB | Actual concurrency and credential enforcement requirements |

## Scene 0: finish a small source task

Goal: change Clock's date presentation or fix a unit conversion in a small repo.
Use `solo` for a new files-only task; keep Clock's existing `project` preset for its
exercise. Codex inspects files, edits code and runs appropriate local checks.
No model proxy is needed for the native Codex provider. A one-off command does
not need Windmill. Files and build outputs belong to the project; reusable code
belongs in integrations only when another project will actually use it.

Flow: user → harness → project files/tests → verified result.
Completion: the requested behavior works and its meaningful checks pass. If the
user asks for durable docs, introduce the project knowledge binding then. Do not
call every context service merely to demonstrate the stack.

## Scene 1A: code plus project knowledge

Goal: deliver a small web app and maintain its brief, plan, tasks and verification.
Clock proves this scene: a dedicated channel, 4 docs, 7 Done tasks, two collections,
scoped key and direct MCP. Codex uses ordinary source tools for code, then Anytype
MCP for project checkpoints. Neither the browser app nor the LLM gets the Anytype
key. The harness executes the tool call.

Flow: user → harness → source/checks; harness → direct Anytype MCP → bound channel.
After an authorized write, read back that object. A qualified same-project
ai-memory binding may receive one derived entry; absence leaves refresh pending.
No background watcher is implied. Read an object before changing it again so UI
edits are preserved. Record IDs immediately after creation to avoid duplicate
objects when verification needs a retry.

Data: source/build files in the repo; canonical docs/tasks in that channel;
credential in a private project file; binding metadata in infra.
Completion: writes, content, task status and collection membership read back.
Failure: source write remains successful even if derived memory is unavailable.

## Scene 1B: daily local-model knowledge work

Goal: turn a short note into a tidy project document, retrieve one task, or mark
an explicitly requested task complete. Same tool/workflow pattern as 1A, different
model route. Codex CLI → OpenCodex → llama.cpp performs inference. Codex separately
calls direct Anytype MCP. A local model is not an MCP server or a code executor.

Start with one small non-thinking instruction model, a modest context window and
one concurrent request. Give it a small relevant tool menu. Let it propose the
correct object/operation; ensure actual scope and read-back outside the model.
Do not assume compatibility because plain chat works. Missing local capability
fails visibly; promotion to DeepSeek or native Codex is a deliberate choice.

Status: llama.cpp installed; model weights deliberately postponed. OpenCodex
health/auth verified; local-model tool use not yet qualified. This scene cannot
be declared ready from a catalog of advertised model names.

## Scene 2: explain a source impact

Goal: identify which callers and docs need changing before a substantial refactor.
Start with search. Select CodeGraph for symbols/callers in a qualified index;
select Graphify for broader code/document relationships. These are different
queries, not reasons to fan every prompt out to both engines. Basic Memory is a
secondary opt-in source for relevant existing Markdown decisions. OpenWiki remains
an optional documentation-generation experiment, not a required retrieval layer.

Flow: user → harness → one selected context tool → source inspection → Anytype
reviewed decision. Use native Codex for heavy code/refactor work. Index boundaries
must match the project; the existing narrow CodeGraph index is not this whole
repository. Missing results are not proof that code is absent.

Data: project-owned source and explicitly approved index/corpus; decision notes
in the project channel. Completion: relationship claim backed by current source,
not just a graph hit. Failure: fall back to ordinary search; no automatic broad
reindexing, mounts or imports. Gateway is optional only if a shared route is useful.

## Scene 3: repeatable report

Goal: weekly validation of a supplied CSV and a deterministic summary artifact.
Codex authors/tests the script. Windmill runs the reviewed script with fixed input
and scoped credentials, records run status and handles explicit retry/schedule
policy. Garage carries immutable input/output objects; Anytype stores the concise
result and an artifact link. WhoDB helps inspect approved business tables when a
project actually has a DB, not by granting access to every application database.

Flow: harness → reviewed script/version → Windmill manual trigger → worker →
project artifacts → harness read/verification → Anytype result.
Move a job to a schedule only when its manual execution and failure behavior work.
Workers execute code; the server owns queue/API state. Dependency environments
and temporary directories belong to jobs/workers. The current Windmill worker's
container boundary is not a strong sandbox for arbitrary hostile generated code.

Data: per-project workspace/resource handles and least-privilege object keys.
A bucket prefix is organization unless credentials enforce it. Shared Postgres
means separate app DB/logins; never repurpose Windmill/n8n's internal tables as a
project business schema. An additional project DB is provisioned only if needed.
Completion: native job succeeds, expected output is checked and cross-project
artifact access is denied. Missing workspace token/bucket binding means blocked,
even when Windmill's container exists.

## Scene 4: app-event intake

Goal: a file-upload event triggers the reviewed report once. n8n handles the app
connector, validates event fields and passes a minimal job envelope to Windmill.
Windmill owns code execution and run state. Return output location/run ID, not
the entire dataset, through the connector path. Anytype remains the project record.

Flow: authorized event source → n8n → reviewed Windmill flow → artifacts/run record
→ authorized delivery or harness checkpoint. No n8n Assistant/sandbox is needed.
Do not enable a schedule or send external messages as part of a design-paper task.

Envelope: project ID, input object ID, reviewed job version, event ID, idempotency
key and correlation ID. Reject mismatched projects before execution. Repeated event
must not duplicate the job/write. A failing output delivery must not repeat an
already completed expensive job. Keep statuses separate: received, running,
output-verified, delivered/documented.
Completion: one synthetic native event reaches one reviewed job exactly once,
with retry/error paths observed. Activepieces is excluded; it is not added here.

## Scene 5: concurrent research and paper investment analysis

Goal: compare fixed datasets or run several reviewed simulations, then retain a
reproducible research note. This is a paper-analysis design, not a live trading or
investment-advice deployment. Codex handles substantial code; a small local model
can label/summarize bounded results. DeepSeek is a separately qualified secondary
model route. Model selection cannot change the authority of the resulting code.

Use Windmill for fan-out/limits/retry and artifact provenance. Introduce a dedicated
business DB/login only when queryable results justify it. Introduce agentgateway
only when several callers need one qualified MCP route/auth policy; its currently
installed graph routes do not provide model translation or project isolation
for an unconfigured backend. OpenCodex remains the Codex model-protocol adapter.
Do not chain gateway → model proxy just to centralize a name.

Data: immutable input hash, script commit, model route/version, parameters,
artifact IDs and concise result. Namespace labels identify ownership; enforced
credentials/DB grants/workspace permissions must prove isolation separately.
Completion: repeatable results, cancellation, bounded concurrency, refusal across
project boundaries and reproducible provenance. Return to a simpler interactive
preset when concurrency is no longer needed; retain data and definitions.

## Suggested next exercise

After local model qualification, do one real daily task: read one Clock doc and
propose a short revision, then perform only the requested update and read-back.
After that, use the existing CSV report fixture as a manual Windmill acceptance
exercise. These are recommendations, not deployments performed by this paper.
