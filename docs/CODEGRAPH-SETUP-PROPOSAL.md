# Approved CodeGraph container setup/test runbook

Approved by the user's “Continue” and completed on 2026-10-01. CodeGraph 1.6.1 is installed in a project-owned image and its direct MCP/source-projection tests passed. This approval covers this component only, not harness registration, a persistent watcher/gateway, broader repository access, Graphify or model setup.

## Completed results

- Resulting image: `mcp-stack-codegraph:1.6.1`; Docker image ID `sha256:4b8cb16b0c3b5bb7446c3f90b8fd2b12f099b0d0029f8bf30113ad482bf75420`; reported size 144,429,568 bytes. Build cache/base layers consume additional/shared storage; this size is not an estimate of total newly used disk space.
- CLI and MCP server both report `1.6.1`; bundled Node reports `v24.16.0`. The bundled native ARM64 Rust kernel loaded successfully.
- Final scoped index: 3 Python source files, 47 nodes, 98 edges; known synthetic caller/callee edges and real `verify-basic-memory.py` source retrieval passed. Shell scripts are outside CodeGraph's supported source extraction in this projection. This is not a complete repository index.
- Both sequential real MCP sessions passed initialization, tool discovery, source queries, explicit status invocation and rejection of a disabled `codegraph_search` call. The retained SQLite index remained queryable after closing/reopening the container.
- Upstream small-project gating means `tools/list` advertises only `codegraph_explore` despite `CODEGRAPH_MCP_TOOLS=explore,status`. The explicitly allowed status handler is callable; other tools are rejected during execution. Do not confuse the server's configured tool gate with future harness/gateway profile enforcement.
- Runtime inspection passed: UID/GID 501:501, source/config mounts read-only, root filesystem read-only, network `none`, no ports, 2 CPUs/2 GiB limits, bounded temporary filesystem, telemetry/update/daemon/watcher opt-outs effective before invocation.
- No test container remains. All 18 pre-existing containers retained identical IDs, start times, status and health, including Basic Memory, PostgreSQL and all 12 `{{mstack:CLIENT_REPO}}` services. The four existing project scripts and both machines' checked mise/Codex config files retained identical SHA-256 hashes.
- State directories are owned by `developer:developer`, mode `0700`, gitignored. At completion, index state uses about 340 KiB and compile-cache state about 1.6 MiB. The index has derived source content: keep it private, despite not containing credentials.
- First build failed on an unexpected EOF downloading a pinned Node base layer. Retrying the identical Dockerfile/digests succeeded; no mirror/global Docker configuration was changed. BuildKit checksum verification of the release download succeeded.
- One initial metadata diagnostic failed because `macctl` translated the absolute container entrypoint `/bin/sh` into a macOS path. Using `--entrypoint sh` and container-relative project arguments fixed the boundary issue. No base/version substitution occurred.

No Basic Memory test script was executed; it was indexed as source only. No host runtime/package installation, model download, secret/database mount, global config change or MCP registration occurred.

## One component and execution boundary

Installed and directly tested **CodeGraph 1.6.1** in a Linux ARM64 container on the existing macOS OrbStack Docker engine. No host/Ubuntu Node, npm, Rust, mise, Docker or Compose installation. All runtime definitions/state belong under this repository's `infra/codegraph/`.

This first step uses short-lived CLI/MCP test containers, not a newly registered harness server or permanently running gateway. A later step will propose the long-running/client-launch arrangement and watcher/profile integration. Basic Memory's remaining setup/tests remain deferred.

Read-only discovery found no `codegraph` command on either checked PATH and no matching Docker image/container. Do not interpret this as a complete search of either machine's storage.

## Source and immutable pins

- Exact upstream: [colbymchenry/codegraph release v1.6.1](https://github.com/colbymchenry/codegraph/releases/tag/v1.6.1), published 2026-09-29.
- Tag commit: `f4ddf508516332419ea3c95702810765936cf679`.
- Linux ARM64 bundle: `https://github.com/colbymchenry/codegraph/releases/download/v1.6.1/codegraph-linux-arm64.tar.gz`.
- Bundle SHA-256 from GitHub release metadata: `3e31bfd645416ab4e34516a9fe444a907132b3527b18889c877148219cdcc966` (62,677,286 compressed bytes). Verify again during installation and stop on a mismatch; do not silently substitute another asset/version.
- Compatible runtime base: official `node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203`.
- Linux ARM64 base manifest: `sha256:a76e7ab9bd5bafb036f520b264884c78fd14b68be1abf9051e5e524e88117108`.
- Local resulting image: `mcp-stack-codegraph:1.6.1`; record its content ID after building.

The base is a compatibility choice supplying the Linux libraries used by Node/Rust binaries without another OS package installation. CodeGraph's official bundle already contains its own Node runtime, compiled application, JavaScript/WASM dependencies and optional native Rust extraction kernel; its launcher uses that bundled Node, not host Node. The base also contains Node/npm, confined to the image; no npm install or compiler run is planned. Record the actual bundled runtime/kernel presence after inspecting the installed artifact. This is our project container recipe, not a claimed official upstream CodeGraph image.

## Implemented files and narrow source access

Files created in the approved step:

- `infra/codegraph/Dockerfile`: pinned base, checksum-verified release download using BuildKit `ADD --checksum`, extraction under `/opt/codegraph`, fixed launcher entrypoint, no `curl | sh` installer or npm hooks.
- `infra/codegraph/.dockerignore`: excludes generated state and unused files from the build context; multi-stage build keeps the archive out of the final image filesystem.
- `infra/codegraph/compose.yaml`: independent optional overlay, no dependencies on database services, no network, no published port, UID/GID `501:501`, read-only container root, bounded writable `/tmp`, 2 GiB memory and 2 CPU limits.
- `infra/codegraph/project.json`: source-scope/exclusion config, mounted read-only at the container's expected `codegraph.json` path. No root/global config is written on either machine.
- `infra/codegraph/fixtures/call-chain.py`: labeled synthetic caller/callee fixture for assertions; contains no credentials.
- `infra/codegraph/state/mcp-stack/`: ignored writable derived index, mounted at the container's `.codegraph` directory; database `codegraph.db` remains SQLite, separate from Basic Memory PostgreSQL.
- `infra/codegraph/state/runtime/`: ignored writable Node compile cache, mounted at `/state`.
- `scripts/verify-codegraph.py`: standard-library MCP-over-stdio test using Ubuntu's existing `/usr/bin/python3`, with timeouts and scoped child-container cleanup; no new Python packages.
- `.gitignore`, README and status/runbook updated after the approved step.

The container project root is `/home/developer/workspace/mcp-stack`, matching Ubuntu source paths. Mount only this repository's `scripts/` read-only, the synthetic fixture directory read-only at `infra/codegraph/fixtures/`, the config and ignored index/cache state. This is deliberately a partial source projection, not a full repository index; returned results must identify that limitation. It permits a real Python source lookup plus a deterministic call-chain test without exposing `.secrets`, Basic Memory state/notes, backups, unrelated repositories or the Docker socket. No source file may be modified by CodeGraph. Broader repository mounts need a later proposal.

## Environment and transport

- `CODEGRAPH_TELEMETRY=0`, `DO_NOT_TRACK=1`, `CODEGRAPH_NO_UPDATE_CHECK=1`: disable upstream default-on usage telemetry and release checks **before the first invocation**.
- `CODEGRAPH_NO_DAEMON=1`: foreground stdio mode for the isolated first test; do not create a host global daemon registry.
- `CODEGRAPH_NO_WATCH=1`, CLI `--no-watch`: no background indexing while testing. Watcher verification is deferred to its own integration step.
- `CODEGRAPH_MCP_TOOLS=explore,status`: explicitly expose only these two tools for the direct test. This allowlist does not establish future gateway authorization by itself.
- `NODE_COMPILE_CACHE=/state/node-compile-cache`: project-owned cache, not a host user cache.
- `network_mode: none`: offline CLI/MCP runtime; image/bundle download requires network only during the approved build.
- Transport: newline-delimited JSON-RPC over stdio. No HTTP adapter, FastMCP service, API key, embedding model or paid API is added.

Do not run bare `codegraph`, `codegraph install`, global `npm install`, `upgrade`, or vendor harness hooks. They can write global registrations or alter instructions. Test using explicit subcommands only.

## Exact setup and repeatable verification commands

These commands were executed from Ubuntu. `macctl run` is the existing bridge to the macOS OrbStack Docker engine, not a new installer. The initial build was retried once after the download EOF. Rebuilding/initializing is a lifecycle action: seek confirmation for a new update, not an automatic routine test.

Important: `macctl` rewrites standalone absolute arguments to host paths. Use `init .` and `serve --path .` to resolve the Dockerfile's container working directory. JSON-RPC `projectPath` stays `/home/developer/workspace/mcp-stack` because it travels over stdin, not as a rewritten command argument. For container diagnostics use `--entrypoint sh`, not `--entrypoint /bin/sh`.

The overlay intentionally omits the running Basic Memory service definition, so Compose warns that it is an “orphan.” It is not disposable: never pass `--remove-orphans`. `--no-deps` keeps existing database/application services untouched.

```sh
macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/compose.yaml \
  config --quiet

macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/compose.yaml \
  build codegraph

macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/compose.yaml \
  run --rm --no-deps -T --name mcp-stack-codegraph-version codegraph --version

macctl run docker compose \
  --project-directory /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/compose.yaml \
  -f /Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack/infra/codegraph/compose.yaml \
  run --rm --no-deps -T --name mcp-stack-codegraph-index codegraph \
  init . --yes

/usr/bin/python3 -u scripts/verify-codegraph.py
```

The verification script launches the same explicit Compose overlay with `run --rm --no-deps -T --name mcp-stack-codegraph-mcp-test codegraph serve --mcp --no-watch --path .`, drives initialization/tools over stdio, then closes it. It also opens a second session to verify retained-index querying. Use the same overlay for any explicit `status`/`explore` diagnostics. Never start/recreate database services to test CodeGraph.

`--no-watch` disables background file watching, not upstream connect-time reconciliation. A later test-script edit was reconciled on reconnect, changing the index from 96 to 98 edges. This behavior is confined to the mounted source projection; it is not a watcher test or permission to scan another repository. Concurrent test sessions are not supported by this runbook.

## Verification and reporting

- Validate Compose and inspect the download checksum, actual CLI version, bundled Node version, optional Rust kernel and resulting image ID. Stop/report deviations rather than changing versions automatically.
- Confirm non-root UID, source-read-only mounts, offline networking, absent host ports and no daemon/update/telemetry behavior.
- Check nonempty index, known caller/callee fixture relationships, a source symbol from `scripts/verify-basic-memory.py`, and no indexed paths outside the approved projection. Do not execute the Basic Memory test script: here it is source material only.
- Complete a real MCP initialize, tools/list and tools/call; require the small-project discovery surface (`codegraph_explore`), useful source/status answers and execution-time rejection of unapproved tools rather than only a working CLI.
- Close the first MCP test, reopen another against the retained SQLite index, verify queries still work and leave no orphaned CodeGraph test container.
- Compare existing container IDs/start times/status/health before and after, especially Basic Memory, PostgreSQL and all `{{mstack:CLIENT_REPO}}` services. Do not claim existing exited services are new failures.
- Record results, filesystem/image storage and deviations after this step. No Basic Memory semantic test, harness registration, n8n/MetaMCP installation or Graphify installation is included.

## Data-preserving rollback

Normally `run --rm` removes the short-lived test containers. If a failed test leaves a running named container, inspect the exact name/image/Compose labels, then stop only that container, for example:

```sh
macctl run docker stop mcp-stack-codegraph-mcp-test
```

Keep the local image, configuration and index for inspection/retry; nothing auto-starts or is registered with the harness. Removing those retained artifacts requires a separately scoped cleanup request. No `down`, `down -v`, broad prune, database-volume deletion or vendor `uninstall` is planned.

## Sources inspected

- [Release metadata](https://api.github.com/repos/colbymchenry/codegraph/releases/latest) and [fixed release](https://github.com/colbymchenry/codegraph/releases/tag/v1.6.1)
- [Bundle layout](https://github.com/colbymchenry/codegraph/blob/v1.6.1/BUNDLING.md) and [bundle builder](https://github.com/colbymchenry/codegraph/blob/v1.6.1/scripts/build-bundle.sh)
- [Telemetry and update-check opt-outs](https://github.com/colbymchenry/codegraph/blob/v1.6.1/TELEMETRY.md)
- [CLI init/serve options](https://github.com/colbymchenry/codegraph/blob/v1.6.1/src/bin/codegraph.ts), [foreground MCP mode](https://github.com/colbymchenry/codegraph/blob/v1.6.1/src/mcp/index.ts), [tool filtering](https://github.com/colbymchenry/codegraph/blob/v1.6.1/src/mcp/tools.ts), and [project configuration](https://github.com/colbymchenry/codegraph/blob/v1.6.1/src/project-config.ts)
- Official Docker registry metadata for the exact Node base tag/digests above; no image was pulled during discovery.
