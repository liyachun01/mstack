"""Role cards: every mstack session is reminded who it is, on every message.

A role given only in a session's first prompt fades: it's summarised away when the chat is
compacted, and a message that arrives later (from the owner, or another session) is answered as
a general assistant. Claude Code re-reads hooks on every turn, and every Claude Desktop session
exposes its own id as $CLAUDE_CODE_HOST_SESSION_ID. So a project-scoped hook
(UserPromptSubmit + SessionStart) looks the session up and adds a short role card to its context.

Roles come from two places:
- registered with `mstack role set` (the project's one orchestrator; a sub-orchestrator per scope), kept in the
  project's private `.mstack/state.json` (runtime.roles);
- the board's runs: a worker or adopted session is the worker for its issue, and a related chat is history.

  mstack role set --project P --session local_… --role orchestrator|sub-orchestrator [--scope S]
  mstack role list --project P
  mstack role install --project P      add the hooks to P/.claude/settings.local.json
  mstack role card --project P --session local_…      print a session's card
  roles.py hook                        (the hook itself: reads the event on stdin)

An unknown session gets nothing: the hook is silent outside registered sessions.
"""
import argparse
import json
import os
from pathlib import Path
import sys

STACK_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STACK_ROOT/'integrations/stack'))
import project_state  # noqa: E402

BOARD_STATE = STACK_ROOT/'.mstack/evidence/taskboard-test.json'
MARK = 'integrations/agents/roles.py'
ENGINE = STACK_ROOT/'mstack'


def project_of(path):
    """The mstack project a folder belongs to (worktrees live inside their project)."""
    path = Path(path).resolve()
    for folder in (path, *path.parents):
        if (folder/'.mstack/stack.json').is_file():
            return folder
    return None


def config(project):
    return json.loads((Path(project)/'.mstack/stack.json').read_text())


def registered(project):
    return project_state.read(project)['runtime'].get('roles', {})


def board_state():
    return json.loads(BOARD_STATE.read_text()) if BOARD_STATE.exists() else {}


def table_name(project):
    for name, entry in board_state().get('tables', {}).items():
        if Path(entry.get('path', '')).resolve() == Path(project).resolve():
            return name
    return (config(project).get('taskboard') or {}).get('table')


def scope_line(scope, conf, board, sessions):
    apps = ', '.join(conf.get('apps') or ['*'])
    links = []
    if '*' in (conf.get('apps') or ['*']) and board.get('link'):
        links.append('%s/%s' % (board['link'].get('workspace'), board['link'].get('team')))
    for code in conf.get('apps') or []:
        link = ((board.get('apps') or {}).get(code) or {}).get('link')
        if link:
            links.append('%s/%s' % (link.get('workspace'), link.get('team')))
    who = sessions.get(scope)
    return '- **%s**: apps %s (%s)%s%s' % (scope, apps, ', '.join(links) or 'table link',
                                       (', focus ' + ', '.join(conf['focus']) if conf.get('focus') else '')
                                       + (', except ' + ', '.join(conf['exclude']) if conf.get('exclude') else ''),
                                       ', session `%s`' % who if who else ', no session registered')


RULES = {
    'orchestrator': 'The **orchestrator** is the project\'s single top-level session. It takes the owner\'s requests, '
                    'turns them into issues, and assigns them: to a sub-orchestrator when the project has '
                    'scopes, otherwise straight to workers.',
    'sub-orchestrator': 'A **sub-orchestrator** owns one scope of the project (apps or focus issues). It plans, '
                        'gets the owner\'s verdict, dispatches one worker per approved issue, forwards feedback '
                        'and reports up.',
    'worker': 'A **worker** implements exactly one issue in its own worktree and reports with note/done.',
    'helper': 'A **helper** does one part of a worker\'s issue, started by that worker as its side session. It '
              'reports only to its worker; the worker alone writes the issue\'s record.',
}
HELPERS = ('You may start **helper** side sessions for parts of *this* issue: start them yourself (side sessions, '
           'nested under you, never moved to top level), then register each with `%s/mstack role set --project %s '
           '--session <helper id> --role helper --task %s --worker %s`. One level only: helpers never start helpers. '
           'Their turn-end notes reach you; merge what they bring back and report it yourself with note/done. '
           'A **sub-issue** of this issue gets its own worker instead: you may start it as your side session too, then '
           'ask your orchestrator to adopt it (`adopt --task <SUB> --session <id>`). It owns its sub-issue\'s record '
           'and stays nested under you, so its progress reaches you. New sub-issues are planned by your '
           'orchestrator (`plan --parent`).')
NO_WORK = ('**You never work on an issue yourself, and do no other real work here either:** no code, docs or config '
           'edits, builds, migrations, fixes or review fixes in this chat. Only orchestrative work stays: planning, '
           'assigning and dispatching, registering routes and roles, relaying messages, reading status and reviews, '
           'recording verdicts and notes, and board or ops commands the owner asked for. Everything else goes to a '
           'worker chat: an issue goes through plan/dispatch; work with no issue goes to a side chat you start '
           '(`start_session`, its own worktree for code, titled `<scope>: <what>`, with a self-contained brief), or '
           'a card you offer when you can\'t start one. The only exception is the owner explicitly approving a named '
           'piece of work in this chat ("do YEL-12 here yourself"). Then say so, record it with `note` when there\'s '
           'an issue, and do only that. When unsure, ask the owner.')


def card(project, session):
    """The role card for a session, or None if it has no mstack role in this project."""
    project = Path(project)
    cfg = config(project)
    board = cfg.get('taskboard') or {}
    name = table_name(project)
    roles = registered(project)
    scopes = board.get('orchestrators') or {}
    subs = {r.get('scope'): s for s, r in roles.items() if r.get('role') == 'sub-orchestrator'}
    top = next((s for s, r in roles.items() if r.get('role') == 'orchestrator'), None)
    run = lambda c: '%s board %s --project %s' % (ENGINE, c, name)
    private = board.get('private')
    spark = ('Something mstack itself could do better? Record it in one line with `%s spark --from %s "<idea>"`, '
             'and don\'t edit mstack.' % (ENGINE, name))
    verdicts = ('Private board: nothing goes to Linear. When the owner says plan, 👍, 👎 or gives feedback, record '
                'it first with `%s --scope %%s --task <ISSUE> "<their words>"`.' % run('owner'))

    def board_duty(scope):
        lines = ['Your board: `%s --scope %s`. Load the `mstack-orchestrator` skill. Plan → owner verdict → '
                 '`dispatch` (one worker session per approved issue, titled `<ISSUE>: <title>`) → forward feedback '
                 '→ `done` reviews. Workers you start stay nested under you: don\'t move them to top level unless the owner '
                 'asks.' % (run('<cmd>'), scope),
                 'Before creating sub-issues, read the existing tree (`%s --scope %s --task <PARENT>`). If the owner '
                 'names sub-issues that don\'t exist yet, or says "create them" without saying issues or sessions, ask '
                 'first. Already handling a request the watcher raised? `%s --scope %s --task <ISSUE>` stops it '
                 'raising the same thing again.' % (run('tree'), scope, run('inhand'), scope)]
        if private:
            lines.append(verdicts % scope)
        workers = [r for r in board_state().get('runs', {}).values()
                   if r.get('table') == name and r.get('scope') == scope and r.get('session')]
        if workers:
            lines.append('Your workers: ' + '; '.join('%s `%s`' % (r.get('issue') or '?', r['session']) for r in workers[:12]))
        return lines

    me = roles.get(session)
    if me and me.get('role') == 'orchestrator':
        lines = ['## Your mstack role: %s **orchestrator** (top level)' % name, RULES['orchestrator'], NO_WORK]
        others = {s: c for s, c in scopes.items() if s != me.get('scope')}
        if others:
            lines += ['You never start worker sessions or run `dispatch`; that is your sub-orchestrators\' job '
                      '(mstack refuses `dispatch` without their scope).',
                      'Assign by area to a sub-orchestrator: SendMessage to its session with the request word for '
                      'word plus the issue ids, then tell the owner where it went. Several areas: split it. Unclear: '
                      'ask the owner.', *[scope_line(s, c, board, subs) for s, c in sorted(others.items())]]
        if me.get('scope'):
            lines += board_duty(me['scope'])
        elif not others:
            lines.append('No scopes are configured yet: assign with `%s` and `dispatch`.' % run('plan'))
        lines.append('Status for the owner: `%s`.' % run('status'))
    elif me and me.get('role') == 'sub-orchestrator':
        scope = me.get('scope')
        lines = ['## Your mstack role: **%s** sub-orchestrator (%s)' % (scope, name), RULES['sub-orchestrator'], NO_WORK,
                 scope_line(scope, scopes.get(scope, {}), board, subs), *board_duty(scope),
                 'If the app refuses `start_session` because your turn began with another session\'s message, offer '
                 'the worker as a proposal card (initiation `own_initiative`) for the owner to start, and tell your '
                 'orchestrator.']
        if top:
            lines.append('Your orchestrator is `%s`. Work it assigns you is the owner\'s request; anything outside '
                         'your scope goes back to it.' % top)
    else:
        run = next(((t, r) for t, r in board_state().get('runs', {}).items() if r.get('session') == session), None)
        related = next((t for t, rs in board_state().get('related', {}).items()
                        if any(r.get('session') == session for r in rs)), None)
        if me and me.get('role') == 'helper':
            lines = ['## Your mstack role: **helper** for %s (%s)' % (me.get('task'), name), RULES['helper'],
                     'Your worker is `%s`. Report your result and any question to it, through your turn-end reply or '
                     'SendMessage. Never write to the issue or board (no note/done), never start sessions, and stay '
                     'inside the part your worker gave you.' % me.get('worker')]
        elif run:
            task, r = run
            lines = ['## Your mstack role: **worker** for %s (%s, %s)' % (r.get('issue') or task, name, r.get('scope') or name),
                     RULES['worker'] + (' Your worktree: `%s`.' % r['tree'] if r.get('tree') else ''),
                     'Load the `mstack-worker` skill. Report with `%s/mstack board note --task %s "…"` and finish with '
                     '`%s/mstack board done --task %s --summary "…"`. Never work on other issues; ask your orchestrator.'
                     % (STACK_ROOT, task, STACK_ROOT, task),
                     HELPERS % (STACK_ROOT, project, r.get('issue') or task, session)]
            runs = board_state().get('runs', {}).values()
            if r.get('parent'):
                above = next((x for x in runs if x.get('issue') == r['parent'] and x.get('session')), None)
                lines.append('This is a sub-issue of %s%s. Tell that worker anything that affects the parent issue; '
                             'your own issue\'s record stays yours (note/done).'
                             % (r['parent'], ' (worker `%s`)' % above['session'] if above else ''))
            subs_here = [x for x in runs if x.get('parent') and x.get('parent') == r.get('issue') and x.get('session')]
            if subs_here:
                lines.append('Your sub-issue workers (nested under you, they own their records): ' + '; '.join(
                    '%s `%s`' % (x.get('issue'), x['session']) for x in subs_here))
            mine = [s for s, h in roles.items() if h.get('role') == 'helper' and h.get('worker') == session]
            if mine:
                lines.append('Your helpers: ' + ', '.join('`%s`' % s for s in mine))
        elif related:
            lines = ['## Your mstack role: history',
                     'This chat is kept as history for an issue (marked obsolete). Don\'t act on its old plan; point the '
                     'owner to the issue\'s current worker or orchestrator.']
        else:
            return None
    lines.append(spark)
    return '\n'.join(lines)


def tree(project):
    """The session hierarchy mstack knows: orchestrator → sub-orchestrators → workers → sub-issue workers / helpers."""
    project = Path(project)
    roles, name = registered(project), table_name(project)
    runs = [r for r in board_state().get('runs', {}).values() if r.get('table') == name and r.get('session')]
    lines = []
    def worker_lines(r, indent):
        out = ['%s- %s worker `%s`%s' % (indent, r.get('issue') or '?', r['session'], ' (adopted)' if r.get('adopted') else '')]
        out += ['%s  - helper `%s`' % (indent, s) for s, h in roles.items()
                if h.get('role') == 'helper' and h.get('worker') == r['session']]
        for sub in runs:
            if sub.get('parent') and sub.get('parent') == r.get('issue'):
                out += worker_lines(sub, indent + '  ')
        return out
    tops = [s for s, r in roles.items() if r.get('role') == 'orchestrator']
    lines.append('%s orchestrator `%s`' % (name, tops[0] if tops else 'not registered'))
    scopes = sorted({r.get('scope') for r in roles.values() if r.get('role') == 'sub-orchestrator'} |
                    {r.get('scope') for r in runs if r.get('scope')} - {None})
    own = next((roles[s].get('scope') for s in tops if roles[s].get('scope')), None)
    for scope in scopes:
        sub = next((s for s, r in roles.items() if r.get('role') == 'sub-orchestrator' and r.get('scope') == scope), None)
        indent = '  '
        if scope != own:
            lines.append('  - %s sub-orchestrator `%s`' % (scope, sub or 'not registered'))
            indent = '    '
        for r in runs:
            if r.get('scope') == scope and not (r.get('parent') and any(x.get('issue') == r['parent'] for x in runs)):
                lines += worker_lines(r, indent)
    return '\n'.join(lines)


def hook():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    session = os.environ.get('CLAUDE_CODE_HOST_SESSION_ID', '')
    project = project_of(event.get('cwd') or os.getcwd())
    if not session or not project:
        return 0
    try:
        text = card(project, session)
    except (OSError, ValueError, KeyError):
        return 0
    if text:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': event.get('hook_event_name', 'UserPromptSubmit'),
                                                 'additionalContext': text}}, ensure_ascii=False))
    return 0


def install(project):
    """Add the role hook to the project's personal Claude settings, keeping everything else."""
    path = Path(project)/'.claude/settings.local.json'
    settings = json.loads(path.read_text()) if path.exists() else {}
    command = 'python3 "%s" hook' % (STACK_ROOT/MARK)
    changed = []
    for event in ('UserPromptSubmit', 'SessionStart'):
        entries = settings.setdefault('hooks', {}).setdefault(event, [])
        if MARK not in json.dumps(entries):
            entries.append({'hooks': [{'type': 'command', 'command': command, 'timeout': 10}]})
            changed.append(event)
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2) + '\n')
    return changed


def main(argv):
    p = argparse.ArgumentParser(prog='mstack role', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('set'); s.add_argument('--project', type=Path, required=True)
    s.add_argument('--session', required=True); s.add_argument('--role', choices=['orchestrator', 'sub-orchestrator', 'helper'], required=True)
    s.add_argument('--scope')
    s.add_argument('--task', help='helper: the issue it helps with'); s.add_argument('--worker', help='helper: its worker session')
    s = sub.add_parser('unset'); s.add_argument('--project', type=Path, required=True); s.add_argument('--session', required=True)
    s = sub.add_parser('list'); s.add_argument('--project', type=Path, required=True)
    s = sub.add_parser('install'); s.add_argument('--project', type=Path, required=True)
    s = sub.add_parser('card'); s.add_argument('--project', type=Path, required=True); s.add_argument('--session', required=True)
    s = sub.add_parser('tree'); s.add_argument('--project', type=Path, required=True)
    sub.add_parser('hook')
    args = p.parse_args(argv)
    if args.command == 'hook':
        return hook()
    project = args.project.resolve()
    if args.command == 'set':
        scopes = (config(project).get('taskboard') or {}).get('orchestrators') or {}
        if args.role == 'helper' and not (args.task and args.worker):
            print('mstack role: a helper needs --task and --worker', file=sys.stderr)
            return 1
        workers = {r.get('session') for r in board_state().get('runs', {}).values()}
        if args.role == 'helper' and args.worker not in workers:
            print('mstack role: %s is not a worker on the board' % args.worker, file=sys.stderr)
            return 1
        if args.role == 'helper' and args.session in workers:
            print('mstack role: a worker cannot also be a helper', file=sys.stderr)
            return 1
        if args.role == 'sub-orchestrator' and args.scope not in scopes or args.scope and args.scope not in scopes:
            print('mstack role: --scope must be one of %s' % ', '.join(sorted(scopes)), file=sys.stderr)
            return 1
        with project_state.edit(project) as state:
            roles = state['runtime'].setdefault('roles', {})
            for other, r in list(roles.items()):         # one session per orchestrator scope (helpers are many)
                if args.role == 'helper':
                    break
                same_scope = args.scope and r.get('scope') == args.scope
                if other != args.session and (same_scope or args.role == 'orchestrator' == r.get('role')):
                    roles.pop(other)
            roles[args.session] = {'role': args.role, **({'scope': args.scope} if args.scope else {}),
                                   **({'task': args.task, 'worker': args.worker} if args.role == 'helper' else {})}
        result = {'session': args.session, 'role': args.role, 'scope': args.scope}
    elif args.command == 'unset':
        with project_state.edit(project) as state:
            result = {'removed': state['runtime'].setdefault('roles', {}).pop(args.session, None)}
    elif args.command == 'list':
        result = registered(project)
    elif args.command == 'tree':
        print(tree(project))
        return 0
    elif args.command == 'install':
        result = {'hooks_added': install(project)}
    else:
        print(card(project, args.session) or '(no mstack role for this session)')
        return 0
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
