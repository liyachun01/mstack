"""One-time private history inventory and configuration/database backup."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time

destination = Path(sys.argv[1])
destination.mkdir(parents=True, exist_ok=False, mode=0o700)
os.umask(0o077)
home = Path.home()
source = home / '.codex'
manifest = {}
for category in ('sessions', 'archived_sessions'):
    for path in (source / category).rglob('*'):
        if path.is_file():
            digest = hashlib.sha256()
            size = 0
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
                    size += len(block)
            manifest[str(path.relative_to(source))] = {'size': size, 'sha256': digest.hexdigest()}
(destination / 'session-manifest.json').write_text(json.dumps(manifest, indent=2))
for name in ('auth.json', 'config.toml', 'session_index.jsonl', '.codex-global-state.json'):
    if (source / name).is_file():
        shutil.copy2(source / name, destination / name)
for name in ('state_5.sqlite', 'thread_history_1.sqlite'):
    path = source / name
    if path.exists():
        # SQLite locking is not reliable on the Mac -> OrbStack shared mount.
        # Build a consistent backup on the native filesystem, then copy it.
        started = time.monotonic()
        def progress(status, remaining, total):
            if time.monotonic() - started > 30:
                raise RuntimeError('SQLite snapshot exceeded 30 seconds')
        try:
            with tempfile.TemporaryDirectory(prefix='mstack-codex-backup-') as temp:
                local = Path(temp) / name
                with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as src:
                    with sqlite3.connect(local) as dst:
                        src.backup(dst, pages=256, progress=progress)
                shutil.copy2(local, destination / name)
        except sqlite3.OperationalError:
            # Some app-owned databases cannot be opened by system SQLite.
            # Retain their originals; a live file bundle is NOT a consistent DB backup.
            for suffix in ('', '-wal', '-shm'):
                opaque = Path(str(path) + suffix)
                if opaque.is_file():
                    shutil.copy2(opaque, destination / (name + suffix + '.live-copy'))
            (destination / (name + '.note')).write_text(
                'System SQLite could not open this database. Originals untouched; '
                'live copies are supplemental, not a consistent restore image.\n')
for label, path in [('claude-settings.json', home / '.claude/settings.json')]:
    if path.is_file():
        shutil.copy2(path, destination / label)
link = home / '.local/bin/codex'
(destination / 'original-codex-link.json').write_text(json.dumps({
    'path': str(link), 'target': os.readlink(link) if link.is_symlink() else None,
    'exists': link.exists()}))
print(json.dumps({'host': sys.platform, 'session_files': len(manifest),
                  'session_bytes': sum(x['size'] for x in manifest.values()),
                  'private_snapshot': str(destination)}))
