"""Verify pre-cutover session bytes are retained, allowing active append-only logs."""
from pathlib import Path
import hashlib
import json
import sys

manifest = json.loads(Path(sys.argv[1]).read_text())
base = Path.home() / '.codex'
failures = []
appended = 0
for relative, before in manifest.items():
    path = base / relative
    if not path.is_file() or path.stat().st_size < before['size']:
        failures.append(relative)
        continue
    digest = hashlib.sha256()
    remaining = before['size']
    with path.open('rb') as stream:
        while remaining:
            block = stream.read(min(1024 * 1024, remaining))
            if not block:
                break
            digest.update(block)
            remaining -= len(block)
    if digest.hexdigest() != before['sha256']:
        failures.append(relative)
    appended += path.stat().st_size > before['size']
result = {'preserved': len(manifest) - len(failures), 'failed': len(failures),
          'append_only_growth': appended}
print(json.dumps(result))
raise SystemExit(bool(failures))
