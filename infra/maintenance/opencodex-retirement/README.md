# OpenCodex removed — 2026-10-21

The user requested removal after moving Claude Desktop to Magpie. This supersedes
all older instructions to retain OpenCodex, its data or its rollback profile.

Removed:

- Stopped container `mcp-stack-opencodex`, exact ID
  `8165bf21056865f51b26ebcde301136008c9f2b634edacfc5dc2b46d4c1d862e`.
- Its two unshared volumes: `mcp-stack_opencodex_state` and
  `mcp-stack_opencodex_codex_state`, including provider/proxy-owned account state.
- Unused image `mcp-stack-opencodex:2.79.0`, digest
  `sha256:2220a07c35556757ba7d06aee42e7c3966bab463878c0b3e09a9dabf48184791`.
- `infra/opencodex/`, `.secrets/opencodex/`, app-specific Compose backup copies,
  old provider/profile/probe helpers and their Python caches.
- Old native Claude profile `caad58fd-df2b-4f21-a04e-f9bc798adb76`, its metadata
  entry, repository copies, credential-bearing migration backup and Magpie stash
  reference. Claude's selected Magpie profile is unchanged.
- The retired A/B test Compose fixture that reused the OpenCodex image as Bun.
  No replacement fixture runtime was installed.

The model catalog keeps `local`/`deepseek` as explicitly unbound choices without
endpoints, tokens or providers. Selecting them cannot launch Codex or inherit
Magpie. The removed `opencodex` tool is rejected by project schema validation.
The default native Codex route is unchanged. Magpie integration for Codex remains
pending the user's explicit request.

Fresh verification found **31 other containers unchanged**, with unchanged
identities, start times, states, settings and mounts. All unrelated volumes and
every network were preserved. No broad Compose command, pruning, image pull,
other service start/stop, provider call or native UI control ran.

Magpie still serves the existing DeepSeek Flash catalog; its management endpoint
returns 401 without its key and 200 with it. Its provider credential, settings,
management key and active Claude profile match the removal baseline. Mac and
Ubuntu Codex config/auth are preserved. The original shared DeepSeek credential
source is retained because Magpie uses that provider.

See [Docker/native proof](qualification.json), [local removal](local-removal.json)
and [final checks](checks.json). Historical migration receipts retain their dated
facts; they are not current inventories or permission to reinstall OpenCodex.
No OpenCodex data backup was created for rollback. Removal is complete.
