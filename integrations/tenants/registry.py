"""Authenticate a session before selecting a server-owned tenant directory."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re

SLUG = re.compile(r'[a-z][a-z0-9-]{0,62}')


def read_bootstrap(fd=0):
    # Read only the first line. Buffered reads could swallow MCP initialization.
    data = bytearray()
    while len(data) < 4096:
        char = os.read(fd, 1)
        if char == b'\n':
            return json.loads(data)
        if not char:
            break
        data.extend(char)
    raise ValueError('Invalid tenant authentication')


def authenticate(registry, supplied):
    if not isinstance(supplied, dict) or set(supplied) != {'tenant', 'token'}:
        raise ValueError('Invalid tenant authentication')
    tenant, token = supplied['tenant'], supplied['token']
    if not isinstance(tenant, str) or not SLUG.fullmatch(tenant):
        raise ValueError('Invalid tenant authentication')
    if not isinstance(token, str) or not re.fullmatch(r'[0-9a-f]{64}', token):
        raise ValueError('Invalid tenant authentication')
    if registry.get('version') != 1:
        raise ValueError('Invalid tenant registry')
    entry = registry.get('tenants', {}).get(tenant, {})
    expected = entry.get('token_sha256', '')
    actual = hashlib.sha256(token.encode()).hexdigest()
    if not isinstance(expected, str) or not hmac.compare_digest(actual, expected):
        raise ValueError('Invalid tenant authentication')
    if entry.get('enabled') is not True:
        raise ValueError('Invalid tenant authentication')
    return tenant, entry


def tenant_file(root, tenant, name):
    root = Path(root).resolve(strict=True)
    folder = root / 'tenants' / tenant
    path = folder / name
    if folder.is_symlink() or path.is_symlink() or not path.is_file():
        raise ValueError('Invalid tenant file')
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(folder) or not folder.is_relative_to(root):
        raise ValueError('Invalid tenant file')
    return resolved
