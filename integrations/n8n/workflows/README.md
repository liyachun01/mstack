# task-start-router: one import, one manual run

Approved by the user on **2026-10-04**. Source and in-memory qualification are
complete for official n8n **2.41.6**; import/saved-editor execution is **not
complete**. The user's n8n tab exists in macOS Edge, but JavaScript automation via
Apple Events is disabled. No browser security setting, login, cookie or password
was changed/read/copied to work around that boundary. No new browser tooling
installed. The bounded manual handoff below completes the UI part of this same
approved task, not another infrastructure step.

```text
Manual start → Task input (4 synthetic tasks) → Split tasks → Route preview
```

Only installed built-in nodes: Manual Trigger v1, Edit Fields v3.5 and Split Out
v1. No Code runner, AI/model, HTTP/MCP request, provider credential, database node,
webhook, schedule, filesystem or subprocess. One workflow, inactive/unpublished.

## Complete the approved UI action

1. In your logged-in [n8n UI](http://127.0.0.1:5678/), check for an existing workflow
   named **mcp-stack · task-start-router · DRY RUN v1** to avoid duplicates. For a
   new workflow, choose **… → Import from File**. In the macOS chooser press
   **Cmd+Shift+G** and paste:

   ```text
   /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack/integrations/n8n/workflows/task-start-router.json
   ```

   Ubuntu source:
   `/home/developer/workspace/mstack/integrations/n8n/workflows/task-start-router.json`.

2. Confirm the four nodes above and keep the workflow unpublished/inactive.
   Save it. Check settings: Asia/Shanghai, timeout 60 seconds, no saved
   success/error/manual execution payloads or execution progress. The JSON
   requests these settings; UI import retention/publication still needs your
   confirmation. No paid license or API key needed.
3. Click **Execute Workflow** once, then **Route preview → Output → JSON**.
   Expect four items, in order:

   | Item | Expected status | Proposed candidates | Deferred |
   | --- | --- | --- | --- |
   | Coding + broader relationships | preview | CodeGraph + relevance-checked Graphify | none |
   | Documentation, no implementation question | preview | relevance-checked Graphify | Basic Memory |
   | Personal/PKM | preview | none; never CodeGraph | Graphify corpus + Basic Memory connection |
   | `dry_run=false` | rejected | none | none |

   Every item must show `actions_executed: []` and `approval_granted: false`.
   The last rejection is intentional; a green node is not authorization.
   No need to edit/reset inputs or execute four separate runs.

**Stopping point:** keep this workflow unpublished. There are no automatic
subsequent jobs, installations, imports or permission requests. The remaining
stack integrations are a deferred backlog, not instructions to continue setup.

Rollback for this same new workflow only: discard an unsaved draft, or archive/
remove the saved copy through the UI if you choose. Do not restart services,
delete volumes or issue SQL commands. The agent has not performed removal.

Official [import instructions](https://docs.n8n.io/build/manage-workflows/export-and-import.md).
The approved runtime impact is only one saved workflow definition in n8n's own
database and transient editor data; no changes to ports, networks, service
configuration, keys, other workflows or {{mstack:CLIENT_REPO}}.

## Use it after the synthetic check

In **Task input**, keep JSON Output **Fixed** and `tasks` as an array. For an
ordinary task preview keep just one input object, replace its synthetic task/
session IDs and task description, and select an explicit profile. Execute once
and review the resulting plan, then work in your existing harness normally.
There is no automatic harness-message interception or agent launcher.

Exact profile values: `coding`, `documentation-research`, `pkm-personal`.
Harness labels: `codex-ide`, `deepseek-harness`; neither starts a harness.
Only `mcp-stack`, its approved Ubuntu repository/domain, and
`index_scope="approved-three-file-projection"` are accepted. A profile/session
ID is not authentication or gateway enforcement. Both indexes are partial
source projections; Graphify requires corpus relevance, and missing graph
results never prove missing source. No personal-document corpus is qualified.

Keep `dry_run` boolean `true`, not string `"true"`.
`implementation_question`, `broader_relationships` and `durable_decisions`
are explicit booleans, not model guesses. `memory_writes="explicit-confirmation"`
and `pkm_sync="off"` are required input intent; output always disables writes
and sync. Basic Memory usage stays deferred. No semantic models downloaded.

Unknown fields/task text/native harness IDs are not echoed in output plans, but
input/browser data can still be visible. This is not DLP. Never enter secrets.
Discard or correct a `status="rejected"` envelope; do not treat it as a tool plan.

## Evidence and source maintenance

Readable pure source: `router.expression.js`, embedded verbatim in the portable
JSON. Tests reject source drift. Runtime config/launch settings remain under
`infra/`; credentials remain in their protected existing locations.

Completed: **25 repository tests**, **90 synthetic policy cases**, and the **4
one-click examples** locally and against the installed n8n VM expression engine,
actual Edit Fields v3.5 and actual Split Out v1 implementations. Installed-node
checks use an ephemeral in-memory context, not a saved workflow or n8n API, and
read no credentials. No import/persistence/editor acceptance claimed.

```sh
python3 -m unittest discover -s integrations/n8n/tests -v
python3 integrations/n8n/tests/test_task_router.py --installed-n8n
```

Existing tools only, no installs. Wrapper accounts for macctl slash-prefix
translation, Node argument parsing and VM-isolate acquisition; no application
patches. Full harness/gateway/memory/PKM integration is not implied by this
dry-run workflow and is not a prerequisite for the manual exercise.
