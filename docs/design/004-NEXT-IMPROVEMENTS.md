# What to improve next

Design paper · 2026-10-07 · Recommendations, not automatic deployments.

The next useful work is to prove the daily path and reduce repeated setup. Adding
another model manager/harness before that test would increase operating work.

| Priority | Improvement | Why | Acceptance |
| --- | --- | --- | --- |
| 1 | Qualify one small local model | Daily tasks become usable with low marginal inference cost | Valid tool arguments, tool result loop, failure/cancellation, actual Anytype read/write/read-back |
| 2 | Narrow Anytype binding wizard | Eliminate manual IDs/key wiring for each project | Creates or selects authorized channel, verifies grant/membership, refuses other-project access |
| 3 | Changed-object memory adapter | Complete the requested follow-up without broad synchronization | Stable Space/object identity, bounded summary, provenance/hash, pending retry after failure |
| 4 | Backup and isolated restore exercise | Docs are now real durable data | Native protected backup and restore verification; exports do not preserve every identity/chat link |
| 5 | One manual native Windmill CSV workflow | Prove that a selected engine actually runs the intended job | Correct artifact, workspace/bucket scope, retry/idempotency and failure path |
| 6 | Small task/run ledger | Make failures visible across tools without a logging platform | Correlation ID, project/tool/model route, run status and artifact/object references; no secrets/full prompts |
| 7 | Upgrade qualification | Keep compatibility without surprise global changes | Pinned version, rollback target, repeat model/MCP acceptance, retain data |

For memory, start with the already installed ai-memory candidate only after its
project namespace/auth semantics are qualified. Its project label is not tenant
RBAC. Do not add another vector database/embedding provider just to remember one
changed doc. Keep Basic Memory secondary and graph engines contextual.

For code execution, use local project commands for immediate development. Promote
reviewed repeatable work to Windmill. If a future workflow executes untrusted model
code, qualify a separate disposable sandbox for that case; the current worker's
container is not the requested security guarantee by itself.

For models, keep native Codex for heavy code, a small local route for daily tasks,
and DeepSeek as explicit escalation once tested through OpenCodex. Cost visibility
and refusal to silently fall back matter more than automatic model routing now.

For packaging, one `stack` entry point across the actual execution domains is the
current target. Keep llama.cpp native for Metal and Anytype native for its existing
identity. Do not force them into a Linux bundle just to obtain one container name.
Only consider a larger control UI after the CLI/prompt workflow repeatedly proves
what information you need to inspect.

The stack-use improvement loop is: observe a concrete workflow failure → record
what happened → fix the narrow helper/preset/skill → verify with the same task →
update the same handover. Do not grow universal policy from a hypothetical failure.
