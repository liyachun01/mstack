# Agentgateway assessment and staged setup plan

Status (2026-10-01): **agentgateway selected instead of MetaMCP; foundation, synthetic qualification, persistent Graphify HTTP and real Graphify connection completed**. Official pinned 1.5.0 at macOS `127.0.0.1:58080`; [foundation/network correction](AGENTGATEWAY-NETWORK-CORRECTION.md) and [synthetic results](AGENTGATEWAY-SYNTHETIC-HOST-CORRECTION.md) retained. [Graphify backend A](GRAPHIFY-GATEWAY-CONNECTION-PROPOSAL.md) and separately approved [connection B](GRAPHIFY-GATEWAY-B-PROPOSAL.md) are running: `/mcp/graphify`, seven query tools, distinct backend auth, scoped denials and actual concurrent sessions verified. Malformed unprefixed resource URI returns HTTP 500 before dispatch, a documented protocol/error-reporting limitation, not an authorization pass. Bare `/mcp` remains 503. No CodeGraph connection, Basic Memory integration, database migration, models or harness registration. Existing data/services and {{mstack:CLIENT_REPO}} are unchanged; Helm remains deferred.

Task profile for this assessment: documentation/research using direct primary-source inspection. No memory-service calls or indexing are needed.

## Decision and fit

Use agentgateway as the gateway/aggregator; stop pursuing MetaMCP patch/fork selection. Retain the [MetaMCP assessment](METAMCP-SETUP-PROPOSAL.md) as historical evidence. Neither a MetaMCP uninstall nor a database migration is necessary: MetaMCP was never installed.

Agentgateway's pinned upstream example combines tools from multiple MCP servers behind one client endpoint. MCP authorization documentation covers discovery filtering as well as calls, with CEL policy rules. It can run standalone in Docker, without Kubernetes. This fits a local, versioned, policy-driven gateway better than maintaining the previously considered MetaMCP application repair/fork. That is a fit assessment, not proof that agentgateway is audited, universally more mature or secure by default.

The repository is Apache-2.0 licensed. The proposed self-hosted core gateway does not require purchasing a managed gateway subscription. Connected model APIs, hosted backends or optional commercial support have their own costs; none is enabled here.

Sources: [pinned multiplex example](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/examples/mcp-multiplex/README.md), [MCP authorization](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authz/), [standalone Docker installation](https://agentgateway.dev/docs/standalone/latest/documentation/setup/install/docker/), [pinned license](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/LICENSE).

## Artifact qualification, metadata only

Candidate: official stable **v1.5.0**, released 2026-08-27, resolving to source commit `fe6732474a96a0363dfb9822859af4e9bab360fa`. Higher v1.6.0-alpha releases are prereleases, not automatic installation choices. Standalone documentation identifies 1.5 as latest; Kubernetes/control-plane versions must not be treated as standalone runtime versions.

The release provides a Linux ARM64 binary and checksum. Anonymous registry metadata also confirms the official image supports Linux ARM64 and AMD64:

- Reference checked: `ghcr.io/agentgateway/agentgateway:v1.5.0`.
- Multi-platform index: `sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896`.
- Linux ARM64 manifest: `sha256:f64c27c8bd8aa25f07864dab07072026e375f22c6298c2c2d64f7d6c08a24130`.
- The official Docker docs use `cr.agentgateway.dev/agentgateway:v1.5.0`; upstream's pinned release workflow publishes to GHCR. Only the GHCR manifest above was independently checked; qualify the final registry/digest pairing explicitly in the install proposal.
- An initial lookup using unprefixed `1.5.0` returned 404; the published tag uses `v1.5.0`. No image layers were pulled.

Prefer the qualified official ARM64 container, pinned by digest, rather than a source build or a new host Rust/Node installation. Published artifact availability removes the architecture-only reason for a custom build; it does not prove runtime/policy compatibility. Inspect the image metadata, configuration schema, current advisories and scoped runtime behavior before declaring it usable. No `agctl` CLI is required merely to choose this product.

Sources: [v1.5.0 release](https://github.com/agentgateway/agentgateway/releases/tag/v1.5.0), [pinned release workflow](https://github.com/agentgateway/agentgateway/blob/fe6732474a96a0363dfb9822859af4e9bab360fa/.github/workflows/release.yml), [public registry manifest](https://ghcr.io/v2/agentgateway/agentgateway/manifests/v1.5.0) (may require an anonymous pull token; metadata is not an installation).

## Initial configuration and database choice

Use explicit, versionable file configuration under `infra/agentgateway/`, supplied with `-f` and mounted read-only. The installed foundation uses `config.storage.mode: readOnly` with admin/UI listeners disabled and no database. Config/template/preparation/verifier and an opt-in Compose overlay are installed; root Compose and mise remain unchanged. See the [operating notes](../infra/agentgateway/README.md).

Do not copy the writable-directory quickstart: it generates a configuration and SQLite database and attaches the UI to the default gateway. With an explicit file, core routing can run without any database. Proposed first phase: MCP routing only, no database-backed analytics/budgets, no UI attached to the client gateway, no paid LLM test calls, and no public admin port. The container's admin interface normally listens on its own loopback at port 15000; publishing that number alone does not make it reachable, and broadening its bind is not implicitly authorized.

A database is optional for later features. Upstream supports PostgreSQL as well as SQLite; database-backed startup can create tables, so enabling it is a migration/setup step requiring approval. If needed, propose a separate database/role on the shared PG18 instance after compatibility verification. Do not attach to `basic_memory` or {{mstack:CLIENT_REPO}}, and do not select SQLite merely because a default quickstart does.

Sources: [Docker defaults and explicit-file mode](https://agentgateway.dev/docs/standalone/latest/documentation/setup/install/docker/), [configuration storage modes](https://agentgateway.dev/docs/standalone/latest/documentation/setup/storage/), [optional database support](https://agentgateway.dev/docs/standalone/latest/documentation/setup/database/).

## Aggregation and access boundaries

Multiple MCP **targets within one MCP backend** form the aggregate. Multiple route backends are not a substitute for that configuration; routing/load balancing is a different concern. Verify tool naming/collisions against the pinned release instead of relying on mutable examples. An upstream example notes that one failed target initialization can fail the combined backend; test outages and consider separate profile endpoints rather than assuming complete failure isolation.

Use [task profiles](MEMORY-ROUTING.md) for agent/workflow selection; aggregation does not infer whether a conversation is coding or PKM. Separately approved endpoints/identities and explicit allowlists can enforce the selected scopes. Agents may reassess their session profile, and n8n may choose a profile for a job; neither should gain unrestricted tools by sending a self-declared profile label.

Qualification must test:

- Allowed tools appear and work; forbidden tools are absent from discovery **and rejected when called by name**.
- Missing/invalid credentials, policy evaluation failures and unavailable backends do not silently widen access.
- Profile endpoints cannot reach excluded tools through aliases, resources, prompts or another exposed route.
- Tool prefixes and target identity are stable, and connection/session concurrency is controlled.
- Logs do not retain credentials or full private memory/tool payloads by default.

Documented capability is not a claim these protections have already been configured or tested locally. Keep server-side restrictions and filesystem boundaries even after gateway filtering is enabled.

## Existing server transports remain separate work

Agentgateway supports stdio targets, but a stdio command executes in the gateway's own execution environment. It does not automatically launch our existing isolated images. Do not grant the gateway Docker socket access, invoke unrestricted Docker commands or mount entire repositories/user homes to make quickstart commands work. Examples using `npx`, `uvx` or `cargo run` were read, not executed; they are not approved dependencies.

- **Graphify:** preserve the existing seven-tool pre-dispatch adapter, foreign-project rejection, read-only query state and narrow corpus. Qualify a bounded HTTP transport for that restricted adapter or another equally isolated design; switching directly to upstream HTTP must not bypass these gates. Transport/authentication changes need a separate proposal.
- **CodeGraph:** currently stdio/raw local socket, not native HTTP. A transport bridge or co-located process arrangement needs explicit packaging/security review. Preserve one writer per index; do not spawn competing sessions/writers against the retained SQLite index. Gateway aggregation alone does not solve that concurrency problem.
- **Basic Memory:** keep its running HTTP service, PostgreSQL and notes unchanged. Do not connect it to agentgateway, invoke new usage tests, select/download embeddings or enable automatic retrieval while its integration remains deferred.

Harness options remain OpenCode directly, a DeepSeek harness (exact distribution pending), or Codex. Registration is a later, separately approved project-scoped step under `infra/`, not a global config edit. n8n and PKM setup remain separate future steps.

## Proposed sequence — each action needs its own approval

1. Completed: [gateway-only foundation](AGENTGATEWAY-FOUNDATION-PROPOSAL.md) and separately approved [network correction](AGENTGATEWAY-NETWORK-CORRECTION.md). Version/security settings, actual loopback publication and HTTP authentication/route checks passed. No backend/test container. Initial route/network/curl errors and corrections are recorded; strict authentication remains intact. This narrower phase does not qualify MCP filtering.
2. Completed: [synthetic qualification and separately approved fixture Host correction](AGENTGATEWAY-SYNTHETIC-HOST-CORRECTION.md). All eight checks passed, including aggregation, discovery/call-denial, missing-claim error denial, concurrent sessions/replay and outage/recovery. Both temporary containers removed; protected resources/live foundation on 58080 unchanged; no downloads. Initial 421 failure retained for audit. This is synthetic qualification, not real memory-server integration or production certification.
3. [Graphify restricted HTTP direct qualification completed](GRAPHIFY-HTTP-SETUP-PROPOSAL.md), authorized with “Approve”: all direct auth/gate/tool/resource/transport/concurrent-read checks passed; temporary container removed, protected data/services unchanged. [Persistent backend A is completed/running](GRAPHIFY-GATEWAY-CONNECTION-PROPOSAL.md), all direct tests and protection comparisons passed. [Gateway connection B](GRAPHIFY-GATEWAY-B-PROPOSAL.md) is separately approved/completed: real backend auth, seven useful tools, valid-request denial and concurrent-session checks passed; malformed-URI 500 recorded separately. Preserve seven-tool gate/read-only index; actual inter-container gateway transport/backend-auth is now verified, with no harness/profile integration. CodeGraph transport/one-writer setup follows independently. Basic Memory is excluded until the user lifts its deferral.
4. Propose the selected harness's project-scoped connection, then n8n workflows and later PKM integrations independently. Do not install all harness candidates by default.

The foundation approval request must give exact commands and file contents; final registry/digest; existing-image status; non-root/read-only constraints; bounded CPU/memory; macOS OrbStack engine usage through `macctl` where necessary; Ubuntu/macOS reachable addresses and authentication; fresh port inventory; project-scoped network and optional overlay; ignored secret paths/permissions; health and negative authorization tests; and targeted data-preserving rollback commands. Avoid global configuration, Ubuntu mise changes and any {{mstack:CLIENT_REPO}} lifecycle action. No port is reserved by this document.

Stopping/removing only a future gateway container would leave the current graph indexes, Basic Memory notes and database intact. Any later database-backed phase needs its own schema/data rollback plan. Retain historical documentation; do not delete working services or volumes to complete the product switch.

The standalone OrbStack/macOS workflow skill stays the **last-step TODO**. Only the existing project setup guard is updated now so future agents remember this decision and the approval boundaries.
