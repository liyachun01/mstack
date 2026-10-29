# Paradev removed — 2026-10-27

The user found Paradev (Superset 2.0.0) hard to use and requested removing it
everywhere, returning to Codex Desktop and Claude Desktop. Paradev had replaced
Paseo earlier the same day.

## Removed

- orb-devbox: `paradev hosts remove orb-devbox` removed the systemd user service,
  stopped the host and revoked its API key. `retire.py` then removed
  `~/superset`, `~/.superset`, the `~/.zshrc` PATH line and the
  `~/.node_modules` adapter link (receipt: `linux.json`).
- Mac: `retire.py` stopped the desktop app and removed `/Applications/Superset.app`,
  `~/.superset` (including CLI credentials) and Superset Library data
  (receipt: `macos.json`).
- Both hosts: Paradev hooks in Claude, Codex, Cursor, Gemini, Factory, Devin,
  Mastra, Muse and Grok configuration (hook-only JSON files were deleted),
  14 `superset-*` skills, the Claude `superset` skill and the Amp/Pi/Oh My
  Pi/Grok extensions; temporary sockets and session logs.
- Projects: `.superset/attachments` copies created by session import in
  `{{mstack:CLIENT_C_FOLDER}}`, `KIKI` and `{{mstack:CLIENT_REPO}}` ({{mstack:CLIENT_REPO}}'s own tracked `.superset` config
  and scripts were kept); the `.git` folders created only for Paradev in
  `Developer/{Recovered Codex chats,{{mstack:CLIENT_C_FOLDER}},codexwork}` and `Documents/KIKI`;
  the empty `mstack` root commit (`refs/heads/main` deleted, so `mstack` has no
  commits again; its pre-existing `refs/codex` checkpoint ref is untouched).
- Repo: `infra/paradev` (README, import receipts, verifier and pinned ACP
  adapters) and its `.gitignore` entries.

Trashed items were lost when the Mac Trash was emptied during this cleanup;
none held user data beyond copies. The imported Paradev sessions existed only in
Paradev; native Codex/Claude histories are unchanged.

## Not done here

The Paradev cloud organization, its offline host entries, the user-created CLI
API key and the Pro subscription remain in the user's Paradev account.
