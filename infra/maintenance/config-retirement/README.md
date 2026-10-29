# Config and example retirement — 2026-10-16

User request: retire the old configuration and remove example projects.

## Configuration completed

`.mstack/stack.json` is the only editable project intent. Generated bindings,
tenants, document IDs, runtime details, gateway launch settings and proof receipts
now share `.mstack/state.json`. Project credentials belong in `.mstack/secrets/`.

The root legacy registry, separate bindings/runtime files and obsolete intent
rollback copy are removed. Runtime readers no longer consume legacy project
filenames. Anytype writes update observed IDs without editing intent. Credential
rotation invalidates qualification. Direct apply does not consult/start the gateway.
Reusable MCP/Windmill/discovery helpers moved out of the example directory.

See [configuration reference](../../../docs/MSTACK-CONFIG.md).

## Example removal completed

- External `/home/developer/workspace/mstack-example`, including its discovery,
  harness configuration, source and local credentials, is removed.
- In-repository project-a, project-b and portfolio-demo are removed.
- The three shared Graphify/Anytype/Headroom tenants, their data and dedicated
  example migration copies are removed. Shared tenant registries are empty.
- The mstack-example Anytype channel and its four documents were deleted through
  the native app during the authorized quiet window. Its revoked API key returns
  HTTP 401. Other channels/keys were left unchanged.
- Gateway A/B routes and caller keys are removed from the retained stopped
  gateway configuration. The nonexistent Clock path was removed from the index;
  unrelated Clock/kase grants were preserved.
- Demo-only acceptance helpers and stale onboarding recipes are retired. Unit
  tests use isolated synthetic fixtures and do not provision example projects.

## Windmill cleanup completed

The user explicitly approved using the documented initial administrator login,
with cleanup restricted to example data and all containers preserved. The
`mstack-example` workspace and its two matched restricted tokens are deleted.
Other workspace IDs were verified unchanged. Read-only follow-up confirmed the
workspace and tokens are absent. Logout verification returned 200 twice, then
401 after a short wait. The verification session token stayed in memory.

The two temporary project token files are removed. No administrator password
reset, shared database reset or container lifecycle operation occurred. Earlier
automatic-review rejections are resolved by explicit approval and in-memory
verification; there is no pending permission or cleanup item.
See [Windmill verification](windmill.json).

## Follow-up: project folder consolidated

The user moved project metadata out of infra. The current layout is
`.mstack/stack.json`, `.mstack/state.json`, `.mstack/secrets/`, optional
`.mstack/anytype/openapi.json`, `.mstack/evidence/` and `.mstack/cache/`.
`.mstack/.gitignore` protects generated/private files while leaving intent trackable.
The intermediate `infra/stack.json` and `infra/.mstack/` paths are retired;
current readers and new-project initialization use only the new layout.
Shared infrastructure definitions and credentials retain their existing paths.

## Verification

83 Python tests pass after the layout migration; five container Node adapter tests
passed during the preceding retirement step. Coverage includes
state concurrency/identity, no legacy fallback, readback retry without duplicate
creation, connection rotation, source-bound proofs, tenant isolation, gateway
preservation, and reviewed Windmill script execution with mocked API calls.
Root plan/doctor/discovery and Codex invocation inspection pass without inference.

All 30 containers retain their IDs, start times, image IDs, mounts, Docker config,
restart counts and running/stopped status. Nine mstack services remain running;
ai-memory and agentgateway remain stopped. No shared service restart, database
reset, model/provider call, new index, schedule or global harness config change.

Evidence: [local removal](local.json), [external removal](external-project.json),
[Anytype revocation](anytype.json), [container comparison](containers.json), and
[current layout verification](layout.json), [checks](checks.json).
Historical qualification receipts elsewhere remain dated
records; they do not imply a runnable demo still exists. Maintenance scripts in
this directory are one-shot evidence helpers, not startup commands.
