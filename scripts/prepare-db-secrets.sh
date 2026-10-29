#!/usr/bin/env bash
set -euo pipefail

task_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$task_repo_root"
umask 077
mkdir -p .secrets
chmod 700 .secrets

for task_secret in postgres_password basic_memory_password; do
  if [[ -e ".secrets/$task_secret" ]]; then
    [[ -f ".secrets/$task_secret" && -s ".secrets/$task_secret" ]] || {
      printf 'Invalid existing secret file: %s\n' "$task_secret" >&2
      exit 1
    }
    printf 'Keeping existing %s\n' "$task_secret"
  else
    # Noclobber protects existing credentials if another invocation races us.
    (set -o noclobber; openssl rand -hex 32 > ".secrets/$task_secret")
    printf 'Created %s (contents not displayed)\n' "$task_secret"
  fi
  # Compose file secrets retain source permissions. The directory remains 0700;
  # the mounted file must be readable by the image's postgres user.
  chmod 644 ".secrets/$task_secret"
done
