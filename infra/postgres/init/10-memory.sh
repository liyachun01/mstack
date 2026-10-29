#!/usr/bin/env bash
# The PostgreSQL entrypoint sources non-executable .sh files on an empty volume.
# Keep secret variables and shell options confined to a subshell.
(
  set -eu
  export BASIC_MEMORY_PASSWORD
  BASIC_MEMORY_PASSWORD="$(cat /run/secrets/basic_memory_password)"
  test -n "$BASIC_MEMORY_PASSWORD"

  # Read the password from the process environment, not a command-line argument.
  psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --no-psqlrc --set ON_ERROR_STOP=1 <<'SQL'
\getenv memory_password BASIC_MEMORY_PASSWORD
CREATE ROLE basic_memory LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
  PASSWORD :'memory_password';
ALTER DATABASE basic_memory OWNER TO basic_memory;
REVOKE ALL ON DATABASE basic_memory FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE basic_memory TO basic_memory;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO basic_memory;
CREATE EXTENSION IF NOT EXISTS vector;
SQL
)
