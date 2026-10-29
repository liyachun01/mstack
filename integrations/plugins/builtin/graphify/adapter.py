"""memory.long joint over the project's shared Graphify tenant (contract: integrations/plugins/contracts.md).

Talks MCP over stdio to `integrations/tenants/launch.py --project <root> --tool graphify`,
which serves the project's own registered graph snapshot. Querying is read-only.
Indexing is an explicit owner step (offline `graphify update` on committed code, then a
tenant registration), never something a query triggers; `forget` is not supported on a
snapshot. An empty result does not mean the answer is absent from the code.
"""
from pathlib import Path
import re
import sys

STACK_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(STACK_ROOT/'integrations/plugins'))
from mcp_client import McpStdio  # noqa: E402

NODE = re.compile(r'^NODE (?P<label>.+?) \[src=(?P<src>\S+) loc=(?P<loc>\S+)(?: community=(?P<community>[^\]]*))?\]')


def launcher(scope):
    return [sys.executable, str(STACK_ROOT/'integrations/tenants/launch.py'),
            '--project', str(scope['root']), '--tool', 'graphify']


def query(scope, text, k=8, client=McpStdio):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('query needs non-empty text')
    if not scope.get('root'):
        raise ValueError('memory.long needs scope.root (the project checkout) to reach its tenant')
    session = client(launcher(scope))
    try:
        answer = session.tool('query_graph', {'question': text, 'token_budget': 1500}, raw=True)
    finally:
        session.close()
    hits = []
    for line in answer.splitlines():
        found = NODE.match(line.strip())
        if found:
            hits.append({'text': found['label'], 'source': '%s:%s' % (found['src'], found['loc']),
                         'community': found['community'], 'score': round(1 / (len(hits) + 1), 3)})
    return hits[:k]


def index(scope, sources):
    raise NotImplementedError(
        'Indexing is an explicit owner step: run `graphify update` offline on committed code, then '
        '`mstack tenant add --tool graphify --graph <graph.json>` (see docs/design/009-SERVICE-TESTS.md).')


def forget(scope, source):
    raise NotImplementedError('The Graphify tenant serves an immutable snapshot; re-index to drop a source.')
