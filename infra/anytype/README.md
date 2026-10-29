# Anytype project documents

Anytype is the native document backend. `mstack-anytype-mcp` is the shared stdio
adapter; it does not host a second document database or HTTP API.

Project intent is the `anytype` section of `.mstack/stack.json`: native API URL,
channel ID, private credential reference and desired document names/draft paths.
Observed object IDs live in `.mstack/state.json` under `documents.anytype`.
The old separate project registry is retired.

Each project needs its own channel-only read/write grant with all-spaces access
turned off. Never reuse Clock, kase or another project's key. The root stack is
unbound. The deleted mstack examples are not onboarding templates.

See [shared tenant onboarding](../services/README.md) and
[configuration fields](../../docs/MSTACK-CONFIG.md). The explicit document helper
`integrations/agents/anytype_mcp.py <project> --sync-documents` uses the configured
shared tenant, creates missing configured documents and reads their content back.
It preserves existing differing content for review. No automatic memory mirror,
background watcher or global harness registration follows.
