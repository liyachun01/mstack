"""A fake hosted-agent MCP server for conductor tests (design 017), built from the P1 receipt's tool list.

Loopback HTTP, MCP JSON-RPC over POST, Bearer auth, SSE answers for wait_message. Channels hold messages with
sequences; a scripted Agent answers each message sent through the API. Attachments go through an upload URL
(PUT) like the real flow. Nothing here reaches the real service.
"""
import http.server
import json
from pathlib import Path
import threading
import time

RECEIPT = Path(__file__).resolve().parents[3]/'runtime/receipts/2026-10-31-mst66-{{mstack:CLIENT_C_FOLDER}}-mcp-p1.json'
TOKEN = 'fake-token'
SCHEMAS = {
    'send_message': {'channelId': {}, 'text': {}, 'idempotencyKey': {}, 'replyToSequence': {}, 'attachmentIds': {}},
    'wait_message': {'channels': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'channelId': {}, 'afterSequence': {}}}}, 'timeoutSeconds': {}},
    'read_messages': {'channelId': {}, 'afterSequence': {}, 'limit': {}},
    'create_attachment_upload': {'channelId': {}, 'fileName': {}, 'contentType': {}, 'size': {}},
    'complete_attachment_upload': {'attachmentId': {}},
    'react_message': {'channelId': {}, 'sequence': {}, 'emoji': {}},
}


class FakeServer:
    """agent(text, attachments) -> list of reply texts (or None) the Agent writes after each API message."""

    def __init__(self, agent=None, time_scale=0.02):
        self.names = json.loads(RECEIPT.read_text())['tools']['names']
        self.agent = agent or (lambda text, files: ['```mstack-actions\n[]\n```'])
        self.scale, self.channels, self.keys, self.uploads, self.calls = time_scale, {}, {}, {}, []
        self.reactions, self.seq, self.cond = [], 0, threading.Condition()
        fake = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_PUT(self):
                body = self.rfile.read(int(self.headers.get('Content-Length') or 0))
                fake.uploads.setdefault(self.path.rsplit('/', 1)[-1], {})['body'] = body.decode()
                self.send_response(200); self.end_headers()

            def do_POST(self):
                if self.headers.get('Authorization') != 'Bearer ' + TOKEN:
                    self.send_response(401); self.end_headers(); return
                msg = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)))
                if 'id' not in msg:
                    self.send_response(202); self.end_headers(); return
                result, sse = fake.handle(msg['method'], msg.get('params') or {})
                body = json.dumps({'jsonrpc': '2.0', 'id': msg['id'], 'result': result})
                self.send_response(200)
                if sse:
                    self.send_header('Content-Type', 'text/event-stream')
                    data = ('event: message\ndata: %s\n\n' % body).encode()
                else:
                    self.send_header('Content-Type', 'application/json')
                    data = body.encode()
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = 'http://127.0.0.1:%d/mcp' % self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    # ---- state
    def add(self, channel, text, kind, via=None):
        with self.cond:
            self.seq += 1
            m = {'sequence': self.seq, 'text': text, 'author': {'kind': kind}}
            if via:
                m['via'] = {'kind': via}
            self.channels.setdefault(channel, []).append(m)
            self.cond.notify_all()
            return m

    def messages(self, channel):
        return list(self.channels.get(channel, []))

    # ---- MCP
    def handle(self, method, params):
        if method == 'initialize':
            return {'protocolVersion': '2025-06-18', 'serverInfo': {'name': 'fake-hosted-agent', 'version': '0'},
                    'capabilities': {'tools': {}}}, False
        if method == 'tools/list':
            return {'tools': [{'name': n, 'inputSchema': {'type': 'object', 'properties': SCHEMAS.get(n, {})}}
                              for n in self.names]}, False
        if method == 'tools/call':
            name, args = params['name'], params.get('arguments') or {}
            self.calls.append((name, args))
            out = getattr(self, 'tool_' + name)(args)
            return {'content': [{'type': 'text', 'text': json.dumps(out)}]}, name == 'wait_message'
        raise ValueError(method)

    def tool_send_message(self, a):
        key = a.get('idempotencyKey')
        if key and key in self.keys:
            return {'message': self.keys[key], 'duplicate': True}
        files = [self.uploads[i]['body'] for i in a.get('attachmentIds') or []]
        m = self.add(a['channelId'], a['text'], 'person', via='api')
        if key:
            self.keys[key] = m
        replies = self.agent(a['text'], files) or []
        for text in replies:
            self.add(a['channelId'], text, 'agent')
        return {'message': m}

    def tool_wait_message(self, a):
        deadline = time.time() + a.get('timeoutSeconds', 1) * self.scale
        wanted = a['channels']
        with self.cond:
            while True:
                found = [m for w in wanted for m in self.channels.get(w['channelId'], [])
                         if w.get('afterSequence') is None or m['sequence'] > w['afterSequence']]
                left = deadline - time.time()
                if found or left <= 0:
                    return {'messages': found}
                self.cond.wait(left)

    def tool_read_messages(self, a):
        after = a.get('afterSequence')
        return {'messages': [m for m in self.channels.get(a['channelId'], []) if after is None or m['sequence'] > after]}

    def tool_create_attachment_upload(self, a):
        aid = 'att%d' % (len(self.uploads) + 1)
        self.uploads[aid] = {'name': a['fileName'], 'size': a['size']}
        return {'attachmentId': aid, 'uploadUrl': self.url.replace('/mcp', '/upload/' + aid)}

    def tool_complete_attachment_upload(self, a):
        self.uploads[a['attachmentId']]['done'] = True
        return {'ok': True}

    def tool_react_message(self, a):
        self.reactions.append((a['sequence'], a['emoji']))
        return {'ok': True}
