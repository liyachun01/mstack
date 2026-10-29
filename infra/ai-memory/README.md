# ai-memory — experimental project memory

Installed 2026-10-06 at the user's request. Official release **2.5.2**, source
commit `7580b74d0fb9d14a6d949dc92f5ea8bb7feb3c83`; Docker index pinned to
`sha256:379d4892737ff6b9db7019a4df5c350fa0402a39bb3b7104eae177522b3ba8f6`,
ARM64 manifest `sha256:8fd85dd8cb14e75ea62d74423565121b1cc2ed20d0016ed38b546e9082f16e65`.
Source: [upstream release](https://github.com/akitaonrails/ai-memory/releases/tag/v2.5.2).

## Runtime and boundaries

- Existing macOS OrbStack Docker engine, Compose project `mcp-stack`, service
  `ai-memory`, container `mcp-stack-ai-memory`.
- Definition `infra/ai-memory/compose.yaml`; macOS loopback MCP
  `http://127.0.0.1:58092/mcp`, public liveness `/healthz`. No web UI enabled.
- Dedicated `mcp-stack-ai-memory-local` bridge and `mcp-stack-ai-memory-data`
  volume at `/data`. Git-backed Markdown wiki + SQLite index; no PostgreSQL use.
- Non-root, read-only root, dropped capabilities, no-new-privileges,
  768 MiB / 1 CPU / 128 PID bounds, 64 MiB temporary filesystem, bounded logs.
- Private generated bearer in ignored `infra/ai-memory/state/runtime.env`, 0600
  within 0700 state. This is service authorization, not an LLM provider key.
- No LLM/embedding provider or credentials, model download, host/project mount,
  Docker socket, harness registration, capture hooks, transcript import or gateway
  change. No automatic memory capture is enabled by this install.

This is an experimental **working/session-memory candidate**, not the canonical
PKM. Anytype owns durable user knowledge. ai-memory's data remains persistent;
"temporary candidate" does not mean automatic deletion or a verified retention TTL.
Project labels/auto-scope are not per-project RBAC: pinned upstream documents a
single-tenant store without per-page RBAC. Qualify a gateway/client scope boundary
or separate stores before relying on cross-project security.

Do not use the upstream host wrapper that mounts `$HOME`, `install-hooks --apply`,
`install-mcp --apply`, or `ai-memory run` as a shortcut: the last can auto-wire
harnesses. Install authorization did not authorize global integrations/capture.

## Commands and acceptance

Commands used from the Ubuntu repository root:

```sh
macctl run docker pull --platform linux/arm64 docker.io/akitaonrails/ai-memory:2.5.2@sha256:379d4892737ff6b9db7019a4df5c350fa0402a39bb3b7104eae177522b3ba8f6
macctl run docker compose -p mstack --env-file infra/ai-memory/state/runtime.env -f infra/ai-memory/compose.yaml config --quiet
macctl run docker compose -p mstack --env-file infra/ai-memory/state/runtime.env -f infra/ai-memory/compose.yaml up -d --no-deps --pull never ai-memory
python3 integrations/ai-memory/verify.py
```

Qualification: healthy, zero restarts, version 2.5.2, liveness 200, anonymous and
wrong-token MCP 401, authenticated initialization/discovery 200 (protocol
2025-03-26). Diagnostic session cleaned; no `tools/call`, data import or model
request. MCP advertises 23 tools; serialized definitions measured 54,001
characters / 54,094 UTF-8 bytes. `memory_query` alone measures 7,631 characters.
These are schema sizes, **not measured model token counts or billing**.

All 26 existing containers retained identity, state, start/finish timestamps,
restart count and mount definitions. They were already stopped and remain so.
An initial comparison incorrectly treated Docker mount-list order as meaningful;
normalizing by destination confirmed no mount change. Source/history preserved.
Compose's orphan warning refers to other retained overlays: it is not a cleanup request.

Private evidence: `state/baseline.json`, `state/direct-qualification.json`,
`state/install-result.json`. No full recovery, native harness usage, project
isolation or gateway registration is claimed. Existing data/services were untouched.

## Rollback and later updates

Only when requested, stop/remove exactly this container, preserving its data:

```sh
macctl run docker stop mcp-stack-ai-memory
macctl run docker rm mcp-stack-ai-memory
```

Keep the named volume and private bearer for resume. Volume/token deletion is a
separate data-removal operation; no cleanup is currently needed. Never broad
Compose `down`, `--remove-orphans`, prune, or clear shared PG. A future upgrade
needs a new qualified digest and a consistent protected data backup/isolated
restore; persistence and wiki Git history do not establish disaster recovery.

[Canonical handover](../../docs/HANDOVER.md),
[memory policy](../../docs/MEMORY-ROUTING.md),
[upstream security model](https://github.com/akitaonrails/ai-memory/blob/v2.5.2/docs/security.md).
