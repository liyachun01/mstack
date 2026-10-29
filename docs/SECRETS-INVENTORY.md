# Secrets inventory and recovery proposal

Metadata-only review, 2026-10-04. No secret contents read, copied, printed, hashed,
rotated, deleted or changed by this review. No backup/export performed. This is
not a vulnerability scan or proof that secrets never appeared in earlier logs.

## Where credentials belong

- Human UI passwords: use your existing password manager, for example macOS
  Passwords. Record service name, local URL and login identity privately there,
  not in Git, runbooks, Basic Memory, PKM or chat. No new vault app/server needed.
- Service originals: ignored `.secrets/` in this repository, with restricted
  permissions. Existing container secret delivery remains unchanged.
- Future n8n provider integrations: create credentials in the n8n Credentials UI
  only when the specific connection is approved. Workflow JSON should reference
  credential bindings rather than embed tokens/headers; scrub names/IDs and
  execution data before publishing an export. No provider credentials created now.
- Existing DeepSeek auth/settings remain in the separately approved retained
  `/home/developer/.dsh` home. Do not relocate, reset or copy them into n8n. Its
  historical backups can contain credentials/private conversations.

No need to log into every component. PostgreSQL, graph adapters and gateway use
existing machine credentials, not new UI accounts. Basic Memory integration is
deferred. Notion/AppFlowy/provider authentication waits for those separate steps.

## Observed file metadata

Absolute prefix: `/home/developer/workspace/mcp-stack/.secrets/`.
Directory: **0700**, numeric owner **501:501**. All files below: owner 501:501.
Git ignore checks passed for the owner-password file and n8n encryption key.
Ignored files are **not encrypted**, not backed up by Git, and readable by the
owner/root. Directory 0700 restricts ordinary traversal; do not call 0644 ideal
secret permissions or assume this protects against privileged/container access.

| File name only | Mode | Purpose / consumer |
| --- | --- | --- |
| `postgres_password` | 0644 | Existing stack PG administrator secret; preserve shared service databases |
| `basic_memory_password` | 0644 | Existing Basic Memory DB login; PG/Basic Memory delivery remains untouched |
| `agentgateway-client-key` | 0600 | Stack gateway client authentication; no automatic n8n credential copy |
| `graphify-http-backend-key` | 0600 | Gateway↔Graphify adapter authentication |
| `codegraph-http-backend-key` | 0600 | Gateway↔CodeGraph adapter authentication |
| `n8n_password` | 0600 | **n8n database login**, not the UI owner password |
| `n8n_encryption_key` | 0600 | Recovery-critical encryption key for n8n stored integration credentials |
| `n8n_runner_token` | 0600 | Reserved app/task-runner authentication; ordinary runner still absent |
| `n8n_user_password` | 0644 | Newly observed user-created owner-password file; contents not inspected; use password manager instead |

The three n8n service originals were previously copied by the approved initializer
to Docker named volume `mcp-stack-n8n-secrets`, delivered read-only at
`/run/secrets/` to UID/GID 1000. Prior qualification verified directory 0700,
files 0600 and exact source equality. That volume is not a password manager or
backup; no new copy/inspection performed by this inventory. Preserve the
encryption key together with the n8n DB and app volume—do not regenerate it as
ordinary housekeeping. [Official encryption-key guidance](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key.md).

## Permission/removal proposal — not executed

1. Privately save and verify the n8n owner login in your password manager. You
   already reported creating/logging into the owner account; the agent has not
   authenticated or independently qualified that account.
2. Separately approve hardening only the known 0644 files after rechecking
   numeric ownership and each container consumer. Same-owner Basic Memory and
   PG delivery need review; no blanket recursive chmod or service restart.
3. Once you confirm the password-manager entry works, separately approve removal
   of **only** `.secrets/n8n_user_password`. Do not confuse it with
   `.secrets/n8n_password` or the encryption key. No removal now; deleting a file
   cannot guarantee erasure from snapshots/backups.
4. If a password/token was actually exposed or reused, propose that credential's
   coordinated rotation and consumer update independently. No mass rotation.

## Encrypted off-machine backup plan — not executed

Choose a destination and an already available encryption/backup tool first.
Do not install a vault/encryption CLI, export credentials or upload private data
without its concrete proposal. An archive copied elsewhere without encryption
is not sufficient. Keep recovery credentials in your password manager, separate
from the backup; don't lose the only decryption key together with this machine.

Proposed recovery unit for n8n:

1. Scoped consistent dump of database `n8n` using existing PG18 tools, protected
   role metadata needed to recreate its own login, plus persistent
   `mcp-stack-n8n-data` and the **original** n8n encryption key. Coordinate a
   checkpoint; any write pause/lifecycle step needs its own approval.
2. Protect service credentials and the named-secret-volume recovery recipe.
   Do not include unrelated databases or {{mstack:CLIENT_REPO}}. Keep secret-free workflow
   source/config in version control separately; Git isn't runtime-state recovery.
3. Manifest: versions, selected volumes/DB, time, sizes and protected checksums.
   Stage in a unique ignored 0700 backup directory with private 0600 artifacts;
   encrypt, verify locally, then transfer only to the selected private destination.
4. Restore into independently approved isolated storage/database, never over
   live shared PG. Verify owner login, selected workflow and encrypted credential
   recovery without paid requests before declaring backups usable.

Basic Memory recovery additionally needs its DB **and** Markdown knowledge
files; attachments/PKM require their own plan later. DeepSeek's retained home and
private sessions are a separate recovery unit, never bundled/published casually.
Existing `backups/` contains private operational archives/metadata; neither full
current-owner recovery nor encrypted off-machine restore is qualified yet.

Suggested cadence after qualification: backup after useful credential/workflow
changes and before upgrades; test isolated restore periodically. No scheduler,
remote upload, retention deletion or sync enabled now. See the
[operations recovery procedure](OPERATIONS-RUNBOOK.md#9-export-cleanup-restore-and-migration-flow).
