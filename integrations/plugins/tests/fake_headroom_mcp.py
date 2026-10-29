"""Stand-in for the Headroom tenant MCP session: same tools and JSON shapes, store in a file."""
import hashlib
import json
from pathlib import Path
import sys

store = Path(sys.argv[1])
data = json.loads(store.read_text()) if store.exists() else {}
for line in sys.stdin:
    msg = json.loads(line)
    if 'id' not in msg:
        continue
    if msg['method'] == 'initialize':
        result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'fake'}}
    else:
        name, args = msg['params']['name'], msg['params']['arguments']
        if name == 'headroom_compress':
            key = hashlib.sha256(args['content'].encode()).hexdigest()[:24]
            data[key] = args['content']
            store.write_text(json.dumps(data))
            words = args['content'].split()
            body = {'compressed': ' '.join(words[:5]) + (' …' if len(words) > 5 else ''), 'hash': key,
                    'original_tokens': len(words), 'compressed_tokens': min(len(words), 6)}
        elif name == 'headroom_retrieve':
            body = ({'hash': args['hash'], 'original_content': data[args['hash']]} if args['hash'] in data
                    else {'error': 'expired or unknown hash', 'hash': args['hash']})
        else:
            body = {'error': 'Unknown tool'}
        result = {'content': [{'type': 'text', 'text': json.dumps(body)}]}
    print(json.dumps({'jsonrpc': '2.0', 'id': msg['id'], 'result': result}), flush=True)
