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
  work     (spawned by dispatch) run a CLI worker's turns; --resume continues its session with queued comments
  forward  pass an owner comment to a CLI worker: queued, or a resumed turn when its process has ended
  stop     stop a CLI worker's process (desktop sessions are stopped with the host's own tool)
  done     a worker in any host reports its task ready for review
  note     reverse path: a session or worker updates the issue
  merged   after merge and push: docs as the issue's Resources, one note, Done (or In Review with --verify)
  status   one table at a glance
  sync     reconcile a linked table with Linear (pull, push or full)
  link     link a table to Linear with an entry of the owner's .secrets/linear.csv
  orchestrators  register|list: which orchestrator session serves a (project, scope)
  events   next|resolve|list|schema: the event hub queue (design 011)
  sessions      todo|observe|done|list: the hub chat's side of the "My tasks" CTAs and session states (design 014)
  status-table  sync|show|rename: the owner's read-only "My tasks" table in Anytype, fed from the hub (design 014)
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent/'stack'))
import board as anyboard
import config as intent
import linear
import linear_board
import runners          # puts integrations/plugins on sys.path
import registry
import project_state
import status_table
import store
import visibility

STACK_ROOT = anyboard.STACK_ROOT
STATE = STACK_ROOT/'.mstack/evidence/taskboard-test.json'
DEFAULT_STATE = STATE
SECRET = re.compile(r'(anytype_[0-9A-Za-z_]{20,}|sk-[0-9A-Za-z_-]{16,}|Bearer\s+\S+|ghp_[0-9A-Za-z]{20,}|lin_api_[0-9A-Za-z]{20,})')
PENDING = ('Awaiting Approval', 'In Review')
SYNC_EVERY = 300          # seconds between Linear syncs per table inside tick/watch
LINEAR_EVERY = 30         # seconds between polls of a Linear board inside tick/watch
TRIGGER = re.compile(r'^\s*(/plan|@agent plan)\b(.*)', re.S | re.I)


def hub_settings():
    try:
        return intent.project_config(STACK_ROOT).get('hub') or {}
    except (ValueError, OSError, KeyError):
        return {}


def board_store():
    """The store for STATE (store.py). Postgres only for the real state file and `hub.store: postgres`;
    any other STATE (tests) is always the plain file."""
    current = store.ACTIVE
    if current is None or current.path != STATE:
        conf = hub_settings() if STATE == DEFAULT_STATE else {}
        current = store.ACTIVE = store.Store(STATE, conf.get('store', 'file'),
                                             conf.get('resend_minutes', store.RESEND_MINUTES))
    return current


@contextlib.contextmanager
def state():
    with board_store().locked() as data:
        yield data


def read_state():
    return board_store().read()


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
        old = s.get('task_tables', {}).get(task)
        # The hub's board-wide verdict poll has no scope: it never erases the scope that planned the task.
        record = {'table': table, 'scope': SCOPE or (old.get('scope') if isinstance(old, dict) else None)}
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


def docs_base(table):
    """The project's taskboard.docs_url ('' when unset or the table is unknown)."""
    entry = read_state().get('tables', {}).get(table or '')
    return project_settings(entry).get('docs_url', '') if entry else ''


def doc_links(table, docs):
    """'Docs: [path](url)' for paths under the project's taskboard.docs_url, so Linear links to the
    repo's docs instead of carrying long text. Empty when no docs were given."""
    if not docs:
        return ''
    base = docs_base(table)
    return '\n\nDocs: ' + ', '.join('[%s](%s%s)' % (d, base, d) if base else '`%s`' % d for d in docs)


def add_resources(b, table, task, docs):
    """Each doc as a Resource on the Linear issue (taskboard.docs_url + path), skipping ones already there.
    Returns the docs added; nothing on Anytype or private boards, or without a docs_url."""
    base = docs_base(table)
    if not docs or not base or not hasattr(b, 'add_resource'):
        return []
    return [d for d in docs if b.add_resource(task, base + d, d)]


def set_status(b, task, status, linear=..., **props):
    """Board phase; on a Linear board also its Linear status (`linear`: an explicit target, None to leave Linear)."""
    if hasattr(b, 'linear_target'):
        b.set(task, task_status=status, linear=linear, **props)
    else:
        b.set(task, task_status=status, **props)


def pushed(b):
    """Linear status changes this board made, for the command's output; a mapped one is also recorded in the
    state (`linear_state_map`), so a team missing a state shows which state stands in for it (MST-53)."""
    moves = getattr(b, 'pushed', None) or []
    mapped = getattr(b, 'mapped', None) or {}
    if mapped:
        with state() as s:
            for (team, wanted), got in mapped.items():
                s.setdefault('linear_state_map', {}).setdefault(team, {})[wanted] = got
    return ['%s → %s%s' % (m['issue'], m['linear'], ' (for %s)' % m['wanted'] if m['mapped'] else '') for m in moves]


def main_branch(repo):
    """The repo's main branch: what origin/HEAD points at, else main or master."""
    head = git(repo, 'symbolic-ref', '--quiet', '--short', 'refs/remotes/origin/HEAD', check=False)
    if head:
        return head.split('/', 1)[1]
    for name in ('main', 'master'):
        if git(repo, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + name, check=False):
            return name
    return 'main'


def run_base(run):
    """The commit a run's worktree started from, if recorded."""
    path = Path(run['tree'])/'.mstack/cache/base' if run.get('tree') else None
    return path.read_text().strip() if path and path.is_file() else None


def merged_not_done(repo, tasks):
    """Tasks whose branch is merged into the local main branch with work of its own, but which are not Done:
    the after-merge follow-up (`board merged`) was forgotten. A branch counts as having work when its tip is off
    main's first-parent line (a --no-ff merge) or differs from the commit its worktree started from."""
    main = main_branch(repo)
    tips = dict(line.split(' ', 1)[::-1] for line in git(
        repo, 'for-each-ref', 'refs/heads', '--format=%(objectname) %(refname:short)', check=False).splitlines())
    if main not in tips:
        return []
    merged = set(git(repo, 'branch', '--merged', main, '--format=%(refname:short)', check=False).splitlines())
    line = None
    runs = read_state().get('runs', {})
    out = []
    for t in tasks:
        branch = t.get('branch')
        if t.get('task_status') in ('Done', 'Canceled') or not branch or branch == main or branch not in merged:
            continue
        if line is None:
            line = set(git(repo, 'rev-list', '--first-parent', main, check=False).splitlines())
        base = run_base(runs.get(t['id']) or {})
        if tips[branch] in line and (not base or base == tips[branch]):
            continue                                  # a branch with no work of its own sits on main's line
        out.append(t)
    return out


SIZES = ('small', 'medium', 'big')
BRIEF_LIMIT = 800         # characters: a consolidated issue description is a short brief plus the doc link


def docs_missing(b, key, run, size, docs):
    """What the docs rule (design by size, 2026-10-30) still needs before `done`: medium and big issues need a
    repo doc passed with --doc, and on a writable Linear board a short issue description that links it."""
    if size == 'small':
        return []
    fix = '--size small' if size == 'medium' else '--force'
    roots = [Path(run['tree'])] if run.get('tree') else []
    entry = read_state().get('tables', {}).get(table_of_task(key) or '')
    if entry:
        roots.append(Path(entry['path']))
    if not docs:
        return ['a doc: write it in the repo from the settled thread and pass `--doc <path>` '
                '(or `%s` if this issue needs none)' % fix]
    gone = [d for d in docs if not any((r/d).exists() for r in roots)]
    if gone:
        return ['the doc %s: not found in %s' % (', '.join('`%s`' % d for d in gone),
                                                   ' or '.join('`%s`' % r for r in roots) or 'any recorded path')]
    if not entry or not is_linear(entry) or project_settings(entry).get('private'):
        return []                                     # private boards: Linear is read-only, the journal is the record
    text = b.body(key)
    wrong = []
    if len(text) > BRIEF_LIMIT:
        wrong.append('is %d characters (at most %d)' % (len(text), BRIEF_LIMIT))
    if not any(d in text or Path(d).name in text for d in docs):
        wrong.append('does not link %s' % ', '.join('`%s`' % d for d in docs))
    if wrong:
        return ['a consolidated issue description: it %s. Shrink it in Linear to a short brief plus the doc link, '
                'keeping the comments, then run done again' % ' and '.join(wrong)]
    return []


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
    if args.size:
        with state() as s:
            for k in filter(None, (task['id'], task.get('linear_identifier'))):
                s.setdefault('task_sizes', {})[k] = args.size
    if args.repos:
        known = workspace_repos(project_settings(table_of(args.project)[1]))
        wrong = [r for r in args.repos if r not in known]
        if wrong:
            raise ValueError('Unknown repos %s (taskboard.repos: %s)' % (', '.join(wrong), ', '.join(sorted(known))))
        with state() as s:
            s.setdefault('task_repos', {})[task['id']] = list(args.repos)
    return {'task': task['id'], 'issue': task.get('linear_identifier'), 'status': 'Awaiting Approval',
            'repos': args.repos or [], 'size': args.size}


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
    for name in names:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE.with_name('poll.%s.lock' % name), 'w') as guard:
            fcntl.flock(guard, fcntl.LOCK_EX)         # one process applies a board's verdicts at a time
            out += poll_board(name, b)
    return out


def recheck(name, base, task):
    """The task's status and verdict read again, past every cache (another process may have applied it)."""
    b = board_for(name, base)
    if hasattr(b, 'fresh'):
        return b, b.fresh(task)
    return b, b.get(task)


def poll_board(name, base):
    out = []
    b = board_for(name, base)
    for task in b.tasks(read_state()['tables'][name].get('collection')):
        status = task.get('task_status')
        if status not in PENDING:
            continue
        remember(task['id'], name)
        verdict, text, ask = anyboard.decide(b.messages(task['id']))
        if verdict in ('approved', 'rejected'):       # it will move
            b, current = recheck(name, base, task['id'])
            if current.get('task_status') != status:
                continue                              # applied meanwhile by another watcher
            verdict, text, ask = anyboard.decide(b.messages(task['id']))
        row = {'table': name, 'task': task['id'], 'name': task.get('name'), 'was': status, 'verdict': verdict,
               'ask': ask, 'scope': scope_of_task(task['id'])}     # the board-wide hub poll routes by the task's scope
        if verdict in ('approved', 'rejected'):
            row['now'] = apply_verdict(b, task['id'], status, verdict)
        elif verdict == 'feedback':
            # A reply with content: the orchestrator reads it and decides (MST-60), nothing moves on wording.
            row['feedback'] = text
            row['action'] = ('orchestrator: read the reply and decide: `board verdict --task <id> approve|reject%s`%s'
                             % ('|changes' if status == 'In Review' else '',
                                ', or revise the plan and `ask` again' if status == 'Awaiting Approval' else ''))
        if verdict != 'pending':
            out.append(row)
    return out


VERDICTS = {('Awaiting Approval', 'approve'): ('Todo', 'Approved, queued for a worker.'),
            ('Awaiting Approval', 'reject'): ('Canceled', 'Dropped.'),
            ('In Review', 'approve'): ('Done', 'Accepted. Branch is ready to merge.'),
            ('In Review', 'reject'): ('Todo', 'Sent back to the worker.'),
            ('In Review', 'changes'): ('Todo', 'Got it, sending your notes back to the worker.')}


def apply_verdict(b, task, status, verdict):
    """Move a pending task on by the owner's verdict (approve, reject, or changes on a result); returns the new phase."""
    verdict = {'approved': 'approve', 'rejected': 'reject'}.get(verdict, verdict)
    if (status, verdict) not in VERDICTS:
        raise ValueError('no %r verdict for a task in %s' % (verdict, status))
    now, text = VERDICTS[(status, verdict)]
    # Private: accepted is not landed yet, so Linear stays In Progress until `merged`.
    set_status(b, task, now, linear=None if now == 'Done' and getattr(b, 'journal', None) else ...)
    b.say(task, text)
    return now


def cmd_verdict(args, b):
    """The orchestrator's reading of an owner reply the watcher left to it (MST-60): approve, reject, or (on a
    finished result) changes. The reply itself stays on the thread and travels to the worker as notes."""
    b = board_of_task(run_key(args.task), b)
    task = b.fresh(args.task) if hasattr(b, 'fresh') else b.get(args.task)
    status = task.get('task_status')
    if status not in PENDING:
        raise ValueError('%s is %s: nothing waits for a verdict' % (args.task, status))
    ident = task.get('id') or args.task
    _, text, _ = anyboard.decide(b.messages(ident))
    now = apply_verdict(b, ident, status, args.verdict)
    if args.why:
        b.say(ident, 'Read the reply as %s: %s' % (args.verdict, SECRET.sub('[redacted]', args.why)[:400]))
    out = {'task': ident, 'issue': task.get('linear_identifier'), 'was': status, 'now': now, 'notes': text}
    moves = pushed(b)
    if moves:
        out['linear_status'] = moves
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


def brief_for(b, task_id, table, tree, tools=(), headless=False):
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
        *(['- ' + HEADLESS, '- Work only in %s: a git worktree on its own branch.' % tree,
           '- You cannot ask mid-run: decide within the approved plan; questions go in your final summary.'] if headless else
          ['- Work only in %s: a git worktree on its own branch. Commit your changes there.' % tree]),
        *(['- This task belongs to app [%s]; its code is in %s.' % (task.get('task_app'), tree/app_path)]
          if app_path else []),
        '- Do not merge, push, or touch other worktrees or the main checkout.',
        *([] if headless else [
            '- If scope or plan changes, tell the owner on the issue:',
            '  %s note --task %s "what changed"' % (board, task_id),
            '- When finished, report for review (this moves the issue to In Review):',
            '  %s done --task %s --summary "what changed and what is left" --doc <path>' % (board, task_id),
            '  (medium and big issues need the doc and a consolidated issue description; a small one passes --size small)']),
        *(['', 'mstack tools in this session (MCP):'] + ['- %s: %s' % (t['name'], t.get('hint', ''))
                                                         for t in tools] if tools else [])])


def wire_mcp(repo, tree, runner, servers):
    """Give this run the project's selected worker MCP servers in the host's own way, never globally.
    Returns (names wired, reasons skipped)."""
    if not servers:
        return [], []
    style = runners.mcp_style(runner, repo)
    names = [s['name'] for s in servers]
    if style in ('codex-config', 'dsh-patch'):
        return names, []          # passed on the run itself (-c overrides, or a --patch overlay in .mstack/cache)
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
    brief = brief_for(b, task['id'], table, tree, [s for s in servers if s['name'] in tools],
                      headless=bool(runner) and runners.sandboxed(runner, repo))
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
    bases = {p.name[5:]: p.read_text().strip() for p in (tree/'.mstack/cache').glob('base.*')} if tree else {}
    if tree is None or not (tree/'.mstack/cache/base').exists() and not bases:
        commits, stat, branch = [], 'commits not counted (no mstack worktree recorded)', \
            (git(tree, 'branch', '--show-current', check=False) if tree and tree.exists() else 'unknown')
    elif bases:                                       # multi-repo workspace: one worktree per touched repo
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
    ended = 'finished' if exit_code is None else 'finished (exit %s)' % exit_code
    # The ask goes first: a poll between the two must never find In Review under an older ask (and its 👍).
    b.say(task_id, '**%s** %s on branch `%s`: %d commit(s), %s.\n\n%s\n\nReact 👍 to accept, or reply with changes.'
          % (who, ended, branch, len(commits), stat,
             SECRET.sub('[redacted]', summary)[-1200:] or '(no summary)'), ask=True)
    b.set(task_id, task_status='In Review', agent_run_count=(current.get('agent_run_count') or 0) + 1)
    return len(commits)


def cmd_dispatch(args, b):
    name, entry = table_of(args.project)
    settings = project_settings(entry)
    repo = Path(entry['path'])
    if settings.get('orchestrators') and not SCOPE:
        raise ValueError('This project has sub-orchestrators: only a scope dispatches (--scope one of %s). The '
                         'top orchestrator assigns work to them instead.' % ', '.join(sorted(settings['orchestrators'])))
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
            # Approved work for a session that already exists: resume it there instead of starting a second worker.
            run = runs[task['id']]
            prompt = 'Approved: continue %s with the plan below.\n\n%s' % (
                task.get('linear_identifier') or task['id'], brief_for(b, task['id'], name, Path(run.get('tree') or repo)))
            b.set(task['id'], task_status='In Progress')
            b.say(task['id'], 'Handed back to the existing session `%s` (status → In Progress).' % run.get('session'))
            with state() as s:
                s['runs'][task['id']].update({'resume': {'session': run.get('session'), 'prompt': prompt}, 'resumed': False})
            started.append({'task': task['id'], 'name': task.get('name'), 'resume': run.get('session')})
            room -= 1
            continue
        waiting = [x for x in as_list(task.get('task_blocked_by')) if b.get(x).get('task_status') != 'Done']
        if waiting:
            continue      # blockers first; their branches are merged in when this task starts
        runner = args.runner or runners.choose(task.get('task_agent'), settings.get('workers', ['codex']), repo)
        tree, short, brief, wiring = prepare(b, repo, task, name, runner)
        app = (settings.get('apps') or {}).get(task.get('task_app') or '')
        work_dir = tree/app['path'] if app else tree
        run = {'table': name, 'scope': SCOPE, 'runner': runner, 'tree': str(tree), 'cwd': str(work_dir), 'pid': None,
               'issue': task.get('linear_identifier'),
               'parent': task.get('parent'),
               'mcp': wiring['servers'], 'dispatched_at': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
        row = {'task': task['id'], 'name': task.get('name'), 'runner': runner,
               'tools': wiring['tools'], 'skipped_tools': wiring['skipped']}
        if runners.kind(runner, repo) == 'spawn':
            log = repo/'.mstack/cache/runs'/(short + '.log')
            log.parent.mkdir(parents=True, exist_ok=True)
            before = runs.get(task['id']) or {}
            # Back from review on the same resumable host: continue its session (the brief now has the owner's notes).
            again = before.get('native_session') and before.get('runner') == runner and runners.can_resume(runner, repo)
            if again:
                run.update({k: before[k] for k in ('session', 'native_session')})
            run['log'] = str(log)
            with state() as s:                 # recorded before the process can read it
                s.setdefault('runs', {})[task['id']] = run
            run['pid'] = row['pid'] = spawn([sys.executable, str(HERE/'cli.py'), 'work', '--task', task['id'],
                                            '--table', name, '--runner', runner, '--tree', str(tree)]
                                           + (['--resume'] if again else []), log)
            where = 'Dispatched to **%s**%s' % (runner, ' (resuming its session)' if again else '')
        else:
            row['handoff'] = run['handoff'] = runners.handoff(runner, session_title(task), work_dir, brief, repo)
            where = 'Handed to **%s**' % runner
        b.set(task['id'], task_status='In Progress', task_agent=runner, agent_session=runner + ' · ' + str(tree))
        b.say(task['id'], '%s in worktree `%s` (branch task/%s).' % (where, tree, short))
        with state() as s:                     # a spawned worker may already have recorded its session: keep it
            s.setdefault('runs', {})[task['id']] = {**s['runs'].get(task['id'], {}), **run} if 'log' in run else run
        started.append(row)
        room -= 1
    return {'table': name, 'started': started, 'already_running': len(busy)}


def run_key(task):
    """The runs key for a task given by id or by its Linear name (IRO-123)."""
    runs = read_state().get('runs', {})
    if task in runs:
        return task
    return next((k for k, r in runs.items() if r.get('issue') == task), task)


def mark_active(st, session):
    """A session ack/adopt just recorded is live: show it as active in My tasks before the next observe."""
    if session:
        st.setdefault('sessions_seen', {})[session] = {**(st.get('sessions_seen') or {}).get(session, {}),
                                                       'state': 'active', 'at': time.strftime('%Y-%m-%dT%H:%M:%S%z')}


def cmd_ack(args, b):
    """The orchestrator started the host session for a handoff, or resumed an adopted worker: stop offering it."""
    key = run_key(args.task)
    with state() as s:
        run = s.get('runs', {}).get(key)
        if not run or not (run.get('handoff') or run.get('adopted')):
            raise ValueError('Task %s has no handoff or adopted worker to acknowledge' % args.task)
        if run.get('adopted') and run.get('session') not in (None, args.session):
            raise ValueError('Task %s is worked by adopted session %s' % (args.task, run['session']))
        run['session'] = args.session
        run['resumed'] = True
        mark_active(s, args.session)
    return {'task': key, 'session': args.session}


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
    tasks = lb.tasks()
    for task in tasks:
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
    out += linear_triggers(name, lb, tasks, runs, seen, fresh)
    out += status_lags(name, lb, tasks, seen, fresh)
    # Branches merged into main whose issue is still open: remind the orchestrator once (after-merge follow-up).
    repo = Path(read_state()['tables'][name]['path'])
    for task in merged_not_done(repo, [t for t in tasks if t.get('managed')]):
        if 'merged:' + task['id'] not in seen:
            out.append({'kind': 'merged', 'table': name, 'task': task['id'], 'issue': task['linear_identifier'],
                        'branch': task['branch'], 'status': task['task_status'],
                        'do': 'run `mstack board merged --task %s --doc <docs>`' % task['linear_identifier']})
            fresh.append('merged:' + task['id'])
    return out


PG = store.PG
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
    store.psql(sql)


def mirror_if_due(name, out):
    """Refresh one Linear board's issue table when MIRROR_EVERY has passed; errors go into `out`."""
    if time.time() - read_state().get('last_mirror', {}).get(name, 0) < MIRROR_EVERY:
        return
    try:
        out.setdefault('mirrored', {})[name] = mirror(name)['rows']
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        out.setdefault('mirror_errors', {})[name] = str(error)[:200]
    with state() as s:
        s.setdefault('last_mirror', {})[name] = time.time()


# ---- the owner's "My tasks" status table (design 014) ----------------------------------------------
STATUS_CALL = None        # tests: a fake Anytype call; None = the macOS bridge (board.macctl)
STATUS_SQL = None         # tests: a fake psql runner; None = store.psql


def status_table_on():
    """`hub.status_table` in mstack's .mstack/stack.json (default on). Only the real state file feeds the
    table; tests switch it on explicitly."""
    return STATE == DEFAULT_STATE and hub_settings().get('status_table', True) is not False


def board_sources():
    """Board name → {teams: {team key: Linear workspace}, scopes: its taskboard.orchestrators}, for the table's
    Item Source and Scope columns. A board whose config can't be read gets nothing (team key alone, no route)."""
    out = {}
    for name, entry in read_state().get('tables', {}).items():
        try:
            settings = project_settings(entry)
        except (ValueError, OSError, KeyError):
            continue
        out[name] = {'teams': {l['team']: l['workspace'] for _, l in links_of(settings) if l.get('team') and l.get('workspace')},
                     'scopes': settings.get('orchestrators') or {}}
    return out


def shown_boards():
    """The boards "My tasks" shows: registered Linear boards. Anytype-backed tables (test-market) are retired from
    automation, and an unregistered board has no entry at all."""
    return {name for name, entry in read_state().get('tables', {}).items() if is_linear(entry)}


def status_table_pass(full=False, limit=None):
    """One pass: refresh stale Linear issue tables, then upsert the rows into "My tasks". Only one pass runs at a
    time (hub watcher, a manual sync): another one is skipped, never run in parallel, so a row is never created twice."""
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE.with_name('status-table.lock'), 'w') as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'skipped': 'another status-table pass is running'}
        return _status_table_pass(full, limit)


def project_roles():
    """Board name → its project's role registry (orchestrators, sub-orchestrators, helpers)."""
    out = {}
    for name, entry in read_state().get('tables', {}).items():
        try:
            out[name] = project_state.read(Path(entry['path']))['runtime'].get('roles', {})
        except (ValueError, OSError, KeyError):
            continue
    return out


def _status_table_pass(full, limit):
    out = {}
    for name, entry in sorted(read_state().get('tables', {}).items()):
        if is_linear(entry):
            mirror_if_due(name, out)
    issues = status_table.read_issues(STATUS_SQL or store.psql)
    current = read_state()
    known = current.get(status_table.STATE_KEY) or {}
    full = full or time.time() - known.get('last_full', 0) >= status_table.FULL_EVERY
    table = status_table.StatusTable(STATUS_CALL or anyboard.macctl)
    rows, takes, retire = status_table.desired(issues, current, board_sources(), roles=project_roles(),
                                               boards=shown_boards())
    try:
        known, counts = table.sync(rows, known, full, limit, takes, retire)
        counts['ctas'] = take_ctas(table, known, rows)
    finally:
        saved = known if table.partial is None else table.partial
        with state() as s:
            mine = dict(saved, last_try=time.time())
            if table.partial is None:
                mine['last_pass'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
                mine['pending'] = counts['pending']
                if full:
                    mine['last_full'] = time.time()        # the rewrite carries on through the forgotten fingerprints
            s[status_table.STATE_KEY] = mine
    return {**out, 'rows': len(rows), 'full': full, **counts}


SESSIONS_EVERY = 900      # seconds between session-state refreshes the hub chat is asked for


def take_ctas(table, known, rows):
    """Read the owner's CTAs (one search) into `known`: forbidden protects a session; continue/archive/delete wait
    in known['ctas'] for the hub chat; a CTA set back to noop cancels a waiting one. A CTA on an issue row (no
    session) is reset. Returns the number waiting."""
    found = table.ctas(known)
    by_id = {r['id']: key for key, r in known.get('rows', {}).items()}
    waiting, protected = dict(known.get('ctas') or {}), set(known.get('protected') or [])
    now_protected = set()
    for object_id, cta in found.items():
        key = by_id.get(object_id, '')
        if not key.startswith('session/'):
            table.set_cta(object_id)                      # issue rows have no session to act on
            continue
        session = key[len('session/'):]
        if cta == 'forbidden':
            now_protected.add(session)
            waiting.pop(session, None)
        elif cta in status_table.ACTIONS and (waiting.get(session) or {}).get('cta') != cta:
            waiting[session] = {'cta': cta, 'object': object_id, 'at': time.time(), 'handed': 0,
                                'name': (rows.get(key) or {}).get('name'),
                                'type': ((rows.get(key) or {}).get('properties') or {}).get('session_type')}
    for session in list(waiting):
        if waiting[session]['object'] not in found:        # the owner set it back to noop
            waiting.pop(session)
    known['ctas'], known['protected'] = waiting, sorted(now_protected)
    known['sessions'] = {key[len('session/'):]: {k: row['properties'].get(v) for k, v in
                                                 (('type', 'session_type'), ('parent', 'session_parent'))}
                         for key, row in rows.items() if key.startswith('session/')}
    if protected != now_protected:
        known['protected_changed'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    return len(waiting)


def hub_work(peek=True):
    """What only the hub chat can do for "My tasks": CTAs to carry out, and a fresh list of session states.
    Without peek, the CTAs are marked handed out (again after hub.resend_minutes)."""
    st = read_state()
    known = st.get(status_table.STATE_KEY) or {}
    resend = board_store().resend * 60
    due = [dict(c, session=s) for s, c in sorted((known.get('ctas') or {}).items())
           if time.time() - c.get('handed', 0) >= resend]
    observe = bool(known.get('rows')) and time.time() - (st.get('sessions_observed') or {}).get('at', 0) >= SESSIONS_EVERY \
        and time.time() - (st.get('sessions_observed') or {}).get('asked', 0) >= SESSIONS_EVERY
    if not peek and (due or observe):
        with state() as s:
            mine = s.setdefault(status_table.STATE_KEY, {})
            for c in due:
                if c['session'] in (mine.get('ctas') or {}):
                    mine['ctas'][c['session']]['handed'] = time.time()
            if observe:
                s.setdefault('sessions_observed', {})['asked'] = time.time()
    return {'ctas': due, 'observe_sessions': observe}


def cmd_sessions(args, b):
    """The hub chat's side of "My tasks" (design 014): `todo` hands out CTAs and asks for session states;
    `observe` takes list_sessions JSON on stdin; `done` records what a CTA did and resets it to noop."""
    key = status_table.STATE_KEY
    if args.action == 'list':
        st = read_state()
        known = st.get(key) or {}
        return {'ctas': known.get('ctas') or {}, 'protected': known.get('protected') or [],
                'observed': (st.get('sessions_observed') or {}).get('at'),
                'states': {k: v.get('state') for k, v in (st.get('sessions_seen') or {}).items()}}
    if args.action == 'todo':
        work = hub_work(peek=False)
        seen = read_state().get('sessions_seen') or {}
        info = (read_state().get(key) or {}).get('sessions') or {}
        ready, refused = [], []
        for c in work['ctas']:
            live = [w for w, i in info.items() if i.get('parent') == c['session']
                    and (seen.get(w) or {}).get('state') not in ('archived', 'deleted')]
            if ':' in c['session']:                   # a spawned CLI worker (`dsh:<id>`) has no chat to act on
                refused.append(cta_done(c['session'], 'refused: CLI worker; use `mstack board forward` or `board stop`'))
            elif c['type'] == 'orchestrator' and c['cta'] in ('archive', 'delete') and live:
                refused.append(cta_done(c['session'], 'refused: this orchestrator still has %d active worker(s)' % len(live)))
            else:
                ready.append({k: c.get(k) for k in ('session', 'cta', 'name', 'type')})
        return {'observe_sessions': work['observe_sessions'], 'ctas': ready, 'refused': refused,
                'how': 'observe_sessions: list_sessions(include_archived: true, limit: 200), pipe the JSON (each row '
                       'keeping at least sessionId, title, link, isArchived, isRunning) to `mstack sessions observe --complete`. For each CTA: continue → SendMessage "Continue: the owner '
                       'asked from My tasks." to the session; archive → archive_session; delete → delete_session (the app '
                       'asks the owner). Then `mstack sessions done --session <id> --result "<what happened>"`.'}
    if args.action == 'observe':
        raw = json.loads(sys.stdin.read() or '[]')
        listed = raw if isinstance(raw, list) else raw.get('sessions') or []
        stamp = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        with state() as st:
            seen = st.setdefault('sessions_seen', {})
            for row in listed:
                ident = row.get('sessionId') or row.get('id')
                if ident:
                    # idle: not archived and not running a turn (MST-46); status_table still shows In Review as active.
                    live = 'active' if row.get('isRunning') else 'idle'
                    link = row.get('link') or seen.get(ident, {}).get('link')    # the chat's own link (MST-49)
                    seen[ident] = {'state': 'archived' if row.get('isArchived') else live, 'at': stamp,
                                   'title': (row.get('title') or seen.get(ident, {}).get('title') or '')[:120],
                                   **({'link': link[:300]} if link else {})}
            listed_ids = {row.get('sessionId') or row.get('id') for row in listed}
            gone = []
            if args.complete:                       # a full listing: our sessions missing from it were deleted
                for ident in (st.get(key) or {}).get('sessions') or {}:
                    # CLI workers (`dsh:<id>`) are never in the app's list; their run says if they live.
                    if ident not in listed_ids and ident != args.hub_session and ':' not in ident:
                        seen[ident] = {**seen.get(ident, {}), 'state': 'deleted', 'at': stamp}
                        gone.append(ident)
            st['sessions_observed'] = {'at': time.time(), 'asked': time.time()}
        return {'observed': len(listed), 'deleted': gone}
    if args.action == 'done':
        if not args.session or not args.result:
            raise ValueError('done needs --session and --result')
        return cta_done(args.session, args.result, args.state)
    raise ValueError('unknown action')


def cta_done(session, result, new_state=None):
    """Record a CTA's outcome on the row (Last Action), reset its CTA to noop, and update the session's state."""
    key = status_table.STATE_KEY
    with state() as st:
        known = st.setdefault(key, {})
        cta = (known.get('ctas') or {}).pop(session, None)
        text = '%s %s: %s' % (time.strftime('%Y-%m-%d %H:%M'), (cta or {}).get('cta') or 'action', result)
        known.setdefault('actions', {})[session] = {'text': text[:300], 'at': time.time()}
        if new_state:
            st.setdefault('sessions_seen', {})[session] = {**(st.get('sessions_seen') or {}).get(session, {}),
                                                           'state': new_state, 'at': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
        row = (known.get('rows') or {}).get('session/' + session)
    if row:
        try:
            status_table.StatusTable(STATUS_CALL or anyboard.macctl).set_cta(row['id'])
        except RuntimeError as error:
            return {'session': session, 'recorded': text, 'reset_error': str(error)[:200]}
    return {'session': session, 'recorded': text}


def status_table_if_due(out):
    """The hub watcher's step (only `tick --hub` calls it; per-scope watchers never do): a pass every status_table.EVERY seconds (BACKLOG_EVERY while rows wait), at most
    BATCH rows each, failures recorded, never fatal. This keeps the table current with no manual runs."""
    if not status_table_on():
        return
    known = read_state().get(status_table.STATE_KEY) or {}
    wait = status_table.BACKLOG_EVERY if known.get('pending') else status_table.EVERY
    if time.time() - known.get('last_try', 0) < wait:
        return
    try:
        out['status_table'] = status_table_pass(limit=status_table.BATCH)
    except (RuntimeError, ValueError, OSError, KeyError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        out['status_table_error'] = str(error)[:200]
        with state() as s:
            s.setdefault(status_table.STATE_KEY, {})['last_try'] = time.time()


def cmd_status_table(args, b):
    if args.action == 'show':
        known = read_state().get(status_table.STATE_KEY) or {}
        return {'on': hub_settings().get('status_table', True) is not False, 'collection': known.get('collection'),
                'rows': len(known.get('rows') or {}), 'pending': known.get('pending', 0), 'last_pass': known.get('last_pass')}
    if hub_settings().get('status_table', True) is False:
        raise ValueError('The status table is off (hub.status_table: false in .mstack/stack.json)')
    if args.action == 'rename':
        if not args.to:
            raise ValueError('rename needs --to NAME')
        status_table.StatusTable(STATUS_CALL or anyboard.macctl).rename_channel(args.to)
        return {'channel': args.to, 'next': 'set "channel" in infra/taskboard/schema.json to the new name'}
    return status_table_pass(full=args.full)


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
        mark_active(s, args.session)
    remember(task['id'], name, task.get('linear_identifier'))
    b.say(task['id'], 'Tracked by the %s orchestrator: session `%s`%s (status → %s).'
          % (SCOPE or name, args.session, ' in `%s`' % args.tree if args.tree else '', status))
    if status == 'In Progress' and hasattr(b, 'push_status'):
        b.push_status(task['id'], b.linear_target(status))   # the note above already records the phase
    out = {'task': task['id'], 'issue': task.get('linear_identifier'), 'scope': SCOPE, 'status': status}
    moves = pushed(b)
    if moves:
        out['linear_status'] = moves
    return out


TRIGGER_LOOKBACK = 86400  # seconds of Linear notifications read back (the hub's seen-keys drop repeats)


def notify_since(name):
    """Where a board's trigger read starts: never before the board's first read (old notifications start
    nothing), at most a day back, and the same value for every scope in the hour so they share one read.
    None on the very first read, which only records the baseline."""
    base = read_state().get('notify_since', {}).get(name)
    if base is None:
        with state() as s:
            s.setdefault('notify_since', {})[name] = time.time()
        return None
    start = max(base, (time.time() - TRIGGER_LOOKBACK) // 3600 * 3600)
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start))


def linear_triggers(name, lb, tasks, runs, seen, fresh):
    """Linear-side triggers (MST-60): a new issue assigned to the owner starts orchestration (a plan for the
    owner's verdict, never work); a comment that @-mentions the owner goes to the issue's live worker, else to the
    scope's orchestrator. Read only, so private boards get them too. Deduped per assignment and per comment."""
    if not hasattr(lb, 'triggers'):
        return []
    since = notify_since(name)
    if since is None:
        return []
    managed = {t['id'] for t in tasks if t.get('managed')}
    status = {t['id']: t['task_status'] for t in tasks}
    out = []
    for hit in lb.triggers(since):
        key = 'new_issue:%s' % hit['id'] if hit['kind'] == 'new_issue' else 'mention:%s' % hit['comment']
        if key in seen or key in fresh:
            continue
        fresh.append(key)
        item = {'kind': hit['kind'], 'table': name, 'task': hit['task'], 'issue': hit['issue'], 'name': hit.get('title'),
                'url': hit.get('url'), 'triage': hit.get('triage')}
        if hit['kind'] == 'new_issue':
            if hit['task'] in managed:
                continue                                  # already planned or worked on: nothing new
            item['do'] = triage_do(hit['issue'], hit.get('triage') or {})
        else:
            run = runs.get(hit['task']) or {}
            live = run.get('session') and status.get(hit['task']) not in ('Done', 'Canceled')
            item.update(author=hit.get('author'), text=hit.get('text'), comment=hit['comment'],
                        session=run.get('session') if live else None,
                        do=('send it to worker `%s` as a Linear mention from %s (not an owner instruction)'
                            % (run.get('session'), hit.get('author'))) if live else
                           ('%s mentioned you: tell the owner, and plan only on their word' % hit.get('author')))
        out.append(item)
    return out


LAG_PHASES = ('Todo', 'In Progress', 'In Review')   # phases whose Linear status is fixed by the board alone


def status_lags(name, lb, tasks, seen, fresh):
    """Managed issues whose Linear status lags the board phase (MST-58), flagged once per (issue, phase, state).
    Closed issues are the consumer's and never flagged."""
    if not hasattr(lb, 'linear_target'):
        return []
    out = []
    for task in tasks:
        phase, target = task['task_status'], lb.linear_target(task['task_status'])
        if not task.get('managed') or phase not in LAG_PHASES or not target or task.get('linear_state_type') in linear_board.CLOSED:
            continue
        link = lb.owner_of[task['id']]
        want = link.state_for(target)
        have = lb.cache[task['id']]['state']
        key = 'lag:%s:%s:%s' % (task['id'], phase, have.get('id'))
        if want['id'] == have.get('id') or key in seen:
            continue
        fresh.append(key)
        out.append({'kind': 'status_lag', 'table': name, 'task': task['id'], 'issue': task['linear_identifier'],
                    'phase': phase, 'linear': have.get('name'), 'want': want.get('name'),
                    'do': 'run `mstack board note --task %s --status "%s" "status sync"`' % (task['linear_identifier'], phase)})
    return out


def triage_do(issue, triage):
    """What the orchestrator does with an issue that arrived from Linear (triage gate, owner 2026-10-30)."""
    if triage.get('missing'):
        return ('triage: %s lacks %s. Tell the owner and ask the product owner to add it; do not plan or start it yet'
                % (issue, ', '.join(triage['missing'])))
    return ('triage: %s priority. Read the hierarchy first (`board tree --task %s`), then draft a plan with '
            '`board propose` in priority order (not necessarily now) and wait for the verdict. Nothing starts unless '
            'the owner, or the product owner in an issue comment, asks for it.' % (triage.get('priority'), issue))


def scope_of_task(task):
    """The orchestrator scope an event about `task` belongs to: this call's, else the one that planned,
    adopted or dispatched it."""
    if SCOPE or not task:
        return SCOPE
    st = read_state()
    record = st.get('task_tables', {}).get(task) or {}
    return (st.get('runs', {}).get(task) or {}).get('scope') or (record.get('scope') if isinstance(record, dict) else None)


def to_events(items, verdicts):
    """Watcher output as queue events. Each needs_orchestrator item is offered once by the watcher's own
    seen-keys; handoffs repeat until acked, so they carry a dedupe key per dispatch."""
    runs = read_state().get('runs', {})
    out = []
    for item in items:
        task = item.get('task')
        if item['kind'] in ('handoff', 'resume'):
            run = runs.get(task) or {}
            dedupe = '%s:%s:%s' % (item['kind'], task, run.get('dispatched_at') or json.dumps(run.get(item['kind']), sort_keys=True))
        else:
            dedupe = '%s:%s' % (item['kind'], hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()[:16])
        out.append({'board': item['table'], 'scope': item.get('scope') or scope_of_task(task) or '', 'kind': item['kind'],
                    'task': task, 'issue': item.get('issue') or item.get('linear'), 'dedupe': dedupe, 'payload': item})
    for row in verdicts:
        # One event per verdict on one ask: a repeat (a second route, a second watcher) returns the existing row.
        dedupe = 'verdict:%s:%s:%s:%s' % (row['task'], row.get('was'), row.get('now'), row.get('ask') or '')
        out.append({'board': row['table'], 'scope': row.get('scope') or scope_of_task(row['task']) or '', 'kind': 'verdict',
                    'task': row['task'], 'issue': None, 'dedupe': dedupe, 'payload': row})
    return out


def cmd_tick(args, b):
    """One unattended pass: apply verdicts, start what is approved, and list what only an orchestrator
    agent can do (start a desktop session, revise a plan). Safe to repeat: nothing is offered twice.
    Everything that needs an orchestrator also goes into the event queue (design 011).
    --hub: one pass for every registered orchestrator (project, scope) instead of the auto tables.
    Linear boards are read once per tick (linear_board.shared); `linear_calls` counts the requests by team."""
    before = dict(linear_board.CALLS)
    with linear_board.shared():
        out = tick_once(args, b) if not getattr(args, 'hub', False) else hub_tick(b)
    calls = {team: n - before.get(team, 0) for team, n in linear_board.CALLS.items() if n > before.get(team, 0)}
    if calls:
        out['linear_calls'] = calls
    return out


def hub_tick(b):
    """One pass for every registered orchestrator. Linear boards are polled per board: the first route of a
    board decides whether it is due this tick, every other route of that board follows, and all of them read
    the one fetch shared by linear_board.shared()."""
    global SCOPE, POLL_DUE, VERDICTS_DONE
    out = {'tables': [], 'verdicts': [], 'started': [], 'needs_orchestrator': []}
    outer = SCOPE
    POLL_DUE, VERDICTS_DONE = {}, set()
    try:
        for entry in sorted(read_state().get('orchestrators', {}).values(), key=lambda e: (e['project'], e.get('scope') or '')):
            SCOPE = entry.get('scope') or None
            try:
                got = tick_once(argparse.Namespace(project=entry['project']), b)
            except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as error:
                out.setdefault('tick_errors', {})[route_key(entry)] = str(error)[:200]
                continue
            for key, value in got.items():
                if isinstance(value, list):
                    out.setdefault(key, []).extend(v for v in value if key != 'tables' or v not in out['tables'])
                elif isinstance(value, dict):
                    out.setdefault(key, {}).update(value)
    finally:
        SCOPE, POLL_DUE, VERDICTS_DONE = outer, None, None
    status_table_if_due(out)
    return out


POLL_DUE = None           # inside a hub tick: board name → polled this tick (one timestamp per board)
VERDICTS_DONE = None      # inside a hub tick: boards whose verdicts were already polled


def poll_once(name, b):
    """Verdicts for one board. The hub polls each board once per tick, board-wide (no scope), so two routes
    over one board never apply or report one verdict twice; outside the hub, the watcher's own scope."""
    global SCOPE
    if VERDICTS_DONE is None:
        return cmd_poll(argparse.Namespace(project=name), b)
    if name in VERDICTS_DONE:
        return []
    VERDICTS_DONE.add(name)
    outer, SCOPE = SCOPE, None
    try:
        return cmd_poll(argparse.Namespace(project=name), b)
    finally:
        SCOPE = outer


def poll_due(name):
    """Whether this tick polls Linear board `name`, stamping the poll. The hub keeps one timestamp per board,
    shared by its scopes; a per-scope watcher (the fallback when no hub runs) keeps its own per scope."""
    key = name if POLL_DUE is not None else '/'.join(filter(None, (name, SCOPE)))
    if POLL_DUE is not None and name in POLL_DUE:
        return POLL_DUE[name]
    due = time.time() - read_state().get('last_linear_poll', {}).get(key, 0) >= LINEAR_EVERY
    if due:
        with state() as s:
            s.setdefault('last_linear_poll', {})[key] = time.time()
    if POLL_DUE is not None:
        POLL_DUE[name] = due
    return due


def hub_running():
    """True while the hub watcher (`watch --hub`) holds its lock."""
    lock = STATE.with_name('watch.hub.lock')
    if not lock.exists():
        return False
    with open(lock, 'a') as probe:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(probe, fcntl.LOCK_UN)
        except BlockingIOError:
            return True
    return False


def left_to_hub(name):
    """Outside the hub, a Linear board's I/O is the hub's while the hub runs and ticks this (board, scope)."""
    return POLL_DUE is None and store.route_key(name, SCOPE) in read_state().get('orchestrators', {}) and hub_running()


def route_key(entry):
    return store.route_key(entry['project'], entry.get('scope'))


def tick_once(args, b):
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
                out['needs_orchestrator'].append({'kind': 'plan', 'table': name, 'task': task['id'], 'name': task.get('name'),
                                                  'linear': task.get('linear_identifier')})
                fresh.append(key)
        if is_linear(entry):
            if left_to_hub(name):
                out.setdefault('left_to_hub', []).append(name)
                continue
            mirror_if_due(name, out)
            if not poll_due(name):
                continue
            try:
                out['needs_orchestrator'] += linear_signals(name, board_for(name, b), seen, fresh)
            except linear.RateLimited as error:
                out.setdefault('rate_limited', {})[name] = error.until
                continue
            except (RuntimeError, ValueError, OSError) as error:
                out.setdefault('sync_errors', {})[name] = str(error)[:200]
                continue
        try:
            rows = poll_once(name, b)
            out['verdicts'] += [r for r in rows if r.get('now')]
            for r in rows:
                key = '%s:%s' % (r['task'], hashlib.sha256(r.get('feedback', '').encode()).hexdigest()[:12])
                if r.get('action') and key not in seen:
                    kind = 'replan' if r['was'] == 'Awaiting Approval' else 'review_reply'
                    out['needs_orchestrator'].append({'kind': kind, 'table': name, 'task': r['task'], 'name': r['name'],
                                                      'feedback': r['feedback'], 'scope': r.get('scope'), 'do': r['action']})
                    fresh.append(key)
            out['started'] += cmd_dispatch(argparse.Namespace(project=name, runner=None), b)['started']
        except linear.RateLimited as error:         # never a failed tick: the board waits out the backoff
            out.setdefault('rate_limited', {})[name] = error.until
    for task, run in read_state().get('runs', {}).items():
        mine = not SCOPE or run.get('scope') in (None, SCOPE)
        if run['table'] in names and run.get('handoff') and not run.get('session') and mine:
            out['needs_orchestrator'].append({'kind': 'handoff', 'task': task, 'table': run['table'], **run['handoff']})
        if run['table'] in names and run.get('resume') and not run.get('resumed') and mine:
            # Send the prompt to the existing session (SendMessage), then `ack --task … --session …`.
            out['needs_orchestrator'].append({'kind': 'resume', 'task': task, 'table': run['table'],
                                              'issue': run.get('issue'), **run['resume']})
    out['needs_orchestrator'], handled = deliver_to_cli(out['needs_orchestrator'], b)
    if handled:
        out['cli_workers'] = handled
    events = to_events(out['needs_orchestrator'], out['verdicts'])
    try:
        ids = board_store().enqueue(events)
        for event, ident in zip(events, ids):
            event['payload']['event'] = ident                 # the same dict as the needs_orchestrator item
    except (RuntimeError, ValueError, OSError) as error:
        out['queue_error'] = str(error)[:200]
    with state() as s:
        s['attention_seen'] = sorted(set(s.get('attention_seen', [])) | set(fresh))
        s['last_tick'] = {'at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tables': names,
                          'started': len(out['started']), 'needs_orchestrator': len(out['needs_orchestrator'])}
    return out


def code_fingerprint():
    """Changes whenever mstack's own code or schemas change (a commit, a merge or a plain edit), or its hub settings."""
    parts = []
    for folder in ('orchestrator', 'stack', 'plugins', 'gateway'):
        for path in sorted((STACK_ROOT/'integrations'/folder).rglob('*')):
            if path.suffix in ('.py', '.json') and '__pycache__' not in path.parts and 'tests' not in path.parts:
                stat = path.stat()
                parts.append('%s:%d:%d' % (path, stat.st_mtime_ns, stat.st_size))
    parts.append(json.dumps(hub_settings(), sort_keys=True))     # switching hub.store restarts every watcher onto it
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
    hub = getattr(args, 'hub', False)
    lock = STATE.with_name('watch.%s.lock' % ('hub' if hub else '.'.join(filter(None, (args.project or 'all', SCOPE)))))
    guard = open(lock, 'w')
    try:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError('Another watcher is already running (lock %s)' % lock)
    failures = 0
    limited = {}                          # board → backoff end already logged (a backoff is logged once)
    started_on = code_fingerprint()
    while True:
        if ARGV is not None and code_fingerprint() != started_on:
            reload_watcher(args)
        try:
            result = cmd_tick(argparse.Namespace(project=args.project, hub=hub), b)
            failures = 0
            print('%s tick: %d verdicts, %d started, %d need orchestrator%s' % (
                time.strftime('%H:%M:%S'), len(result['verdicts']), len(result['started']),
                len(result['needs_orchestrator']),
                ''.join('; sync %s failed: %s' % kv for kv in result.get('sync_errors', {}).items())
                + ''.join('; %s skipped: %s' % kv for kv in result.get('skipped_tables', {}).items())
                + ('; status table failed: %s' % result['status_table_error'] if result.get('status_table_error') else '')
                + rate_note(result.get('rate_limited') or {}, limited)
                + ('; Linear calls: %s' % ', '.join('%s %d' % kv for kv in sorted(result['linear_calls'].items()))
                   if result.get('linear_calls') else '')
                + ('; Linear left to the hub: %s' % ', '.join(result['left_to_hub']) if result.get('left_to_hub') else '')),
                file=sys.stderr, flush=True)
            if hub and not result.get('queue_error'):
                try:
                    waiting = [e for e in board_store().take(peek=True) if e.get('session')]
                except RuntimeError as error:
                    waiting, result['queue_error'] = None, str(error)[:200]
                if waiting:
                    return {**result, 'events_waiting': len(waiting),
                            'next': 'run `mstack events next` and deliver each group with SendMessage'}
                work = hub_work() if status_table_on() else {}
                if work.get('ctas') or work.get('observe_sessions'):
                    return {**result, 'hub_work': {'ctas': len(work['ctas']), 'observe_sessions': work['observe_sessions']},
                            'next': 'run `mstack sessions todo` and do what it lists (My tasks CTAs, session states)'}
                if waiting is not None and not (args.exit_on_start and result['started']):
                    result = {**result, 'needs_orchestrator': []}      # queued: delivered through `events next`
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


def rate_note(now_limited, logged):
    """'; Linear rate-limited …' for backoffs not logged yet; a backoff that ended is forgotten."""
    fresh = {name: until for name, until in now_limited.items() if logged.get(name) != until}
    for name in [n for n in logged if n not in now_limited]:
        del logged[name]
    logged.update(fresh)
    return ''.join('; %s: Linear rate-limited until %s' % (name, time.strftime('%H:%M:%S', time.localtime(until)))
                   for name, until in sorted(fresh.items()))


def cli_run(run):
    """A run of a spawned CLI host (dispatch gave it a run log), as opposed to a desktop or adopted session."""
    return bool(run) and 'log' in run and not run.get('handoff') and not run.get('adopted')


HEADLESS = ('You run headless in a sandbox: do not run `git commit` or `mstack board` (both are refused there). '
            'mstack commits your changes on the task branch and posts your final answer when your turn ends. End '
            'with a short summary: what changed, what is left, and anything the owner must decide.')


def take_queued(task, sandboxed=False):
    """The owner comments waiting for a CLI worker, as the next turn's prompt; None (and the run marked not live)
    when there are none. One lock, so a comment can't slip in between the check and the end of the run."""
    with state() as s:
        run = s.get('runs', {}).get(task) or {}
        queued = run.pop('queued', [])
        if not queued or run.get('stopped'):
            run['live'] = False
            return None
    how = HEADLESS if sandboxed else 'Then report with `mstack board note` or `mstack board done` as before.'
    return ('The owner commented on your issue (from Linear). Act on it. %s\n\n' % how
            + '\n\n'.join('- ' + q['text'] for q in queued))


def commit_turn(tree, runner, message):
    """For a sandboxed host (MST-56: dsh can't commit in a worktree): commit what its turn changed, from outside
    the sandbox, on the task branch. A multi-repo task folder commits each repo worktree. Returns commits made."""
    bases = sorted(p.name[5:] for p in (tree/'.mstack/cache').glob('base.*'))
    made = 0
    for repo in [tree/name for name in bases] or [tree]:
        git(repo, 'add', '-A', '--', '.', ':(exclude).mstack', ':(exclude).mcp.json', ':(exclude).claude')
        if subprocess.run(['git', '-C', str(repo), 'diff', '--cached', '--quiet']).returncode == 0:
            continue                                  # nothing staged in this repo
        title = (message or '').strip().splitlines()[0][:72] if (message or '').strip() else 'work turn'
        git(repo, '-c', 'user.name=mstack %s worker' % runner, '-c', 'user.email=%s@mstack.local' % runner,
            'commit', '-q', '-m', '%s: %s' % (runner, title), '-m', SECRET.sub('[redacted]', message or '')[:4000])
        made += 1
    return made


def run_turn(argv, work_dir, env, stream, out_file):
    """One host process; its output is parsed line by line (session id as soon as it appears) and kept beside the
    run log. Same process group as `work`, so `board stop` ends both."""
    proc = subprocess.Popen(argv, cwd=work_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True)
    with open(out_file, 'a') as keep, proc.stdout:
        for line in proc.stdout:
            keep.write(SECRET.sub('[redacted]', line))
            found = stream.feed(line)
            if found:
                yield found
    proc.wait()
    stream.exit = proc.returncode


def cmd_work(args, b):
    """Detached CLI worker: one or more turns of one non-interactive agent session, then report back for review.
    A host with a JSON event stream (manifest `stream`) gets its session id recorded on the run, so "My tasks"
    shows it. Owner comments forwarded while it runs wait in the run's queue and become the next turn of the same
    session (manifest `resume`); `--resume` starts with that queue (or, back from review, with the updated brief).
    The review ask is skipped when the worker already ran `board done` itself during the last turn."""
    b = board_of_task(args.task, b)
    tree = Path(args.tree)
    brief = (tree/'.mstack/cache/brief.md').read_text()
    repo = Path(table_of(args.table)[1]['path'])
    env = dict(os.environ, MSTACK_TASK=args.task, MSTACK_AGENT=args.runner)
    if args.runner == 'codex':
        env['MSTACK_CODEX_NOTIFY'] = '1'
    with state() as s:
        run = s.setdefault('runs', {}).setdefault(args.task, {})
        run.update(live=True, pid=os.getpid())
        run.pop('stopped', None)
        run = dict(run)
    work_dir = Path(run.get('cwd') or tree)
    native = run.get('native_session')
    boxed = runners.sandboxed(args.runner, repo)
    prompt = brief
    if args.resume:
        if not native:
            raise ValueError('Task %s has no recorded session to resume' % args.task)
        prompt = take_queued(args.task, boxed) or ('The owner replied to your review; their notes are in the updated '
                                                   'brief below. Continue the same task.\n\n' + brief)
        with state() as s:
            s['runs'][args.task]['live'] = True
    out_file = Path(run['log']).with_suffix('.stream.log') if run.get('log') else tree/'.mstack/cache/run.stream.log'
    out_file.parent.mkdir(parents=True, exist_ok=True)
    turns, stream, committed, usage = [], None, 0, {}
    while prompt is not None:
        started = time.time()
        stream = runners.Stream(args.runner, repo)
        argv = runners.command(args.runner, prompt, work_dir, repo, run.get('mcp', []),
                               session=native if (args.resume or turns) else None, cache=tree/'.mstack/cache')
        for found in run_turn(argv, work_dir, env, stream, out_file):
            native = native or found
            with state() as s:
                s['runs'][args.task].update(session='%s:%s' % (args.runner, native), native_session=native)
        turns.append({'exit': stream.exit, 'ended': stream.ended, 'completed': stream.completed(),
                      'blocked': len(stream.blocked)})
        for name, n in stream.usage.items():
            usage[name] = usage.get(name, 0) + n
        if boxed and stream.completed():
            committed += commit_turn(tree, args.runner, stream.final)
        prompt = take_queued(args.task, boxed) if native and runners.can_resume(args.runner, repo) else None
        if prompt is None:
            with state() as s:
                s['runs'][args.task].update(live=False, **({'usage': usage} if usage else {}))
    output = SECRET.sub('[redacted]', stream.summary().strip())
    run = read_state().get('runs', {}).get(args.task) or {}
    report = run.get('report') or {}
    last = turns[-1]
    result = {'task': args.task, 'exit': last['exit'], 'turns': len(turns), 'session': native,
              'completed': last['completed'], 'blocked': [b for b in dict.fromkeys(stream.blocked)],
              'committed': committed, 'output_tail': output[-4000:]}
    if run.get('stopped'):
        return {**result, 'finish': 'skipped: stopped'}
    if not last['completed']:
        # Not a crash to hide and not a finished turn: tell the owner, keep the issue In Progress (a comment resumes it).
        b.say(args.task, '**%s** turn did not complete (%s, exit %s) on session `%s`. Comment to resume it, or close '
                         'the issue to stop it.%s' % (args.runner, last['ended'] or 'no turn end', last['exit'], native,
                                                      '\n\n' + output[-1200:] if output else ''))
        record_report(args.task, 'note', 'turn did not complete: ' + output[-500:])
        return {**result, 'finish': 'skipped: turn did not complete'}
    if report.get('kind') == 'done' and report.get('ts', 0) >= started:
        return {**result, 'finish': 'skipped: the worker already reported done'}
    result['commits'] = finish(b, args.task, tree, args.runner, output, last['exit'])
    if boxed:
        record_report(args.task, 'done', output)
    return result


def forward_to_cli(task, text):
    """An owner comment for a CLI worker. It is queued on the run; while the worker's process runs, it becomes the
    next turn when the current one ends. Otherwise a resumed turn starts now (`work --resume`)."""
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    with state() as s:
        run = s.get('runs', {}).get(task)
        if not cli_run(run):
            raise ValueError('Task %s has no CLI worker' % task)
        if run.get('stopped'):
            return 'not delivered: the worker was stopped'
        run.setdefault('queued', []).append({'text': SECRET.sub('[redacted]', text)[:4000], 'at': stamp})
        if run.get('live') and alive(run.get('pid')):
            return 'queued for the running %s worker (next turn)' % run['runner']
        run = dict(run)
    repo = Path(read_state()['tables'][run['table']]['path'])
    if not run.get('native_session') or not runners.can_resume(run['runner'], repo):
        return 'queued: %s recorded no resumable session; dispatch it again to act on it' % run['runner']
    pid = spawn([sys.executable, str(HERE/'cli.py'), 'work', '--task', task, '--table', run['table'],
                 '--runner', run['runner'], '--tree', run['tree'], '--resume'], run['log'])
    with state() as s:
        s['runs'][task].update(pid=pid, live=True)
    return 'resumed %s session %s (pid %d)' % (run['runner'], run['native_session'], pid)


def our_worker(pid, task):
    """Identity check before a signal: the pid is still a `cli.py work` process for this task (Linux /proc)."""
    try:
        argv = Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')
    except OSError:
        return False
    return b'work' in argv and task.encode() in argv and any(a.endswith(b'cli.py') for a in argv)


def stop_cli(task):
    """End a CLI worker: SIGTERM to its process group (`work` and the host), after an identity check. The run is
    marked stopped either way, so queued comments are dropped and nothing resumes it."""
    with state() as s:
        run = s.get('runs', {}).get(task)
        if not cli_run(run):
            raise ValueError('Task %s has no CLI worker (desktop sessions are stopped with stop_session)' % task)
        pid = run.get('pid')
        live = run.get('live') and alive(pid)
        if live and not our_worker(pid, task):
            live = None
        run.update(stopped=time.strftime('%Y-%m-%dT%H:%M:%S%z'), live=False, queued=[])
    if live:
        os.killpg(pid, signal.SIGTERM)
        return 'stopped %s worker (pid %d)' % (run['runner'], pid)
    if live is None:
        return 'pid %d is no longer this worker; nothing signalled' % pid
    return 'the %s worker was not running' % run['runner']


def cmd_forward(args, b):
    key = run_key(args.task)
    text = (sys.stdin.read() if args.text == '-' else args.text).strip()
    return {'task': key, 'delivered': forward_to_cli(key, text)}


def cmd_stop(args, b):
    key = run_key(args.task)
    done = stop_cli(key)
    board_of_task(key, b).say(key, 'Worker stopped: %s.%s' % (done, ' ' + args.reason if args.reason else ''))
    return {'task': key, 'stopped': done}


def deliver_to_cli(items, b):
    """The hub's part for CLI workers: `forward`, `stop` and worker `mention` items whose worker is a spawned CLI run are carried out
    here (resume or queue; SIGTERM) instead of going to the orchestrator chat. Returns (left for the
    orchestrator, done here)."""
    runs = read_state().get('runs', {})
    left, done = [], []
    for item in items:
        cli_mention = item['kind'] == 'mention' and item.get('session')
        if (item['kind'] not in ('forward', 'stop') and not cli_mention) or not cli_run(runs.get(item.get('task'))):
            left.append(item)
            continue
        try:
            if cli_mention:
                result = forward_to_cli(item['task'], 'Linear mention from %s (a teammate, not the owner): %s'
                                        % (item.get('author'), item.get('text') or ''))
            elif item['kind'] == 'forward':
                result = forward_to_cli(item['task'], item.get('text') or '')
                board_for(item['table'], b).say(item['task'], 'Your comment went to the CLI worker: %s.' % result)
            else:
                result = stop_cli(item['task'])          # linear_signals already told the owner it stopped
        except (ValueError, OSError) as error:
            result = 'failed: %s' % str(error)[:200]
        done.append({'kind': item['kind'], 'task': item['task'], 'issue': item.get('issue'), 'result': result})
    return left, done


def cmd_done(args, b):
    """A worker in any host (desktop session, manual) reports its task ready for review."""
    key = run_key(args.task)
    b = board_of_task(key, b)
    run = read_state().get('runs', {}).get(key)
    if not run:
        raise ValueError('Task %s has no worker on the board (dispatch or adopt it first)' % args.task)
    sizes = read_state().get('task_sizes', {})
    size = args.size or sizes.get(key) or sizes.get(run.get('issue') or '') or 'medium'
    missing = docs_missing(b, key, run, size, args.doc)
    if missing and not args.force:
        raise ValueError('%s is a %s issue; before done it still needs %s.' % (args.task, size, '; and '.join(missing)))
    summary = (sys.stdin.read() if args.summary == '-' else args.summary) + doc_links(table_of_task(key), args.doc)
    if missing:
        summary += '\n\n(Forced past the docs check; still missing: %s.)' % '; '.join(missing)
    tree = Path(run['tree']) if run.get('tree') else None      # adopted sessions may have no recorded worktree
    commits = finish(b, key, tree, run.get('runner') or 'worker', summary)
    added = add_resources(b, table_of_task(key), key, args.doc)
    record_report(key, 'done', summary)
    out = {'task': key, 'status': 'In Review', 'commits': commits, 'size': size, 'forced': bool(missing),
           'resources_added': added}
    moves = pushed(b)
    if moves:
        out['linear_status'] = moves
    return out


def cmd_note(args, b):
    b = board_of_task(args.task, b)
    text = SECRET.sub('[redacted]', sys.stdin.read() if args.text == '-' else args.text).strip()
    who = {'in': '%s ← owner (session)', 'out': '%s → (session)', 'note': '%s'}[args.direction] % args.agent
    b.say(args.task, '%s: %s%s' % (who, text[:1800], doc_links(table_of_task(args.task), args.doc)))
    added = add_resources(b, table_of_task(args.task), args.task, args.doc)
    record_report(run_key(args.task), 'note', text)
    if args.status:
        b.set(args.task, task_status=args.status)
    return {'task': args.task, 'posted': True, 'status': args.status, 'resources_added': added}


def cmd_merged(args, b):
    """After merge and push: check the commit is on the pushed main (or the scope's `landing` branch, MST-60), add
    the docs as the issue's Resources, post one short note, and set Done (or keep In Review with --verify "what is
    left"). Linear: --verify (live on Preview for the consumer) is In Review; landed on a `never_done` scope stays
    In Progress (the consumer closes it); otherwise Done."""
    key = run_key(args.task)
    run = read_state().get('runs', {}).get(key) or {}
    if args.project:
        table, entry = table_of(args.project)
        b = board_for(table, b)
        remember(args.task, table)
    else:
        table = table_of_task(key) or table_of_task(args.task)
        if not table:
            raise ValueError('Task %s is not on a registered board: pass --project' % args.task)
        entry = read_state()['tables'][table]
        b = board_of_task(key, b)
    repo = Path(entry['path'])
    task = b.get(args.task)
    main = args.branch or getattr(b, 'landing', None) or main_branch(repo)
    remote = 'origin/' + main
    branch = task.get('branch') or run.get('branch')
    tip = git(repo, 'rev-parse', '--verify', '--quiet', 'refs/heads/%s^{commit}' % branch, check=False) if branch else ''
    commit = git(repo, 'rev-parse', '--verify', '--quiet', (args.commit or tip or '') + '^{commit}', check=False)
    if not commit:
        raise ValueError('No commit to check: pass --commit <sha> (the merge on %s)' % main)
    if not git(repo, 'rev-parse', '--verify', '--quiet', remote, check=False):
        raise ValueError('%s has no %s: push the merge first' % (repo, remote))
    if subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', commit, remote]).returncode:
        raise ValueError('%s is not on the pushed %s: merge and push first, then run merged again' % (commit[:9], remote))
    if not args.commit and commit == tip:              # default: the merge that brought the branch into main
        merges = git(repo, 'rev-list', '--ancestry-path', '--merges', '--reverse', '%s..%s' % (tip, remote)).split()
        commit = merges[0] if merges else commit
    gone = [d for d in args.doc if subprocess.run(['git', '-C', str(repo), 'cat-file', '-e', '%s:%s' % (commit, d)],
                                                   capture_output=True).returncode]
    if gone:
        raise ValueError('not in %s: %s' % (commit[:9], ', '.join(gone)))
    warnings = []
    if tip and subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', tip, remote]).returncode:
        warnings.append('branch %s has commits not on the pushed %s' % (branch, main))
    parents = git(repo, 'rev-list', '--parents', '-n', '1', commit).split()[1:]
    base = run_base(run) or (git(repo, 'merge-base', *parents) if len(parents) == 2 else None)
    work = tip or (parents[1] if len(parents) == 2 else None)
    if args.doc and base and work:
        touched = set(git(repo, 'diff', '--name-only', base, work, check=False).splitlines())
        stale = [d for d in args.doc if d not in touched]
        if stale:
            warnings.append('docs not updated by the branch: %s (check them against the merged code)' % ', '.join(stale))
    elif args.doc:
        warnings.append('could not tell which docs the branch touched (no recorded base or merge commit)')
    added = add_resources(b, table, args.task, args.doc)
    if args.doc and not docs_base(table):
        warnings.append('no taskboard.docs_url: docs are named in the note only, not added as Resources')
    status = 'In Review' if args.verify else 'Done'
    text = 'Merged as `%s` on %s (status → %s).' % (commit[:9], main, status)
    if args.verify:
        text += ' Still to verify: %s' % SECRET.sub('[redacted]', args.verify)[:600]
    b.say(args.task, text + doc_links(table, args.doc))
    linear = 'In Review' if args.verify else ('In Progress' if getattr(b, 'never_done', False) else 'Done')
    if getattr(b, 'journal', None):
        b.push_status(args.task, linear)              # private boards: the note above already records the phase
    else:
        set_status(b, args.task, status, linear=linear)
    record_report(key, 'merged', text)
    out = {'task': args.task, 'commit': commit, 'branch': main, 'status': status, 'resources_added': added,
           'warnings': warnings}
    moves = pushed(b)
    if moves:
        out['linear_status'] = moves
    return out


def record_report(key, kind, text):
    """The worker's latest report on its run, for the session column of "My tasks" (design 014). A note doesn't
    replace a done report unless it is newer work: the latest one always wins."""
    with state() as s:
        run = s.get('runs', {}).get(key)
        if run is not None:
            run['report'] = {'kind': kind, 'at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'ts': time.time(),
                             'text': SECRET.sub('[redacted]', text)[:2000]}


def cmd_owner(args, b):
    """Private boards: pass on what the owner said in the orchestrator chat (`/plan …`, 👍, a reply)."""
    name, entry = table_of(args.project)
    lb = board_for(name, b)
    if not hasattr(lb, 'owner_says'):
        raise ValueError('%s is not a Linear board' % name)
    text = (sys.stdin.read() if args.text == '-' else args.text).strip()
    if getattr(args, 'side', False):
        text = anyboard.SIDE + ' ' + text
    task = lb.get(args.task)
    lb.owner_says(task['id'], text)
    out = {'task': task['id'], 'issue': task.get('linear_identifier'), 'recorded': text[:200]}
    if not text.startswith(anyboard.SIDE) and task.get('task_status') in PENDING:
        out['verdict'] = anyboard.decide(lb.messages(task['id']))[0]   # what the next poll will read it as
    return out


def cmd_inhand(args, b):
    """The orchestrator is already handling an issue's latest owner messages (a plan request, a reply):
    mark them seen so the watcher doesn't stop again for the same thing."""
    name, entry = table_of(args.project)
    lb = board_for(name, b)
    task = lb.get(args.task)
    messages = lb.messages(task['id'])
    keys = ['trigger:' + m['id'] for m in messages] + ['fwd:' + m['id'] for m in messages]
    verdict, text, _ = anyboard.decide(messages)
    if verdict == 'feedback':
        keys.append('%s:%s' % (task['id'], hashlib.sha256(text.encode()).hexdigest()[:12]))
    with state() as s:
        s['attention_seen'] = sorted(set(s.get('attention_seen', [])) | set(keys))
    return {'task': task['id'], 'issue': task.get('linear_identifier'), 'marked': len(keys)}


def cmd_tree(args, b):
    """An issue's sub-issue tree, as far as the owner's issues show it. Read it before creating sub-issues."""
    name, entry = table_of(args.project)
    lb = board_for(name, b)
    root = lb.get(args.task)
    rows = lb.tasks(entry.get('collection'))
    kids = {}
    for t in rows:
        if t.get('parent'):
            kids.setdefault(t['parent'], []).append(t)
    runs = read_state().get('runs', {})
    def node(t, depth=0):
        run = runs.get(t['id']) or {}
        out = [{'issue': t.get('linear_identifier'), 'title': t.get('name'), 'status': t.get('task_status'),
                'depth': depth, **({'worker': run['session']} if run.get('session') else {})}]
        for child in sorted(kids.get(t.get('linear_identifier'), []), key=lambda c: c.get('linear_identifier') or ''):
            out += node(child, depth + 1)
        return out
    return {'root': root.get('linear_identifier'), 'parent': root.get('parent'), 'tree': node(root),
            'note': 'Only issues assigned to or created by the owner are visible.'}


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


def cmd_orchestrators(args, b):
    """The hub's routing table: which orchestrator session serves a (project, scope)."""
    if args.action == 'list':
        return {'orchestrators': sorted(read_state().get('orchestrators', {}).values(),
                                        key=lambda e: (e['project'], e.get('scope') or ''))}
    if not args.project:
        raise ValueError('--project is required')
    name, entry = table_of(args.project)
    scope = args.scope_name
    if scope:
        scope_conf(project_settings(entry), scope)            # must be a scope in taskboard.orchestrators
    key = store.route_key(name, scope)
    with state() as s:
        known = s.setdefault('orchestrators', {})
        if args.action == 'remove':
            return {'removed': known.pop(key, None)}
        if not args.session:
            raise ValueError('--session is required')
        previous = (known.get(key) or {}).get('session')
        known[key] = {'project': name, 'scope': scope, 'session': args.session, 'note': args.note,
                      'at': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    return {'registered': known[key], 'replaced': previous if previous != args.session else None}


def event_line(e):
    """One event as a line of the hub's message."""
    p = e.get('payload') or {}
    what = e.get('issue') or p.get('issue') or p.get('linear') or e.get('task')
    detail = {'plan': lambda: 'owner asked for a plan%s' % (': ' + p['notes'][:300] if p.get('notes') else ''),
              'replan': lambda: 'owner replied to the plan (read it and decide: verdict, or revise and ask): ' + (p.get('feedback') or '')[:400],
              'review_reply': lambda: 'owner replied to the result (read it and decide: verdict approve|reject|changes): ' + (p.get('feedback') or '')[:400],
              'forward': lambda: 'owner comment for worker `%s`: %s' % (p.get('session'), (p.get('text') or '')[:400]),
              'stop': lambda: 'owner closed it (now %s); stop worker `%s`' % (p.get('now'), p.get('session')),
              'handoff': lambda: 'approved, ready for a worker: start a %s session titled "%s" in %s '
                                 '(brief: .mstack/cache/brief.md), then `board ack`' % (p.get('host'), p.get('title'), p.get('cwd')),
              'resume': lambda: 'approved plan for adopted chat `%s`: send it the prompt, then `board ack`' % p.get('session'),
              'verdict': lambda: 'verdict %s: %s → %s' % (p.get('verdict'), p.get('was'), p.get('now')),
              'status_lag': lambda: 'Linear says %s but the board is %s (want %s): %s' % (p.get('linear'), p.get('phase'), p.get('want'), p.get('do')),
              'new_issue': lambda: '"%s" assigned to you in Linear (%s): %s' % (p.get('name'), p.get('url'), p.get('do')),
              'mention': lambda: '%s mentioned you: %s; %s' % (p.get('author'), (p.get('text') or '')[:400], p.get('do')),
              'merged': lambda: 'branch `%s` is merged into main but the issue is %s: %s' % (p.get('branch'), p.get('status'), p.get('do'))}
    text = detail.get(e['kind'], lambda: json.dumps(p, ensure_ascii=False)[:300])()
    resent = ' (resent, try %d)' % e['sends'] if (e.get('sends') or 0) > 1 else ''
    return '- event %s [%s] %s: %s%s' % (e['id'], e['kind'], what, text, resent)


def cmd_events(args, b):
    """The event queue (design 011). next: hand out new events and overdue sent ones, grouped by the
    session that should get them, each with a ready-to-send message; resolve: the receiving orchestrator
    has acted on them."""
    st = board_store()
    if args.action == 'schema':
        sql = store.SCHEMA.read_text()
        if not args.apply:
            return {'schema': str(store.SCHEMA), 'sql': sql,
                    'apply': 'owner-approved setup step: mstack events schema --apply'}
        st.sql(sql)
        return {'applied': str(store.SCHEMA), 'database': store.PG['db']}
    if args.action == 'resolve':
        if not args.id:
            raise ValueError('--id is required')
        done = st.resolve(args.id, by=args.by or SCOPE or os.environ.get('MSTACK_AGENT'), note=args.note)
        return {'resolved': done, 'not_found_or_done': [i for i in args.id if i not in done]}
    if args.action == 'list':
        return {'backend': st.backend, 'events': st.events(args.status)}
    rows = st.take(peek=args.peek)
    info = [e['id'] for e in rows if e['kind'] == 'verdict' and e.get('session')]
    if info and not args.peek:                                # information only: never resent
        st.resolve(info, by='hub', note='delivered (information only)')
    groups, unrouted = {}, []
    for e in rows:
        if not e.get('session'):
            unrouted.append(e)
            continue
        g = groups.setdefault(e['session'], {'session': e['session'], 'routes': [], 'events': []})
        route = store.route_key(e['board'], e.get('scope'))
        if route not in g['routes']:
            g['routes'].append(route)
        g['events'].append(e)
    for g in groups.values():
        g['message'] = '\n'.join(['Events from the mstack hub for %s:' % ', '.join(g['routes'])]
                                 + [event_line(e) for e in g['events']]
                                 + ['After acting on each one: `%s/mstack events resolve --id <N>` '
                                    '(unresolved events are resent after %d minutes; verdicts are '
                                    'information only and already resolved).' % (STACK_ROOT, st.resend)])
    return {'backend': st.backend, 'deliver': list(groups.values()),
            'unrouted': [{'id': e['id'], 'route': store.route_key(e['board'], e.get('scope')), 'kind': e['kind'],
                          'issue': e.get('issue')} for e in unrouted],
            'hint': 'unrouted events wait for `mstack orchestrators register`' if unrouted else None}


def cmd_status(args, b):
    name, entry = table_of(args.project)
    st = read_state()
    runs, related = st.get('runs', {}), st.get('related', {})
    rows = []
    tasks = board_for(name, b).tasks(entry.get('collection'))
    forgotten = {t['id'] for t in merged_not_done(Path(entry['path']), tasks)}
    for t in tasks:
        row = {'task': t['id'], 'name': t.get('name'), 'status': t.get('task_status'), 'agent': t.get('task_agent'),
               'running': t['id'] in runs and alive(runs[t['id']]['pid'])}
        if t['id'] in forgotten:
            row['merged_not_done'] = 'branch merged into main: run `mstack board merged --task %s`' % (
                t.get('linear_identifier') or t['id'])
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
    out = {'table': name, 'links': links or 'private', 'tasks': rows}
    if forgotten:
        out['merged_not_done'] = [r.get('issue') or r['task'] for r in rows if r.get('merged_not_done')]
    return out


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
    s.add_argument('--size', choices=SIZES, help='record the issue size for the docs check at done')
    s = sub.add_parser('worktree', help='multi-repo workspace: add a repo worktree to a task folder')
    s.add_argument('--task', required=True, help='issue id or IRO-123'); s.add_argument('--repo', required=True)
    s = sub.add_parser('ask'); s.add_argument('--task', required=True); s.add_argument('text')
    s.add_argument('--status', default='Awaiting Approval', choices=list(PENDING))
    s = sub.add_parser('poll'); s.add_argument('--project')
    s = sub.add_parser('dispatch'); s.add_argument('--project', required=True)
    s.add_argument('--runner', help='agent plugin name (built-in or the project\'s own)')
    s = sub.add_parser('work'); s.add_argument('--task', required=True); s.add_argument('--table', required=True)
    s.add_argument('--runner', required=True); s.add_argument('--tree', required=True)
    s.add_argument('--resume', action='store_true', help='continue the recorded session with the queued comments')
    s = sub.add_parser('forward', help='pass an owner comment to a CLI worker (queued, or resumes its session)')
    s.add_argument('--task', required=True, help='issue id or IRO-123'); s.add_argument('text', help='text or - for stdin')
    s = sub.add_parser('stop', help='stop a CLI worker (SIGTERM to its process group) and note it on the issue')
    s.add_argument('--task', required=True, help='issue id or IRO-123'); s.add_argument('--reason')
    s = sub.add_parser('tick'); s.add_argument('--project')
    s.add_argument('--hub', action='store_true', help='one pass per registered orchestrator (project, scope)')
    s = sub.add_parser('watch'); s.add_argument('--project'); s.add_argument('--interval', type=int, default=10)
    s.add_argument('--hub', action='store_true', help='the hub watcher: tick every registered orchestrator, '
                   'exit when the queue has events to deliver')
    s.add_argument('--max-ticks', type=int, default=0, help='stop after N ticks (0 = run until work appears)')
    s.add_argument('--exit-on-start', action='store_true', help='also exit when a CLI worker was started')
    s = sub.add_parser('ack'); s.add_argument('--task', required=True); s.add_argument('--session', required=True)
    s = sub.add_parser('done'); s.add_argument('--task', required=True)
    s.add_argument('--summary', default='', help='text or - for stdin')
    s.add_argument('--doc', action='append', default=[], help='repo doc path to link (taskboard.docs_url)')
    s.add_argument('--size', choices=SIZES, help='small needs no doc; medium/big need --doc and a consolidated '
                   'description (default: the size from propose, else medium)')
    s.add_argument('--force', action='store_true', help='report despite a failed docs check (noted on the issue)')
    s = sub.add_parser('note'); s.add_argument('--task', required=True); s.add_argument('text')
    s.add_argument('--doc', action='append', default=[], help='repo doc path to link (taskboard.docs_url)')
    s.add_argument('--agent', default=os.environ.get('MSTACK_AGENT', 'agent'))
    s.add_argument('--direction', choices=['in', 'out', 'note'], default='note')
    s.add_argument('--status', choices=['Todo', 'In Progress', 'In Review', 'Done', 'Canceled'])
    s = sub.add_parser('merged', help='after merge and push: docs as Resources, one note, Done (or In Review with --verify)')
    s.add_argument('--task', required=True, help='issue id or MST-123')
    s.add_argument('--project', help='the board, when the issue has no run or plan recorded here')
    s.add_argument('--commit', help='the merge commit (default: the tip of the issue branch)')
    s.add_argument('--doc', action='append', default=[], help='repo doc path to add as a Resource (taskboard.docs_url)')
    s.add_argument('--verify', help='what is still to check after merge: keeps the issue In Review')
    s.add_argument('--branch', help="the branch it landed on (default: the scope's taskboard landing branch, else main)")
    s = sub.add_parser('status'); s.add_argument('--project', required=True)
    s = sub.add_parser('owner', help='private boards: record what the owner said in chat (/plan …, 👍, a reply)')
    s.add_argument('--project', required=True); s.add_argument('--task', required=True, help='issue id or IRO-123')
    s.add_argument('text', help='text or - for stdin')
    s.add_argument('--side', action='store_true',
                   help="the owner's OK or answer for a side action (not the plan): kept on the thread, never a verdict")
    s = sub.add_parser('verdict', help="record the orchestrator's reading of an owner reply: approve, reject or changes")
    s.add_argument('--task', required=True, help='issue id or IRO-123')
    s.add_argument('verdict', choices=['approve', 'reject', 'changes'])
    s.add_argument('--why', help='one line on how the reply was read (posted on the thread)')
    s = sub.add_parser('handover', help='brief for a fresh orchestrator session taking over this board or scope')
    s.add_argument('--project', required=True)
    s.add_argument('--messages', type=int, default=2, help='latest messages to include per open issue')
    s = sub.add_parser('inhand', help="mark an issue's latest owner messages as being handled (watcher won't stop again)")
    s.add_argument('--project', required=True); s.add_argument('--task', required=True)
    s = sub.add_parser('tree', help="an issue's sub-issue tree (read before creating sub-issues)")
    s.add_argument('--project', required=True); s.add_argument('--task', required=True)
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
    s = sub.add_parser('orchestrators', help='register|list|remove: which session serves a (project, scope)')
    s.add_argument('action', choices=['register', 'list', 'remove']); s.add_argument('--project')
    s.add_argument('--scope', dest='scope_name', help='scope from taskboard.orchestrators (omit: the whole board)')
    s.add_argument('--session', help='Claude Desktop session id (local_…)'); s.add_argument('--note')
    s = sub.add_parser('events', help='next|resolve|list|schema: the event hub queue')
    s.add_argument('action', choices=['next', 'resolve', 'list', 'schema'])
    s.add_argument('--id', action='append', default=[], help='event id to resolve (repeatable)')
    s.add_argument('--note'); s.add_argument('--by', help='who resolved it (default: the scope or MSTACK_AGENT)')
    s.add_argument('--peek', action='store_true', help='next: show without marking sent')
    s.add_argument('--status', choices=['new', 'sent', 'resolved'], help='list: only this status')
    s.add_argument('--apply', action='store_true', help='schema: run it against mstack_orchestrator (owner-approved)')
    s = sub.add_parser('sessions', help='todo|observe|done|list: the hub chat\'s side of the My tasks CTAs (design 014)')
    s.add_argument('action', choices=['todo', 'observe', 'done', 'list'])
    s.add_argument('--session', help='done: the session the CTA was for')
    s.add_argument('--result', help='done: what happened (shown as Last Action)')
    s.add_argument('--state', choices=['active', 'idle', 'archived', 'deleted'], help='done: the session\'s state now')
    s.add_argument('--complete', action='store_true', help='observe: the list is every session, archived included')
    s.add_argument('--self', dest='hub_session', help='observe: the hub\'s own session id (list_sessions leaves it out)')
    s = sub.add_parser('status-table', help='sync|show|rename: the owner\'s read-only "My tasks" table in Anytype (design 014)')
    s.add_argument('action', choices=['sync', 'show', 'rename'])
    s.add_argument('--full', action='store_true', help='sync: rewrite every row (overwrites hand edits now)')
    s.add_argument('--to', help='rename: the channel\'s new name')
    return p


ARGV = None                               # real command line (never set when main() is called from tests)


def main(argv=None, b=None):
    global SCOPE, ARGV
    p = parser()
    for name, sp in p._subparsers._group_actions[0].choices.items():
        if name != 'orchestrators':                           # it has its own --scope (the one to register)
            sp.add_argument('--scope', help='orchestrator scope from taskboard.orchestrators')
    args = p.parse_args(argv)
    SCOPE = getattr(args, 'scope', None)
    if argv is None:
        ARGV = list(sys.argv[1:])          # a real command line: only then may a watcher re-exec itself
    try:
        result = globals()['cmd_' + args.command.replace('-', '_')](args, b or anyboard.Board())
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print('mstack board: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
