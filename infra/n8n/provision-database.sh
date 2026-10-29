#!/usr/bin/env bash
# MUTATING: obtain the database-only approval in docs/N8N-DATABASE-PROPOSAL.md.
set -euo pipefail

[[ "${1:-}" == --approved-database-only && $# == 1 ]] || {
  printf '%s\n' 'Refusing execution: obtain explicit database-only approval first.' >&2
  exit 2
}
task_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
[[ "$task_repo_root" == /home/developer/workspace/mstack ]] || exit 2
cd -- "$task_repo_root"
umask 077
task_pg=(macctl run docker exec -i mcp-stack-postgres-1)
task_expected_image='pgvector/pgvector:0.8.6-pg18-trixie@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff'
task_actual="$(macctl run docker inspect mcp-stack-postgres-1 --format '{{.Config.Image}} {{.State.Status}} {{.State.Health.Status}}')"
[[ "$task_actual" == "$task_expected_image running healthy" ]] || {
  printf '%s\n' 'Unexpected PostgreSQL image/state; no provisioning performed.' >&2
  exit 1
}
task_preflight="$("${task_pg[@]}" psql -X -q -U postgres -d postgres -At -v ON_ERROR_STOP=1 <<'SQL'
SELECT current_setting('server_version_num')::int / 10000 = 18
  AND NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')
  AND NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'n8n');
SQL
)"
[[ "$task_preflight" == t ]] || {
  printf '%s\n' 'Database/role already exists or PG major differs; refusing to reuse/alter it.' >&2
  exit 1
}
[[ -d .secrets && ! -L .secrets && ! -e .secrets/n8n_password && ! -L .secrets/n8n_password ]] || exit 1
[[ ! -L backups ]] || exit 1
mkdir -p backups
task_backup_dir="backups/n8n-db-before-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 -- "$task_backup_dir"
# Includes password verifiers: ignored/restricted, never display contents.
(set -C; "${task_pg[@]}" pg_dumpall -U postgres --globals-only > "$task_backup_dir/globals.sql")
[[ -s "$task_backup_dir/globals.sql" ]] || exit 1
(set -C; openssl rand -hex 32 > .secrets/n8n_password)
chmod 600 .secrets/n8n_password
IFS= read -r task_password < .secrets/n8n_password
[[ "$task_password" =~ ^[0-9a-f]{64}$ ]] || exit 1

# Password travels via stdin into child environment, not argv/log output.
{
  printf '%s\n' "$task_password"
  command cat infra/n8n/provision-database.sql
} | "${task_pg[@]}" sh -c 'IFS= read -r MCP_STACK_N8N_PASSWORD; export MCP_STACK_N8N_PASSWORD; exec psql -X -q -U postgres -d postgres -v ON_ERROR_STOP=1'

task_verification="$("${task_pg[@]}" psql -X -q -U postgres -d n8n -At -v ON_ERROR_STOP=1 <<'SQL'
SELECT EXISTS (
  SELECT FROM pg_roles WHERE rolname = 'n8n' AND rolcanlogin
  AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
  AND NOT rolreplication AND NOT rolbypassrls
) AND pg_get_userbyid((SELECT datdba FROM pg_database WHERE datname = 'n8n')) = 'n8n'
  AND NOT has_database_privilege('n8n', 'basic_memory', 'CONNECT')
  AND NOT has_database_privilege('basic_memory', 'n8n', 'CONNECT');
SQL
)"
[[ "$task_verification" == t ]] || exit 1
{
  printf '%s\n' "$task_password"
  printf '%s\n' 'BEGIN;' 'CREATE TABLE public.mcp_stack_n8n_probe (id integer);' \
    'INSERT INTO public.mcp_stack_n8n_probe VALUES (1);' \
    "DO \$probe\$ BEGIN IF current_user <> 'n8n' OR current_database() <> 'n8n' OR (SELECT count(*) FROM public.mcp_stack_n8n_probe) <> 1 THEN RAISE EXCEPTION 'Identity/write check failed'; END IF; END; \$probe\$;" \
    'ROLLBACK;'
} | "${task_pg[@]}" sh -c 'IFS= read -r PGPASSWORD; export PGPASSWORD; exec psql -X -q -h 127.0.0.1 -U n8n -d n8n -v ON_ERROR_STOP=1'
if printf '%s\n' "$task_password" | "${task_pg[@]}" sh -c \
  'IFS= read -r PGPASSWORD; export PGPASSWORD; exec psql -X -q -h 127.0.0.1 -U n8n -d basic_memory -v ON_ERROR_STOP=1 -c "SELECT 1"' >/dev/null 2>&1; then
  printf '%s\n' 'Unexpected Basic Memory database access; stop and investigate.' >&2
  exit 1
fi
unset task_password
printf '%s\n' 'New n8n database/login: authenticated transactional DDL/write and cross-database denial checks passed.'
printf 'Restricted metadata backup: %s/globals.sql\n' "$task_backup_dir"
printf '%s\n' 'Stop before application installation. No image, container or network changes performed.'
