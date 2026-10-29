# Joint contracts

Each joint is one interface. A plugin fills it with any transport from the
manifest. `python` modules expose these functions; `jsonrpc-stdio` processes answer
`{"op": "<name>", "args": {...}}` with `{"ok": true, "result": ...}` or
`{"ok": false, "error": "..."}`, one JSON object per line. All data is JSON. Every
call carries `scope = {"project": <slug>, "task": <id|null>, "session": <id|null>}`,
and a plugin must not return data from another project's scope.

Status: **agent** runs through manifests, **board**/**link** are the existing
Anytype/Linear code, and **compress** has a Headroom adapter that passes its
contract kit (`tests/test_compress_contract.py`). The other joints are specified, with adapters pending.

## agent — a host that works on one task
| Op | In | Out |
|---|---|---|
| (argv) start | `{brief, cwd, notify}` filled into `command` | process exit; mstack runs `finish` |
| (handoff) launch spec | `{host, via, cwd, title, prompt}` | the orchestrator/owner starts it |
| (server) `start` | `{brief, cwd, title}` | `{session_id}` |
| (server) `status` | `{session_id}` | `{state: running|idle|done|failed}` |

Every host must: start in `cwd`, read the brief, see the task binding
(`MSTACK_TASK` or `.mstack/cache/current-task`), and report only through
`mstack board note` / `done`. Capability `notify`: it can mirror turns.

## board — the source of truth for tasks
`ensure_table(project)` → table handle (Anytype: a collection of the shared task type), `tasks(table)`, `get(task)`, `body(task)`,
`create(project, title, plan, agent, priority, labels)`, `set(task, **props)`,
`thread(task)`, `say(task, text, ask)`, `messages(task)` → `[{id, order, text, reactions}]`.
Required fields: Project, Task Status (the 7 states), Priority, Assigned Agent,
Source, Run Count. Capability `reactions`: without it, verdicts come only from replies.

## link — an external tracker mirrored into a table
`sync(board, project, table, link_settings)` → `{pulled, updated_in_anytype, pushed, updated_in_linear}`.
Settings carry `mode` (pull|push|full) and `scope` (mine|label). Match by external
identifier; the newer side wins on shared fields; agent fields never leave the board.

## memory.instant — working memory for one task or session
`put(scope, key, value, ttl_s)`, `get(scope, key)`, `recent(scope, n)`, `clear(scope)`.
Fast, small, expires. Example: the decisions a worker made so far in this task.

## memory.long — retrieval over a project corpus (RAG, graphs)
`index(scope, sources[])` → `{indexed, skipped}`, `query(scope, text, k)` →
`[{text, source, score}]`, `forget(scope, source)`. Indexing is explicit, never
automatic. Results always carry a `source`. An empty result does not mean the
answer is absent.

## compress — keep large outputs out of the context window (Headroom-like)
`compress(scope, text, budget_tokens)` → `{summary, handle, original_tokens}`,
`expand(scope, handle)` → original text. Handles expire, and foreign handles are rejected.

## gateway — routes and policies for MCP/LLM traffic
`routes(scope)` → endpoints a worker may use, `apply(scope, routes)` → plan/diff
(changing live routes needs owner approval), and `events(scope, since)` → turn
records `{at, direction, route, tool|model, tokens, task}` for the capture sink.

## docs — human-readable project documents
`list(scope)`, `read(scope, doc)`, `write(scope, doc, markdown)` → `{id, readback_hash}`.
Writes must be read back. Docs are data, never instructions.

## Conformance

`mstack plugin validate` checks manifests against the schema. A replacement
must also pass its joint's contract tests: the agent and board joints have them
in `integrations/orchestrator/tests`. Each new joint adapter brings its test kit.
