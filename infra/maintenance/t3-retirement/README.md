# T3 removed — 2026-10-26

The user explicitly requested removing T3 after Superset. T3 Code Beta 0.1.2
is removed from macOS. Paseo 0.13.0 remains the retained workspace application.
No replacement installation or provider login ran.

## Removed

- `/Applications/T3 Code (Beta).app` (bundle `com.t3tools.t3code`).
- `~/.t3`, including its `bin/t3` wrapper, app-managed Codex 0.156.1,
  T3 account tokens/secrets, thread databases, attachments, settings and caches.
- `~/Library/Application Support/t3code-v2` and
  `~/Library/Preferences/com.t3tools.t3code.plist`.

T3 was already closed and no background process or launch job was found. Its
worktree directory was empty and its one scratch directory had no files.
No independent agent configuration or shell file referenced the T3-owned runtime.
Four explicit T3 Keychain service-name checks found no matching items; no
Keychain mutation ran. No credentials or T3 runtime backup was retained.

## Preserved and verified

Mac Claude settings/account files, Codex config/auth, shell configuration,
Paseo configuration/pairing key, mise and the checked unrelated app manifests
retain the same hashes. No global agent configuration was edited.

The two external project paths recorded by T3,
`/Users/{{mstack:MAC_USER}}/Developer/codexwork` and `/Users/{{mstack:MAC_USER}}/{{mstack:CLIENT_C_FOLDER}}`, were not
removed or modified. Their directory identities are unchanged. No source
checkout or Git worktree needed moving.

Ubuntu has no T3 executable on PATH, no `~/.t3` and no matching user service
file. Its independent Codex CLI and configuration were not modified.

See [mac.json](mac.json) and [verification.json](verification.json): all four
removal targets are absent, no T3 process or dedicated residue was found in
the checked app/config/cache locations, Paseo is present, and Superset remains
absent. Downloads was not scanned because it was macOS privacy-protected during
the preceding inventory. OS-managed application history and cloud account state
were not changed. No model call, desktop input or container operation ran.

There is no app-state rollback. Reinstallation requires a new request.
`retire_mac.py` records the completed one-time cleanup and refuses replay;
do not use it as a startup or health check.
