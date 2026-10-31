"""{{mstack:CLIENT_C_APP}} MCP client (design 017): token storage, refresh and MCP framing. {{mstack:CLIENT_C_APP}} is never reached."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import {{mstack:CLIENT_C_FOLDER}}


class Client(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / 'secrets' / '{{mstack:CLIENT_C_FOLDER}}-oauth.json'

    def tearDown(self):
        self.dir.cleanup()

    def state(self, **kw):
        s = {'client_id': 'c1', 'token_endpoint': 'https://auth.test/token', 'resource': {{mstack:CLIENT_C_FOLDER}}.MCP_URL,
             'access_token': 'old', 'refresh_token': 'r1', 'expires_at': int(time.time()) + 3600}
        s.update(kw)
        {{mstack:CLIENT_C_FOLDER}}.save(s, self.path)
        return s

    def test_secrets_file_is_private(self):
        self.state()
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_expired_token_refreshes_and_keeps_rotated_refresh(self):
        self.state(expires_at=int(time.time()) - 10)
        seen = {}

        def fake(url, data=None, headers=None, form=False, timeout=60):
            seen.update(url=url, data=data, form=form)
            return 200, {}, json.dumps({'access_token': 'new', 'refresh_token': 'r2', 'expires_in': 3600}).encode()

        with patch.object({{mstack:CLIENT_C_FOLDER}}, '_http', fake):
            self.assertEqual({{mstack:CLIENT_C_FOLDER}}.token(self.path), 'new')
        self.assertEqual((seen['data']['grant_type'], seen['data']['refresh_token'], seen['form']),
                         ('refresh_token', 'r1', True))
        self.assertEqual({{mstack:CLIENT_C_FOLDER}}.load(self.path)['refresh_token'], 'r2')

    def test_fresh_token_is_not_refreshed(self):
        self.state()
        with patch.object({{mstack:CLIENT_C_FOLDER}}, '_http', side_effect=AssertionError('no network')):
            self.assertEqual({{mstack:CLIENT_C_FOLDER}}.token(self.path), 'old')

    def test_sse_reply_is_matched_by_id(self):
        self.state()
        body = (b': keep-alive\n\nevent: message\ndata: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n'
                b'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"send_message"}]}}\n\n')
        with patch.object({{mstack:CLIENT_C_FOLDER}}, '_http', return_value=(200, {'Content-Type': 'text/event-stream'}, body)):
            out = {{mstack:CLIENT_C_FOLDER}}.MCP(self.path).rpc('tools/list')
        self.assertEqual(out['transport'], 'sse')
        self.assertEqual(out['result']['tools'][0]['name'], 'send_message')

    def test_rpc_error_raises(self):
        self.state()
        body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32601, 'message': 'nope'}}).encode()
        with patch.object({{mstack:CLIENT_C_FOLDER}}, '_http', return_value=(200, {'Content-Type': 'application/json'}, body)):
            with self.assertRaises(RuntimeError):
                {{mstack:CLIENT_C_FOLDER}}.MCP(self.path).rpc('tools/list')


if __name__ == '__main__':
    unittest.main()
