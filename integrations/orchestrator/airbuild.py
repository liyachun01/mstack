"""{{mstack:CLIENT_C_APP}}'s public MCP server as an mstack client (design 017, MST-66).

Standard library only. `login` registers a public OAuth client (RFC 7591), runs the authorization-code flow with
PKCE through the owner's browser and a one-shot loopback listener, and stores the tokens in a 0600 file. `tools`
and `call` speak MCP JSON-RPC over streamable HTTP with that token, refreshing it when it has expired. Tokens are
never printed.

    python3 -I integrations/orchestrator/{{mstack:CLIENT_C_FOLDER}}.py login [--open-with "macctl run open"]
    python3 -I integrations/orchestrator/{{mstack:CLIENT_C_FOLDER}}.py tools
    python3 -I integrations/orchestrator/{{mstack:CLIENT_C_FOLDER}}.py call <tool> '<json arguments>'
    python3 -I integrations/orchestrator/{{mstack:CLIENT_C_FOLDER}}.py refresh
"""
import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MCP_URL = 'https://mcp.{{mstack:CLIENT_C_SITE}}/mcp'
RESOURCE_META = 'https://mcp.{{mstack:CLIENT_C_SITE}}/.well-known/oauth-protected-resource/mcp'
SECRETS = Path('.mstack/secrets/{{mstack:CLIENT_C_FOLDER}}-oauth.json')
PORT = 53682
PROTOCOL = '2025-06-18'
CLIENT_NAME = 'mstack (MST-66 P1)'


def _http(url, data=None, headers=None, form=False, timeout=60):
    """(status, headers, body bytes); never raises on HTTP errors."""
    body = None
    headers = dict(headers or {})
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
        else:
            body = json.dumps(data).encode()
            headers.setdefault('Content-Type', 'application/json')
    headers.setdefault('User-Agent', 'mstack-{{mstack:CLIENT_C_FOLDER}}/0.1')
    req = urllib.request.Request(url, data=body, headers=headers, method='POST' if body is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def _json(status, body, what):
    try:
        out = json.loads(body or b'{}')
    except ValueError:
        out = {'raw': body[:300].decode(errors='replace')}
    if status >= 400:
        raise RuntimeError('%s failed: HTTP %s %s' % (what, status, json.dumps(out)[:300]))
    return out


def load(path=SECRETS):
    return json.loads(Path(path).read_text())


def save(state, path=SECRETS):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)


def discover():
    meta = _json(*_http(RESOURCE_META)[::2], what='resource metadata')
    issuer = meta['authorization_servers'][0].rstrip('/')
    server = _json(*_http(issuer + '/.well-known/oauth-authorization-server')[::2], what='server metadata')
    return meta, server


def _store_tokens(state, tokens):
    now = int(time.time())
    state['access_token'] = tokens['access_token']
    if tokens.get('refresh_token'):
        state['refresh_token'] = tokens['refresh_token']
    state['expires_at'] = now + int(tokens.get('expires_in') or 3600)
    state['token_type'] = tokens.get('token_type', 'Bearer')
    state['scope'] = tokens.get('scope', state.get('scope'))
    state.setdefault('history', []).append({'at': now, 'expires_in': tokens.get('expires_in'),
                                            'refresh_rotated': bool(tokens.get('refresh_token'))})


def login(open_with=None, port=PORT, path=SECRETS, timeout=600):
    meta, server = discover()
    redirect = 'http://127.0.0.1:%d/callback' % port
    reg = _json(*_http(server['registration_endpoint'], {
        'client_name': CLIENT_NAME, 'redirect_uris': [redirect], 'grant_types': ['authorization_code', 'refresh_token'],
        'response_types': ['code'], 'token_endpoint_auth_method': 'none', 'scope': '{{mstack:CLIENT_C_FOLDER}}'})[::2], what='registration')
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    state_param = secrets.token_urlsafe(16)
    url = server['authorization_endpoint'] + '?' + urllib.parse.urlencode({
        'response_type': 'code', 'client_id': reg['client_id'], 'redirect_uri': redirect, 'state': state_param,
        'code_challenge': challenge, 'code_challenge_method': 'S256', 'resource': meta['resource'], 'scope': '{{mstack:CLIENT_C_FOLDER}}'})
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if urllib.parse.urlparse(self.path).path != '/callback':
                self.send_response(404); self.end_headers(); return
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'mstack: sign-in received. You can close this tab.\n')

        def log_message(self, *a):
            pass

    httpd = http.server.HTTPServer(('127.0.0.1', port), Handler)
    httpd.timeout = 5
    print('Sign-in waiting: open this URL and press Allow:\n' + url, flush=True)
    if open_with:
        subprocess.run(shlex.split(open_with) + [url], check=False)
    deadline = time.time() + timeout
    while not got and time.time() < deadline:
        httpd.handle_request()
    httpd.server_close()
    if not got:
        raise RuntimeError('no callback within %d s' % timeout)
    if got.get('error'):
        raise RuntimeError('authorization refused: %s' % got['error'])
    if got.get('state') != state_param:
        raise RuntimeError('state mismatch')
    if got.get('iss') and got['iss'].rstrip('/') != server['issuer'].rstrip('/'):
        raise RuntimeError('issuer mismatch')
    tokens = _json(*_http(server['token_endpoint'], {
        'grant_type': 'authorization_code', 'code': got['code'], 'redirect_uri': redirect, 'client_id': reg['client_id'],
        'code_verifier': verifier, 'resource': meta['resource']}, form=True)[::2], what='token exchange')
    state = {'client_id': reg['client_id'], 'client_name': CLIENT_NAME, 'token_endpoint': server['token_endpoint'],
             'revocation_endpoint': server.get('revocation_endpoint'), 'resource': meta['resource'],
             'redirect_uri': redirect, 'created_at': int(time.time())}
    _store_tokens(state, tokens)
    save(state, path)
    return {'client_id': state['client_id'], 'expires_in': tokens.get('expires_in'),
            'has_refresh': bool(tokens.get('refresh_token')), 'scope': tokens.get('scope')}


def refresh(path=SECRETS):
    state = load(path)
    tokens = _json(*_http(state['token_endpoint'], {
        'grant_type': 'refresh_token', 'refresh_token': state['refresh_token'], 'client_id': state['client_id'],
        'resource': state['resource']}, form=True)[::2], what='refresh')
    _store_tokens(state, tokens)
    save(state, path)
    return {'expires_in': tokens.get('expires_in'), 'refresh_rotated': bool(tokens.get('refresh_token'))}


def token(path=SECRETS):
    state = load(path)
    if state.get('expires_at', 0) - 60 < time.time():
        refresh(path)
        state = load(path)
    return state['access_token']


def _sse_messages(body):
    out = []
    for block in body.decode(errors='replace').split('\n\n'):
        data = '\n'.join(line[5:].lstrip() for line in block.splitlines() if line.startswith('data:'))
        if data:
            try:
                out.append(json.loads(data))
            except ValueError:
                pass
    return out


class MCP:
    def __init__(self, path=SECRETS, url=MCP_URL, timeout=300):
        self.path, self.url, self.timeout, self.n = path, url, timeout, 0

    def rpc(self, method, params=None, notify=False):
        self.n += 1
        msg = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
        if not notify:
            msg['id'] = self.n
        headers = {'Authorization': 'Bearer ' + token(self.path), 'Accept': 'application/json, text/event-stream',
                   'MCP-Protocol-Version': PROTOCOL}
        started = time.time()
        status, hdrs, body = _http(self.url, msg, headers, timeout=self.timeout)
        took = round(time.time() - started, 2)
        if notify:
            return {'status': status}
        if status >= 400:
            raise RuntimeError('%s: HTTP %s %s' % (method, status, body[:300].decode(errors='replace')))
        ctype = {k.lower(): v for k, v in hdrs.items()}.get('content-type', '')
        msgs = _sse_messages(body) if 'event-stream' in ctype else [json.loads(body)]
        reply = next((m for m in msgs if m.get('id') == msg['id']), msgs[-1] if msgs else {})
        if 'error' in reply:
            raise RuntimeError('%s: %s' % (method, json.dumps(reply['error'])[:300]))
        return {'result': reply.get('result'), 'seconds': took, 'transport': 'sse' if 'event-stream' in ctype else 'json'}

    def initialize(self):
        out = self.rpc('initialize', {'protocolVersion': PROTOCOL, 'capabilities': {},
                                      'clientInfo': {'name': 'mstack', 'version': '0.1'}})
        self.rpc('notifications/initialized', notify=True)
        return out

    def tools(self):
        return self.rpc('tools/list')

    def call(self, name, arguments):
        return self.rpc('tools/call', {'name': name, 'arguments': arguments})


CONTRACT = Path(__file__).resolve().parent/'{{mstack:CLIENT_C_FOLDER}}_contract.json'


def pick(data, paths):
    """The first value found at one of the dotted paths ('*' walks every item of a list or dict)."""
    for path in paths:
        found = _walk(data, path.split('.'))
        if found is not None:
            return found
    return None


def _walk(data, parts):
    if not parts:
        return data
    head, rest = parts[0], parts[1:]
    if head == '*':
        items = data.values() if isinstance(data, dict) else data if isinstance(data, list) else []
        out = []
        for item in items:
            got = _walk(item, rest)
            out.extend(got if isinstance(got, list) else [got] if got is not None else [])
        return out or None
    return _walk(data.get(head), rest) if isinstance(data, dict) else None


def tool_result(result):
    """The JSON a tools/call returned: structuredContent, else the first text item parsed."""
    result = result or {}
    if result.get('isError'):
        raise RuntimeError('tool error: ' + json.dumps(result.get('content'))[:300])
    if isinstance(result.get('structuredContent'), dict):
        return result['structuredContent']
    text = ((result.get('content') or [{}])[0] or {}).get('text') or '{}'
    try:
        return json.loads(text)
    except ValueError:
        return {'text': text}


def check_contract(tools, contract=None):
    """Compare the contract with a tools/list answer: every mapped tool exists and takes the mapped arguments.
    Returns a list of problems (empty: the contract holds)."""
    contract = contract or json.loads(CONTRACT.read_text())
    listed = (tools.get('result') or tools).get('tools') if isinstance(tools, dict) else tools
    by_name = {t['name']: t for t in listed or []}
    problems = []
    for need, name in contract['tools'].items():
        if name not in by_name:
            problems.append('%s: tool %s not offered' % (need, name))
            continue
        props = (by_name[name].get('inputSchema') or {}).get('properties') or {}
        for role, arg in contract['args'].get(need, {}).items():
            if need == 'wait' and role in ('channel', 'after'):
                outer = props.get(contract['args']['wait']['channels']) or {}
                inner = ((outer.get('items') or {}).get('properties')) or {}
                if arg not in inner and arg not in props:
                    problems.append('%s: %s takes no %s (per channel)' % (need, name, arg))
            elif arg not in props:
                problems.append('%s: %s takes no %s' % (need, name, arg))
    return problems


class Adapter:
    """The conductor's view of a hosted Agent's chat (017 §2.2): send a batch, wait for replies, read recent
    messages, attach files. Every tool and field name comes from the contract (config), none from code."""
    harness = '{{mstack:CLIENT_C_FOLDER}}'

    def __init__(self, mcp=None, contract=None, path=SECRETS, url=MCP_URL):
        self.c = contract or json.loads(CONTRACT.read_text())
        self.mcp = mcp or MCP(path, url)
        self._ready = False

    def _call(self, need, values):
        if not self._ready:
            self.mcp.initialize()
            self._ready = True
        names = self.c['args'].get(need, {})
        args = {names[k]: v for k, v in values.items() if v is not None and k in names}
        return tool_result(self.mcp.call(self.c['tools'][need], args)['result'])

    def _message(self, raw):
        r = self.c['result']
        author, via = pick(raw, r['author_kind']), pick(raw, r['via_kind'])
        frm = 'conductor' if via == 'api' else 'agent' if author == 'agent' else 'owner'
        return {'seq': pick(raw, r['message_sequence']), 'text': pick(raw, r['message_text']) or '', 'from': frm}

    def _messages(self, data):
        return [self._message(m) for m in (pick(data, self.c['result']['messages']) or []) if isinstance(m, dict)]

    def send(self, agent, text, files=(), key=None):
        """Post one message (with files attached) and return its sequence."""
        limit = self.c['limits']['text']
        if len(text) > limit:
            raise ValueError('message is %d characters; the limit is %d' % (len(text), limit))
        attachments = [self.attach(agent, name, body) for name, body in files]
        out = self._call('send', {'channel': agent['channel'], 'text': text, 'attachments': attachments or None,
                                  'idempotency': (key or '')[:self.c['limits']['idempotency']] or None})
        return pick(out, self.c['result']['sequence'])

    def wait(self, agent, after, seconds):
        seconds = max(1, min(int(seconds), self.c['limits']['wait_seconds']))
        a = self.c['args']['wait']
        out = self._call('wait', {'channels': [{a['channel']: agent['channel'], a['after']: after}], 'timeout': seconds})
        return self._messages(out)

    def recent(self, agent, after=None, limit=50):
        return self._messages(self._call('read', {'channel': agent['channel'], 'after': after, 'limit': limit}))

    def attach(self, agent, name, body):
        data = body.encode() if isinstance(body, str) else body
        r = self.c['result']
        up = self._call('upload', {'channel': agent['channel'], 'name': name, 'type': 'text/markdown', 'size': len(data)})
        url, attachment = pick(up, r['upload_url']), pick(up, r['attachment_id'])
        if not url or not attachment:
            raise RuntimeError('upload answer has no url or attachment id: %s' % json.dumps(up)[:200])
        headers = {'Content-Type': 'text/markdown', **(pick(up, r['upload_headers']) or {})}
        req = urllib.request.Request(url, data=data, headers=headers, method='PUT')
        with urllib.request.urlopen(req, timeout=60) as reply:
            if reply.status >= 300:
                raise RuntimeError('upload PUT: HTTP %s' % reply.status)
        self._call('complete_upload', {'attachment': attachment})
        return attachment

    def react(self, agent, seq, emoji):
        try:
            self._call('react', {'channel': agent['channel'], 'sequence': seq, 'emoji': emoji})
        except (RuntimeError, OSError):
            pass                                        # reactions are a courtesy, never a failure


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--secrets', default=str(SECRETS))
    sub = p.add_subparsers(dest='cmd', required=True)
    lg = sub.add_parser('login')
    lg.add_argument('--open-with', help='command that opens the URL in the owner\'s browser, e.g. "macctl run open"')
    lg.add_argument('--port', type=int, default=PORT)
    sub.add_parser('refresh')
    sub.add_parser('tools')
    c = sub.add_parser('call')
    c.add_argument('tool')
    c.add_argument('arguments', nargs='?', default='{}')
    a = p.parse_args(argv)
    if a.cmd == 'login':
        out = login(a.open_with, a.port, a.secrets)
    elif a.cmd == 'refresh':
        out = refresh(a.secrets)
    else:
        m = MCP(a.secrets)
        init = m.initialize()
        out = {'server': (init['result'] or {}).get('serverInfo'),
               'protocol': (init['result'] or {}).get('protocolVersion')}
        if a.cmd == 'tools':
            out['tools'] = m.tools()
        else:
            out['call'] = m.call(a.tool, json.loads(a.arguments))
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    sys.exit(main())
