# Approval B — connect the running Graphify backend to agentgateway

Status (2026-10-01): **approved with “Approve”; completed with a documented malformed-URI limitation**. [Persistent Graphify
backend A](GRAPHIFY-GATEWAY-CONNECTION-PROPOSAL.md) is completed and running. This
step updates only the existing gateway component on the macOS OrbStack Docker
engine. It does not install another gateway/container, harness or memory service.

## Completion report

- Created four approved files under `infra/agentgateway/graphify/`; extended
  `infra/graphify/http/verify.py` with the explicit `--gateway-connected` mode.
  Python syntax, exact route/overlay, pinned-release JSON schema and merged
  Compose checks passed. Base gateway and Graphify wrappers/Compose definitions
  were not edited.
- Reused the existing official 1.5.0 ARM64 image without pull/build/package/model
  installation. Created ignored `state/graphify/config.json` (hash-only, 0644)
  and a backend-token copy `backend.key` (macOS 501:501, 0640), within state 0700.
  Original client/backend keys remain distinct and unchanged at 0600.
- Current gateway still runs UID/GID 65532:65532 with supplementary group 501,
  exactly two read-only file binds and the original privilege/resource/log/tmpfs
  limits. It alone joins both the original normal gateway bridge and existing
  internal Graphify network. Graphify remains internal-only with no host port.
- Actual macOS loopback endpoint is `http://127.0.0.1:58080/mcp/graphify`, mandatory
  gateway client Bearer key. Bare `/mcp` still returns 503, authenticated `/healthz`
  200, admin/UI/API remain disabled. Foundation verifier passed.
- Backend-key file/header integration passed real initialization and useful calls
  to all seven prefixed tools on the retained 37-node/48-edge graph. Missing/wrong
  client key, backend-as-client key and client-as-backend key are rejected.
- Resource discovery is empty. Prompt/template discovery returns explicit MCP
  unsupported-method `-32601`, not a successful prompt/resource surface.
  All three prefixed PR tools, unprefixed/unknown tools, properly prefixed resource
  reads and prompt gets return HTTP 400; foreign project arguments return the
  unchanged server gate's `isError` result. These strict authorization tests never
  accept 5xx as a denial.
- Three independently initialized sessions had distinct IDs; reconnect, genuine
  parallel reads, unknown-session rejection and cross-route replay to the bare
  `/mcp` 503 placeholder passed. This is not multi-harness/profile integration.
- The direct Graphify verifier in connected mode passed all retained auth/tool/
  resource/scope/Host/Origin/reconnect/concurrency checks. No live backend outage
  was induced; synthetic outage/recovery remains a separate prior qualification.
- All **19 other pre-existing container snapshots and 267 protected hashes** match
  the fresh 20-container baseline; only the gateway identity/start changed. All
  checked macOS mise/Codex and additional wrapper/Compose hashes match. Graphify
  did not restart; Basic Memory, PostgreSQL and all {{mstack:CLIENT_REPO}} resources are intact.
- Two test-expectation failures triggered the approved foundation rollback and
  successful foundation/direct-Graphify checks before retrying the same B config.
  Only the gateway was recreated (initial attempt, two rollbacks, two retries).
  Compose orphan warnings were ignored without cleanup. No policy/image/mount/key
  relaxation or custom upstream patch was made.
- Final gateway connection is left running. Data-preserving foundation rollback
  remains available below. All new state/source files are retained; no cleanup,
  commit/push, harness registration, CodeGraph setup or Basic Memory call occurred.

### Known malformed-URI error and test correction

The first failure was a verifier expectation: it assumed `prompts/list` always
returns `prompts: []`. The pinned upstream has no prompt handlers and returns
`-32601`; the verifier now accepts only empty lists or that explicit unsupported
method for optional prompt/template discovery. Other errors still fail.

The second failure was `resources/read` with **unprefixed** `graphify://stats`:
it returns HTTP 500, not an authorization denial. With `prefixMode: always`, a
valid multiplexed URI would be `graphify+graphify://stats` (denied HTTP 400 here).
The pinned [URI parser](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/handler.rs#L529)
requires a target prefix and emits `InvalidRequest` before the
[resource authorization/dispatch sequence](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/crates/agentgateway/src/mcp/session.rs#L621).
Thus source inspection supports the conclusion that this malformed request is
rejected before backend dispatch. Runtime returned no resource contents.

The verifier isolates this **known error-reporting limitation**, requires HTTP
500 with no result/resource/fixture/credential content, and prints a limitation
notice. It does not count it as an authorization test and does not allow 5xx in
`rejected()`. Upstream source was inspected read-only (including a pinned source
archive read into memory); no source checkout/install/build/patch was made.
Investigate improved 4xx/JSON-RPC invalid-request mapping in a separately scoped
upstream fix/upgrade assessment; do not claim full protocol conformance or silently
patch/upgrade the gateway. Approval B's policy/config remain exactly as proposed.

## Versions and impact

Reuse official agentgateway **1.5.0**, ARM64 image
`ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896`,
release commit `fe6732474a96a0363dfb9822859af4e9bab360fa`. The existing image is
already installed. Recheck image/ownership/container/network inventory before
mutation. No download, build, new CLI, macOS/Ubuntu mise or global config change.

Recreate **only `mcp-stack-agentgateway-1`**, causing a brief interruption on
existing macOS `127.0.0.1:58080`. No new listener/port, database or provider.
Graphify stays running/internal/read-only; PostgreSQL, Basic Memory, {{mstack:CLIENT_REPO}} and
CodeGraph images/indexes stay unchanged. Current gateway key and original
foundation config/template/Compose file remain untouched for rollback.

## Exact project file/config changes

Create under `infra/agentgateway/graphify/`:

- `config.template.json`: copy the foundation template and insert the exact
  Graphify route below immediately before `mcp-not-configured`. All existing
  gateway/API-key/health/placeholder/catchall/settings remain unchanged.
- `compose.yaml`: the exact overlay below, used together with the existing
  gateway Compose file, never with root Compose or the Graphify service overlay.
- `prepare.py`: stdlib-only, validates existing distinct 64-hex client/backend
  keys and backend hash config, refuses symlinks/existing output, creates ignored
  `infra/agentgateway/state/graphify/` (0700), renders client hash-only `config.json`
  (0644), and copies **only** the existing backend token, no newline, to
  `backend.key` (initially 0600). Do not generate/rotate either credential or
  overwrite any foundation file. Fail closed if validation/permissions differ.
- `verify.py`: bounded stdlib probes/inspection; authentication supplied to
  existing macOS curl on stdin, never argv/env/printed output. No auto-start,
  lifecycle action, raw secret-bearing response or package dependency.

The new backend-key copy will be **macOS owner/group 501:501, mode 0640**; check
actual metadata after the explicit scoped chmod below. Add supplementary group
501 to this gateway container only while retaining UID/primary GID 65532:65532.
That allows its non-root process to read the explicitly mounted copy without
world-readable secrets, root, host user/group creation or changing the original
0600 keys. Only the new config and backend-key files are mounted, not their state
directory or host home. Abort on unexpected ownership; do not relax permissions.

Exact route JSON (original tool names are used in authorization; discovery is
expected to prefix them with `graphify_`):

```json
{
  "name": "graphify",
  "gateways": ["foundation"],
  "matches": [{"path": {"exact": "/mcp/graphify"}}],
  "policies": {
    "mcpAuthorization": {
      "rules": ["mcp.tool.target == \"graphify\" && mcp.tool.name in [\"query_graph\", \"get_node\", \"get_neighbors\", \"get_community\", \"god_nodes\", \"graph_stats\", \"shortest_path\"]"]
    }
  },
  "backends": [{
    "mcp": {
      "targets": [{
        "name": "graphify",
        "mcp": {"host": "http://graphify-http:8000/mcp/"},
        "policies": {
          "backendAuth": {
            "key": {
              "value": {"file": "/run/secrets/graphify-backend-key"},
              "location": {"header": {"name": "authorization", "prefix": "Bearer "}}
            }
          }
        }
      }],
      "statefulMode": "stateful",
      "prefixMode": "always",
      "failureMode": "failClosed",
      "dnsRebindingProtection": true
    }
  }]
}
```

The [pinned schema](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/schema/config.json)
supports HTTP-target transport policies and static-key file references. Official
[backend-auth documentation](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/backend-authn/key/)
documents file keys and Bearer header insertion. Schema/documentation support is
not a completed runtime test. Do not forward the client key or use passthrough.

Tools-only is deliberate for this first live route: filter/reject resources and
prompts as well as excluded tools. The original Graphify adapter still blocks
GitHub PR tools and foreign `project_path` before upstream dispatch. No task
classifier/profile identity, automatic memory use or full-repository graph is
implied. Bare `/mcp` stays 503; authenticated `/healthz` stays 200.

Exact Compose overlay:

```yaml
services:
  agentgateway:
    group_add: ["501"]
    networks: [gateway, graphify]
    volumes:
      - type: bind
        source: ./infra/agentgateway/state/graphify/config.json
        target: /config/config.json
        read_only: true
        bind: {create_host_path: false}
      - type: bind
        source: ./infra/agentgateway/state/graphify/backend.key
        target: /run/secrets/graphify-backend-key
        read_only: true
        bind: {create_host_path: false}
networks:
  graphify:
    name: mcp-stack-graphify-transport
    external: true
```

Compose replaces the config bind by container target, not by editing its existing
source. Validate the merged definition has **exactly two read-only file binds**,
two intended networks and unchanged image/user/loopback/resource/privilege/log/
restart/tmpfs settings before recreation. No secret environment variables.

Extend `infra/graphify/http/verify.py` with a separate, explicit
`--gateway-connected` mode requiring `--service`: assert exactly the persistent
Graphify and expected Compose-owned gateway are network members, gateway has
only its two planned networks, and Graphify still has only the internal network.
Keep default and `--service` A-only assertions unchanged. All graph/auth/scope
probes remain unchanged; this is not permission to accept arbitrary members.

## Exact commands — run only after B approval

```sh
MCP_STACK_HOST_REPO=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack
python3 infra/agentgateway/graphify/prepare.py
macctl run chmod 640 /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/state/graphify/backend.key
macctl run stat -f '%u:%g %Lp' /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/agentgateway/state/graphify/backend.key
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/graphify/compose.yaml" config --quiet
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/graphify/compose.yaml" up -d --no-deps --no-build --pull never --force-recreate agentgateway
python3 infra/agentgateway/verify.py
python3 infra/agentgateway/graphify/verify.py
python3 infra/graphify/http/verify.py --service --gateway-connected
```

Preparer permissions/content checks are captured without printing tokens. Protect
the new state path with existing ignore rules; never print full runtime config,
secret, environment or diagnostic output. Do not run the original preparers.

## Verification and failure handling

- Inspect exact digest/ownership/isolation/secret-file mode/mounts/network members;
  require runtime initialization to prove the gateway can read/use the backend
  key. Test missing/wrong client credentials, backend token as client token, and
  client token sent directly to Graphify (all denied).
- Initialize via macOS loopback `/mcp/graphify`; discover exactly seven expected
  prefixed tools and run meaningful checks for all seven on the retained fixture.
  Check PR/unprefixed/unknown tool calls, denied resources/prompts, and foreign
  project arguments; no disclosure or successful excluded call is acceptable.
- Check fresh/reconnected and genuinely concurrent independent gateway sessions,
  invalid session rejection and cross-route replay to the foundation placeholder.
  Use the unchanged direct Graphify verifier for retained server-level protections.
- Compare existing containers/protected hashes; only gateway recreation/network/
  mounts and new ignored Graphify gateway config/key-copy files may differ.
  Graphify must not restart or change its source/index/hash/key. Do not test live
  outages by stopping it or corrupting credentials. Synthetic outage qualification
  remains recorded separately; do not claim a live outage test occurred.
- On any validation/runtime test failure, report sanitized diagnostics and restore
  only the gateway with the unchanged foundation definition below. If runtime
  behavior requires a new policy, version or weaker protection, stop and ask.

```sh
macctl run docker compose -p mcp-stack --project-directory "$MCP_STACK_HOST_REPO" -f "$MCP_STACK_HOST_REPO/infra/agentgateway/compose.yaml" up -d --no-deps --no-build --pull never --force-recreate agentgateway
python3 infra/agentgateway/verify.py
python3 infra/graphify/http/verify.py --service
```

Rollback recreates only the gateway, restoring its original config, one network
and no backend-key mount/supplementary group; Graphify and retained data stay
running/intact. Retain new ignored files as rollback material, no cleanup/prune.
Report success/failure before presenting a separate CodeGraph transport proposal.
No Basic Memory call/integration/models, n8n, PKM, harness registration, watcher,
corpus expansion, database migration, {{mstack:CLIENT_REPO}} work or VM/workflow-skill changes.
