# Shared Headroom

`mstack-headroom` runs Headroom **0.34.0**, the same release as the existing
harness helper, with MCP **1.29.0**. Its official Python package and dependencies
are pinned with hashes in `requirements.lock`; the Python ARM64 base is pinned
in `Dockerfile`. The built runtime image is pinned in `../services/compose.yaml`.

One shared container serves authenticated project tenants through native stdio
MCP sessions. Each tenant has its own SQLite compression cache and statistics.
The example tenant is retired. Existing global harness helpers remain
installed/connected; project registration does not silently change other chats.

```sh
./mstack services status
./mstack tenant add --project /path/to/project --tool headroom
./mstack services stop headroom
./mstack services start headroom
```

After registering a project, qualify its three MCP tools and configure its
project-only binding using the [shared-service guide](../services/README.md).
The launcher command uses `--tool headroom`. No per-project container is needed.
Stopping the service affects all its tenants but preserves their cache files.

## Scope and retention

- Available: `headroom_compress`, `headroom_retrieve`, `headroom_stats`.
- Original content is stored in that tenant's native SQLite cache. For explicit
  MCP compression, Headroom's TTL is **one hour**. Reconnects and service restarts
  retain originals within their TTL; this is not durable personal memory.
- Statistics/cache paths are selected before importing Headroom. Requests cannot
  override project identity or storage paths; file-reading tools are disabled.
- The runtime has no network, published ports, source mounts, model/provider
  credentials or proxy fallback. No learned model weights are installed. Build
  time includes tokenizer vocabulary tables, which do not run inference.
- Compression is content-dependent and may remove details. Retrieve the original
  when needed. This deployment does not automatically compact chat history or
  intercept provider traffic. Existing model/login settings stay unchanged.
- The local Docker owner and service administrator are trusted, as with the other
  shared tools. Project tenants isolate MCP access, not hostile Docker owners.

State lives under ignored `infra/services/state/headroom/`. A separate private
client token stays under each consumer's `.mstack/secrets/`; only its hash is registered
server-side. Original compressed inputs can be sensitive, so retain the private
directory permissions and do not put these caches in Git or Anytype.

## Verification and rollback

The former example acceptance helper is retired along with its tenant. The dated
qualification receipt remains historical evidence; use the generic regression
suite for local adapter checks. No automatic service restart or example recreation.
