"""compress joint over the project's shared Headroom tenant (contract: integrations/plugins/contracts.md).

Talks MCP over stdio to `integrations/tenants/launch.py --project <root> --tool headroom`,
which authenticates the project's own tenant in the shared `mstack-headroom` container.
Headroom takes no token budget: `budget_tokens` is reported against, not enforced.
"""
import json
from pathlib import Path
import re
import sys

STACK_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(STACK_ROOT/'integrations/plugins'))
from mcp_client import McpStdio  # noqa: E402
HANDLE = re.compile(r'[a-f0-9]{1,64}')


def launcher(scope):
    return [sys.executable, str(STACK_ROOT/'integrations/tenants/launch.py'),
            '--project', str(scope['root']), '--tool', 'headroom']


def _session(scope, client):
    if not scope.get('root'):
        raise ValueError('compress needs scope.root (the project checkout) to reach its tenant')
    return client(launcher(scope))


def compress(scope, text, budget_tokens=None, client=McpStdio):
    if not isinstance(text, str) or not text:
        raise ValueError('compress needs non-empty text')
    session = _session(scope, client)
    try:
        data = session.tool('headroom_compress', {'content': text})
    finally:
        session.close()
    summary = data['compressed'] if isinstance(data['compressed'], str) else json.dumps(data['compressed'])
    out = {'summary': summary, 'handle': data['hash'], 'original_tokens': data['original_tokens'],
           'compressed_tokens': data['compressed_tokens']}
    if budget_tokens is not None:
        out['over_budget'] = data['compressed_tokens'] > budget_tokens
    return out


def expand(scope, handle, client=McpStdio):
    if not isinstance(handle, str) or not HANDLE.fullmatch(handle):
        raise ValueError('Invalid compress handle')
    session = _session(scope, client)
    try:
        return session.tool('headroom_retrieve', {'hash': handle})['original_content']
    finally:
        session.close()
