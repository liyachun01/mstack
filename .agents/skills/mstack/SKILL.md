---
name: mstack
description: Use mstack project presets to coordinate existing harness tools, gstack work skills, scoped graph context and Anytype project documents; verify integration exercises with real-use receipts.
---

# mstack

Read this project's `.mstack/stack.json` (editable intent) and
`.mstack/state.json` (generated bindings, tenants, document IDs, runtime and
proof records). The separate legacy configuration files are retired; do not read
or recreate them. Run the repository-local `mstack plan --project <path>` to
resolve choices and `doctor` for local readiness. Neither makes a live call.
The old `stack` command remains an alias. Project credentials belong in
`.mstack/secrets/`; do not move shared infrastructure settings or credentials.

Use `daily` by default: shared Headroom, Graphify, Anytype and Windmill, with the
existing gstack browser available. The intent can be just {"project":"my-project"}.
Use `solo`, `build`, `notes` or `automate` only for an intentional smaller selection.
Project grants still require explicit onboarding; never copy another project's
credentials. `proof` remains an equivalent full-workflow preset. Neither daily
nor proof requires every tool to be called for each task. Compose namespace is
`mstack`; stable container names and tenant identities remain unchanged.
See docs/MSTACK-CONFIG.md for the detailed configuration and routing diagrams.
Keep the existing harness/provider. `run` configures a separate Codex invocation;
it does not change this chat or configure Claude Desktop.

The harness coordinates the tools. For `workflow.gstack`, read the selected
installed gstack skill, then perform its actual task. Use existing executables
from `infra/stack/helpers.json`; do not run installers/updaters as setup checks.
Keep temporary browser state in the selected project's ignored `.mstack/cache/`,
without changing another project's browser or global preferences.

When Headroom is selected, prefer this project's explicit shared binding over an
inherited duplicate helper. `mstack-headroom` has a separate authenticated SQLite
cache/statistics per tenant, with one-hour original retention across reconnects
and service restarts. Existing global helpers stay available to other projects.
Compress a useful tool result and retain the returned
retrieval hash. Retrieve and compare the original for an integration proof.
Headroom does not compact the harness's entire conversation automatically.

Reuse actual harness-provided capabilities. Missing selected capabilities use a
shared containerized backend with a project tenant. A skill is not an engine.
Graphify runs in `mstack-graphify`; each project has its own authenticated session
and index. Anytype uses `mstack-anytype-mcp` with a separate channel-only key per
tenant. Do not create a tool container per project. Use `infra/services/README.md`
for registration and lifecycle. Stopping a shared service affects every tenant;
registration does not start services, index source or qualify harness bindings.
Ignore CodeGraph for now. Answer a concrete source question through MCP;
discovery alone is insufficient. No broad indexing or model call follows from
selection.

Anytype requires an explicit project channel and private scoped grant. Read before
updating, write only authorized project content, then read it back. Do not inherit
Clock/kase credentials, mirror to another memory store, or call a source write
successful from a local file. Use the computer-use skill for authorized native
channel/key setup when needed; global MCP registration is outside this workflow.

For an explicit proof exercise, save bounded outputs in project `.mstack/evidence/`
and receipts via `integrations/stack/proof.py`. `mstack proof --project <path>`
checks all selected steps against current source/configuration and artifact hashes.
Receipts are operator-recorded evidence, not cryptographic attestation. Report
missing or failed stages honestly and continue independent work.

Runtime changes follow the repository setup guard using existing task authorization.
Retain system tools, services and data. AI mail integrations remain removed.

The user actively uses the Mac. Use APIs, containers and isolated headless browser
sessions. Do not activate native apps, send desktop input, move windows or alter
display sleep without an explicit quiet setup window. Ordinary document work
uses background MCP/API. Do not bypass a rejected UI action.

Windmill proof means a reviewed script actually ran and its result was read back;
prefer its native MCP and a workspace/script-restricted token. No schedule follows.
The examples are retired. Do not recreate them, their grants, or their state as
startup. Use real projects with explicit grants. Project MCP settings remain
subject to harness trust; the launcher does not edit global configuration or
hot-reload existing chats.
