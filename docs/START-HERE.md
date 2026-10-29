# Start here — do the work

**[mstack commands and daily presets](MSTACK.md)** are the
current operating guide. Use `daily` by default: it selects shared Headroom,
Graphify, Anytype and Windmill, with the existing gstack browser available.
The [configuration diagrams](MSTACK-CONFIG.md) explain the one-field intent file.
Project grants still require onboarding; default selection never copies access.

Selected tools use [shared services with project tenants](../infra/services/README.md).
Graphify, Anytype MCP and Headroom each have one shared container; another project
gets its own index/channel/cache binding. CodeGraph is ignored for now.
WhoDB is available at Mac [localhost:58091](http://127.0.0.1:58091/). ai-memory
and agentgateway are optional; direct project MCP bindings work without them.

**Starting a fresh project? Copy the [three-channel prompt](FRESH-PROJECT-PROMPT.md#copyable-prompt).**
That single document also lists the existing tools as a reference shelf.

Updated 2026-10-21. The everyday workflow is **Codex or Claude + Anytype**, with
**Windmill for useful repeatable jobs**. This is the working default; the stack
does not need to finish every integration before a real project can begin.

Claude Desktop now uses [Magpie → official DeepSeek](../infra/magpie/README.md).
Codex keeps its existing route; its Magpie integration is pending your request.
OpenCodex and its dedicated data/setup have been [removed](../infra/maintenance/opencodex-retirement/README.md).

Keep Llama.app, PostgreSQL + pgvector, WhoDB, Garage,
and existing harness helpers as support. OrbStack and mise are protected system
tools. Keeping these does not require using them in every project. AI mail
integrations were removed and must not be resumed.

## Three roles

| Role | Tool | Everyday use |
| --- | --- | --- |
| Work with an assistant | Codex or Claude | Pick one for the task; give it an outcome and the relevant context. |
| Keep durable context | Anytype | Keep a short personal working note, project briefs, and useful decisions/results. |
| Run repeatable work | Windmill | Move a proven task here when repetition or a schedule makes automation worthwhile. |

These are separate roles, not three steps every request must pass through.
Code and executable scripts stay in their project files. Anytype can link to
them; it does not need another copy of the codebase or every conversation.

## A work session

1. Open the actual project in Codex or Claude. State one concrete outcome.
2. Provide your short personal note and the relevant project brief, if useful.
   Read them through a qualified Anytype connection when available; otherwise
   paste the relevant text. Connector setup need not block the task.
3. Do the work and check the result.
4. Save only useful decisions, results, and the next action in the project note.
5. When a task repeats, consider a Windmill job with clear inputs, outputs, and
   a way to see failures. Verify one manual run before scheduling it.

## Personal context: one short note

Keep one canonical Anytype note, **How to work with me**. Start with a few stable
preferences and constraints, not a complete autobiography. For example:

> I use Codex and Claude for interactive work, Anytype for durable notes, and
> Windmill for repeatable automation. Prefer the smallest workflow that completes
> the task. Start with the tools already available. Add infrastructure when a
> concrete task needs it. Help me finish work before expanding the stack.

Add personal goals or preferences yourself as they become relevant. Keep
project-specific details in the project brief. Update the personal note when
your preferences change; do not automatically infer a profile from all chats.

At project start, explicitly supply this note to the chosen harness. Until a
verified read path exists, a manual copy is enough. This provides shared context
without a separate memory database, embeddings, sync service, or background
capture. It does not claim either harness automatically remembers across chats.

## What counts as ready

A project is ready to start when you can give a harness a real task, provide the
needed context, and save/check the result. Windmill readiness is assessed for
the specific job when needed. A complete MCP catalog is not a readiness gate.

Agentgateway, extra memory services and unfinished integrations are outside the
everyday checklist. Graphify is available in the default routing; a graph lookup
is still not a prerequisite for every task. Revisit an extra component only for a
concrete need in current work. Cleaning up installations is a separate task.

## Connection status and maintenance

The Compose group is `mstack`. At the October 21 migration check, its services
were stopped; the unrelated `yel453-stage8-postgres` container was running.
No container state changed in the Magpie migration. OpenCodex was later removed
on request; all 31 other containers present at removal stayed unchanged. Example projects and their local bindings are retired; see the
[cleanup record](../infra/maintenance/config-retirement/README.md).
New projects use one editable intent and one generated state file.
Native project trust still applies to harness adapters; Claude sessions require
separate qualification.
See [namespace evidence](MSTACK-NAMESPACE.md).

Use [HANDOVER.md](HANDOVER.md) for dated evidence or a specific maintenance task,
and the [Windmill runbook](WINDMILL-RUNBOOK.md) when working on a real job.
Historical setup checkpoints are references, not a queue to resume automatically.
