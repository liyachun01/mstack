"""stdio ↔ agentgateway bridge for worker sessions (one project route).

Workers run on the dev machine; the gateway is published on the Mac's loopback
(127.0.0.1:58080) and reached through OrbStack's host alias. Its MCP DNS-rebinding
protection only accepts a loopback Host, so the bridge sends the gateway's own
published Host while connecting through the alias; protection stays on and the
project key is still required. The key is read from the project's .mstack/secrets
and never written into a worktree. Each call carries the bound task as
x-mstack-task for the gateway's access log.

  python3 stdio_bridge.py --project /path/to/project [--url http://host.orb.internal:58080]
"""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

PUBLISHED_HOST = '127.0.0.1:58080'


def bound_task(project):
    task = os.environ.get('MSTACK_TASK', '').strip()
    for root in (Path.cwd(), project):
        marker = root/'.mstack/cache/current-task'
        if not task and marker.is_file():
            task = marker.read_text().strip()
    return task


def bridge(project, base, instream=sys.stdin, outstream=sys.stdout, opener=urllib.request.urlopen):
    slug = json.loads((project/'.mstack/stack.json').read_text())['project']
    key = (project/'.mstack/secrets/agentgateway-key').read_text().strip()
    url = '%s/mcp/projects/%s' % (base.rstrip('/'), slug)
    session = None
    for line in instream:
        if not line.strip():
            continue
        message = json.loads(line)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                   'Authorization': 'Bearer ' + key, 'Host': PUBLISHED_HOST}
        task = bound_task(project)
        if task:
            headers['x-mstack-task'] = task
        if session:
            headers['mcp-session-id'] = session
        request = urllib.request.Request(url, method='POST', data=json.dumps(message).encode(), headers=headers)
        try:
            with opener(request, timeout=120) as response:
                session = response.headers.get('mcp-session-id') or session
                body = response.read().decode()
        except urllib.error.HTTPError as error:
            body = ''
            if 'id' in message:
                reply = {'jsonrpc': '2.0', 'id': message['id'],
                         'error': {'code': -32000, 'message': 'gateway HTTP %s: %s' % (error.code, error.read().decode()[:200])}}
                outstream.write(json.dumps(reply) + '\n')
                outstream.flush()
            continue
        if 'id' not in message:
            continue                      # notification: nothing to return
        for chunk in body.splitlines():
            if chunk.startswith('data:'):
                outstream.write(chunk[5:].strip() + '\n')
        if not any(c.startswith('data:') for c in body.splitlines()) and body.strip():
            outstream.write(body.strip() + '\n')
        outstream.flush()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--url', default=os.environ.get('MSTACK_GATEWAY_URL', 'http://host.orb.internal:58080'))
    args = p.parse_args()
    bridge(args.project.resolve(), args.url)


if __name__ == '__main__':
    main()
