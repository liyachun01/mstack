# Graphify isolated setup proposal

Status (2026-10-01): **approved and completed — isolated container/direct MCP step only**. The user's “continue” approved the preceding proposal. No harness/gateway registration, persistent Graphify service, broader corpus, model setup or host package change was performed. The approved scope and pins below are retained as a runbook.

## Completed setup and verification

- Image: `mcp-stack-graphify:0.9.72`, Linux ARM64. Docker inspect image ID: `sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac`; Docker-reported size: **80,574,267 bytes** (not a total Docker disk-usage measurement). Python 3.12.14, Graphify 0.9.72, MCP SDK 1.29.0. All approved artifact checksums passed and 59 packages passed `uv pip check`.
- No source compilation, apt package, model, standalone FastMCP package, host Python/uv/Graphify installation or Ubuntu mise configuration. Container-only uv builder was not retained in the final virtual environment. The pinned base's bundled pip remains; no pip upgrade was performed.
- Offline code-only extraction: **3 files, 37 nodes, 48 edges, 6 communities, zero input/output LLM tokens**. Fixture call relations are `EXTRACTED`; source scope and node endpoints were checked. The post-build diagnostic reports no missing/dangling endpoints, self-loops, duplicates or collapsed endpoint pairs. This does not measure losses before the build stage.
- Direct MCP tests passed twice after the final verification-script update: all seven graph tools, native graph resources, pre-dispatch rejection of all three PR tools and foreign-project selection, retained graph on reconnect, and unchanged source/state hashes during query sessions. Native initialization reports server `graphify` version **1.29.0** (SDK version), distinct from installed Graphify **0.9.72**.
- Both producer and query isolation were inspected: UID 501, no network/ports, read-only root/source mounts, 2 CPU / 2 GiB limits. Only the producer's `/state` is writable; the query server mounts state read-only. Host state directory is `501:501`, mode `0700`, ignored, with approximately **100 KiB** of allocated files after extraction.
- Minimal extraction intentionally creates graph JSON, manifest, AST cache and analysis, not `GRAPH_REPORT.md` or HTML. The native report resource truthfully returns “not found”; other native graph resources were read successfully. Community names are numeric/default, not LLM-generated.
- Temporary extraction, metadata/isolation and MCP test containers were removed automatically. No Graphify container remains running. The image and private derived state are retained; rollback remains data-preserving as below.
- All **18** pre-existing containers retained identical IDs/start times/status/health/ports. Checked project scripts, `infra/mise.toml`, both machines' mise/harness configs where present and {{mstack:CLIENT_REPO}}'s Graphify distribution metadata hashes stayed unchanged. Basic Memory's deferred work remains deferred.
- The existing Ubuntu Graphify 0.9.39 is owned by the {{mstack:CLIENT_REPO}} workflow per the user and remains untouched. This step neither moves it into {{mstack:CLIENT_REPO}} nor edits {{mstack:CLIENT_REPO}}. See [team setup/knowledge ownership](TEAM-MEMORY-AND-REPRODUCIBILITY.md).

Deviations caught and corrected:

- Compose rejected an initial nested YAML source-mount list before any container started; replaced it with individual mount anchors without changing scope.
- First verification expected bare function labels; upstream uses `name()`. The test now normalizes that display suffix, preserving ID-based edge checks. No graph or source rewrite was needed.
- Extraction completed before an immediate producer inspection could find the auto-removed container. A separate ten-second, offline producer metadata session with the same service definition verified mounts/resources; it created no graph data and auto-removed itself.
- Baseline full inspect output was too large; a compact template initially failed for containers without health checks, then was corrected and captured all 18 containers before installation. These were read-only checks.
- The pinned Python base download took about two minutes; the build succeeded without changing sources or pins. A builder pip update notice was informational only. Compose's Basic Memory “orphan” warning was ignored; **no orphan removal** occurred.

The seven-tool adapter follows the Graphify skill's MCP guidance but the global auto-install/full semantic pipeline was deliberately not run: user-approved container-only scope and per-component controls take precedence. Final stop point: before MetaMCP or harness setup.

## One component, limited scope

Install Graphify in a project-owned Linux ARM64 Docker image on the existing macOS OrbStack engine. Build a small code-only graph and test its stdio MCP interface directly, without registering it with Codex, MetaMCP, or n8n or enabling a persistent watcher/server.

Graphify provides graph/community orientation; CodeGraph remains the more targeted code-navigation tool. Their derived indexes are independent and rebuildable, not a replacement for Basic Memory's durable Markdown/PKM layer. The accepted [routing policy](MEMORY-ROUTING.md) remains unchanged. This step tests coexistence; it does not implement gateway routing.

First corpus: read-only mounts of `scripts/verify-basic-memory.py`, `scripts/verify-codegraph.py`, and a new synthetic Python call-chain fixture. This is not a full-repository index. No `knowledge/`, secrets, Basic Memory state, database volume, unrelated repository, Docker socket, or host home is exposed.

Code-only AST extraction and local NetworkX clustering need no LLM or embedding model. Do not enable semantic extraction, LLM deduplication/community naming, media/PDF/Leiden extras, hosted Graphify, or API credentials. Document/media knowledge graphs need a separate scope/provider/cost proposal later. This step produces graph JSON and analysis metadata, not a document/media semantic graph or a browser visualization.

## Existing installation and pinned sources

Read-only discovery found an existing Ubuntu user-level Graphify **0.9.39**:

- `/home/developer/.local/bin/graphify` points into `/home/developer/.local/share/uv/tools/graphifyy/`.
- Version was read from `graphifyy-0.9.39.dist-info/METADATA`, not by running the CLI. The installation was not made during this project setup.
- Preserve it: no execution, upgrade, removal, global skill refresh, or PATH change. No Graphify image or macOS PATH command was found during discovery.

Proposed container sources:

| Item | Exact pin / integrity |
| --- | --- |
| Graphify | Official `Graphify-Labs/graphify`, release **v0.9.72**, commit `1cd9a36c0c57a661d2d2234bc3207e887e1ba104` |
| Graphify wheel | PyPI **`graphifyy`** (double `y`), `graphifyy-0.9.72-py3-none-any.whl`; SHA-256 `d193dcc43b07c9534826277fc92c8e54dc22aba102d58aaf424494a0906216c5` |
| Python base | `python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e`; inspected ARM64 config reports **3.12.14** |
| Dependency lock | Commit-pinned upstream `uv.lock`; SHA-256 `ccf9fe88fee925a26c181b5e1f1582d1aaac1430c2be1e3779c45f0c434e138d` |
| Project metadata | Same commit's `pyproject.toml`; SHA-256 `51ea326f1dad916e838164612210a00291f8c3180ba79bf1cdebc8a874a9f1e2` |
| Container-only build tool | `uv` **0.12.21**, `uv-0.12.21-py3-none-manylinux_2_28_aarch64.whl`; SHA-256 `fcd28fd87972f677f0e12d577842deb5d445adf36bcd4cd1ebaaec4c67788d7f` |
| MCP dependencies | Upstream lock selects official Python MCP SDK **1.29.0** and Starlette **1.3.1**; no standalone `fastmcp` package or separate FastMCP service is proposed |

Download locations:

- Graphify wheel: `https://files.pythonhosted.org/packages/2d/4b/1b96b22bd263447cfaa326a029543891369f4b5b484ec59f963b6cfb02fe/graphifyy-0.9.72-py3-none-any.whl`
- uv wheel: `https://files.pythonhosted.org/packages/c2/5a/09c78f5864c33958cd6d2682f71cd03d44265669a5c3cd426abecc369000/uv-0.12.21-py3-none-manylinux_2_28_aarch64.whl`
- Lock and metadata: `https://raw.githubusercontent.com/Graphify-Labs/graphify/1cd9a36c0c57a661d2d2234bc3207e887e1ba104/uv.lock` and the same prefix with `pyproject.toml`.

Core dependencies include NetworkX, NumPy, RapidFuzz, Tree-sitter and language grammars. The MCP extra brings the official SDK and its locked transitive dependencies (including HTTP/ASGI support); installed support does not mean an HTTP listener will be started. Record the complete resolved package inventory after installation. Do not use the upstream unpinned Dockerfile or install all development/optional extras.

Use a multi-stage build: checksum-verified remote artifacts; uv only in the build stage; `/opt/venv` copied to the final pinned Python image. Proposed dependency commands inside the builder:

```sh
python -m pip install --no-cache-dir --no-deps /tmp/uv-0.12.21-py3-none-manylinux_2_28_aarch64.whl
uv sync --frozen --no-dev --extra mcp --no-install-project --no-build
uv pip install --python /opt/venv/bin/python --no-deps --no-build /tmp/graphifyy-0.9.72-py3-none-any.whl
```

Builder environment: `UV_PROJECT_ENVIRONMENT=/opt/venv`, `UV_PYTHON_DOWNLOADS=never`, `UV_NO_CACHE=1`. Sync runs beside the verified lock/metadata. Fail and report if compatible wheels are unavailable or the lock cannot be used; do not silently add a compiler, apt packages, source builds, a new dependency resolution, or another version. Runtime imports and installed dependency consistency must pass before MCP tests.

This installs neither uv nor Python/Graphify on Ubuntu/macOS. `infra/mise.toml` stays unchanged: Docker is already OrbStack-provided, macOS mise remains the only approved host tool manager, and Ubuntu mise is not authorized.

## MCP interface and explicit tool gate

The pinned Graphify server uses the official SDK's low-level `Server`, not the standalone FastMCP framework. Its native tool list also contains GitHub PR tools. There is no suitable native seven-tool filter in this version, so approval includes a small project-local adapter, `infra/graphify/serve_filtered.py`:

- Reuse the pinned `graphify.serve._build_server` factory and official SDK stdio transport; no new framework, web service, or gateway.
- Advertise and allow execution of only `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, and `shortest_path`.
- Reject other tool names **before** forwarding to upstream, including PR tools; discovery filtering alone is insufficient.
- Bind calls to the one approved graph. Reject nonempty `project_path` overrides rather than letting callers switch projects.
- Preserve graph resources only within that same mounted graph scope; inspect their contents during verification.
- Pin and test the private-factory/SDK-handler integration. An upstream upgrade requires revalidation, not a blind version bump.

The MCP 1.x branch may advertise an SDK-default server version rather than the Graphify package version. Verify Graphify's installed distribution version separately and record the actual initialization result; do not confuse those versions.

## Files, runtime and persistence

Proposed file changes after approval:

- New `infra/graphify/Dockerfile`, `.dockerignore`, `compose.yaml`, `serve_filtered.py`, and `fixtures/call-chain.py`.
- New stdlib-only `scripts/verify-graphify.py` using existing Ubuntu Python; it launches Docker stdio sessions through `macctl run` and does not install SDK packages on Ubuntu.
- Add `infra/graphify/state/` to `.gitignore`; update this runbook, README, setup status and TODO with actual results.
- Root Compose remains a PostgreSQL-only entry point. Graphify is a manually selected overlay; existing runtime/config files and global harness/skill settings remain unchanged.

Runtime image: `mcp-stack-graphify:0.9.72`; services `graphify-build` (one-shot producer) and `graphify` (one-shot stdio query test). Both use UID/GID `501:501`, read-only root filesystem, `network_mode: none`, no ports, no restart policy, 2 CPU / 2 GiB limits and a 64 MiB `/tmp` tmpfs. Neither joins the database network.

Persistence: ignored `infra/graphify/state/mcp-stack/`, mode `0700`, owned by `501:501`, mounted at `/state`. Producer has read/write state; query server has read-only state. Sources/adapter are read-only mounts. Generated graph: `infra/graphify/state/mcp-stack/graphify-out/graph.json`; extraction cache, manifest and analysis remain beside it. No volume or database is created. Image layers consume Docker-managed disk; final size and state usage will be reported, not guessed. The graph is rebuildable but may contain source-derived text and should remain private.

Runtime environment:

```text
GRAPHIFY_NO_AUTO_REFRESH=1
GRAPHIFY_QUERY_LOG_DISABLE=1
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
HOME=/tmp/graphify-home
XDG_CACHE_HOME=/tmp/graphify-cache
XDG_CONFIG_HOME=/tmp/graphify-config
```

`HOME` here is a container environment setting, not a shell variable repurposed on either host. The ephemeral container locations never mount a user's real home. No host environment/API keys/SSH credentials are passed. Explicitly disable upstream skill auto-refresh and query logging; offline runtime prevents external model, telemetry, PR, or update traffic regardless of optional support in dependencies.

Producer command, defined inside Compose (not passed as translated absolute CLI arguments):

```text
/opt/venv/bin/python -m graphify extract . --code-only --out /state --max-workers 2
```

Working directory is the read-only source projection at `/home/developer/workspace/mcp-stack`. Upstream `--out` places extraction caches and outputs under `/state`, not the source tree. No `--global`, `install`, `watch`, LLM deduplication, PostgreSQL extraction or partial-build override is used. The query service starts the local adapter with `/state/graphify-out/graph.json` using official MCP stdio.

## Approved commands and repeatable tests

Before mutation, inventory existing container IDs/start times/status/health, running ports, relevant project files and both machines' mise/harness config hashes. Confirm only the target test containers/image/state are absent or owned by this project; preserve any unexpected existing content and ask if overlapping.

After creating/reviewing the proposed files with `apply_patch`, these commands run from the repository's Ubuntu working directory. `macctl run` is only the existing host-command bridge, not a package manager. It translates host paths; container paths stay inside Compose configuration. No host install command is needed.

```sh
mkdir -p infra/graphify/state/mcp-stack
macctl run chmod 700 infra/graphify/state/mcp-stack
macctl run docker compose -f compose.yaml -f infra/graphify/compose.yaml config --quiet
macctl run docker compose -f compose.yaml -f infra/graphify/compose.yaml build graphify
macctl run docker compose -f compose.yaml -f infra/graphify/compose.yaml run --rm --no-deps --name mcp-stack-graphify-build-smoke graphify-build
python3 scripts/verify-graphify.py
```

Check state ownership through macOS before starting; existing workflow normally creates host-visible files as `501:501`. A mismatch must be corrected only for this explicitly approved state directory, not any broad parent. The test script will launch and close two sessions with names `mcp-stack-graphify-mcp-smoke` and `mcp-stack-graphify-mcp-reconnect` via `docker compose run --rm --no-deps -T`; it must reap its subprocesses. Do not use `--remove-orphans`: Basic Memory may appear as an overlay orphan but is intentionally running and must be preserved.

Image pulls/dependency downloads occur during the build only, from Docker Hub, PyPI/files.pythonhosted.org and commit-pinned GitHub raw files. No hosted account, subscription, API key or paid model call is required by this proposed test; normal local disk/memory/network usage applies.

## Acceptance and after-step report

1. Verify checksums, Graphify 0.9.72, Python, SDK/dependency inventory, absence of standalone `fastmcp`, and final image ID/size. Build tools must not be installed on the hosts or retained unnecessarily in the final image.
2. Inspect container network/ports, UID, limits, read-only root/source mounts, and producer/query state permissions. Verify no mounted secrets/home/socket/database and no persistent Graphify container.
3. Graph extraction exits successfully, contains only the three approved source files, includes fixture symbols/call relationships and communities, and reports zero LLM tokens. Preserve outputs and report actual node/edge counts. No source file changes are permitted.
4. Initialize MCP, list exactly seven graph tools, query a fixture symbol, retrieve its node/neighbors/community, inspect graph stats/ranking and a known connected path. Validate useful content, not just absence of protocol errors.
5. Explicitly call an excluded PR tool and a permitted tool with a foreign `project_path`; both must return an error before upstream dispatch. Inspect resource discovery/read behavior for graph-only scope.
6. Disconnect/reconnect in a second fresh query container. Query results persist, and read-only graph/cache hashes do not change during either query session.
7. Verify temporary containers are gone. Compare all pre-existing containers' identities/start/status/health and checked mise/harness config hashes; PostgreSQL, Basic Memory, CodeGraph and `{{mstack:CLIENT_REPO}}` remain unchanged.
8. Record commands, deviations/failures, resolved versions, image/state size, privacy/backup limitations and rollback availability. Stop before any harness/MetaMCP/n8n registration or next component.

A passing fixture test is not evidence of full-repository scalability, semantic/document extraction, multilingual search, persistent indexing, or correct gateway enforcement. Those remain separate steps. Basic Memory's deferred work stays deferred.

## Data-preserving rollback

Normal test completion leaves only the project image and ignored derived state, not a running service. If interrupted, inspect the exact named containers first:

```sh
macctl run docker inspect mcp-stack-graphify-build-smoke
macctl run docker inspect mcp-stack-graphify-mcp-smoke
macctl run docker inspect mcp-stack-graphify-mcp-reconnect
```

Only after verifying each existing target's `com.docker.compose.project=mcp-stack`, Graphify service label and expected image, stop that exact test container with `macctl run docker stop NAME`. The `--rm` container should disappear; if it remains stopped, inspect again before `docker rm NAME`. Do not apply these commands to an unexpected owner/image. Leave the image/state for inspection or recovery. No `compose down`, volume deletion, broad prune, global uninstall or shared-service restart is needed. Removing the image/state later needs a separately confirmed exact cleanup proposal.

## Primary references

- [Graphify v0.9.72 release](https://github.com/Graphify-Labs/graphify/releases/tag/v0.9.72), including the opt-out for automatic skill refresh.
- [Pinned CLI extraction implementation](https://github.com/Graphify-Labs/graphify/blob/1cd9a36c0c57a661d2d2234bc3207e887e1ba104/graphify/cli.py).
- [Pinned MCP server implementation](https://github.com/Graphify-Labs/graphify/blob/1cd9a36c0c57a661d2d2234bc3207e887e1ba104/graphify/serve.py) and [query logging opt-out](https://github.com/Graphify-Labs/graphify/blob/1cd9a36c0c57a661d2d2234bc3207e887e1ba104/graphify/querylog.py).
- [Pinned dependency metadata](https://github.com/Graphify-Labs/graphify/blob/1cd9a36c0c57a661d2d2234bc3207e887e1ba104/pyproject.toml) and [lock](https://github.com/Graphify-Labs/graphify/blob/1cd9a36c0c57a661d2d2234bc3207e887e1ba104/uv.lock).
- [uv locked synchronization](https://docs.astral.sh/uv/concepts/projects/sync/) and [Docker integration](https://docs.astral.sh/uv/guides/integration/docker/).
- [Official MCP SDK 1.29.0 low-level server](https://github.com/modelcontextprotocol/python-sdk/blob/v1.29.0/src/mcp/server/lowlevel/server.py).

## Resolved virtual-environment package inventory

Captured from the final image using `importlib.metadata` (59 distributions). These versions came from the verified upstream lock plus the verified Graphify wheel, not a new resolution:

```text
annotated-types==0.7.0
anyio==4.13.0
attrs==26.1.0
certifi==2026.4.22
cffi==2.0.0
click==8.3.3
cryptography==49.0.0
graphifyy==0.9.72
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
httpx-sse==0.4.3
idna==3.15
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
mcp==1.29.0
networkx==3.6.1
numpy==1.26.4
pycparser==3.0
pydantic==2.13.4
pydantic-core==2.46.4
pydantic-settings==2.14.2
PyJWT==2.13.0
python-dotenv==1.2.2
python-multipart==0.0.32
RapidFuzz==3.14.5
referencing==0.37.0
rpds-py==0.30.0
sse-starlette==3.4.4
starlette==1.3.1
tree-sitter==0.25.2
tree-sitter-bash==0.25.1
tree-sitter-c==0.24.2
tree-sitter-c-sharp==0.23.5
tree-sitter-cpp==0.23.4
tree-sitter-elixir==0.3.5
tree-sitter-fortran==0.6.0
tree-sitter-go==0.25.0
tree-sitter-groovy==0.1.2
tree-sitter-java==0.23.5
tree-sitter-javascript==0.25.0
tree-sitter-json==0.24.8
tree-sitter-julia==0.23.1
tree-sitter-kotlin==1.1.0
tree-sitter-lua==0.5.0
tree-sitter-objc==3.0.2
tree-sitter-php==0.24.1
tree-sitter-powershell==0.26.4
tree-sitter-python==0.25.0
tree-sitter-ruby==0.23.1
tree-sitter-rust==0.24.2
tree-sitter-scala==0.26.0
tree-sitter-swift==0.7.2
tree-sitter-typescript==0.23.2
tree-sitter-verilog==1.0.3
tree-sitter-zig==1.1.2
typing-extensions==4.15.0
typing-inspection==0.4.2
uvicorn==0.47.0
```
