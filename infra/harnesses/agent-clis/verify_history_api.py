"""Read-only protocol proof: installed CLI can list retained thread records."""
from pathlib import Path
import json
import selectors
import subprocess
import time

process = subprocess.Popen([str(Path.home() / '.local/bin/codex'),
                            'app-server', '--listen', 'stdio://'],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, text=True, bufsize=1)
selector = selectors.DefaultSelector()
selector.register(process.stdout, selectors.EVENT_READ)
def send(value):
    process.stdin.write(json.dumps(value) + '\n')
    process.stdin.flush()
def receive(request_id):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if not selector.select(timeout=1):
            continue
        line = process.stdout.readline()
        if not line:
            raise RuntimeError('App server exited before response')
        value = json.loads(line)
        if value.get('id') == request_id:
            if 'error' in value:
                raise RuntimeError(str(value['error']))
            return value['result']
    raise TimeoutError('App-server read timed out')
try:
    send({'id': 1, 'method': 'initialize', 'params': {
        'clientInfo': {'name': 'mstack_history_check', 'version': '1.0'},
        'capabilities': {'experimentalApi': True}}})
    receive(1)
    send({'method': 'initialized'})
    send({'id': 2, 'method': 'thread/list', 'params': {'limit': 100, 'sourceKinds': []}})
    result = receive(2)
    print(json.dumps({'thread_list_count': len(result.get('data', [])),
                      'has_more': bool(result.get('nextCursor')),
                      'model_request_sent': False}))
finally:
    process.stdin.close()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=5)
