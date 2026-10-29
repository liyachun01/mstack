#!/usr/bin/env bash
# One-shot approved macOS OrbStack app setup; never a general service launcher.
set -euo pipefail
task_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
[[ "$task_repo_root" == /home/developer/workspace/mstack ]] || exit 2
cd -- "$task_repo_root"
exec python3 -I -B "$task_repo_root/integrations/n8n/app_setup.py" "$@"
