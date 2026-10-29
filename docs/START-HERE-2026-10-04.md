# Start here — no setup chain

> Retired2026-10-05: the Windmill trial containers, all three volumes, network
> and runtime credentials were deleted after successful shared-PG replacement.
> This is historical evidence; trial lifecycle commands no longer apply.
> Use [the current Windmill runbook](WINDMILL-RUNBOOK.md).

2026-10-04. Existing services stay running. **No more automatic installations or
“approve the next component” prompts.** Future integrations remain deferred;
you decide if/when to reopen them. This page is the everyday entry point; the
longer operations runbook is reference, not a mandatory checklist to install.

## Finish the one approved workflow

n8n is healthy at [http://127.0.0.1:5678/](http://127.0.0.1:5678/) on macOS.
Owner login is user-reported. The agent found your Edge n8n tab but cannot import
or execute it: Edge's Apple Events JavaScript automation is disabled. No browser
permission/security settings, credentials or cookies were changed to bypass it.

In your existing logged-in UI:

1. New workflow → **… → Import from File**, using the existing file below.
2. Save, keep unpublished/inactive, verify execution saving is disabled.
3. **Execute Workflow** → **Route preview → Output → JSON**: four results,
   three previews and one intentional rejection. Every result executes no action.

Mac file chooser (**Cmd+Shift+G**):

```text
/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/integrations/n8n/workflows/task-start-router.json
```

No extra installation, API key, paid license, Code runner or new approval needed
for this already-approved manual import/test. Check for an existing copy first.
The [bounded workflow guide](../integrations/n8n/workflows/README.md) contains
expected results, settings, reuse instructions and rollback. Source/installed
node tests passed; actual saved/editor import is not claimed complete.

## Work normally

- Open the actual project in your existing Codex or DeepSeek harness. No new
  harness installation or job launch is part of this task.
- In n8n's Task input, replace the demo tasks array with one explicit task,
  project/session IDs and profile. Execute and review a **plan**, not tool calls.
- Continue normal source inspection in the harness. No n8n interception of every
  message, automatic three-tool retrieval, indexing, memory saves or PKM sync.
- Keep passwords in your password manager. Existing machine secrets stay
  untouched; the [inventory/recovery proposal](SECRETS-INVENTORY.md) is reference,
  not an instruction to rotate/export/remove anything now.

## What is deliberately not connected

The router is a **dry-run planning exercise**, not the full automated stack.
No n8n gateway/tool/model execution, Codex stack registration, Basic Memory
harness connection or PKM synchronization is qualified by it. Installed graph
indexes cover only narrow projections. The external Code runner, embeddings,
Notion/AppFlowy, backups/migrations and generalized OrbStack skill stay deferred;
none is required to complete this exercise. No services are shut down or removed.

There is no implicit next setup step. Stop after the manual preview and use the
current setup; reopen a specific deferred item only if you ask for it.

## Optional Windmill trial — installed at your request

2026-10-05: [Windmill](http://127.0.0.1:58090/) is running on macOS OrbStack:
official CE1.823.1, its own PG18.6 and one non-privileged worker. Existing n8n,
stack PostgreSQL, {{mstack:CLIENT_REPO}} and other containers are unchanged. UI/process checks
passed; no owner login, scripts or harness/memory connections were performed.

Use the [trial runbook](WINDMILL-TRIAL-RUNBOOK.md) for first login, status and
scoped start/stop commands. Trusted personal scripts only: per-job isolation is
disabled. There is no automatic next integration or service installation.
