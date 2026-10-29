#!/usr/bin/env bash
set -euo pipefail

# Codex's current execution domain is Ubuntu; Docker is on the macOS host.
task_host_repo=/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack
task_compose=(macctl run docker compose --project-directory "$task_host_repo" -f "$task_host_repo/compose.yaml")

"${task_compose[@]}" exec -T postgres psql -U postgres -d basic_memory \
  --no-psqlrc --set ON_ERROR_STOP=1 <<'SQL'
SELECT version();
SHOW data_directory;
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication
FROM pg_roles WHERE rolname = 'basic_memory';
DO $verification$
BEGIN
  IF current_setting('server_version_num')::int / 10000 <> 18 THEN
    RAISE EXCEPTION 'Expected PostgreSQL 18';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector' AND extversion = '0.8.6') THEN
    RAISE EXCEPTION 'Expected pgvector 0.8.6';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'basic_memory'
      AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
      AND NOT rolreplication AND NOT rolbypassrls
  ) THEN
    RAISE EXCEPTION 'Application role has unexpected privileges';
  END IF;
END
$verification$;
SQL

# Password exists only in the child environment, never output or command args.
"${task_compose[@]}" exec -T postgres sh -c \
  'PGPASSWORD="$(cat /run/secrets/basic_memory_password)" exec psql -h 127.0.0.1 -U basic_memory -d basic_memory --no-psqlrc --set ON_ERROR_STOP=1' <<'SQL'
SELECT current_user, current_database();
BEGIN;
CREATE TEMPORARY TABLE mcp_stack_verify_vectors (id integer, embedding vector(3));
INSERT INTO mcp_stack_verify_vectors VALUES (1, '[1,0,0]'), (2, '[0,1,0]');
SELECT id, embedding <-> '[1,0,0]'::vector AS distance
FROM mcp_stack_verify_vectors ORDER BY distance;
DO $verification$
BEGIN
  IF current_user <> 'basic_memory' OR current_database() <> 'basic_memory' THEN
    RAISE EXCEPTION 'Unexpected application identity';
  END IF;
  IF (SELECT id FROM mcp_stack_verify_vectors ORDER BY embedding <-> '[1,0,0]'::vector LIMIT 1) <> 1 THEN
    RAISE EXCEPTION 'Vector distance test failed';
  END IF;
END
$verification$;
ROLLBACK;
SQL

macctl run nc -z 127.0.0.1 55322
printf '%s\n' 'PostgreSQL 18, pgvector, role, authenticated writes, vector search, and host TCP checks passed.'
