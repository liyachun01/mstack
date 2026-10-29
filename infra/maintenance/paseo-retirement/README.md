# Paseo removed — 2026-10-27

The user explicitly requested removing Paseo and clearing everything related
after moving to Paradev (itself removed later that day, see
[Paradev retirement](../paradev-retirement/README.md)). Paseo held no running agent
at removal; its idle Codex 0.159.2 app-servers exited with each daemon.

Moved to the Mac owner's Trash under `~/.Trash/paseo-retirement-20261027/`:

- `/Applications/Paseo.app`, `~/.paseo` (daemon state, keys, hosts, logs),
  `~/Downloads/Paseo-0.13.0-arm64.dmg`, the empty `~/Documents/paseotest`.
- Library: Application Support/Paseo, Caches (`sh.paseo.desktop`, ShipIt,
  `@getpaseodesktop-updater`), Preferences plist, Logs/Paseo, HTTPStorages.
- Repo: `infra/paseo` (including its import receipts and the Linux daemon home)
  and `integrations/toolchains/{paseo-cli,finish_paseo_import.py,
  verify_paseo_imports.py,import_codex_sessions.py,codex_import_inventory.py}`.

Also trashed: six Paseo skills (`paseo`, `-advisor`, `-committee`, `-handoff`,
`-help`, `-plugin`) from orb-devbox `~/.claude/skills` and `~/.agents/skills`
(`devbox-skills/` in the Trash folder). No agent config held Paseo hooks/MCP.

On orb-devbox the daemon was stopped with `paseo daemon stop` and mise
`npm:@getpaseo/cli@0.13.0` was uninstalled. Shared Node 24.19.0 remains.
`~/.local/bin/paseo` was removed on both hosts. Agent-clis README, qualifier and
snapshot no longer reference Paseo; both hosts re-qualified without a prompt.

Native `~/.codex` and Claude histories are unchanged. The Mac Trash was emptied later the same day, so no rollback copy remains.
