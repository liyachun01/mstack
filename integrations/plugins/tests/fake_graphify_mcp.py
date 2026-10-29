"""Stand-in for a Graphify tenant session: query_graph answers in the real text format."""
import json
import sys

NODES = [('Cart', 'market/cart.py', 'L4', 'Cart'), ('.subtotal_cents()', 'market/cart.py', 'L18', 'Cart'),
         ('Catalog', 'market/catalog.py', 'L12', 'Catalog'), ('MarketTests', 'tests/test_market.py', 'L7', 'Tests')]
for line in sys.stdin:
    msg = json.loads(line)
    if 'id' not in msg:
        continue
    if msg['method'] == 'initialize':
        result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'fake'}}
    else:
        q = msg['params']['arguments']['question'].lower()
        hits = [n for n in NODES if any(w in n[0].lower() or w in n[1] for w in q.split())]
        text = 'Graph: tenants/x/graph.json | %d nodes found\n\n' % len(hits) + '\n'.join(
            'NODE %s [src=%s loc=%s community=%s]' % n for n in hits) + '\nEDGE Cart --contains--> .subtotal_cents()'
        result = {'content': [{'type': 'text', 'text': text}]}
    print(json.dumps({'jsonrpc': '2.0', 'id': msg['id'], 'result': result}), flush=True)
