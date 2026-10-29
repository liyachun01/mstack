"""Minimal stdio MCP client shared by plugin adapters (no SDK dependency)."""
import json
import subprocess


class McpStdio:
    """Minimal MCP client: initialize, then tools/call over newline-delimited JSON-RPC."""
    def __init__(self, argv):
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True)
        self.n = 0
        self.request('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                    'clientInfo': {'name': 'mstack-plugin', 'version': '0.1.0'}})
        self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + '\n')
        self.proc.stdin.flush()

    def request(self, method, params):
        self.n += 1
        self.send({'jsonrpc': '2.0', 'id': self.n, 'method': method, 'params': params})
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError('MCP session closed (service stopped or tenant not registered?)')
            message = json.loads(line)
            if message.get('id') == self.n:
                if 'error' in message:
                    raise RuntimeError('MCP: ' + message['error'].get('message', 'error'))
                return message['result']

    def tool(self, name, arguments, raw=False):
        result = self.request('tools/call', {'name': name, 'arguments': arguments})
        text = (result.get('content') or [{}])[0].get('text', '')
        if result.get('isError'):
            raise RuntimeError(text or 'MCP tool error')
        if raw:
            return text
        data = json.loads(text)
        if 'error' in data:
            raise RuntimeError(data['error'])
        return data

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
