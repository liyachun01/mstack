# Standalone llama.cpp — retired

The user replaced this command-line-only host with **Llama.app 0.43.0** on
2026-10-07. See [the active GUI installation](../llama-app/README.md) and the
canonical [handover](../../docs/HANDOVER.md).

Removed only `state/runtime/b11429` and its pinned download archive. No weights
had been downloaded, no standalone daemon was running, and there were no model
volumes to remove. `state/` is empty. Preserve this infra entry and its historical
release/hash metadata. The old launcher refuses this retired definition.
Port 58093 is retired; the GUI's own engine uses Mac loopback 9931. Reinstallation
of b11429 is a separate lifecycle decision, never an automatic fallback.

## Historical installation record — commands inactive

Installed on 2026-10-07 for native macOS/Metal: b11429, official v0.6.0-linked
release, exact archive hash and commit in runtime.json. `state/` is ignored.
No global tool install. The Mac executable version check passed.

Runtime options are in runtime.json; launcher source is
../../integrations/models/llama_host.py. Execute with macctl from the stack root:

```sh
macctl run python3 integrations/models/llama_host.py infra/llama.cpp version
```

The user subsequently accepted Qwen3-4B-Instruct-2507, but weights remain absent.
The start action refuses an unset/missing model. No inference daemon/autostart was
created. Planned macOS loopback port 58093, context 8192, parallel 1. Later qualify
Metal loading, memory/latency, tool template and actual tool-call round trip.
Do not mark a model ready from an executable version check.

Rollback: keep runtime.json/docs, stop only this exact foreground process if one
is later started, and remove the recorded state/runtime/b11429 artifact if wanted.
Never delete model data as incidental cleanup. A reinstall verifies the same
upstream release hash. See ../../docs/design/003-LOCAL-MODELS-AND-PROXY.md.

Metal device discovery also passed: MTL0 Apple M5 and Accelerate are available.
This is backend detection, not a loaded-model latency/memory benchmark.
