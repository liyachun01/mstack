"""mstack board: the orchestrator's toolbelt over the shared Anytype task board.

The orchestrator *agent* (a Claude/Codex session the owner talks to) decides what to
plan and who works; these commands do the deterministic parts:

  table    register a project's table (from its .mstack/stack.json `taskboard`)
  plan     create a task with its plan and ask the owner for a verdict
  ask      post a revised plan / question and wait for a verdict again
  poll     read owner reactions and replies; move approved/rejected tasks on
  tick     one unattended pass over `taskboard.auto` tables: verdicts, dispatch, what needs an agent
  watch    shell loop of tick; exits with the work when an orchestrator agent is needed
  ack      record that the host session for a handoff was started
  dispatch start one worker per approved task, each in its own git worktree:
           CLI hosts are spawned; desktop hosts get a launch spec (handoff)
  done     a worker in any host reports its task ready for review
  note     reverse path: a session or worker updates the issue
  status   one table at a glance
  sync     reconcile a linked table with Linear (pull, push or full)
  link     link a table to Linear with an entry of the owner's .secrets/linear.csv
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent/'stack'))
import board as anyboard
import config as intent
import runners          # puts integrations/plugins on sys.path
import registry
import visibility

STACK_ROOT = anyboard.STACK_ROOT
STATE = STACK_ROOT/'.mstack/evidence/taskboard-test.json'
SECRET = re.compile(r'(anytype_[0-9A-Za-z_]{20,}|sk-[0-9A-Za-z_-]{16,}|Bearer\s+\S+|ghp_[0-9A-Za-z]{20,}|lin_api_[0-9A-Za-z]{20,})')
PENDING = ('Awaiting Approval', 'In Review')
SYNC_EVERY = 300          # seconds between Linear syncs per table inside tick/watch
LINEAR_EVERY = 30         # seconds between polls of a Linear board inside tick/watch
TRIGGER = re.compile(r'^\s*(/plan|@agent plan)\b(.*)', re.S | re.I)


@contextlib.contextmanager
def state():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE.with_suffix('.lock'), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(STATE.read_text()) if STATE.exists() else {}
        yield data
        STATE.write_text(json.dumps(data, indent=2) + '\n')


def read_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def table_of(project):
    """Registered table for a project name or path: (name, entry)."""
    tables = read_state().get('tables', {})
    if project in tables:
        return project, tables[project]
    path = str(Path(project).resolve())
    for name, entry in tables.items():
        if entry['path'] == path:
            return name, entry
    raise ValueError('No registered table for %s; run: mstack board table --project <path>' % project)


def project_settings(entry):
    cfg = intent.project_config(Path(entry['path']))
    return cfg['taskboard']


def owner_notes(messages):
    return [m.get('text', '') for m in messages if not m.get('text', '').startswith(anyboard.MARK)]


def git(cwd, *args, check=True):
    return subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, check=check).stdout.strip()


def spawn(argv, log):
    """Start a detached worker; its stdout/stderr go to the run log."""
    with open(log, 'a') as handle:
        return subprocess.Popen(argv, stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True).pid


def alive(pid):
    if not pid:          # handed to a desktop host: no process of ours to check
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def linear_board_factory(path, settings, scope=None, all_issues=False):
    import linear_board
    return linear_board.LinearBoard(path, settings, scope=scope, all_issues=all_issues)


SCOPE = None                              # --scope: which orchestrator of a repo this call acts for
MIRROR_EVERY = 300                        # seconds between local issue-table refreshes in tick/watch


LINEAR_BOARD = linear_board_factory      # tests replace this with a fake


def is_linear(entry):
    try:
        return project_settings(entry).get('backend') == 'linear'
    except (ValueError, OSError, KeyError):
        return entry.get('backend') == 'linear'


def scope_conf(settings, scope=None):
    scope = scope or SCOPE
    if not scope:
        return None
    try:
        return settings['orchestrators'][scope]
    except KeyError:
        raise ValueError('No orchestrator scope %r in taskboard.orchestrators' % scope)


def board_for(name, b, scope=None):
    """The board a table lives on: Linear (backend: linear, narrowed to the orchestrator scope)
    or the Anytype board `b`."""
    entry = read_state()['tables'][name]
    if not is_linear(entry):
        return b
    settings = project_settings(entry)
    return LINEAR_BOARD(entry['path'], settings, scope=scope_conf(settings, scope))


def remember(task, table, ident=None):
    with state() as s:
        record = {'table': table, 'scope': SCOPE}
        for key in filter(None, (task, ident)):
            s.setdefault('task_tables', {})[key] = record


def board_of_task(task, b):
    """Board for a single task (id or IRO-123), from the run, plan or adoption that recorded it."""
    st = read_state()
    run = st.get('runs', {}).get(task) or {}
    record = st.get('task_tables', {}).get(task) or {}
    if isinstance(record, str):
        record = {'table': record}
    name = run.get('table') or record.get('table')
    scope = run.get('scope') or record.get('scope')
    return board_for(name, b, scope) if name in st.get('tables', {}) else b


def doc_links(table, docs):
    """'Docs: [path](url)' for paths under the project's taskboard.docs_url, so Linear links to the
    repo's docs instead of carrying long text. Empty when no docs were given."""
    if not docs:
        return ''
    base = ''
    if table in read_state().get('tables', {}):
        base = project_settings(read_state()['tables'][table]).get('docs_url', '')
    return '\n\nDocs: ' + ', '.join('[%s](%s%s)' % (d, base, d) if base else '`%s`' % d for d in docs)


def table_of_task(task):
    st = read_state()
    record = st.get('task_tables', {}).get(task) or {}
    return (st.get('runs', {}).get(task) or {}).get('table') or (record if isinstance(record, str) else record.get('table'))


# ---- commands ---------------------------------------------------------
def cmd_table(args, b):
    path = Path(args.project).resolve()
    settings = intent.project_config(path).get('taskboard')
    if not settings:
        raise ValueError('Project config has no taskboard section')
    name = settings['table']
    known = read_state().get('tables', {}).get(name, {})
    if known and known['path'] != str(path):
        raise ValueError('Table %s already belongs to %s' % (name, known['path']))
    if settings.get('backend') == 'linear':
        if not links_of(settings):
            raise ValueError('A Linear board needs taskboard.link or apps.<CODE>.link (mstack board link)')
        with state() as s:
            s.setdefault('tables', {})[name] = {'backend': 'linear', 'path': str(path)}
        return {'table': name, 'backend': 'linear', 'path': str(path),
                'links': {code or '*': '%s/%s' % (l['workspace'], l['team']) for code, l in links_of(settings)}}
    table = b.ensure_table(name, known)
    b.tidy_views(table['collection'])
    moved = []
    if known.get('query') and not known.get('collection'):
        # Earlier layouts (a filtered query, or a per-project type): re-type in place onto the
        # shared Agent Task type, add to the collection, then remove the old objects.
        shared = b.ensure_type()
        for task in b.tasks(known['query'], kind='queries'):
            b.move(task['id'], shared)
            moved.append(task['id'])
        if moved:
            b.add(table['collection'], moved)
        b.call('DELETE', 'objects/' + known['query'])
        if known.get('widget'):
            b.call('DELETE', 'widgets/' + known['widget'])
        if known.get('type'):
            b.call('DELETE', 'types/' + known['type'])
    with state() as s:
        s.setdefault('tables', {})[name] = {**table, 'path': str(path)}
    return {'table': name, **table, 'path': str(path), 'moved': moved,
            'links': {code or '*': l['mode'] for code, l in links_of(settings)} or 'private'}


def cmd_plan(args, b):
    name, entry = table_of(args.project)
    apps = project_settings(entry).get('apps') or {}
    if args.app and apps and args.app not in apps:
        raise ValueError('Unknown app %s for table %s (apps: %s)' % (args.app, name, ', '.join(sorted(apps))))
    if args.kind and args.kind not in anyboard.KINDS:
        raise ValueError('Kind must be one of ' + ', '.join(anyboard.KINDS))
    plan = sys.stdin.read() if args.plan == '-' else Path(args.plan).read_text()
    b = board_for(name, b)
    extra = {'parent': args.parent} if args.parent else {}
    task = b.create(name, args.title, plan, agent=args.agent, priority=args.priority, labels=args.labels,
                    collection=entry.get('collection'), app=args.app, kind=args.kind, **extra)
    remember(task, name)
    b.say(task, 'Plan ready for **%s**. React 👍 to approve, 👎 to drop, or reply with changes.' % args.title, ask=True)
    return {'task': task, 'status': 'Awaiting Approval'}


def cmd_propose(args, b):
    """Answer a /plan trigger: post the plan on the owner's existing issue (never touching its description)."""
    name, _ = table_of(args.project)
    b = board_for(name, b)
    task = b.get(args.task)
    plan = sys.stdin.read() if args.plan == '-' else Path(args.plan).read_text()
    b.say(task['id'], 'Plan ready for **%s** (agent: %s).\n\n## Plan\n\n%s\n\nReact 👍 to approve, 👎 to drop, '
          'or reply with changes.' % (task['name'], args.agent, plan.strip() + doc_links(name, args.doc)), ask=True)
    remember(task['id'], name, task.get('linear_identifier'))
    if args.repos:
        known = workspace_repos(project_settings(table_of(args.project)[1]))
        wrong = [r for r in args.repos if r not in known]
        if wrong:
            raise ValueError('Unknown repos %s (taskboard.repos: %s)' % (', '.join(wrong), ', '.join(sorted(known))))
        with state() as s:
            s.setdefault('task_repos', {})[task['id']] = list(args.repos)
    return {'task': task['id'], 'issue': task.get('linear_identifier'), 'status': 'Awaiting Approval',
            'repos': args.repos or []}


def cmd_worktree(args, b):
    """A workspace task needs another repo: add its worktree inside the task folder, on the issue's branch."""
    lb = board_of_task(args.task, b)
    task = lb.get(args.task)
    name = table_of_task(task['id']) or table_of_task(args.task)
    entry = read_state()['tables'][name]
    run = read_state().get('runs', {}).get(task['id']) or {}
    short = (task.get('linear_identifier') or task['id'][-8:]).lower()
    tree = Path(run.get('tree') or Path(entry['path'])/'.mstack/worktrees'/short)
    target = add_repo(entry['path'], tree, args.repo, task.get('branch') or 'task/' + short, project_settings(entry))
    with state() as s:
        repos = s.setdefault('task_repos', {}).setdefault(task['id'], [])
        if args.repo not in repos:
            repos.append(args.repo)
    return {'task': task['id'], 'repo': args.repo, 'worktree': str(target)}


def cmd_ask(args, b):
    text = sys.stdin.read() if args.text == '-' else args.text
    b = board_of_task(args.task, b)
    b.say(args.task, text.strip() + '\n\nReact 👍 to approve, or reply with changes.', ask=True)
    b.set(args.task, task_status=args.status)
    return {'task': args.task, 'status': args.status}


def cmd_poll(args, b):
    names = [table_of(args.project)[0]] if args.project else list(read_state().get('tables', {}))
    out = []
    base = b
    for name in names:
        b = board_for(name, base)
        for task in b.tasks(read_state()['tables'][name].get('collection')):
            status = task.get('task_status')
            if status not in PENDING:
                continue
            remember(task['id'], name)
            verdict, text, _ = anyboard.decide(b.messages(task['id']))
            row = {'table': name, 'task': task['id'], 'name': task.get('name'), 'was': status, 'verdict': verdict}
            if verdict == 'approved':
                row['now'] = 'Todo' if status == 'Awaiting Approval' else 'Done'
                b.set(task['id'], task_status=row['now'])
                b.say(task['id'], {'Todo': 'Approved, queued for a worker.',
                                   'Done': 'Accepted. Branch is ready to merge.'}[row['now']])
            elif verdict == 'rejected':
                row['now'] = 'Canceled' if status == 'Awaiting Approval' else 'Todo'
                b.set(task['id'], task_status=row['now'])
                b.say(task['id'], 'Dropped.' if row['now'] == 'Canceled' else 'Sent back to the worker.')
            elif verdict == 'feedback':
                row['feedback'] = text
                if status == 'In Review':
                    # Change requests on finished work go straight back to the worker with the notes.
                    row['now'] = 'Todo'
                    b.set(task['id'], task_status='Todo')
                    b.say(task['id'], 'Got it, sending your notes back to the worker.')
                else:
                    row['action'] = 'orchestrator: revise the plan, then `ask` again'
            if verdict != 'pending':
                out.append(row)
    return out


def revisions(messages):
    """Plan revisions the orchestrator asked about after the first plan (`ask`), oldest first."""
    asks = [m.get('text', '') for m in messages if m.get('text', '').startswith(anyboard.ASK)]
    out = []
    for i, t in enumerate(asks):
        text = t[len(anyboard.ASK):].split('\n\nReact ')[0].strip()
        if re.match(r'\*\*[a-z0-9-]+\*\* finished', text):
            continue                                   # a worker's result, not a plan
        if i > 0 or '\n' in text:                     # the first ask counts when it carries the plan
            out.append(text)
    return out


def brief_for(b, task_id, table, tree, tools=()):
    task = b.get(task_id)
    try:
        apps = project_settings(read_state()['tables'][table]).get('apps') or {}
    except (KeyError, ValueError, OSError):
        apps = {}
    app_path = (apps.get(task.get('task_app') or '') or {}).get('path')
    messages = b.messages(task_id)
    notes = owner_notes(messages)
    revised = revisions(messages)
    board = '%s/mstack board' % STACK_ROOT
    return '\n'.join([
        'Task: ' + task.get('name', ''), 'Project table: %s   Task id: %s' % (table, task_id), '',
        'Approved plan:', b.body(task_id), '',
        *(['Approved revisions (these override the plan above where they differ):',
           *['- ' + r for r in revised], ''] if revised else []),
        'Owner notes:', *(['- ' + n for n in notes] or ['- (none)']), '',
        'Rules:',
        '- Work only in %s: a git worktree on its own branch. Commit your changes there.' % tree,
        *(['- This task belongs to app [%s]; its code is in %s.' % (task.get('task_app'), tree/app_path)]
          if app_path else []),
        '- Do not merge, push, or touch other worktrees or the main checkout.',
        '- If scope or plan changes, tell the owner on the issue:',
        '  %s note --task %s "what changed"' % (board, task_id),
        '- When finished, report for review (this moves the issue to In Review):',
        '  %s done --task %s --summary "what changed and what is left"' % (board, task_id),
        *(['', 'mstack tools in this session (MCP):'] + ['- %s: %s' % (t['name'], t.get('hint', ''))
                                                         for t in tools] if tools else [])])


def wire_mcp(repo, tree, runner, servers):
    """Give this run the project's selected worker MCP servers in the host's own way, never globally.
    Returns (names wired, reasons skipped)."""
    if not servers:
        return [], []
    style = runners.mcp_style(runner, repo)
    names = [s['name'] for s in servers]
    if style == 'codex-config':
        return names, []          # passed as -c overrides on the run itself
    if style != 'mcp-json':
        return [], ['%s does not accept per-run MCP servers' % runner]
    if git(repo, 'ls-files', '--', '.mcp.json', check=False):
        return [], ['project tracks its own .mcp.json; mstack will not edit a team file']
    if intent.project_config(repo).get('visibility') != 'local':
        return [], ['.mcp.json wiring needs local visibility so it stays out of git']
    visibility.apply(repo, True)
    (tree/'.mcp.json').write_text(json.dumps({'mcpServers': {
        s['name']: {'command': s['command'][0], 'args': s['command'][1:]} for s in servers}}, indent=2) + '\n')
    settings_path = tree/'.claude/settings.local.json'
    settings = json.loads(settings_path.read_text()) if settings_path.is_file() else {}
    settings['enabledMcpjsonServers'] = sorted(set(settings.get('enabledMcpjsonServers', [])) | set(names))
    settings_path.parent.mkdir(exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + '\n')
    return names, []


def as_list(value):
    return value if isinstance(value, list) else [value] if value else []


def session_title(task):
    """Worker session title: '<ISSUE>: <title>' (e.g. 'IRO-104: Preview → Production migration')."""
    ident, name = task.get('linear_identifier'), task.get('name', '')
    return '%s: %s' % (ident, name) if ident and not name.startswith(ident) else name


def workspace_repos(settings):
    """Multi-repo workspace: taskboard.repos maps a name to {path, base}; the project root is not a repo."""
    return settings.get('repos') or {}


def add_repo(project, tree, name, branch, settings):
    """Give a workspace task its own worktree of one repo (<task folder>/<name>) on the issue's branch."""
    conf = workspace_repos(settings).get(name)
    if not conf:
        raise ValueError('No repo %r in taskboard.repos (known: %s)' % (name, ', '.join(sorted(workspace_repos(settings)))))
    source, target = Path(project)/conf.get('path', name), tree/name
    if not target.exists():
        base = conf.get('base') or (git(source, 'symbolic-ref', '--quiet', '--short', 'refs/remotes/origin/HEAD',
                                        check=False) or 'HEAD')
        exists = git(source, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch, check=False)
        git(source, 'worktree', 'add', '-q', *([str(target), branch] if exists else ['-b', branch, str(target), base]))
        (tree/'.mstack/cache').mkdir(parents=True, exist_ok=True)
        (tree/'.mstack/cache'/('base.' + name)).write_text(git(target, 'rev-parse', 'HEAD'))
    return target


def prepare(b, repo, task, table, runner=None):
    """Worktree + branch + task binding + MCP wiring + brief file: everything any host needs to start.
    A new worktree starts with its finished blockers' task branches merged in (that branch only).
    In a multi-repo workspace the task gets a plain folder; each repo it touches becomes a worktree
    inside it (the repos chosen at propose time, more with `board worktree`)."""
    short = (task.get('linear_identifier') or task['id'][-8:]).lower()
    branch_name = task.get('branch') or 'task/' + short
    tree = repo/'.mstack/worktrees'/short
    settings = project_settings(read_state()['tables'][table])
    if workspace_repos(settings):
        (tree/'.mstack/cache').mkdir(parents=True, exist_ok=True)
        for name in read_state().get('task_repos', {}).get(task['id'], []):
            add_repo(repo, tree, name, branch_name, settings)
    elif not tree.exists():
        git(repo, 'worktree', 'add', '-q', '-b', branch_name, str(tree))
        for blocker in as_list(task.get('task_blocked_by')):
            branch = b.get(blocker).get('branch') or 'task/' + blocker[-8:]
            if not git(repo, 'rev-parse', '--verify', '--quiet', branch, check=False):
                continue
            merged = subprocess.run(['git', '-C', str(tree), '-c', 'user.name=mstack orchestrator',
                                     '-c', 'user.email=orchestrator@mstack.local', 'merge', '--no-edit',
                                     '-m', 'Bring in %s (dependency)' % branch, branch],
                                    capture_output=True, text=True)
            if merged.returncode:
                git(tree, 'merge', '--abort', check=False)
                raise ValueError('Dependency %s does not merge cleanly into task/%s; resolve before dispatch'
                                 % (branch, short))
    cache = tree/'.mstack/cache'
    cache.mkdir(parents=True, exist_ok=True)
    (cache/'current-task').write_text(task['id'])
    if not (cache/'base').exists() and not workspace_repos(settings):
        (cache/'base').write_text(git(tree, 'rev-parse', 'HEAD'))
    local = repo/'.claude/settings.local.json'
    if local.is_file():
        (tree/'.claude').mkdir(exist_ok=True)
        (tree/'.claude/settings.local.json').write_text(local.read_text())
    servers, skipped = registry.worker_servers(repo)
    tools, refused = wire_mcp(repo, tree, runner, servers) if runner else ([], [])
    brief = brief_for(b, task['id'], table, tree, [s for s in servers if s['name'] in tools])
    if workspace_repos(settings):
        brief += ('\n\n## Workspace\nThis project is several repos. Your task folder is `%s`; each repo you change gets '
                  'its own worktree inside it on branch `%s`. Have: %s. Add one with `%s/mstack board worktree --task %s '
                  '--repo <name>` (repos: %s). Never edit the repos under the project root directly.'
                  % (tree, branch_name, ', '.join(sorted(p.name for p in tree.iterdir() if (p/'.git').exists())) or 'none yet',
                     STACK_ROOT, task.get('linear_identifier') or task['id'], ', '.join(sorted(workspace_repos(settings)))))
    (cache/'brief.md').write_text(brief + '\n')
    return tree, short, brief, {'tools': tools, 'servers': [s for s in servers if s['name'] in tools],
                                'skipped': skipped + refused}


def finish(b, task_id, tree, who, summary, exit_code=None):
    """Shared end of every run: commits since base, review ask, In Review."""
    bases = {p.name[5:]: p.read_text().strip() for p in (tree/'.mstack/cache').glob('base.*')}
    if bases:                                       # multi-repo workspace: one worktree per touched repo
        count, parts = 0, []
        for name, base in sorted(bases.items()):
            found = git(tree/name, 'log', '--oneline', base + '..HEAD', check=False).splitlines()
            count += len(found)
            parts.append('%s %d commit(s)' % (name, len(found)))
        commits, stat = ['x'] * count, '; '.join(parts)
        branch = git(tree/sorted(bases)[0], 'branch', '--show-current')
    else:
        base = (tree/'.mstack/cache/base').read_text().strip()
        commits = git(tree, 'log', '--oneline', base + '..HEAD', check=False).splitlines()
        stat = git(tree, 'diff', '--shortstat', base, 'HEAD', check=False) or 'no committed changes'
        branch = git(tree, 'branch', '--show-current')
    current = b.get(task_id)
    b.set(task_id, task_status='In Review', agent_run_count=(current.get('agent_run_count') or 0) + 1)
    ended = 'finished' if exit_code is None else 'finished (exit %s)' % exit_code
    b.say(task_id, '**%s** %s on branch `%s`: %d commit(s), %s.\n\n%s\n\nReact 👍 to accept, or reply with changes.'
          % (who, ended, branch, len(commits), stat,
             SECRET.sub('[redacted]', summary)[-1200:] or '(no summary)'), ask=True)
    return len(commits)


def cmd_dispatch(args, b):
    name, entry = table_of(args.project)
    settings = project_settings(entry)
    repo = Path(entry['path'])
    if workspace_repos(settings):
        pass                              # a folder of repos: each task gets worktrees of the repos it touches
    elif not git(repo, 'rev-parse', '--verify', 'HEAD', check=False):
        raise ValueError('Project needs at least one commit before worktrees can be created')
    elif Path(git(repo, 'rev-parse', '--show-toplevel')).resolve() != repo.resolve():
        raise ValueError('Dispatch needs the project at its repository root')
    runs = read_state().get('runs', {})
    b = board_for(name, b)
    tasks = b.tasks(entry.get('collection'))
    # Busy: in progress with a live CLI process, or handed to a desktop host that has not reported done.
    busy = [t['id'] for t in tasks if t.get('task_status') == 'In Progress' and t['id'] in runs
            and (runs[t['id']].get('pid') is None or alive(runs[t['id']]['pid']))]
    room = settings.get('max_parallel', 3) - len(busy)
    started = []
    for task in tasks:
        if room <= 0:
            break
        if task.get('task_status') != 'Todo' or task.get('task_agent') == 'human':
            continue
        if (runs.get(task['id']) or {}).get('adopted'):
            continue                      # an existing session already works on it
        waiting = [x for x in as_list(task.get('task_blocked_by')) if b.get(x).get('task_status') != 'Done']
        if waiting:
            continue      # blockers first; their branches are merged in when this task starts
        runner = args.runner or runners.choose(task.get('task_agent'), settings.get('workers', ['codex']), repo)
        tree, short, brief, wiring = prepare(b, repo, task, name, runner)
        app = (settings.get('apps') or {}).get(task.get('task_app') or '')
        work_dir = tree/app['path'] if app else tree
        run = {'table': name, 'runner': runner, 'tree': str(tree), 'cwd': str(work_dir), 'pid': None,
               'issue': task.get('linear_identifier'),
               'parent': task.get('parent'),
               'mcp': wiring['servers']}
        row = {'task': task['id'], 'name': task.get('name'), 'runner': runner,
               'tools': wiring['tools'], 'skipped_tools': wiring['skipped']}
        if runners.kind(runner, repo) == 'spawn':
            log = repo/'.mstack/cache/runs'/(short + '.log')
            log.parent.mkdir(parents=True, exist_ok=True)
            run['pid'] = row['pid'] = spawn([sys.executable, str(HERE/'cli.py'), 'work', '--task', task['id'],
                                            '--table', name, '--runner', runner, '--tree', str(tree)], log)
            run['log'] = str(log)
            where = 'Dispatched to **%s**' % runner
        else:
            row['handoff'] = run['handoff'] = runners.handoff(runner, session_title(task), work_dir, brief, repo)
            where = 'Handed to **%s**' % runner
        b.set(task['id'], task_status='In Progress', task_agent=runner, agent_session=runner + ' · ' + str(tree))
        b.say(task['id'], '%s in worktree `%s` (branch task/%s).' % (where, tree, short))
        with state() as s:
            s.setdefault('runs', {})[task['id']] = run
        started.append(row)
        room -= 1
    return {'table': name, 'started': started, 'already_running': len(busy)}


def cmd_ack(args, b):
    """The orchestrator started the host session for a handoff: stop offering it."""
    with state() as s:
        run = s.get('runs', {}).get(args.task)
        if not run or not run.get('handoff'):
            raise ValueError('Task %s has no handoff to acknowledge' % args.task)
        run['session'] = args.session
    return {'task': args.task, 'session': args.session}


def auto_tables(skipped=None):
    out = []
    for name, entry in read_state().get('tables', {}).items():
        try:
            if project_settings(entry).get('auto'):
                out.append(name)
        except (ValueError, OSError, KeyError) as error:
            # A table whose project config is gone or invalid is never automated, but says why.
            if skipped is not None:
                skipped[name] = str(error)[:200]
    return out


def linear_signals(name, lb, seen, fresh):
    """What only the orchestrator agent can act on, from one read of a Linear board:
    /plan triggers, your comments on work in progress (to forward to the worker), and
    issues you closed while a worker still had them."""
    runs = read_state().get('runs', {})
    out = []
    for task in lb.tasks():
        messages = lb.messages(task['id'])
        mine = [m for m in messages if not m['text'].startswith(anyboard.MARK)]
        last_bot = max([m['order'] for m in messages if m['text'].startswith(anyboard.MARK)] or [''])
        for m in mine:
            hit = TRIGGER.match(m['text'])
            if hit and m['order'] > last_bot and 'trigger:' + m['id'] not in seen:
                out.append({'kind': 'plan', 'table': name, 'task': task['id'], 'issue': task['linear_identifier'],
                            'name': task['name'], 'notes': hit.group(2).strip(), 'url': task.get('linear_url')})
                fresh.append('trigger:' + m['id'])
        run = runs.get(task['id'])
        if run and (task['task_status'] == 'In Progress' or run.get('adopted')) and not task.get('closed_by_owner') \
                and task['task_status'] not in ('Done', 'Canceled'):
            for m in mine:
                if m['order'] > last_bot and not TRIGGER.match(m['text']) and 'fwd:' + m['id'] not in seen:
                    out.append({'kind': 'forward', 'table': name, 'task': task['id'], 'issue': task['linear_identifier'],
                                'session': run.get('session'), 'text': m['text']})
                    fresh.append('fwd:' + m['id'])
        if task.get('closed_by_owner') and run and 'stop:' + task['id'] not in seen:
            out.append({'kind': 'stop', 'table': name, 'task': task['id'], 'issue': task['linear_identifier'],
                        'session': run.get('session'), 'now': task['task_status']})
            lb.say(task['id'], 'Stopped: you closed this issue in Linear (status → %s).' % task['task_status'])
            fresh.append('stop:' + task['id'])
    return out


PG = {'host': 'host.orb.internal', 'port': '55322', 'db': 'mstack_orchestrator', 'user': 'mstack_orchestrator',
      'password_file': STACK_ROOT/'.secrets/postgres/mstack_orchestrator.password'}
COLUMNS = ('identifier', 'linear_id', 'team', 'app', 'title', 'state', 'state_type', 'parent', 'focus',
           'scopes', 'managed', 'agent_phase', 'url', 'updated_at')


def mirror(name, run_sql=None):
    """Refresh the local issue table (Postgres orchestrator.issues) for one Linear board: every
    issue assigned to or created by the owner, with which orchestrator scopes focus on it.
    A read-only view of Linear; sessions are never started from it."""
    entry = read_state()['tables'][name]
    settings = project_settings(entry)
    board = LINEAR_BOARD(entry['path'], settings, all_issues=True)
    rows = board.tasks()
    scopes = {s: LINEAR_BOARD(entry['path'], settings, scope=conf) for s, conf in (settings.get('orchestrators') or {}).items()}
    out = []
    for t in rows:
        issue = board.cache.get(t['id']) or {}
        in_scopes = sorted(s for s, b in scopes.items()
                           if (b.focus or b.exclude) and any(l.app == board.owner_of[t['id']].app for l in b.links)
                           and b.in_focus(t['linear_identifier'], board.owner_of[t['id']]))
        out.append({'identifier': t['linear_identifier'], 'linear_id': t['id'],
                    'team': board.owner_of[t['id']].conf['team'], 'app': t.get('task_app'), 'title': t['name'],
                    'state': t.get('linear_state'), 'state_type': t.get('linear_state_type'), 'parent': t.get('parent'),
                    'focus': bool(in_scopes), 'scopes': ','.join(in_scopes), 'managed': t.get('managed', False),
                    'agent_phase': t['task_status'] if t.get('managed') else None, 'url': t.get('linear_url'),
                    'updated_at': issue.get('updatedAt')})
    payload = json.dumps(out)
    tag = '$m%s$' % hashlib.sha256(payload.encode()).hexdigest()[:8]
    cols = ', '.join(COLUMNS)
    sql = ("BEGIN;\nCREATE TEMP TABLE incoming AS SELECT * FROM jsonb_to_recordset(%s%s%s::jsonb) AS x("
           "identifier text, linear_id text, team text, app text, title text, state text, state_type text, "
           "parent text, focus boolean, scopes text, managed boolean, agent_phase text, url text, updated_at timestamptz);\n"
           "INSERT INTO orchestrator.issues (board, %s, synced_at, present) SELECT %s, %s, now(), true FROM incoming "
           "ON CONFLICT (board, identifier) DO UPDATE SET %s, synced_at = now(), present = true;\n"
           "UPDATE orchestrator.issues SET present = false WHERE board = %s AND identifier NOT IN (SELECT identifier FROM incoming);\n"
           "COMMIT;\n") % (tag, payload, tag, cols, "'%s'" % name, cols,
                            ', '.join('%s = EXCLUDED.%s' % (c, c) for c in COLUMNS), "'%s'" % name)
    (run_sql or psql)(sql)
    return {'table': name, 'rows': len(out), 'focus': sum(1 for r in out if r['focus'])}


def psql(sql):
    env = dict(os.environ, PGPASSWORD=Path(PG['password_file']).read_text().strip())
    subprocess.run(['psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-h', PG['host'], '-p', PG['port'], '-U', PG['user'],
                    '-d', PG['db']], input=sql, text=True, env=env, check=True, capture_output=True, timeout=60)


def cmd_mirror(args, b):
    return mirror(table_of(args.project)[0])


def cmd_adopt(args, b):
    """Track an existing session as the worker for an issue: record the link, and say so on the issue."""
    name, entry = table_of(args.project)
    b = board_for(name, b)
    task = b.get(args.task)
    if args.related:
        # An earlier or obsolete chat about the issue: listed with it, never its worker, nothing posted.
        with state() as s:
            sessions = s.setdefault('related', {}).setdefault(task['id'], [])
            sessions[:] = [r for r in sessions if r['session'] != args.session]
            sessions.append({'session': args.session, 'tree': args.tree, 'scope': SCOPE, 'note': args.related})
        remember(task['id'], name, task.get('linear_identifier'))
        return {'task': task['id'], 'issue': task.get('linear_identifier'), 'scope': SCOPE, 'related': args.related}
    # A session is already on it: In Progress unless the issue is closed (never "Todo", which would dispatch a second worker).
    status = {'completed': 'Done', 'canceled': 'Canceled', 'duplicate': 'Canceled'}.get(task.get('linear_state_type'), 'In Progress')
    with state() as s:
        s.setdefault('runs', {})[task['id']] = {'table': name, 'scope': SCOPE, 'runner': 'claude-desktop', 'pid': None,
                                                'session': args.session, 'tree': args.tree, 'cwd': args.tree,
                                                'issue': task.get('linear_identifier'),
                                                'parent': task.get('parent'),
                                                'adopted': True}
    remember(task['id'], name, task.get('linear_identifier'))
    b.say(task['id'], 'Tracked by the %s orchestrator: session `%s`%s (status → %s).'
          % (SCOPE or name, args.session, ' in `%s`' % args.tree if args.tree else '', status))
    return {'task': task['id'], 'issue': task.get('linear_identifier'), 'scope': SCOPE, 'status': status}


def cmd_tick(args, b):
    """One unattended pass over every `taskboard.auto` table: apply verdicts, start what is
    approved, and list what only an orchestrator agent can do (start a desktop session,
    revise a plan). Safe to repeat: nothing is offered twice."""
    skipped = {}
    names = [table_of(args.project)[0]] if args.project else auto_tables(skipped)
    out = {'tables': names, 'verdicts': [], 'started': [], 'needs_orchestrator': []}
    if skipped:
        out['skipped_tables'] = skipped
    seen = set(read_state().get('attention_seen', []))
    fresh = []
    for name in names:
        entry = read_state()['tables'][name]
        links = [] if is_linear(entry) else links_of(project_settings(entry))
        if links:
            missing = [code or '*' for code, link in links if not (Path(entry['path'])/link['credential_file']).is_file()]
            last = read_state().get('last_sync', {}).get(name, 0)
            if missing:
                out.setdefault('waiting', []).append('%s: Linear link configured, key file missing (%s)'
                                                     % (name, ', '.join(missing)))
            elif time.time() - last >= SYNC_EVERY:
                # A Linear outage must never stop the board loop: record it and carry on.
                try:
                    synced = cmd_sync(argparse.Namespace(project=name), b)
                    out.setdefault('synced', {})[name] = {k: synced[k] for k in ('pulled', 'pushed') if k in synced}
                except (RuntimeError, ValueError, OSError) as error:
                    out.setdefault('sync_errors', {})[name] = str(error)[:200]
                with state() as s:
                    s.setdefault('last_sync', {})[name] = time.time()
        for task in ([] if is_linear(entry) else b.tasks(entry['collection'])):
            key = 'plan:' + task['id']
            if task.get('task_source') == 'linear' and task.get('task_status') == 'Backlog' and key not in seen:
                out['needs_orchestrator'].append({'kind': 'plan', 'task': task['id'], 'name': task.get('name'),
                                                  'linear': task.get('linear_identifier')})
                fresh.append(key)
        if is_linear(entry):
            if time.time() - read_state().get('last_mirror', {}).get(name, 0) >= MIRROR_EVERY:
                try:
                    out.setdefault('mirrored', {})[name] = mirror(name)['rows']
                except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                    out.setdefault('mirror_errors', {})[name] = str(error)[:200]
                with state() as s:
                    s.setdefault('last_mirror', {})[name] = time.time()
            last = read_state().get('last_linear_poll', {}).get(name, 0)
            if time.time() - last < LINEAR_EVERY:
                continue
            with state() as s:
                s.setdefault('last_linear_poll', {})[name] = time.time()
            try:
                out['needs_orchestrator'] += linear_signals(name, board_for(name, b), seen, fresh)
            except (RuntimeError, ValueError, OSError) as error:
                out.setdefault('sync_errors', {})[name] = str(error)[:200]
                continue
        rows = cmd_poll(argparse.Namespace(project=name), b)
        out['verdicts'] += [r for r in rows if r.get('now')]
        for r in rows:
            key = '%s:%s' % (r['task'], hashlib.sha256(r.get('feedback', '').encode()).hexdigest()[:12])
            if r.get('action') and key not in seen:
                out['needs_orchestrator'].append({'kind': 'replan', 'task': r['task'], 'name': r['name'],
                                                  'feedback': r['feedback']})
                fresh.append(key)
        out['started'] += cmd_dispatch(argparse.Namespace(project=name, runner=None), b)['started']
    for task, run in read_state().get('runs', {}).items():
        if run['table'] in names and run.get('handoff') and not run.get('session'):
            out['needs_orchestrator'].append({'kind': 'handoff', 'task': task, **run['handoff']})
    with state() as s:
        s['attention_seen'] = sorted(set(s.get('attention_seen', [])) | set(fresh))
        s['last_tick'] = {'at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tables': names,
                          'started': len(out['started']), 'needs_orchestrator': len(out['needs_orchestrator'])}
    return out


def code_fingerprint():
    """Changes whenever mstack's own code or schemas change (a commit, a merge or a plain edit)."""
    parts = []
    for folder in ('orchestrator', 'stack', 'plugins', 'gateway'):
        for path in sorted((STACK_ROOT/'integrations'/folder).rglob('*')):
            if path.suffix in ('.py', '.json') and '__pycache__' not in path.parts and 'tests' not in path.parts:
                stat = path.stat()
                parts.append('%s:%d:%d' % (path, stat.st_mtime_ns, stat.st_size))
    return hashlib.sha256('\n'.join(parts).encode()).hexdigest()


def reload_watcher(args):
    """mstack changed under a running watcher: sync its project, then restart in place (same PID,
    same command line) so it runs the new code. The lock is released by exec and taken again."""
    if args.project:
        try:
            path = table_of(args.project)[1]['path']
            subprocess.run([str(STACK_ROOT/'mstack'), 'sync', '--project', path, '--quiet'], timeout=120, check=False)
        except (ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
            print('sync before reload failed: %s' % str(error)[:200], file=sys.stderr, flush=True)
    print('%s mstack updated: reloading watcher' % time.strftime('%H:%M:%S'), file=sys.stderr, flush=True)
    os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve()), *ARGV])


def cmd_watch(args, b):
    """Shell-only loop (no model calls): tick every --interval seconds; exit with the work
    when an orchestrator agent is needed, so a waiting agent wakes only for real work.
    Only one watcher may run: a second one refuses to start instead of racing on dispatch."""
    STATE.parent.mkdir(parents=True, exist_ok=True)
    lock = STATE.with_name('watch.%s.lock' % '.'.join(filter(None, (args.project or 'all', SCOPE))))
    guard = open(lock, 'w')
    try:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError('Another watcher is already running (lock %s)' % lock)
    failures = 0
    started_on = code_fingerprint()
    while True:
        if ARGV is not None and code_fingerprint() != started_on:
            reload_watcher(args)
        try:
            result = cmd_tick(argparse.Namespace(project=args.project), b)
            failures = 0
            print('%s tick: %d verdicts, %d started, %d need orchestrator%s' % (
                time.strftime('%H:%M:%S'), len(result['verdicts']), len(result['started']),
                len(result['needs_orchestrator']),
                ''.join('; sync %s failed: %s' % kv for kv in result.get('sync_errors', {}).items())
                + ''.join('; %s skipped: %s' % kv for kv in result.get('skipped_tables', {}).items())),
                file=sys.stderr, flush=True)
            if result['needs_orchestrator'] or (args.exit_on_start and result['started']):
                return result
        except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as error:
            failures += 1
            print('tick failed (%d): %s' % (failures, str(error)[:200]), file=sys.stderr, flush=True)
            if failures >= 5:
                raise RuntimeError('watch stopped after 5 failed ticks in a row: ' + str(error)[:200])
        if args.max_ticks and args.max_ticks <= 1:
            return {'stopped': 'max ticks reached'}
        args.max_ticks = args.max_ticks - 1 if args.max_ticks else 0
        time.sleep(args.interval)


def cmd_work(args, b):
    """Detached CLI worker: one non-interactive agent session, then report back for review."""
    b = board_of_task(args.task, b)
    tree = Path(args.tree)
    brief = (tree/'.mstack/cache/brief.md').read_text()
    env = dict(os.environ, MSTACK_TASK=args.task, MSTACK_AGENT=args.runner)
    if args.runner == 'codex':
        env['MSTACK_CODEX_NOTIFY'] = '1'
    run = read_state().get('runs', {}).get(args.task, {})
    work_dir = Path(run.get('cwd') or tree)
    done = subprocess.run(runners.command(args.runner, brief, work_dir, Path(table_of(args.table)[1]['path']),
                                          run.get('mcp', [])),
                          cwd=work_dir, env=env,
                          capture_output=True, text=True)
    output = SECRET.sub('[redacted]', (done.stdout + done.stderr).strip())
    commits = finish(b, args.task, tree, args.runner, output, done.returncode)
    return {'task': args.task, 'exit': done.returncode, 'commits': commits, 'output_tail': output[-4000:]}


def cmd_done(args, b):
    """A worker in any host (desktop session, manual) reports its task ready for review."""
    b = board_of_task(args.task, b)
    run = read_state().get('runs', {}).get(args.task)
    if not run:
        raise ValueError('Task %s was not dispatched' % args.task)
    summary = (sys.stdin.read() if args.summary == '-' else args.summary) + doc_links(table_of_task(args.task), args.doc)
    commits = finish(b, args.task, Path(run['tree']), run['runner'], summary)
    return {'task': args.task, 'status': 'In Review', 'commits': commits}


def cmd_note(args, b):
    b = board_of_task(args.task, b)
    text = SECRET.sub('[redacted]', sys.stdin.read() if args.text == '-' else args.text).strip()
    who = {'in': '%s ← owner (session)', 'out': '%s → (session)', 'note': '%s'}[args.direction] % args.agent
    b.say(args.task, '%s: %s%s' % (who, text[:1800], doc_links(table_of_task(args.task), args.doc)))
    if args.status:
        b.set(args.task, task_status=args.status)
    return {'task': args.task, 'posted': True, 'status': args.status}


def cmd_owner(args, b):
    """Private boards: pass on what the owner said in the orchestrator chat (`/plan …`, 👍, a reply)."""
    name, entry = table_of(args.project)
    lb = board_for(name, b)
    if not hasattr(lb, 'owner_says'):
        raise ValueError('%s is not a Linear board' % name)
    text = (sys.stdin.read() if args.text == '-' else args.text).strip()
    task = lb.get(args.task)
    lb.owner_says(task['id'], text)
    return {'task': task['id'], 'issue': task.get('linear_identifier'), 'recorded': text[:200]}


def cmd_thread(args, b):
    """The issue's conversation as the board sees it (on a private board: the local journal too)."""
    name, entry = table_of(args.project)
    lb = board_for(name, b)
    task = lb.get(args.task)
    return {'issue': task.get('linear_identifier'), 'status': task['task_status'],
            'messages': [{'at': m['order'], 'text': m['text'], 'reactions': m['reactions']} for m in lb.messages(task['id'])]}


def watcher_running(project, scope):
    """True if a watcher holds the lock for this project (by name or as given) and scope."""
    for key in {project, table_of(project)[0]}:
        lock = STATE.with_name('watch.%s.lock' % '.'.join(filter(None, (key, scope))))
        if not lock.exists():
            continue
        with open(lock, 'a') as probe:
            try:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(probe, fcntl.LOCK_UN)
            except BlockingIOError:
                return True
    return False


def cmd_handover(args, b):
    """Everything a fresh orchestrator session needs to take over this board (or scope) from
    a session whose chat grew too long: open issues, what waits on the owner, workers and
    related chats, the latest messages per open issue, and a ready-to-use prompt."""
    name, entry = table_of(args.project)
    settings = project_settings(entry)
    lb = board_for(name, b)
    st = read_state()
    runs = {k: v for k, v in st.get('runs', {}).items() if v.get('table') == name and v.get('scope') == SCOPE}
    related = st.get('related', {})
    open_rows, waiting = [], []
    for t in lb.tasks(entry.get('collection')):
        tid, status = t['id'], t.get('task_status')
        if not (t.get('managed') or tid in runs or tid in related) or status in ('Done', 'Canceled') and tid not in runs:
            continue
        row = {'issue': t.get('linear_identifier') or tid, 'title': t.get('name'), 'status': status}
        if tid in runs:
            row['worker'] = runs[tid].get('session')
            if runs[tid].get('tree'):
                row['tree'] = runs[tid]['tree']
        if related.get(tid):
            row['related'] = ['%s (%s)' % (r['session'], r['note']) for r in related[tid] if r.get('scope') in (None, SCOPE)]
        if status not in ('Done', 'Canceled'):
            msgs = lb.messages(tid) if hasattr(lb, 'messages') else []
            row['latest'] = [m['text'][:300] for m in msgs[-args.messages:]] if args.messages else []
        if status in ('Awaiting Approval', 'In Review'):
            waiting.append(row['issue'])
        open_rows.append(row)
    order = ['Awaiting Approval', 'In Review', 'In Progress', 'Todo', 'Backlog', 'Done', 'Canceled']
    open_rows.sort(key=lambda r: order.index(r['status']) if r['status'] in order else 99)
    who = SCOPE or name
    flag = ' --scope %s' % SCOPE if SCOPE else ''
    running = watcher_running(args.project, SCOPE)
    lines = ['You are the **%s orchestrator** for %s, taking over from a previous session whose chat grew too long.'
             % (who, entry['path']),
             'Load the `mstack-orchestrator` skill and follow it. Engine: `%s/mstack board <cmd> --project %s%s`.'
             % (STACK_ROOT, name, flag)]
    if SCOPE:
        lines.append('Scope: %s.' % json.dumps(scope_conf(settings), ensure_ascii=False))
    if settings.get('private'):
        lines.append('This board is PRIVATE: nothing is written to Linear; the owner gives /plan, 👍, 👎 and feedback '
                     'in your chat and you record them with `owner`.')
    lines.append('Watcher: %s.' % ('the previous session\'s watcher is still running; ask the owner to stop it there, '
                                   'or stop that process, before starting yours' if running else
                                   'none running; start `watch --project %s%s` in the background' % (name, flag)))
    lines.append('Workers are existing sessions: message them with SendMessage by id; never start a second one for an issue.')
    if waiting:
        lines.append('Waiting on the owner: %s.' % ', '.join(waiting))
    lines.append('Board state now (from `handover`):')
    for r in open_rows:
        extra = ''.join([' worker `%s`' % r['worker'] if r.get('worker') else '',
                         ' related: %s' % ', '.join(r['related']) if r.get('related') else ''])
        lines.append('- %s [%s] %s%s' % (r['issue'], r['status'], r['title'], extra))
        for m in r.get('latest') or []:
            lines.append('    > ' + m.replace('\n', ' ')[:200])
    lines.append('First run `status` and `handover` yourself to confirm, then tell the owner you have taken over.')
    return {'table': name, 'scope': SCOPE, 'private': bool(settings.get('private')), 'watcher_running': running,
            'waiting_on_owner': waiting, 'issues': open_rows, 'prompt': '\n'.join(lines)}


def cmd_status(args, b):
    name, entry = table_of(args.project)
    st = read_state()
    runs, related = st.get('runs', {}), st.get('related', {})
    rows = []
    for t in board_for(name, b).tasks(entry.get('collection')):
        row = {'task': t['id'], 'name': t.get('name'), 'status': t.get('task_status'), 'agent': t.get('task_agent'),
               'running': t['id'] in runs and alive(runs[t['id']]['pid'])}
        if t.get('linear_identifier'):
            row['issue'] = t['linear_identifier']
        if t['id'] in runs:
            row['session'] = runs[t['id']].get('session')
        if related.get(t['id']):
            row['related'] = [{'session': r['session'], 'note': r['note']} for r in related[t['id']]]
        rows.append(row)
    order = ['Awaiting Approval', 'Todo', 'In Progress', 'In Review', 'Backlog', 'Done', 'Canceled']
    rows.sort(key=lambda r: order.index(r['status']) if r['status'] in order else 99)
    links = {code or '*': '%s/%s %s' % (l['workspace'], l['team'], l['mode']) for code, l in links_of(project_settings(entry))}
    return {'table': name, 'links': links or 'private', 'tasks': rows}


def cmd_link(args, b):
    """Link a project's table to Linear with one entry of the owner's central key file.
    The key is verified live, then copied into that project's own .mstack/secrets (0600)."""
    import linear
    project = Path(args.project).resolve()
    rows = linear.central_keys(STACK_ROOT/'.secrets/linear.csv')
    if args.entry not in rows:
        raise ValueError('No entry %s in .secrets/linear.csv' % args.entry)
    key = rows[args.entry]['key']
    post = linear.http(key)
    org = post(linear.WHO, {})['organization']
    teams = {t['key']: t['name'] for t in post(linear.TEAMS, {})['teams']['nodes']}
    if args.team not in teams:
        raise ValueError('Team %s is not in workspace %s (teams: %s)' % (args.team, org['urlKey'], ', '.join(sorted(teams))))
    cfg = json.loads((project/'.mstack/stack.json').read_text())
    apps = cfg.get('taskboard', {}).get('apps') or {}
    if args.app and args.app not in apps:
        raise ValueError('Unknown app %s; add it to taskboard.apps first' % args.app)
    ref = '.mstack/secrets/linear-api-key' + ('-' + args.app.lower() if args.app else '')
    target = project/ref
    if target.exists() and target.read_text().strip() != key and not args.replace:
        raise ValueError('%s already holds a different key; pass --replace to swap it' % ref)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as out:
        out.write(key)
    os.chmod(target, 0o600)
    path = project/'.mstack/stack.json'
    link = {'provider': 'linear', 'mode': args.mode, 'scope': 'mine', 'workspace': org['urlKey'],
            'team': args.team, 'key_entry': int(args.entry), 'credential_file': ref}
    if args.app:
        cfg['taskboard']['apps'][args.app]['link'] = link
    else:
        cfg.setdefault('taskboard', {})['link'] = link
    path.write_text(json.dumps(cfg, indent=2) + '\n')
    intent.project_config(project)          # the result must still validate
    return {'project': str(project), 'app': args.app, 'workspace': org['urlKey'], 'workspace_name': org['name'],
            'team': args.team, 'team_name': teams[args.team], 'mode': args.mode, 'key_entry': int(args.entry)}


def links_of(settings):
    """[(app code or None, link)]: the table-wide link and each app's own link."""
    out = [(None, settings['link'])] if settings.get('link') else []
    out += [(code, app['link']) for code, app in sorted((settings.get('apps') or {}).items()) if app.get('link')]
    return out


def cmd_sync(args, b):
    import linear
    name, entry = table_of(args.project)
    settings = project_settings(entry)
    links = links_of(settings)
    if not links:
        return {'table': name, 'link': 'private', 'synced': False}
    others = [code for code, _ in links if code]
    total = {'table': name, 'links': {}, 'pulled': [], 'pushed': []}
    for code, link in links:
        key = intent.project_state.credential(Path(entry['path']), link['credential_file'], exists=True).read_text().strip()
        got = linear.sync(b, name, entry['collection'], link, linear.http(key), app=code, others=others)
        total['links'][code or '*'] = {'mode': link['mode'], 'workspace': link['workspace'], 'team': link['team'],
                                       **{k: got[k] for k in ('pulled', 'pushed', 'updated_in_anytype', 'updated_in_linear')}}
        total['pulled'] += got['pulled']
        total['pushed'] += got['pushed']
    return total


def parser():
    p = argparse.ArgumentParser(prog='mstack board', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('table'); s.add_argument('--project', required=True)
    s = sub.add_parser('plan'); s.add_argument('--project', required=True); s.add_argument('--title', required=True)
    s.add_argument('--plan', required=True, help='file or - for stdin'); s.add_argument('--agent', default='codex')
    s.add_argument('--priority', default='Medium', choices=['Urgent', 'High', 'Medium', 'Low'])
    s.add_argument('--labels', nargs='*', default=[])
    s.add_argument('--app', help='app code from taskboard.apps; title becomes [APP][KIND] …')
    s.add_argument('--kind', help='FEAT, BUG, CHORE, DOCS, TEST, REFACTOR, PERF, SEC or OPS')
    s.add_argument('--parent', help='Linear boards: create as a sub-issue of this issue (e.g. IRO-123)')
    s = sub.add_parser('propose', help='post a plan on an existing issue and ask for a verdict (the /plan flow)')
    s.add_argument('--project', required=True); s.add_argument('--task', required=True, help='issue id or IRO-123')
    s.add_argument('--plan', required=True, help='file or - for stdin'); s.add_argument('--agent', default='claude-desktop')
    s.add_argument('--doc', action='append', default=[], help='repo doc path to link (taskboard.docs_url)')
    s.add_argument('--repos', nargs='*', default=[], help='multi-repo workspace: repos the task will change')
    s = sub.add_parser('worktree', help='multi-repo workspace: add a repo worktree to a task folder')
    s.add_argument('--task', required=True, help='issue id or IRO-123'); s.add_argument('--repo', required=True)
    s = sub.add_parser('ask'); s.add_argument('--task', required=True); s.add_argument('text')
    s.add_argument('--status', default='Awaiting Approval', choices=list(PENDING))
    s = sub.add_parser('poll'); s.add_argument('--project')
    s = sub.add_parser('dispatch'); s.add_argument('--project', required=True)
    s.add_argument('--runner', help='agent plugin name (built-in or the project\'s own)')
    s = sub.add_parser('work'); s.add_argument('--task', required=True); s.add_argument('--table', required=True)
    s.add_argument('--runner', required=True); s.add_argument('--tree', required=True)
    s = sub.add_parser('tick'); s.add_argument('--project')
    s = sub.add_parser('watch'); s.add_argument('--project'); s.add_argument('--interval', type=int, default=10)
    s.add_argument('--max-ticks', type=int, default=0, help='stop after N ticks (0 = run until work appears)')
    s.add_argument('--exit-on-start', action='store_true', help='also exit when a CLI worker was started')
    s = sub.add_parser('ack'); s.add_argument('--task', required=True); s.add_argument('--session', required=True)
    s = sub.add_parser('done'); s.add_argument('--task', required=True)
    s.add_argument('--summary', default='', help='text or - for stdin')
    s.add_argument('--doc', action='append', default=[], help='repo doc path to link (taskboard.docs_url)')
    s = sub.add_parser('note'); s.add_argument('--task', required=True); s.add_argument('text')
    s.add_argument('--doc', action='append', default=[], help='repo doc path to link (taskboard.docs_url)')
    s.add_argument('--agent', default=os.environ.get('MSTACK_AGENT', 'agent'))
    s.add_argument('--direction', choices=['in', 'out', 'note'], default='note')
    s.add_argument('--status', choices=['Todo', 'In Progress', 'In Review', 'Done', 'Canceled'])
    s = sub.add_parser('status'); s.add_argument('--project', required=True)
    s = sub.add_parser('owner', help='private boards: record what the owner said in chat (/plan …, 👍, a reply)')
    s.add_argument('--project', required=True); s.add_argument('--task', required=True, help='issue id or IRO-123')
    s.add_argument('text', help='text or - for stdin')
    s = sub.add_parser('handover', help='brief for a fresh orchestrator session taking over this board or scope')
    s.add_argument('--project', required=True)
    s.add_argument('--messages', type=int, default=2, help='latest messages to include per open issue')
    s = sub.add_parser('thread', help="an issue's conversation as the board sees it")
    s.add_argument('--project', required=True); s.add_argument('--task', required=True, help='issue id or IRO-123')
    s = sub.add_parser('mirror', help='refresh the local Postgres issue table for a Linear board')
    s.add_argument('--project', required=True)
    s = sub.add_parser('adopt', help='track an existing session as the worker for an issue')
    s.add_argument('--project', required=True); s.add_argument('--task', required=True, help='issue id or IRO-123')
    s.add_argument('--session', required=True); s.add_argument('--tree', help='its worktree, if it has its own')
    s.add_argument('--related', metavar='NOTE', help='list the session with the issue (e.g. "obsolete") instead of as its worker')
    s = sub.add_parser('sync'); s.add_argument('--project', required=True)
    s = sub.add_parser('link'); s.add_argument('--project', required=True); s.add_argument('--entry', required=True)
    s.add_argument('--team', required=True); s.add_argument('--mode', choices=['pull', 'push', 'full'], default='pull')
    s.add_argument('--replace', action='store_true')
    s.add_argument('--app', help='link only this app (code from taskboard.apps); its own key file')
    return p


ARGV = None                               # real command line (never set when main() is called from tests)


def main(argv=None, b=None):
    global SCOPE, ARGV
    p = parser()
    for sp in p._subparsers._group_actions[0].choices.values():
        sp.add_argument('--scope', help='orchestrator scope from taskboard.orchestrators')
    args = p.parse_args(argv)
    SCOPE = getattr(args, 'scope', None)
    if argv is None:
        ARGV = list(sys.argv[1:])          # a real command line: only then may a watcher re-exec itself
    try:
        result = globals()['cmd_' + args.command](args, b or anyboard.Board())
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print('mstack board: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
