"""Sparks: ideas for mstack noticed while working in a project, reported back to mstack's own board.

Any session, in any project, can file one. It becomes an MST issue in Backlog, titled `[SPARK] …`
and assigned to the owner, recording where it came from. Nothing else happens until the owner
triages it (a `/plan` comment, or closing it). The project's own code and board are never touched,
and the session doesn't edit mstack.

  mstack spark --from {{mstack:CLIENT_REPO}} "Orchestrators should …" [--detail TEXT|-] [--doc PATH]

`--doc` names a file in the source project to look at. The path is recorded, not uploaded.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import linear_board

STACK_ROOT = Path(__file__).resolve().parents[2]


def mstack_link():
    board = json.loads((STACK_ROOT/'.mstack/stack.json').read_text())['taskboard']
    return linear_board.Link(None, board['link'], STACK_ROOT)


def file_spark(source, title, detail='', docs=(), link=None):
    link = link or mstack_link()
    session = os.environ.get('CLAUDE_CODE_HOST_SESSION_ID', 'unknown')
    body = ['**From:** %s, session `%s`, %s' % (source, session, datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))]
    if detail.strip():
        body += ['', detail.strip()[:4000]]
    if docs:
        body += ['', 'Look at: ' + ', '.join('`%s`' % d for d in docs)]
    body += ['', '_Filed with `mstack spark`. Comment `/plan` to work on it, or close it._']
    made = link.post(linear_board.CREATE, {'input': {
        'teamId': link.team()['id'], 'title': '[SPARK] ' + title.strip()[:180], 'description': '\n'.join(body),
        'assigneeId': link.me(), 'priority': 4, 'stateId': link.state_id('Backlog')}})['issueCreate']['issue']
    return {'issue': made['identifier'], 'id': made['id'], 'from': source}


def main(argv):
    p = argparse.ArgumentParser(prog='mstack spark', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--from', dest='source', required=True, help='project the idea came from')
    p.add_argument('title')
    p.add_argument('--detail', default='', help='a few lines, or - for stdin')
    p.add_argument('--doc', action='append', default=[], help='file in the source project to look at')
    args = p.parse_args(argv)
    detail = sys.stdin.read() if args.detail == '-' else args.detail
    try:
        result = file_spark(args.source, args.title, detail, args.doc)
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        print('mstack spark: %s' % error, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
