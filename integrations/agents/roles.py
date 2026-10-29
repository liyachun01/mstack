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
                                       ', focus ' + ', '.join(conf['focus']) if conf.get('focus') else '',
                                       ', session `%s`' % who if who else ', no session registered')


RULES = {
    'orchestrator': 'The **orchestrator** is the project\'s single top-level session. It takes the owner\'s requests, '
                    'turns them into issues, and assigns them: to a sub-orchestrator when the project has '
                    'scopes, otherwise straight to workers.',
    'sub-orchestrator': 'A **sub-orchestrator** owns one scope of the project (apps or focus issues). It plans, '
                        'gets the owner\'s verdict, dispatches one worker per approved issue, forwards feedback '
                        'and reports up.',
    'worker': 'A **worker** implements exactly one issue in its own worktree and reports with note/done.',
}
NO_WORK = ('**You never work on an issue yourself:** no code changes, builds, migrations or fixes in this chat. '
           'You assign, track and report. The only exception is the owner explicitly approving it in this chat '
           'for a named issue ("do YEL-12 here yourself"). Then say so, record it with `note`, and do only that issue.')


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
                 '→ `done` reviews.' % (run('<cmd>'), scope)]
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
            lines += ['Assign by area to a sub-orchestrator: SendMessage to its session with the request word for '
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
                 scope_line(scope, scopes.get(scope, {}), board, subs), *board_duty(scope)]
        if top:
            lines.append('Your orchestrator is `%s`. Work it assigns you is the owner\'s request; anything outside '
                         'your scope goes back to it.' % top)
    else:
        run = next(((t, r) for t, r in board_state().get('runs', {}).items() if r.get('session') == session), None)
        related = next((t for t, rs in board_state().get('related', {}).items()
                        if any(r.get('session') == session for r in rs)), None)
        if run:
            task, r = run
            lines = ['## Your mstack role: **worker** for %s (%s, %s)' % (r.get('issue') or task, name, r.get('scope') or name),
                     RULES['worker'] + (' Your worktree: `%s`.' % r['tree'] if r.get('tree') else ''),
                     'Load the `mstack-worker` skill. Report with `%s/mstack board note --task %s "…"` and finish with '
                     '`%s/mstack board done --task %s --summary "…"`. Never start sessions or work on other issues; '
                     'ask your orchestrator.' % (STACK_ROOT, task, STACK_ROOT, task)]
        elif related:
            lines = ['## Your mstack role: history',
                     'This chat is kept as history for an issue (marked obsolete). Don\'t act on its old plan; point the '
                     'owner to the issue\'s current worker or orchestrator.']
        else:
            return None
    lines.append(spark)
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
    s.add_argument('--session', required=True); s.add_argument('--role', choices=['orchestrator', 'sub-orchestrator'], required=True)
    s.add_argument('--scope')
    s = sub.add_parser('unset'); s.add_argument('--project', type=Path, required=True); s.add_argument('--session', required=True)
    s = sub.add_parser('list'); s.add_argument('--project', type=Path, required=True)
    s = sub.add_parser('install'); s.add_argument('--project', type=Path, required=True)
    s = sub.add_parser('card'); s.add_argument('--project', type=Path, required=True); s.add_argument('--session', required=True)
    sub.add_parser('hook')
    args = p.parse_args(argv)
    if args.command == 'hook':
        return hook()
    project = args.project.resolve()
    if args.command == 'set':
        scopes = (config(project).get('taskboard') or {}).get('orchestrators') or {}
        if args.role == 'sub-orchestrator' and args.scope not in scopes or args.scope and args.scope not in scopes:
            print('mstack role: --scope must be one of %s' % ', '.join(sorted(scopes)), file=sys.stderr)
            return 1
        with project_state.edit(project) as state:
            roles = state['runtime'].setdefault('roles', {})
            for other, r in list(roles.items()):         # one session per orchestrator scope
                same_scope = args.scope and r.get('scope') == args.scope
                if other != args.session and (same_scope or args.role == 'orchestrator' == r.get('role')):
                    roles.pop(other)
            roles[args.session] = {'role': args.role, **({'scope': args.scope} if args.scope else {})}
        result = {'session': args.session, 'role': args.role, 'scope': args.scope}
    elif args.command == 'unset':
        with project_state.edit(project) as state:
            result = {'removed': state['runtime'].setdefault('roles', {}).pop(args.session, None)}
    elif args.command == 'list':
        result = registered(project)
    elif args.command == 'install':
        result = {'hooks_added': install(project)}
    else:
        print(card(project, args.session) or '(no mstack role for this session)')
        return 0
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
