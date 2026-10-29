# Subscription CLIs — retired 2026-10-27

**Historical.** Later on 2026-10-27 the user returned to Codex Desktop and
Claude Desktop and both CLIs were uninstalled on Mac and orb-devbox, with their
`~/.local/bin` launchers. orb-devbox `~/.local/bin/codex` again points to Codex
Desktop's standalone install. `state/` keeps Claude CLI config/history and
receipts. Do not reinstall from the declarations below unless asked.

Installed on Mac and orb-devbox: mise-managed Codex 0.163.0 and Claude Code
2.1.310. Both Codex CLIs completed Microsoft Edge OAuth using their same existing
ChatGPT account; both Claude CLIs were independently authorized through Microsoft
Edge and report Claude Max. Existing histories remain in place.
Paradev briefly ran both CLIs; it and Paseo were removed the same day.

Global use does not require mise. Here mise provides one explicit version owner,
checksummed native packages, and consistent Mac/Linux launchers. The discovery
links `~/.local/bin/{codex,claude}` point to `integrations/toolchains/`.
Launchers resolve the pinned tools without auto-installing or changing the
working directory. Upgrades are explicit; Claude's self-updater is disabled.

Codex Desktop is the bundle named ChatGPT.app, ID `com.openai.codex`.
Application removal receipts in this directory identify the exact bundles and
Trash locations. Native history/configuration directories are deliberately
retained. The currently running Codex window can remain until the owner exits
after reading the handoff; uninstalling the bundle does not kill that process.

Exact official GitHub release archives and SHA256 digests are declared in
`macos/mise.toml` and `linux/mise.toml`. Codex is 0.163.0 (raised from 0.159.2
for Paradev chat sessions); Claude Code is 2.1.310. Use the existing mise in each domain:
`mise -C <this-directory>/<platform> install github:openai/codex`, then
`mise -C <this-directory>/<platform> install github:anthropics/claude-code`.
For isolated maintenance, set `MISE_CEILING_PATHS` to this directory and
`MISE_GLOBAL_CONFIG_FILE` to its `empty-global.toml` before the commands above.
These install steps require no listener or model request.

Keep native `~/.codex` (sessions, archived sessions, indexes, SQLite databases,
settings, auth, plugins and attachments) in place. Do not delete it as application
residue. Private pre-change manifests/configuration snapshots belong in `state/`.
Application Support/Codex and Application Support/Claude are retained until
their history has been assessed; deleting an app does not authorize history loss.

Global command availability uses repo-owned launchers and user-bin discovery
links, not independent user-global version selections. Installation rollback
removes only the newly installed mise version and restores the original command
link. Codex 0.159.2 installs remain for rollback via `*.bak-0.159.2`. No unrelated containers,
Magpie configuration, provider grants, or global MCP registrations are changed.

Claude uses separate private `state/{macos,linux}/claude` config directories;
inherited API keys, API endpoints, and third-party switches are removed by the
subscription launcher. Mac network settings explicitly reuse the user's existing
HTTP proxy at 127.0.0.1:7897; Edge already used this system proxy. The initial Mac
OAuth exchange failed with HTTP 403 without it and succeeded after it was set.
This is a network proxy, not Magpie, a model gateway, or an API-billing route.

History proof: all 116 original Mac session files and 1,113 Ubuntu session files
retain their original bytes. Two live Ubuntu files grew by appending. Counts
refer to files, not distinct conversations. The installed CLIs' read-only
`thread/list` calls returned 10 Mac and 46 Ubuntu records without model calls.
Mac's app-owned thread_history database could not be opened by system SQLite;
its original remains intact, with supplemental live copies (not a consistent
database backup). state_5 and Ubuntu history databases have SQLite backups.

## Everyday use

Run `claude`, `codex`, or `codex resume --all --include-non-interactive` from the
project directory. Do not open the same active thread
concurrently in two clients.

No inference request, automatic fallback, Composio grant, or global MCP
registration was performed by this setup. Existing project bindings remain
subject to their own normal trust and qualification requirements.
