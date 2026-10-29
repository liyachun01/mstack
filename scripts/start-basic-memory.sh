#!/bin/sh
set -eu

task_memory_password="$(cat /run/secrets/basic_memory_password)"
# The approved DB preparation generates hexadecimal credentials. Refuse other
# characters rather than silently constructing a malformed connection URL.
case "$task_memory_password" in
  ''|*[!0-9a-fA-F]*)
    printf '%s\n' 'Expected a nonempty hexadecimal database secret.' >&2
    exit 1
    ;;
esac
export BASIC_MEMORY_DATABASE_URL="postgresql+asyncpg://basic_memory:${task_memory_password}@postgres:5432/basic_memory"
unset task_memory_password
exec "$@"
