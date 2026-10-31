"""mstack conductor: wakes conductor-hosted orchestrator Agents with their mail and runs what they ask
(design 016 §4, 017 §2.2–2.3, M1 + M4; MST-67).

One process per machine (lock `conductor.lock`). Each tick, per hosted agent with waiting mail:
  batch (30 s / 20 items) → render one message (hub header, events, issue context, PLAYBOOK.md when its hash
  changed, CONTEXT-<batch>.md when large) → send through the harness adapter → wait for the reply holding a
  ```mstack-actions``` block (asks once if a turn ends without one) → validate every action → record it in the
  execute-once log → run it with `mstack board` (live mode) or only log it (shadow) → resolve the batch.
A failed turn is requeued; three in a row pause the agent and mail the owner (`wake_failed`).
Agents also answer the owner in their own chat; actions blocks found there are checked and run the same way.

    mstack conductor run [--once] [--interval 10]
    mstack conductor run --dry-run --peek [--replay N] [--assume orch:mstack={{mstack:CLIENT_C_FOLDER}}] [--reply FILE]
    mstack conductor contract --tools <tools/list JSON>
    mstack conductor playbook [--address orch:mstack]

Intent lives in each project's `.mstack/stack.json` (`taskboard.agent`, or `taskboard.orchestrators.<scope>.agent`);
runtime state in orchestrator.agents / turns / actions (schema.sql).
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
import {{mstack:CLIENT_C_FOLDER}}
import mailbox
import store

STACK_ROOT = HERE.parents[1]
PLAYBOOK = HERE/'playbook.md'
SKILL = STACK_ROOT/'.agents/skills/mstack-orchestrator/SKILL.md'
SKILL_SECTIONS = ('Roles (strict)', 'After every merge', 'Linear status at every stage', 'Rules', 'Private boards')
DESKTOP_ONLY = re.compile(r'start_session|SendMessage|stop_session|side session|archive_session|list_sessions|Claude Desktop', re.I)
DEFAULTS = {'mode': 'shadow', 'batch_wait': 30, 'batch_cap': 20, 'max_turn_seconds': 900, 'nudge_seconds': 300,
            'turns_per_day': 48, 'inline_limit': 12000, 'resend_minutes': 5, 'chat_every': 60}
ADAPTERS = {'{{mstack:CLIENT_C_FOLDER}}': {{mstack:CLIENT_C_FOLDER}}.Adapter}
MAX_TEXT = 20000
FAILURES_TO_PAUSE = 3
SIZES = ('small', 'medium', 'big')
STATUSES = ('Backlog', 'Todo', 'In Progress', 'In Review', 'Done', 'Canceled')
ISSUE = re.compile(r'^([A-Z][A-Z0-9]*)-[0-9]+$')
TO = re.compile(r'^(orch:[a-z0-9][a-z0-9.-]*(/[a-z0-9][a-z0-9.-]*)?|worker:[A-Z][A-Z0-9]*-[0-9]+|dock|owner)$')
BLOCK = re.compile(r'```mstack-actions[ \t]*\n(.*?)```', re.S)
NUDGE = ('mstack hub · your turn ended without an ```mstack-actions``` block. Reply with one now '
         '(`[]` if there is nothing to do); see PLAYBOOK.md § Actions.')

# do: (required, optional) fields besides "do"
SPEC = {'propose': ({'task', 'plan'}, {'size', 'agent', 'doc'}),
        'ask': ({'task', 'text'}, set()),
        'note': ({'task', 'text'}, {'status'}),
        'verdict': ({'task', 'verdict'}, {'why'}),
        'owner': ({'task', 'text'}, set()),
        'dispatch': (set(), {'runner'}),
        'forward': ({'task', 'text'}, set()),
        'stop': ({'task'}, {'reason'}),
        'send': ({'to', 'text'}, set()),
        'say': ({'text'}, set()),
        'fetch': ({'what'}, {'task'}),
        'resolve': ({'events'}, set())}
MAIL_KINDS = {'message': lambda p: 'from %s: %s' % (p.get('from'), p.get('text') or ''),
              'owner_message': lambda p: 'the owner: %s' % (p.get('text') or ''),
              'worker_report': lambda p: 'worker %s ended a turn: %s' % (p.get('from'), p.get('text') or ''),
              'fetch_result': lambda p: '%s %s:\n%s' % (p.get('what'), p.get('task') or '', p.get('text') or ''),
              'wake_failed': lambda p: '%s failed %s turns: %s' % (p.get('address'), p.get('failures'), p.get('error'))}


def digest(*parts, n=64):
    return hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:n]


def compact(text):
    return ' '.join((text or '').split())


# ---- the actions block ---------------------------------------------------------------------------------------
def parse_actions(text):
    """(actions, error). (None, None) when the text has no block; the last block wins."""
    blocks = BLOCK.findall(text or '')
    if not blocks:
        return None, None
    try:
        actions = json.loads(blocks[-1])
    except ValueError as error:
        return None, 'the actions block is not valid JSON: %s' % error
    if not isinstance(actions, list) or not all(isinstance(a, dict) for a in actions):
        return None, 'the actions block must be a JSON list of objects'
    return actions, None


def validate(action, agent, ctx):
    """None when the action may run; else why it is refused. ctx: own_ids (event ids this agent may resolve),
    owner_texts (what the owner wrote in the agent's chat lately)."""
    do = action.get('do')
    if do not in SPEC:
        return 'unknown action %r' % do
    required, optional = SPEC[do]
    missing = sorted(required - set(action))
    if missing:
        return 'missing %s' % ', '.join(missing)
    extra = sorted(set(action) - required - optional - {'do'})
    if extra:
        return 'unknown field %s' % ', '.join(extra)
    for key, value in action.items():
        if isinstance(value, str) and len(value) > MAX_TEXT:
            return '%s is longer than %d characters' % (key, MAX_TEXT)
    if 'task' in action:
        m = ISSUE.match(str(action['task']))
        if not m:
            return 'task must be an issue key like MST-70'
        if m.group(1) not in agent['prefixes']:
            return 'task %s is not on this board (%s)' % (action['task'], ', '.join(sorted(agent['prefixes'])) or 'no link')
    if do == 'propose':
        if action.get('size') not in (None,) + SIZES:
            return 'size must be small, medium or big'
        if not isinstance(action.get('doc', []), list) or any(not isinstance(d, str) or d.startswith('/') or '..' in d
                                                               for d in action.get('doc', [])):
            return 'doc must be a list of repo-relative paths'
    if do == 'verdict' and action['verdict'] not in ('approve', 'reject', 'changes'):
        return 'verdict must be approve, reject or changes'
    if do == 'note' and action.get('status') not in (None,) + STATUSES:
        return 'status must be one of %s' % ', '.join(STATUSES)
    if do == 'send':
        if not TO.match(str(action['to'])):
            return 'unknown address %r' % action['to']
        if action['to'] == agent['address']:
            return 'an agent does not mail itself'
    if do == 'fetch':
        if action['what'] not in ('thread', 'tree', 'status'):
            return 'fetch what must be thread, tree or status'
        if action['what'] != 'status' and 'task' not in action:
            return 'fetch %s needs a task' % action['what']
    if do == 'resolve':
        ids = action['events']
        if not isinstance(ids, list) or not ids:
            return 'events must be a non-empty list'
        foreign = [i for i in ids if str(i) not in ctx.get('own_ids', set())]
        if foreign:
            return 'events %s are not waiting for you' % ', '.join(map(str, foreign))
    if do == 'owner':
        said = compact(action['text'])
        if not said or not any(said in compact(t) for t in ctx.get('owner_texts', [])):
            return "the text is not in the owner's recent messages in this chat"
    return None


def board_argv(action, agent):
    """(argv after `mstack board`, stdin) for an action that is a board command; None for the others."""
    do, project = action['do'], agent['project']
    scope = ['--scope', agent['scope']] if agent.get('scope') else []
    if do == 'propose':
        argv = ['propose', '--project', project, '--task', action['task'], '--plan', '-']
        argv += ['--size', action['size']] if action.get('size') else []
        argv += ['--agent', action['agent']] if action.get('agent') else []
        for doc in action.get('doc') or []:
            argv += ['--doc', doc]
        return argv + scope, action['plan']
    if do == 'ask':
        return ['ask', '--task', action['task'], action['text']] + scope, None
    if do == 'note':
        argv = ['note', '--task', action['task'], action['text'], '--agent', agent['address']]
        return argv + (['--status', action['status']] if action.get('status') else []) + scope, None
    if do == 'verdict':
        return ['verdict', '--task', action['task'], action['verdict']] + (
            ['--why', action['why']] if action.get('why') else []) + scope, None
    if do == 'owner':
        return ['owner', '--project', project, '--task', action['task'], '-'] + scope, action['text']
    if do == 'dispatch':
        return ['dispatch', '--project', project] + (['--runner', action['runner']] if action.get('runner') else []) + scope, None
    if do == 'forward':
        return ['forward', '--task', action['task'], '-'] + scope, action['text']
    if do == 'stop':
        return ['stop', '--task', action['task']] + (['--reason', action['reason']] if action.get('reason') else []) + scope, None
    if do == 'fetch':
        if action['what'] == 'status':
            return ['status', '--project', project] + scope, None
        return [action['what'], '--project', project, '--task', action['task']] + scope, None
    return None


def run_board(root):
    def run(argv, stdin=None):
        done = subprocess.run([str(Path(root)/'mstack'), 'board', *argv], input=stdin, text=True, capture_output=True,
                              timeout=600)
        if done.returncode:
            raise RuntimeError((done.stderr or done.stdout).strip()[-400:] or 'exit %d' % done.returncode)
        try:
            return json.loads(done.stdout)
        except ValueError:
            return {'output': done.stdout[-2000:]}
    return run


# ---- the playbook and rendering (M4) ---------------------------------------------------------------------------
def skill_excerpt(path=SKILL, sections=SKILL_SECTIONS):
    """The orchestrator skill's judgment sections, without the Claude Desktop tool lines."""
    if not Path(path).exists():
        return ''
    out, keep = [], False
    for line in Path(path).read_text().splitlines():
        if line.startswith('## '):
            keep = any(line[3:].startswith(s) for s in sections)
            if keep:
                out.append('#' + line)
            continue
        if keep and not DESKTOP_ONLY.search(line):
            out.append(line)
    return '\n'.join(out).strip() + '\n'


def playbook(agent, template=PLAYBOOK, skill=SKILL):
    scope = ' (scope %s)' % agent['scope'] if agent.get('scope') else ''
    text = Path(template).read_text()
    for key, value in (('{address}', agent['address']), ('{board}', agent['board']), ('{scope_line}', scope)):
        text = text.replace(key, value)
    return text + '\n' + skill_excerpt(skill)


def event_line(e):
    p = e.get('payload') or {}
    if e['kind'] in MAIL_KINDS:
        return '- event %s [%s] %s' % (e['id'], e['kind'], MAIL_KINDS[e['kind']](p)[:4000])
    return board_cli().event_line(e)


def board_cli():
    """integrations/orchestrator/cli.py (`import cli` would find integrations/stack/cli.py first)."""
    if 'board_cli' not in sys.modules:
        import importlib.util
        spec = importlib.util.spec_from_file_location('board_cli', HERE/'cli.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules['board_cli'] = module
        spec.loader.exec_module(module)
    return sys.modules['board_cli']


def thread_context(found):
    """Prefetched `board thread` output as a few quoted lines."""
    if not found:
        return []
    if isinstance(found, str):
        return ['  > ' + found[:600]]
    lines = ['  status: %s' % found.get('status')] if found.get('status') else []
    for m in (found.get('messages') or [])[-3:]:
        lines.append('  > ' + compact(m.get('text'))[:600])
    return lines


def render(agent, rows, state, contexts=None, playbook_text=None, refused=()):
    """The batch as (message, files, info). files: [(name, text)]."""
    ids = [str(r['id']) for r in rows]
    batch = digest(agent['address'], ids, n=6)
    pb_hash = digest(playbook_text, n=8) if playbook_text else None
    send_playbook = bool(playbook_text) and pb_hash != state.get('playbook_hash')
    header = 'mstack hub · batch %s · events %s' % (batch, ', '.join(ids))
    meta = 'to %s · board %s%s · %s mode%s' % (
        agent['address'], agent['board'], ' / ' + agent['scope'] if agent.get('scope') else '', agent['mode'],
        ' · playbook %s%s' % (pb_hash, ' (attached: PLAYBOOK.md)' if send_playbook else '') if pb_hash else '')
    top = [header, meta, '']
    if refused:
        top += ['Refused last turn (fix or drop):'] + ['- %s' % r for r in refused] + ['']
    body = ['Events:']
    seen = set()
    for r in rows:
        body.append(event_line(r))
        issue = r.get('issue') or r.get('task')
        if issue and issue not in seen and contexts and contexts.get(issue):
            seen.add(issue)
            body += thread_context(contexts[issue])
    foot = ['', 'End your turn with one ```mstack-actions``` block (PLAYBOOK.md § Actions); `[]` if there is nothing to do.']
    files = [('PLAYBOOK.md', playbook_text)] if send_playbook else []
    text = '\n'.join(top + body + foot)
    if len(text) > agent['inline_limit']:
        name = 'CONTEXT-%s.md' % batch
        files.append((name, '\n'.join(['# ' + header, ''] + body) + '\n'))
        short = ['Events (full text and context in %s, attached):' % name]
        short += ['- event %s [%s] %s' % (r['id'], r['kind'], r.get('issue') or r.get('task') or '') for r in rows]
        text = '\n'.join(top + short + foot)
    return text, files, {'batch': batch, 'ids': ids, 'playbook_hash': pb_hash, 'playbook_sent': send_playbook,
                         'key': 'mstack:%s:%s' % (agent['address'], digest(agent['address'], ids, n=32))}


# ---- agents from config ----------------------------------------------------------------------------------------
def agent_conf(board, scope, conf, project, prefixes):
    agent = {**DEFAULTS, **conf, 'board': board, 'scope': scope, 'project': str(project),
             'address': mailbox.address(board, scope), 'prefixes': set(prefixes)}
    if agent.get('harness') == '{{mstack:CLIENT_C_FOLDER}}':
        agent['session'] = '{{mstack:CLIENT_C_FOLDER}}:%s/%s' % (agent.get('team') or '?', agent.get('agent') or '?')
    return agent


def link_teams(taskboard, apps=None):
    links = [('*', taskboard['link'])] if taskboard.get('link') else []
    links += [(code, a['link']) for code, a in (taskboard.get('apps') or {}).items() if a.get('link')]
    return {l['team'] for code, l in links if apps is None or code in apps or code == '*' and '*' in apps}


def configured_agents(tables, project_config):
    """Conductor-hosted agents declared in each registered project's stack.json."""
    out = []
    for board, entry in sorted(tables.items()):
        try:
            tb = project_config(Path(entry['path'])).get('taskboard') or {}
        except (ValueError, OSError, KeyError):
            continue
        if tb.get('agent'):
            out.append(agent_conf(board, None, tb['agent'], entry['path'], link_teams(tb)))
        for scope, sc in sorted((tb.get('orchestrators') or {}).items()):
            if sc.get('agent'):
                out.append(agent_conf(board, scope, sc['agent'], entry['path'], link_teams(tb, sc.get('apps'))))
    return out


# ---- the conductor -----------------------------------------------------------------------------------------------
class Conductor:
    def __init__(self, mb, agents, adapters, board=None, prefetch=None, clock=time.time, log=None,
                 playbook_for=playbook):
        self.mb, self.agents = mb, {a['address']: a for a in agents}
        self.adapters, self.board, self.prefetch = adapters, board, prefetch
        self.clock, self.log = clock, log or (lambda line: print(line, file=sys.stderr, flush=True))
        self.playbook_for = playbook_for
        self.swept = {}                                      # address → when its chat was last read

    # -- when to wake
    def why_not(self, agent, state, rows, now):
        if state['state'] == 'paused':
            return 'paused'
        if state['state'] == 'running' and now - _ts(state.get('last_wake')) < agent['max_turn_seconds'] + 60:
            return 'a turn is running'
        today = time.strftime('%Y-%m-%d', time.gmtime(now))
        if state.get('day') == today and state.get('turns_day', 0) >= agent['turns_per_day']:
            return 'daily turn cap (%d)' % agent['turns_per_day']
        urgent = any(r['kind'] in mailbox.URGENT for r in rows)
        newest = min(mailbox.age_seconds(r, now) for r in rows)
        if not urgent and len(rows) < agent['batch_cap'] and newest < agent['batch_wait']:
            return 'collecting (newest mail %ds old)' % newest
        return None

    def contexts(self, agent, rows):
        if not self.prefetch:
            return {}
        out = {}
        for r in rows:
            issue = r.get('issue') or r.get('task')
            if issue and ISSUE.match(str(issue)) and issue not in out:
                try:
                    out[issue] = self.prefetch(agent, issue)
                except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
                    out[issue] = 'context not available: %s' % str(error)[:200]
        return out

    def plan(self, agent, rows, state):
        rows = rows[:agent['batch_cap']]
        text, files, info = render(agent, rows, state, self.contexts(agent, rows), self.playbook_for(agent),
                                   (state.get('cursor') or {}).get('refused') or [])
        return {'rows': rows, 'text': text, 'files': files, **info}

    # -- one tick
    def tick(self, dry_run=False):
        now = self.clock()
        report = {'turns': [], 'chats': []}
        pending = self.mb.pending(set(self.agents), resend_minutes=min(a['resend_minutes'] for a in self.agents.values())
                                  if self.agents else 5)
        by_addr = {}
        for r in pending:
            by_addr.setdefault(r['recipient'], []).append(r)
        for addr, agent in self.agents.items():
            state = self.mb.agent(addr)
            if (not dry_run and agent.get('channel') and state['state'] not in ('paused', 'running')
                    and now - self.swept.get(addr, 0) >= agent['chat_every']):
                self.swept[addr] = now
                report['chats'] += self.sweep_chat(agent, state)
                state = self.mb.agent(addr)
            rows = by_addr.get(addr)
            if not rows:
                continue
            wait = self.why_not(agent, state, rows, now)
            if dry_run:
                report['turns'].append(self.describe(agent, rows, state, wait))
            elif wait:
                report['turns'].append({'address': addr, 'waiting': wait, 'events': [r['id'] for r in rows]})
            else:
                report['turns'].append(self.turn(agent, rows, state))
        return report

    def describe(self, agent, rows, state, wait):
        p = self.plan(agent, rows, state)
        c = getattr(self.adapters.get(agent.get('harness')), 'c', None) or {}
        tools = c.get('tools') or {}
        return {'address': agent['address'], 'harness': agent.get('harness'), 'mode': agent['mode'],
                'would': 'wait: ' + wait if wait else 'send now', 'events': p['ids'], 'batch': p['batch'],
                'send': {'tool': tools.get('send'), 'channel': agent.get('channel'), 'idempotency_key': p['key'],
                         'files': [{'name': n, 'chars': len(t)} for n, t in p['files']], 'chars': len(p['text'])},
                'then': '%s up to %ds (calls of ≤240 s); ask once if no actions block; validate; %s; resolve %s'
                        % (tools.get('wait'), agent['max_turn_seconds'],
                           'run them with mstack board' if agent['mode'] == 'live' else 'log them (shadow)',
                           ', '.join(p['ids'])),
                'message': p['text']}

    def turn(self, agent, rows, state):
        addr, adapter = agent['address'], self.adapters[agent['harness']]
        p = self.plan(agent, rows, state)
        attempt = 1 + max(int(r.get('attempts') or 0) for r in p['rows'])
        turn_id = '%s-%d' % (p['batch'], attempt)
        ids = self.mb.take(p['ids'], turn_id, agent.get('session'))
        if not ids:
            return {'address': addr, 'skipped': 'events taken by someone else'}
        now = self.clock()
        today = time.strftime('%Y-%m-%d', time.gmtime(now))
        turns_day = (state.get('turns_day') or 0) + 1 if state.get('day') == today else 1
        self.mb.turn_start({'id': turn_id, 'address': addr, 'events': ids, 'attempt': attempt})
        self.mb.save_agent(addr, role='orchestrator', harness=agent['harness'], session=agent.get('session'),
                           mode=agent['mode'], state='running', last_wake=mailbox.iso(now), day=today, turns_day=turns_day)
        cursor = dict(state.get('cursor') or {})
        reply, error, owner_texts = None, None, list(cursor.get('owner_recent') or [])
        try:
            sent = adapter.send(agent, p['text'], p['files'], key=p['key'])
            reply, after, owners = self.collect(adapter, agent, sent, now + agent['max_turn_seconds'])
            owner_texts += owners
            if reply is None:
                sent = adapter.send(agent, NUDGE, key=p['key'] + ':nudge')
                reply, after, owners = self.collect(adapter, agent, sent, self.clock() + agent['nudge_seconds'])
                owner_texts += owners
            cursor['seq'] = after
            if reply is None:
                error = 'no actions block within %ds and the nudge' % agent['max_turn_seconds']
        except (RuntimeError, OSError, ValueError) as e:
            error = str(e)[:300]
        actions, parse_error = parse_actions(reply['text']) if reply else (None, None)
        error = error or parse_error
        if error:
            return self.fail(agent, state, cursor, turn_id, ids, error)
        ctx = {'own_ids': set(ids) | {str(r['id']) for r in self.mb.pending({addr})}, 'owner_texts': owner_texts}
        results = self.execute(agent, actions, turn_id, ids, ctx)
        self.mb.resolve(ids, by=addr, note='turn %s' % turn_id)
        cursor['refused'] = ['action %d (%s): %s' % (r['index'] + 1, r['do'], r['reason'])
                             for r in results if r['status'] in ('refused', 'failed')]
        cursor['owner_recent'] = owner_texts[-20:]
        adapter.react(agent, reply['seq'], '⚠️' if cursor['refused'] else '✅')
        self.mb.turn_end(turn_id, status='done', reply=reply['text'][:20000])
        self.mb.save_agent(addr, state='idle', failures=0, cursor=cursor, last_result='done: %d action(s)' % len(results),
                           **({'playbook_hash': p['playbook_hash']} if p['playbook_sent'] else {}))
        self.log('%s turn %s: %d action(s), %d refused' % (addr, turn_id, len(results), len(cursor['refused'])))
        return {'address': addr, 'turn': turn_id, 'events': ids, 'actions': results}

    def collect(self, adapter, agent, after, deadline):
        """Wait for the agent's message holding an actions block: (message or None, last seq, owner texts)."""
        owners = []
        while self.clock() < deadline:
            for m in adapter.wait(agent, after, deadline - self.clock()):
                if m['seq'] is not None and (after is None or m['seq'] > after):
                    after = m['seq']
                if m['from'] == 'owner':
                    owners.append(m['text'])
                elif m['from'] == 'agent' and BLOCK.search(m['text'] or ''):
                    return m, after, owners
        return None, after, owners

    def fail(self, agent, state, cursor, turn_id, ids, error):
        addr = agent['address']
        failures = (state.get('failures') or 0) + 1
        self.mb.requeue(ids, note='turn %s failed: %s' % (turn_id, error[:200]))
        self.mb.turn_end(turn_id, status='no_actions' if 'actions block' in error else 'failed', error=error)
        paused = failures >= FAILURES_TO_PAUSE
        if paused:
            self.mb.post([{'recipient': mailbox.OWNER, 'sender': 'conductor', 'kind': 'wake_failed', 'board': agent['board'],
                           'scope': agent.get('scope') or '', 'dedupe': 'wake_failed:%s:%s' % (addr, turn_id),
                           'payload': {'address': addr, 'failures': failures, 'error': error}}])
        self.mb.save_agent(addr, state='paused' if paused else 'idle', failures=failures, cursor=cursor,
                           last_result='failed: ' + error[:200])
        self.log('%s turn %s failed (%d): %s%s' % (addr, turn_id, failures, error, '; paused' if paused else ''))
        return {'address': addr, 'turn': turn_id, 'events': ids, 'failed': error, 'paused': paused}

    def sweep_chat(self, agent, state):
        """Catch up on the agent's chat between hub turns: owner messages, and actions blocks the agent wrote
        when the owner asked it something directly."""
        adapter, addr = self.adapters[agent['harness']], agent['address']
        cursor = dict(state.get('cursor') or {})
        try:
            msgs = adapter.recent(agent, after=cursor.get('seq'))
        except (RuntimeError, OSError, ValueError) as error:
            return [{'address': addr, 'chat': 'not read: %s' % str(error)[:200]}]
        out, owners = [], list(cursor.get('owner_recent') or [])
        for m in sorted((m for m in msgs if m['seq'] is not None), key=lambda m: m['seq']):
            if cursor.get('seq') is not None and m['seq'] <= cursor['seq']:
                continue
            cursor['seq'] = m['seq']
            if m['from'] == 'owner':
                owners.append(m['text'])
            elif m['from'] == 'agent':
                actions, error = parse_actions(m['text'])
                if actions is None and not error:
                    continue
                turn_id = 'chat-%s' % m['seq']
                if error:
                    out.append({'address': addr, 'turn': turn_id, 'refused': error})
                    continue
                ctx = {'own_ids': set(), 'owner_texts': owners}
                out.append({'address': addr, 'turn': turn_id,
                            'actions': self.execute(agent, actions, turn_id, ['msg:%s' % m['seq']], ctx)})
        cursor['owner_recent'] = owners[-20:]
        if cursor != (state.get('cursor') or {}):
            self.mb.save_agent(addr, role='orchestrator', harness=agent['harness'], cursor=cursor)
        return out

    # -- actions
    def execute(self, agent, actions, turn_id, event_ids, ctx):
        addr, results = agent['address'], []
        for i, action in enumerate(actions):
            key = digest(addr, sorted(map(str, event_ids)), i, action)
            reason = validate(action, agent, ctx)
            claimed = self.mb.claim_action(key, turn_id, addr, action)
            row = {'index': i, 'do': action.get('do'), 'key': key[:12]}
            if claimed != 'new':
                results.append({**row, 'status': 'skipped', 'reason': 'already %s' % claimed})
                continue
            if reason:
                self.mb.finish_action(key, 'refused', reason=reason)
                results.append({**row, 'status': 'refused', 'reason': reason})
                continue
            if agent['mode'] != 'live':
                self.mb.finish_action(key, 'shadow', result={'would_run': self.describe_action(action, agent)})
                results.append({**row, 'status': 'shadow', 'would_run': self.describe_action(action, agent)})
                continue
            try:
                result = self.run_action(action, agent, key)
                self.mb.finish_action(key, 'done', result=result)
                results.append({**row, 'status': 'done'})
            except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
                self.mb.finish_action(key, 'failed', reason=str(error)[:400])
                results.append({**row, 'status': 'failed', 'reason': str(error)[:400]})
        return results

    @staticmethod
    def describe_action(action, agent):
        argv = board_argv(action, agent)
        if argv:
            return 'mstack board ' + ' '.join(argv[0]) + (' <<< %d chars' % len(argv[1]) if argv[1] else '')
        if action['do'] in ('send', 'say'):
            return 'mail to %s (%d chars)' % (action.get('to', mailbox.OWNER), len(action['text']))
        return 'resolve events %s' % ', '.join(map(str, action['events']))

    def run_action(self, action, agent, key):
        addr, do = agent['address'], action['do']
        if do in ('send', 'say'):
            to = action.get('to', mailbox.OWNER)
            return {'mail': self.mb.post([{'recipient': to, 'sender': addr, 'kind': 'message', 'board': agent['board'],
                                           'scope': agent.get('scope') or '', 'dedupe': 'msg:' + key,
                                           'payload': {'from': addr, 'text': action['text']}}])}
        if do == 'resolve':
            return {'resolved': self.mb.resolve([str(i) for i in action['events']], by=addr, note='resolved by its agent')}
        argv, stdin = board_argv(action, agent)
        out = self.board(argv, stdin)
        if do == 'fetch':                                 # the answer comes in the agent's next batch
            text = json.dumps(out, ensure_ascii=False, indent=1)[:MAX_TEXT]
            self.mb.post([{'recipient': addr, 'sender': 'conductor', 'kind': 'fetch_result', 'board': agent['board'],
                           'scope': agent.get('scope') or '', 'dedupe': 'fetch:' + key, 'issue': action.get('task'),
                           'payload': {'what': action['what'], 'task': action.get('task'), 'text': text}}])
        return out


def _ts(iso):
    """Epoch seconds of an ISO stamp (0 when unset)."""
    return mailbox.epoch(iso) if iso else 0


# ---- command line ---------------------------------------------------------------------------------------------
def tables(mb):
    out = mb.sql(mb.q("SELECT value FROM orchestrator.board_state WHERE key = 'tables';\n"), fetch=True) or ''
    return json.loads(out.strip() or '{}')


def prefetcher(board):
    def get(agent, issue):
        return board(['thread', '--project', agent['project'], '--task', issue]
                     + (['--scope', agent['scope']] if agent.get('scope') else []))
    return get


@contextlib.contextmanager
def lock(root):
    path = Path(root)/'.mstack/evidence/conductor.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('another conductor holds %s' % path)
        yield


def use_root(root):
    """Point the Postgres password at <root>/.secrets (a worktree has none of its own)."""
    secret = Path(root)/'.secrets/postgres/mstack_orchestrator.password'
    if secret.exists():
        store.PG['password_file'] = secret


def cmd_run(a):
    import config as intent
    root = Path(a.root).resolve()
    use_root(root)
    if a.peek and not a.dry_run:
        raise ValueError('--peek goes with --dry-run (nothing is marked, sent or run)')
    mb = mailbox.PgMailbox()
    agents = configured_agents(tables(mb), intent.project_config)
    for assume in a.assume:                                    # dry run only: treat an address as hosted
        addr, _, harness = assume.partition('=')
        if not a.dry_run:
            raise ValueError('--assume is for --dry-run only')
        if addr not in {x['address'] for x in agents}:
            board, _, scope = addr[5:].partition('/')
            entry = tables(mb).get(board)
            if not entry:
                raise ValueError('no registered board %s' % board)
            tb = intent.project_config(Path(entry['path'])).get('taskboard') or {}
            agents.append(agent_conf(board, scope or None, {'harness': harness or '{{mstack:CLIENT_C_FOLDER}}', 'channel': '<channel>'},
                                     entry['path'], link_teams(tb)))
    board = run_board(root)
    adapters = {name: cls.__new__(cls) for name, cls in ADAPTERS.items()} if a.dry_run else {}
    for adapter in adapters.values():                           # dry run: the contract only, no client, no token
        adapter.c = json.loads({{mstack:CLIENT_C_FOLDER}}.CONTRACT.read_text())
    if not a.dry_run:
        live = [x for x in agents if x['mode'] == 'live']
        if len(live) != len(agents):
            raise ValueError('shadow agents (%s) need M5: shadow turns must read events without taking them from '
                             'the Claude orchestrator (P4)' % ', '.join(x['address'] for x in agents if x not in live))
        if not mb.upgraded:
            raise RuntimeError('the mailbox migration is not applied (mstack events schema --apply, owner-approved)')
        adapters = {h: ADAPTERS[h]() for h in {x['harness'] for x in agents}}
    c = Conductor(mb, agents, adapters, board=board, prefetch=None if a.no_prefetch else prefetcher(board))
    if a.dry_run:
        return dry_run(c, mb, a)
    with lock(root):
        while True:
            report = c.tick()
            if report['turns'] or report['chats']:
                print(json.dumps(report, ensure_ascii=False), flush=True)
            if a.once:
                return report
            time.sleep(a.interval)


def dry_run(c, mb, a):
    """What the conductor would send and run now. Reads Postgres (and `board thread` for context); writes,
    sends and runs nothing."""
    out = {'dry_run': True, 'schema': 'mailbox' if mb.upgraded else 'pre-mailbox (migration pending)',
           'agents': [{'address': x['address'], 'harness': x.get('harness'), 'mode': x['mode'],
                       'channel': x.get('channel')} for x in c.agents.values()]}
    if not c.agents:
        out['note'] = ('no conductor-hosted agent is configured (taskboard.agent in a project stack.json); '
                       'pass --assume orch:<board>={{mstack:CLIENT_C_FOLDER}} to preview one')
    report = c.tick(dry_run=True)
    if a.replay:
        rows = [r for r in mb.recent(limit=200) if r['recipient'] in c.agents][-a.replay:]
        for addr in sorted({r['recipient'] for r in rows}):
            mine = [dict(r, status='new') for r in rows if r['recipient'] == addr]
            report['turns'].append({**c.describe(c.agents[addr], mine, c.mb.agent(addr), None),
                                    'replay': 'already resolved events, rendered as a sample'})
    out['turns'] = report['turns']
    out['chat'] = 'not read: a dry run makes no hosted-agent calls'
    if a.reply:
        text = Path(a.reply).read_text()
        actions, error = parse_actions(text)
        addr = next(iter(c.agents), None)
        if error or actions is None or not addr:
            out['reply'] = {'error': error or ('no actions block' if addr else 'no agent')}
        else:
            agent = c.agents[addr]
            ctx = {'own_ids': {e for t in out['turns'] for e in t.get('events', [])}, 'owner_texts': []}
            out['reply'] = {'address': addr, 'actions': [
                {'do': x.get('do'), 'refused': validate(x, agent, ctx)} if validate(x, agent, ctx) else
                {'do': x['do'], 'would_run': Conductor.describe_action(x, agent)} for x in actions]}
    return out


def cmd_contract(a):
    tools = json.loads(Path(a.tools).read_text())
    if 'tools' in tools and isinstance(tools['tools'], dict):             # `{{mstack:CLIENT_C_FOLDER}}.py tools` output
        tools = tools['tools']
    problems = {{mstack:CLIENT_C_FOLDER}}.check_contract(tools)
    return {'contract': str({{mstack:CLIENT_C_FOLDER}}.CONTRACT), 'ok': not problems, 'problems': problems}


def cmd_playbook(a):
    board, _, scope = a.address[5:].partition('/')
    agent = {'address': a.address, 'board': board, 'scope': scope or None}
    text = playbook(agent)
    return {'address': a.address, 'hash': digest(text, n=8), 'chars': len(text), 'playbook': text}


def main(argv=None):
    p = argparse.ArgumentParser(prog='mstack conductor', description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run', help='wake hosted agents with their mail and run their actions')
    r.add_argument('--root', default=os.environ.get('MSTACK_ROOT', str(STACK_ROOT)),
                   help='the mstack checkout whose state and secrets to use (default: this one)')
    r.add_argument('--once', action='store_true'); r.add_argument('--interval', type=int, default=10)
    r.add_argument('--dry-run', action='store_true', help='print what would be sent and run; change nothing')
    r.add_argument('--peek', action='store_true', help='with --dry-run: read the live queue without marking it')
    r.add_argument('--replay', type=int, default=0, help='dry run: also render the last N resolved events as a sample')
    r.add_argument('--assume', action='append', default=[], metavar='ADDR=HARNESS',
                   help='dry run: preview an address as hosted (e.g. orch:mstack={{mstack:CLIENT_C_FOLDER}})')
    r.add_argument('--reply', help='dry run: an Agent reply to validate and translate into commands')
    r.add_argument('--no-prefetch', action='store_true', help='skip `board thread` context reads')
    c = sub.add_parser('contract', help='check the adapter contract against a saved tools/list answer')
    c.add_argument('--tools', required=True)
    b = sub.add_parser('playbook', help='print the PLAYBOOK.md an agent would receive, with its hash')
    b.add_argument('--address', default='orch:mstack')
    a = p.parse_args(argv)
    try:
        out = {'run': cmd_run, 'contract': cmd_contract, 'playbook': cmd_playbook}[a.cmd](a)
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print('mstack conductor: ' + str(error), file=sys.stderr)
        return 1
    if a.cmd == 'playbook':
        print(out.pop('playbook'))
        print(json.dumps(out), file=sys.stderr)
        return 0
    print(json.dumps(out, indent=2, ensure_ascii=False, default=sorted))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
