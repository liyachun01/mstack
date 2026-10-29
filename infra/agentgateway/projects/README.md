# Project connections

Current status and flows are in [the canonical handover](../../../docs/HANDOVER.md).
The persistent v1.5.0 gateway belongs to **mstack**, not a separate app namespace.
The MCP listener is macOS `127.0.0.1:58080`. No model traffic runs through it.

## Unified input source (2026-10-08)

**Edit project `.mstack/stack.json` and shared [connections.json](../../stack/connections.json).**
`../projects.json` is now generated from those files; strategy is not edited there.
`stack plan/apply --project <directory>` is the normal reconciliation path.
The A/B placeholders, their routes and caller keys are retired. The optional
gateway is retained stopped; the owner UI password remains unchanged. Direct
daily projects do not require this gateway.
Read [the full config contract](../../stack/README.md) for secret references,
per-project URL overrides, no-op behavior, owner UI drift and recovery.
The compiled-field tables below explain the gateway view, not a second input source.

## Web UI and typed configuration

Open `http://127.0.0.1:58084/ui` **directly in the Mac address bar**.
Codex Command-click was observed rewriting it to `localhost:62966`, which does
not reach the native Mac gateway. Bypass that forwarding with:

```sh
macctl run open http://127.0.0.1:58084/ui
```

Username **owner**; the existing password is unchanged in ignored
`.secrets/agentgateway/ui-password` (0600), separate from project caller keys. The user superseded the earlier unrequested read-only
setting. **Native UI configuration editing is enabled**; save returns 200 and
updates the active runtime. No gateway database/log analytics was added. The UI
does not edit `projects.json` or automatically log in to each provider.

The UI uses strict Basic authentication on Mac loopback and forwards `/ui`,
`/api` and the root redirect to the native application. Raw admin/debug/shutdown
listeners remain unpublished. Its bcrypt hash is bound by file; the plaintext
password never enters gateway config. File-reference authentication avoids the
loader's `$2b` environment expansion problem.

The active file is `infra/agentgateway/state/projects/runtime/config.yaml`.
A writable directory mount allows native atomic saves and persists across
recreation. Non-root UID 65532 receives supplementary group 501 for this directory
(0770; active file 0660), while the root filesystem stays read-only.
Project registry and bindings remain separate intent/evidence. UI changes are
runtime edits, not automatically synchronized into those files.

Project/catalog/UI files carry local `$schema` links; the compatibility view remains documented:

| Editable file | Contract | Purpose |
| --- | --- | --- |
| `../projects.json` | [projects.schema.json](../../../integrations/gateway/schemas/projects.schema.json) | Generated project/account/scope view; edit stack config/catalog |
| `../projects.bindings.json` | [bindings.schema.json](../../../integrations/gateway/schemas/bindings.schema.json) | Accepted live tool/scope/access evidence |
| [ui.json](ui.json) | [ui.schema.json](../../../integrations/gateway/schemas/ui.schema.json) | Owner UI settings and password reference |

This is **typed configuration through JSON Schema 2020-12**. It documents field
types, defaults and meanings, rejects unknown keys and wildcards, and validates
before plan/render. The existing Ubuntu `jsonschema 4.19.2` and `bcrypt` libraries
were reused; no package manager/global settings changed. `validate` does not read
provider secret contents, create keys, log in, or prove a connection is ready.

```sh
./stack connections validate
./stack connections plan --project <registered-project>
```

[VS Code's JSON support](https://code.visualstudio.com/docs/languages/json)
provides schema-based suggestions, hovers and error markers without new global
settings. Plain JSON is the current CLI input; the schema can also describe a
parsed YAML document, but YAML loading has not been added. Schema defaults explain
omitted fields; they do not populate credentials or grant access.

| Option | Recommendation for this repo |
| --- | --- |
| JSON + JSON Schema | Use now: one documented contract for editor and CLI; no new config runtime |
| [Pydantic](https://pydantic.dev/docs/validation/latest/concepts/json_schema/) | Consider if the CLI becomes a larger Python application needing typed objects; can generate a schema, but avoid maintaining two independent contracts |
| [CUE](https://cuelang.org/docs/introduction/) | Consider for complex configuration composition; adds another language/toolchain, unnecessary for two personal projects |

## Project input reference

| Field | Meaning |
| --- | --- |
| `projects.<slug>.input.repo` | Real repo path, blank until known; not an authentication claim |
| `input.display_name`, `input.description` | Human-facing project name/goal |
| `harnesses` | `codex` and/or `claude`; renderer issues distinct keys only for selected callers |
| `tool_transport` | `agentgateway` for these shared connectors; no model-provider change |
| `tools.<tool>.connection` | Named account reference, reusable by another project |
| `tools.<tool>.enabled` | Disable this project's tool without removing its source/credential |
| `tools.<tool>.access` | `read-only` default or explicit `read-write`; live binding must qualify the same mode |
| `tools.<tool>.purpose` | Tool-use guidance for the harness, not an enforced permission |
| `tools.<tool>.space` | Empty object inherits; nonempty replaces the complete provider-specific scope |
| `connections.<name>.input.auth_type` | Selected OAuth/API-key method; no automatic OAuth broker |
| `input.credential_file` | Private provider credential reference under `.secrets/`, not a literal key |
| `input.oauth_client_id`, `oauth_client_secret_file`, `oauth_scopes` | Optional registered OAuth app inputs/desired permissions, all blank initially |
| Anytype `input.api_url` | Intended local API URL, blank until its transport is qualified |

Changing account, scope or requested access invalidates the binding fingerprint.
Disabling a tool blocks it even with qualified evidence. Duplicate enabled Anytype
Space IDs across projects are rejected; docs/tasks collections are organizational
boundaries within the separately authorized Space. Existing caller keys are reused,
not rotated during a schema/UI update.

## Fill one connection at a time

Edit project `.mstack/stack.json` and shared [connections.json](../../stack/connections.json).
`project-a` and `project-b` are placeholders,
not discovered repositories. Use real project configs and stable identities when known; set `input.repo` there.
The gateway does not trust a repo path sent by a caller: it authenticates the key.
Changing an indexed identity is rejected; initialize/register the new project and
retire old identities explicitly without deleting unrelated credentials.

| Tool | Shared connection `input` | Connection `space` |
| --- | --- | --- |
| Slack | Workspace ID; ignored credential file reference | Allowed channel IDs |
| Linear | Workspace ID; ignored credential file reference | Allowed team and project IDs |
| Figma | Account label; ignored credential file reference | Allowed file keys |
| Notion (optional) | Workspace ID; ignored credential file reference | Allowed page/data-source IDs |
| Anytype (separate per project) | Ignored project credential file reference | Space ID; docs/tasks collection IDs |

Both projects initially reference `slack-shared`, `linear-shared`, `figma-shared`:
fill their common scopes once. A project's nonempty `tools.<tool>.space` replaces
that shared default if the projects later separate. Empty override means inherit;
empty inherited defaults mean **disconnected**, never “all resources.”
Notion is a blank optional connector, not a replacement for Anytype or a sync job.

Anytype: make each project's own Space/channel and docs/tasks collections when its
name is known. No remote objects have been created in this task. A collection is
an organizational boundary; require a Space-only credential or verified scoped
adapter for access isolation. Never copy Clock's credential into another project.

```sh
./stack connections plan --project <registered-project>
./stack connections render
```

Plan is read-only. Render is local only: it reuses or generates four private caller
keys and writes a hash-only candidate at `state/projects/config.json`. Existing
UI edits are preserved in `state/projects/runtime/config.yaml`. On first render
only, an absent runtime is seeded. Render neither opens OAuth nor activates a
connection just because the input fields have values. Secrets stay in ignored
`.secrets/agentgateway/projects/<project>/{codex,claude}-token`, mode 0600. Provider
tokens are different secrets, stored through the named connection's private binding.
Never paste tokens into the JSON intent file or chat.

## Activation boundary

[projects.bindings.json](../projects.bindings.json) starts with every tool pending.
An active binding requires `status: qualified`, the exact `scope_fingerprint` from
plan, matching `access`, `mcp_url`, explicit unprefixed `tools`, `scope_enforcement`
and `evidence_file`.
Scope enforcement is either `upstream-credential` (a provider grant actually limited
to those resources) or `scoped-adapter` (checks every call before accessing data).
A credential-backed direct target also needs a `/run/secrets/<name>` backend key
mount in a targeted Compose overlay; renderer never forwards the caller's key.
An adapter must hold its provider credentials and have qualified gateway-only access.

Evidence records project/tool/fingerprint and successful allowed read,
out-of-scope denial and no unauthorized data access/dispatch. These are trusted
operator records, not a cryptographic proof or an automated OAuth/scope validator.
Scope changes invalidate evidence. Verify the actual tool schemas and provider
authorization before marking qualified; do not enable global search, arbitrary
IDs/URLs, or free-form queries with broad account credentials.

Pinned gateway `mcpAuthorization` filters tool names/targets and resources/prompts;
its resource RBAC context does not provide the call's arbitrary argument map.
Thus a tool-name allowlist cannot enforce Slack channel or Linear issue ownership
by itself. Provider-specific restrictions or a scoped adapter are still necessary.
No provider adapter or refresh-token broker was installed in this task.

Official endpoint references (templates only, no OAuth performed):
[Slack](https://docs.slack.dev/ai/slack-mcp-server/),
[Linear](https://linear.app/docs/mcp),
[Figma](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/),
[Notion](https://developers.notion.com/guides/mcp/get-started-with-mcp).
Their OAuth/account access is not automatically project isolation.
Pinned policy source:
[agentgateway v1.5.0 RBAC](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/rbac.rs).

## Runtime and clients

For a reviewed project/catalog/binding change, use the unified path:

```sh
./stack plan --project examples/project-a
./stack apply --project examples/project-a
```

The following lower-level compatibility sequence also exists; normal strategy
changes no longer need separate registry edits or manual recreation:

```sh
./stack connections validate
./stack connections render
./stack connections apply
macctl run docker compose -p mcp-stack --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack -f infra/agentgateway/compose.yaml -f infra/agentgateway/projects/compose.yaml up -d --no-deps --pull never --force-recreate agentgateway
```

`apply` copies the last rendered candidate to the active file; before replacement,
it stores the previous file as `runtime/config.before-<sha256>.yaml` (0600).
It starts no services. Review UI edits before replacing them. Rendering alone
preserves active edits; recreation alone uses the current active file. UI saves
reload automatically and survive recreation. Runtime may be YAML after UI saves;
do not assume it remains JSON.

Operate this exact service only. Never use broad `down`, `--remove-orphans`, or
shared-volume deletion. Base + projects overlay mounts the owner runtime
**directory**, candidate and hashed UI login, not historical graph data/keys.
Those old definitions/state are preserved and their containers were absent on
discovery. Rollback: stop only agentgateway, retain all keys/config. To restore
one runtime backup, copy that exact reviewed private backup over the active file
and recreate only agentgateway. To disable only the UI, set `ui.json` `enabled`
false, validate/render/apply and recreate only this service; keep its password.

The bounded owner save/persistence probe adds then removes one no-backend route;
**do not run it concurrently with owner edits**:

```sh
macctl run python3 /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/integrations/gateway/verify_ui.py --restart
```

Clients use `/mcp/projects/<slug>` with that project's caller key. In parallel,
Codex A uses A/codex and Claude B uses B/claude. Give each session only its selected
project credentials. If an app has both projects enabled, that app can use both
authorized connections; a chat title does not change its access. No global Codex
configuration or Claude Desktop MCP menu was changed by this task. A client in
Ubuntu cannot assume its own loopback reaches the Mac listener; qualify a scoped
transport before registering it. Native clients use the Mac loopback directly.

## Verification

[qualification.json](qualification.json) distinguishes the live pending gateway
checks from synthetic scope checks. Both projects completed five reads concurrently;
wrong route keys, session replay, hidden tools and foreign channel data reads were
denied. Real Slack/Linear/Figma/Notion/Anytype calls: **zero**.

Historical October 8 evidence: the synthetic fixture reused the then-installed pinned OpenCodex image solely
as a Bun runtime with its app entrypoint replaced and no proxy secrets/state mounts.
Test containers/network/config were removed. Persistent OpenCodex was untouched.
An initial test publication on 58081 closed connections despite internal reachability;
changing only the disposable test port to 58083 resolved it. The production port
58080 passed without a network/IPv6/security workaround. A fixture URL initially
omitted port 8000; corrected before the successful test. Failures are not counted
as authorization successes.

The A/B live fixture and its project credentials are retired. Its old
`test.compose.yaml`, which depended on the removed OpenCodex image, is now deleted. Do not replay the
historical container probes against deleted examples. Current local regression
checks use isolated test fixtures:

```sh
python3 -m unittest discover -s integrations/gateway/tests -v
```

They do not require live projects, provider credentials or service lifecycle actions.
