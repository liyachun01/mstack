# Superset removed — 2026-10-26

The user explicitly requested removing and clearing Superset first. Superset
Desktop 1.40.0 is removed from macOS. Paseo 0.13.0 and T3 Code Beta 0.1.2 remain.
The earlier conditional Paseo removal is not part of this operation.

Subsequent update: the user then requested removing T3, now completed in the
[T3 retirement record](../t3-retirement/README.md). Paseo remains installed.
The receipts below describe the Superset operation before that later removal.

## Removed

- `/Applications/Superset.app` and `~/.superset`, including app login state,
  databases, wrappers, hook scripts and runtime logs.
- Superset's Application Support, caches, updater caches, preferences,
  HTTP storage and logs in the Mac user's Library.
- 50 owned hook commands from Claude, Codex, Cursor, Gemini, Droid/Factory,
  Devin and Mastra configuration. Unrelated settings were preserved; JSON files
  containing only removed hooks were deleted.
- Muse's Superset managed-hook path/environment list and Grok's marked
  Superset compatibility block.
- Superset extensions for Amp, Pi, Oh My Pi and Grok, and the Superset skills
  installed in Claude and shared agent discovery locations.
- The obsolete `infra/superset` installation proposal and
  `docs/SUPERSET-WORKFLOW.md`. Independent Claude CLI preparation is retained
  with workspace-neutral guidance.

Two identity-checked Superset processes stopped with SIGTERM before removal.
No model call, foreground UI action, other app restart, container operation,
toolchain install or global MCP registration ran. The Superset MCP ownership
ledger was empty. No matching LaunchAgent/LaunchDaemon was found. Four explicit
Superset Keychain service-name checks returned no item; no Keychain deletion ran.

## Preserved project

The Superset-owned directory contained `supertest`, with one initial empty commit,
no tracked files or uncommitted work, and two linked worktrees. All were moved to:

```text
/Users/{{mstack:MAC_USER}}/Developer/recovered-from-superset-20261026/
  projects/supertest/
  worktrees/supertest/charming-daffodil-c735b09a/
  worktrees/supertest/set-up-superset-workspace-359a0669/
```

`git worktree repair` updated the moved Git links. All three working directories
retain the same HEAD and pass clean status checks. This directory contains
retained project data, not an installed Superset runtime.

## Verification and scope

See [mac.json](mac.json) for exact removed paths, hook counts, hashes and project
preservation. Protected Mac Codex config/auth, Claude account files, shell
configuration, Paseo configuration and pairing key, mise, and the checked app
manifests are unchanged. Claude's non-hook settings were preserved structurally.

The follow-up scan found no Superset references in the checked agent configuration
locations, dedicated Library residue, or launch jobs. Ubuntu has no Superset
executable on PATH and no `~/.superset` state. Downloads was not scanned: that
directory was macOS privacy-protected at the preceding inventory. OS-managed
application history and external account/subscription state were not modified.

App binaries, login state and runtime databases were deleted without a retained
backup. Reinstalling would require a new request; do not restore the obsolete
proposal or run the retirement helper as a startup/health check.

`retire_mac.py` is the completed one-time operation, guarded against replay by
the receipt and exact application identity. It is retained only for audit.
