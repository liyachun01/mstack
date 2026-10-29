# Claude Desktop → Magpie → official DeepSeek

Updated 2026-10-21. Claude Desktop **3.1623.0** uses the installed Magpie
**0.1.1206**, gateway `http://127.0.0.1:3425`, and **DeepSeek Flash (official)**.
Codex remains unchanged and its Magpie integration is pending explicit request.
No Claude Code CLI was installed.

See the [Magpie operating guide](../magpie/README.md) for the comparison,
startup, configuration layout, verification limits and current operation.
[config.json](config.json) records the current public binding;
[Magpie qualification](../magpie/qualification.json) records the fresh checks.

The native generated library is
`~/Library/Application Support/Claude-3p/configLibrary`. It is now a real Mac
directory so Magpie can atomically update its metadata. The old broken relocation
symlink is retired. Magpie's selected profile ID is
`00000000-0000-4000-8000-6d6167706965`; the obsolete OpenCodex profile was subsequently removed.
The provider credential stays in Magpie's ignored private repository state.
Claude receives only Magpie's public local caller marker, not the provider key.

Open Claude normally to load the new route. Streaming and an automatic synthetic
tool/result round trip passed against Magpie; the native window was not opened
in this background-only migration. Code/Cowork file access, project MCP/Anytype
bindings and long sessions still need their own qualification when requested.

## Historical OpenCodex evidence

The earlier October 8 route and its [qualification.json](qualification.json)
remain historical evidence. OpenCodex was removed at the user's request on
October 21, including its container, dedicated volumes/image, proxy credentials,
old native profile and repository profile copies. Its setup/probe helpers are
removed. No retained OpenCodex rollback exists.

See the [removal record](../maintenance/opencodex-retirement/README.md).
The active Magpie profile, DeepSeek credential and native Codex state are preserved.
