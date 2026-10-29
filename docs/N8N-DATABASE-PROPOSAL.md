# n8n database provisioning — completed

Prepared on 2026-10-01; **approved and completed on 2026-10-04** following the user's "Then install it!" response to the pending database-first sequence. Guided setup step 1 is done; application/network/task-runner installation remains a separately proposed step. Do not rerun provisioning: the script intentionally refuses existing objects/password files.

## Completed outcome (2026-10-04)

- Executed `bash infra/n8n/provision-database.sh --approved-database-only` against the existing pinned, healthy PostgreSQL **18.6** container. No image pull, network change or service restart.
- Created database/login `n8n`, owned by the new restricted login, with no superuser/create-DB/create-role/replication/bypass-RLS privileges. New public-schema/database grants are restricted to its owner; no existing DB/role flags or ACLs changed.
- Actual TCP/password login, transactional create/insert/identity check/rollback, catalog cross-database denials and denied `n8n` login to `basic_memory` passed. No permanent probe table or Basic Memory application/tool test.
- New `.secrets/n8n_password` is **0600**, under the existing **0700** secret directory. Existing secrets and protected files unchanged; no password printed or passed in argv.
- Restricted metadata backup and secret-free qualification: `backups/n8n-db-before-20261004T083802Z/globals.sql` and `qualification.json`, **0700** directory / **0600** files. The globals dump includes password verifiers: do not display/commit or restore wholesale over the shared instance.
- All **21** retained container IDs/status/start times/restart counts/ports/networks match the pre-step baseline. Existing database owners/ACLs and role flags, protected project files/secrets and the full retained DeepSeek home manifest match too.
- Data-preserving rollback remains the separately approved `ALTER ROLE n8n NOLOGIN` below; no rollback, deletion or cleanup performed. The app/UI is **not installed** by this DB step. [Next exact app/network proposal](N8N-APP-SETUP-PROPOSAL.md).

The original bounded scope below is retained for audit, not another pending database approval.

## Target and prerequisite evidence

- Existing macOS OrbStack container `mcp-stack-postgres-1`, reached from Ubuntu with `macctl run docker`. Installed PostgreSQL **18.6** + pgvector **0.8.6**, image `pgvector/pgvector:0.8.6-pg18-trixie@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff`.
- Read-only inspection: exact image running healthy; `n8n` database/login absent; `basic_memory` database has no PUBLIC grants. Recheck before mutation; refuse collisions rather than adopting existing objects.
- n8n needs schema/table migration permissions in its own DB, not superuser. [Official database policy](https://docs.n8n.io/deploy/host-n8n/configure-n8n/choose-n8ns-database).
- No package/image/model installation, toolchain change, port allocation, PG restart, network change, n8n application migration or Supabase access.

## Exact files, command and changes

Prepared `infra/n8n/provision-database.sh` and `infra/n8n/provision-database.sql`; no Compose edits or addition to PG's initialization directory. After explicit approval, from `/home/developer/workspace/mcp-stack`:

```sh
bash infra/n8n/provision-database.sh --approved-database-only
```

The flag guards execution, not a substitute for user approval. The wrapper:

1. Checks exact PG image/health, PG major, and absence of both new names.
2. Creates ignored `backups/n8n-db-before-<UTC timestamp>/globals.sql` with `pg_dumpall -U postgres --globals-only`, directory `0700`/file `0600`. Includes password verifiers: never display/commit or restore wholesale over the shared instance.
3. Creates only ignored `.secrets/n8n_password`, random 64-character hex, `0600`. Refuses existing files, changes no other password/file or existing secret-directory permissions. Existing container-local admin socket authentication is reused; the app receives no admin credential.
4. Creates login `n8n` with `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`, no memberships. Creates database `n8n`, owner `n8n`, from `template0`. Removes PUBLIC access only on this **new** DB/schema; owner can perform n8n migrations. No vector extension needed for workflow metadata.
5. Sends the new password through stdin into child process environments, never argv/output. Trusted container/engine administrators can still inspect processes; environments are not a vault.

Persistence: existing `mcp-stack-postgres-data` volume; no new volume. Existing `127.0.0.1:55322` publication unchanged. App credentials/encryption-key mounting and network reachability require later proposals.

## Verification and impact

- Check ownership/role flags and catalog CONNECT denial both ways between `n8n` and `basic_memory`.
- Test actual password-authenticated TCP login **inside PG** at `127.0.0.1:5432`, not host routing. Create/insert/check a probe table inside a transaction in `n8n`, then roll it back. Test denied connection to `basic_memory`, without reading its data or calling Basic Memory.
- Compare all retained container IDs/start times/status/network/ports and existing DB owners/ACLs before/after. Current PG, Basic Memory, graph/gateway and all 16 stopped containers must stay unchanged. Report exact objects, grants, files and verification/failures afterward; do not run Basic Memory application tests.
- PG CPU/RAM/storage and administrator trust are shared. Per-service DBs are logical separation, not independent-instance isolation; denial to default maintenance DBs is not claimed. Provisioning does not qualify app migrations or resource performance.

## Failure and data-preserving rollback

`CREATE DATABASE` cannot share the role-creation transaction. Failures may leave a role/DB/secret; stop, report exact residue and keep secret-free diagnostics. Do not auto-drop, rotate, retry/reuse or grant more privileges. A retained password file deliberately blocks blind reruns.

No service exists to stop at this step. If cancellation/failure requires disabling the new login, separately approve this exact **new role only** rollback:

```sh
macctl run docker exec mcp-stack-postgres-1 psql -X -U postgres -d postgres \
  -v ON_ERROR_STOP=1 -c 'ALTER ROLE n8n NOLOGIN;'
```

Keep DB/role/secret/backup for diagnosis or later use. No global metadata restore, database drop, volume deletion or rollback of unrelated PG data. Complete removal requires scoped approval. Stop after the after-report and present the next network/application proposal.
