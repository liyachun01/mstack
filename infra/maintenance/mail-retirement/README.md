# AI mail retirement — 2026-10-15

The user explicitly requested removal of all Inbox Zero and TimeCyber/email-mcp
setup, their Microsoft registrations and their Google connections. Earlier mail
setup/preservation instructions are superseded. Do not restart onboarding.

## Completed

- Deleted **TimeCyber Mail MCP** and **Inbox Zero Personal** in Entra after
  matching each client ID to its private local configuration. Entra confirmed
  both deletions; refreshing All applications shows neither app.
- Revoked the dedicated Inbox Zero Google grant through Google's official endpoint
  (HTTP 200), using the stored token only in memory. No mailbox data was requested.
- Revoked **TimeCyber Mail MCP** in the verified Gmail account's App passwords UI;
  the named entry and its Revoke control are absent afterward.
- Stopped and removed exactly Inbox Zero's web, Redis and Redis HTTP containers,
  its `inbox_zero` database and login, dedicated Redis volume and two mail-only
  networks. Detached only the dedicated mail network from shared PostgreSQL.
- Removed the three unused mail-specific image references after verifying no
  remaining container used them. No broad pruning or Compose down occurred.
- Deleted both local runtime/source trees, launch/config files, credential files,
  caches and app-specific backups. Only retirement README markers remain under
  their previous infra paths. Removed mail environment values from nine entries
  in historical shared container snapshots, preserving unrelated entries.

## Google client cleanup completed

Deleted **Inbox Zero Local** after matching the full client ID and project to
its former private config. Google's confirmation was completed and the active
client list now says **No OAuth clients to display**. No matching downloaded
client JSON remained in either machine's Downloads folder. Local client secrets
and tokens were deleted. All six user-requested retirement items are complete.

## Preservation and checks

All 27 unrelated Docker containers preserve their IDs, states and start times.
Shared PostgreSQL and the existing databases for Basic Memory, n8n and Windmill
remain. Its pre-mail recovery copy was moved from the removed Inbox Zero tree to
ignored `infra/postgres/.state/recovery-20261009` (private files); the after-mail
copy of globals was removed with the mail setup. The toolchain rollback archive
contains no mail-specific files and remains untouched.

The retained PostgreSQL base config now declares the same existing external
volume, ARM64 platform and no-pull policy previously carried by the mail overlay.
`docker compose -f compose.yaml config --quiet` passes; no database restart ran.
No shared OpenCodex/DeepSeek key or native harness configuration was changed.
Mailboxes, messages, subscriptions and other provider apps remain untouched.

Final verification: zero TimeCyber runtime processes; no mail containers, volumes,
networks, database role or private credential directories remain. The only files
at the former infra locations are retirement README markers. Temporary native UI
exports, target identifiers and cloud-operation helpers were removed.

Evidence: `qualification.json`, `cloud-status.json`, `google-revocation.json`, `local-removal.json`,
`filesystem-removal.json`, and `credential-copy-cleanup.json`.
Provider deletions use their normal provider retention policies; app runtime,
private credentials and dedicated database are removed locally. There is no
automatic rollback or retained usable mail credential bundle.

## Stored mailbox records removed — 2026-10-15

On the user's follow-up request, verified the mail database and role are absent
and both installations contain only retirement markers. Removed old per-account
connection/onboarding summaries from `AGENTS.md` and `docs/HANDOVER.md`, keeping
only generic removal evidence and unrelated service recovery information. No
mailbox address or credential is retained in this receipt. Unrelated service
login records, personal documents and the provider accounts were not changed.
See `mailbox-records-cleanup.json`.
