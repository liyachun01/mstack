import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stdio_bridge


class Resp(io.BytesIO):
    def __init__(self, body, session='s-1'):
        super().__init__(body.encode())
        self.headers = {'mcp-session-id': session}
    def __enter__(self): return self
    def __exit__(self, *a): pass


class BridgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)
        (self.project / '.mstack/secrets').mkdir(parents=True)
        (self.project / '.mstack/stack.json').write_text('{"project": "market"}')
        (self.project / '.mstack/secrets/agentgateway-key').write_text('k123')
        self.sent = []

    def run_bridge(self, lines, reply):
        out = io.StringIO()
        def opener(req, timeout):
            self.sent.append(req)
            return reply(req)
        with patch.dict(os.environ, {'MSTACK_TASK': 'bafy-task-1'}):
            stdio_bridge.bridge(self.project, 'http://host.orb.internal:58080',
                                io.StringIO(''.join(json.dumps(l) + '\n' for l in lines)), out, opener)
        return [json.loads(l) for l in out.getvalue().splitlines()]

    def test_headers_session_and_sse(self):
        lines = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'},
                 {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                 {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}]
        out = self.run_bridge(lines, lambda req: Resp('event: message\ndata: {"jsonrpc":"2.0","id":%s,"result":{}}\n'
                                                      % json.loads(req.data)['id'] if b'"id"' in req.data else ''))
        self.assertEqual([o['id'] for o in out], [1, 2])                 # notification produced no output
        first, second = self.sent[0], self.sent[2]
        self.assertEqual(first.full_url, 'http://host.orb.internal:58080/mcp/projects/market')
        self.assertEqual(first.get_header('Host'), '127.0.0.1:58080')   # gateway's published host
        self.assertEqual(first.get_header('Authorization'), 'Bearer k123')
        self.assertEqual(first.get_header('X-mstack-task'), 'bafy-task-1')
        self.assertEqual(second.get_header('Mcp-session-id'), 's-1')

    def test_http_errors_become_jsonrpc_errors(self):
        def denied(req):
            raise urllib.error.HTTPError(req.full_url, 401, 'no', {}, io.BytesIO(b'bad key'))
        out = self.run_bridge([{'jsonrpc': '2.0', 'id': 7, 'method': 'tools/list'}], denied)
        self.assertEqual((out[0]['id'], out[0]['error']['code']), (7, -32000))
        self.assertIn('401', out[0]['error']['message'])


if __name__ == '__main__':
    unittest.main()
