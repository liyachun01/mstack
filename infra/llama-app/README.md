# Llama — native local-model UI

Installed from the user's downloaded `Llama.dmg` on 2026-10-07:
**0.43.0**, bundle **261002.1149**, arm64. The DMG hash matches the official
[release asset](https://github.com/ggml-org/Llama-macOS/releases/tag/0.43.0).
Bundle signature and notarized Gatekeeper assessment passed. Exact versions,
hashes, storage links and verification are in `runtime.json`.

Open **Llama** from macOS Applications. It is a **menu-bar app**, so use its icon
at the top of the screen for installed models, recommendations, settings and
Open chat. Its model API is `http://127.0.0.1:9931/v1` on the Mac; health and empty
models-list checks passed. No Qwen weights were downloaded and no inference ran.
Qwen3-4B-Instruct-2507 remains the accepted first model; a GGUF artifact still
needs selection. Harness integration remains unconfigured; OpenCodex is removed.

## Storage and configuration

**Current storage:** restored to the repo on 2026-10-07 at the user's explicit
request. The temporary native Mac move was reversed; engine, model cache and
generated state are again under `infra/llama-app/state`. File hashes, native engine
version, app links/cache preference and router endpoints passed after restoration.
The temporary `~/Develop/mcp-stack/local-models` folder was removed after verifying
the restored copies. No model weights existed. Keep this placement unless the
user requests another change. The owned app links resolve as follows:

| Native location | Current target |
| --- | --- |
| `~/.llama-app` | `infra/llama-app/state/engine` |
| `~/.config/llama` | `infra/llama-app/config` |
| `~/Library/Application Support/Llama` | `infra/llama-app/state/application-support` |

The model-download directory is explicitly set to
the Mac shared path for `infra/llama-app/state/models/hub`, retaining the Hugging Face cache
layout. Future downloads go there; no weights existed at migration.
`preferences.plist` records secret-free setup preferences with the current cache
pointer; the app also persists UI preferences in the `app.llama.Llama` macOS domain.
This file is a setup
snapshot, not a live sync mechanism. Subsequent UI settings should be recorded
deliberately; never export tokens into tracked files. Native logs are under
`~/Library/Logs/Llama/`. No shared shell environment or harness configuration was
changed. Login autostart, automatic app updates and agent mode are disabled.
The API listener was verified on Mac loopback only; no LAN exposure was enabled.
Ubuntu/Docker connectivity and proxy/tool calls have not been qualified.

Llama still needs a llama.cpp-based engine. Release 0.43.0 pins **b11200**;
the running router reports `b11200-81bc6b83f`. The standalone b11429 installation
was removed. The app initially failed copying its helper into the OrbStack-backed
folder; the same pinned official artifacts were prepared with byte writes and
stdin/stdout decompression. Initial terminal `version` probes exited via SIGKILL;
atomic engine replacement while the app was stopped resolved them. Native version
now reports `0.5.0-dev (build 11200, commit 81bc6b83f)`, and live router checks
passed. The app again uses VM-backed files, with native macOS execution. Never
overwrite a running engine in place. App-managed updates and actual model
downloads remain untested; retain the documented install workaround.
The app-created terminal symlink `~/.local/bin/llama` was removed; the GUI resolves
its engine directly. An app engine reinstall/upgrade may recreate that symlink.

Llama and its engine execute on macOS; Linux-hosted files do not move inference
into the VM. Storage can affect loading and page-fault access; resident weights
can make it less relevant during generation. No model/performance benchmark has
run, and no claim of zero storage impact or proven slowdown is made. The user
prefers the repo placement. Runtime data/overrides need repo access; this is not VM
independence. [OrbStack file sharing](https://docs.orbstack.dev/machines/file-sharing),
[engine memory mapping](https://github.com/ggml-org/llama.cpp/blob/b11200/src/llama-mmap.cpp).

The GUI's engine/model updates are app operations, not `stack init` behavior.
Keep updates deliberate while versions are pinned. No broad cleanup or old model
cache deletion is authorized by this installation.

## Verification and rollback

On macOS, GET `/health`, `/props` and `/v1/models` on `127.0.0.1:9931` for readiness,
build metadata and installed models. A healthy router with zero models is not
an inference/tool-call test. No inference calls are needed to inspect it.

To undo the GUI installation, quit only Llama, verify the installed bundle/version,
and remove only `/Applications/Llama.app`. Remove each native link only after
checking that it still targets this installation; preserve repo model/state files
unless their deletion is separately requested. Remove only this app's preferences
if desired, never unrelated domains. The original DMG remains in Downloads and a
verified staging copy is in ignored `state/downloads`. No global manager was used,
and native Codex/OpenCodex/Anytype credentials and protected services are untouched.

The native-storage migration has already been reversed and its temporary copies
removed after hash verification. `runtime.json` retains that history; the active
paths above are authoritative. Do not repeat either migration automatically.
