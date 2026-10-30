"""Anytype task board as seen by the orchestrator: one channel, one shared Agent Task type,
one collection (= table) per project.

Runs on Ubuntu. Every request goes through `anytype_taskboard.py api` on macOS
(the Anytype API listens on Mac loopback only) and stays inside the granted channel.
The orchestrator's key acts as the same Anytype user as the owner, so orchestrator
messages carry MARK (ASK when they wait for a verdict); everything else in a
discussion is the owner speaking.
"""
import json
import re
from pathlib import Path
import subprocess
import time

STACK_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((STACK_ROOT/'infra/taskboard/schema.json').read_text())
MARK = '🤖'          # every orchestrator/agent line
ASK = MARK + '❓'      # a line that waits for the owner's reaction or reply
APPROVE = {'👍', '✅', '🚀', '👌', '❤️'}
REJECT = {'👎', '❌'}
APPROVE_WORDS = ('approve', 'approved', 'lgtm', 'go ahead', 'ship it', 'yes', 'ok', 'go', 'approve it', 'do it')
# Bare approval only ("ok, go ahead"); a reply with anything more is read by the orchestrator, not by a rule.
ONLY_APPROVE = re.compile(r'^(?:(?:%s)[\s,.!]*)+$' % '|'.join(sorted(map(re.escape, APPROVE_WORDS), key=len, reverse=True)))
SIDE = '(side)'      # owner text recorded with `board owner --side`: kept on the thread, never a verdict
# Anytype comments can store emoji as shortcodes (a typed 👍 arrives as ":+1:").
SHORTCODES = {':+1:': '👍', ':thumbsup:': '👍', ':white_check_mark:': '✅', ':rocket:': '🚀',
              ':ok_hand:': '👌', ':heart:': '❤️', ':-1:': '👎', ':thumbsdown:': '👎', ':x:': '❌'}


def macctl(method, path, body=None, runner=subprocess.run, sleep=time.sleep, attempts=6):
    """One channel-relative request through the macOS bridge; returns the parsed body.
    Anytype's local API rate-limits bursts (HTTP 429): those are retried with backoff."""
    argv = ['macctl', 'run', 'python3', 'integrations/agents/anytype_taskboard.py', 'api',
            SCHEMA['credential_file'], method, path] + (['-'] if body is not None else [])
    for attempt in range(attempts):
        done = runner(argv, cwd=STACK_ROOT, input=json.dumps(body) if body is not None else None,
                      capture_output=True, text=True)
        if not done.returncode:
            return json.loads(done.stdout)['body']
        error = (done.stderr or done.stdout).strip()[-600:]
        if 'HTTP 429' not in error or attempt == attempts - 1:
            raise RuntimeError(error)
        sleep(min(2 ** attempt, 8))


KINDS = tuple(SCHEMA.get('naming', {}).get('kinds', ()))


def titled(title, app=None, kind=None):
    """Naming convention: [APP][KIND] description. A title already carrying this exact prefix is kept;
    other leading brackets (e.g. a Linear "[clientapp-api] …") stay part of the description."""
    prefix = ''.join('[%s]' % x for x in (app, kind) if x)
    if not prefix or title.startswith(prefix):
        return title
    return prefix + ' ' + title


def flatten(props):
    return {k: (v[0] if isinstance(v, list) and len(v) == 1 else v) for k, v in (props or {}).items()}


class Board:
    def __init__(self, call=macctl):
        self.call = call

    # ---- tables -------------------------------------------------------
    def ensure_type(self):
        """The one reusable Agent Task type every project's tasks share."""
        t = SCHEMA['type']
        if t['key'] not in {row['key'] for row in self.call('GET', 'types?limit=200').get('data') or []}:
            self.call('POST', 'types', {
                'api_key': t['key'], 'name': t['name'], 'plural_name': t['plural_name'],
                'icon': {'format': 'emoji', 'emoji': t['emoji']}, 'default_view': t['default_view'],
                'layout': 'basic',
                'property_definitions': [{'property': p['key'], 'section': p.get('section', 'hidden')}
                                         for p in SCHEMA['properties']]})
        return t['key']

    def ensure_table(self, project, known=None):
        """A project's table is a collection of Agent Tasks named "<project> tasks", with Board
        (kanban by status) and Table views and a sidebar widget. Membership is explicit, so
        projects never mix. Returns {collection, widget}; an existing table is kept."""
        if known and known.get('collection'):
            return known
        self.ensure_type()
        collection = self.call('POST', 'collections', {'name': project + ' tasks'})['id']
        self.call('PATCH', 'objects/' + collection, {'ops': [
            {'op': 'insert_view', 'name': 'Board', 'position': 'first',
             'set': {'type': 'kanban', 'group_by': 'task_status'}},
            {'op': 'insert_view', 'name': 'Table', 'set': {'type': 'table'}}]})
        self.tidy_views(collection)
        widget = self.call('POST', 'widgets', {'target': collection, 'scope': 'space', 'layout': 'view',
                                               'position': 'last'}).get('id')
        return {'collection': collection, 'widget': widget}

    def tidy_views(self, collection):
        """Board (kanban by status) and Table show task fields, not Anytype's default metadata;
        the auto-created All tab is dropped. Safe to repeat."""
        views = self.call('GET', 'collections/%s/views' % collection).get('data') or []
        noise = {k: None for k in ('type', 'created_date', 'creator', 'last_modified_date', 'last_modified_by',
                                   'lastOpenedDate', 'backlinks', 'tag', 'description')}
        fields = {k: {} for k in ('task_priority', 'task_agent', 'linear_identifier', 'agent_run_count')}
        ops = []
        for view in views:
            if view['name'] == 'Board':
                ops.append({'op': 'update_view', 'view': view['id'], 'columns': {**noise, **fields}})
            elif view['name'] == 'Table':
                ops.append({'op': 'update_view', 'view': view['id'],
                            'columns': {**noise, 'task_status': {}, **fields, 'task_due': {}}})
            elif view['name'] == 'All' and len(views) > 1:
                ops.append({'op': 'delete_view', 'view': view['id']})
        if ops:
            self.call('PATCH', 'objects/' + collection, {'ops': ops})

    def add(self, collection, tasks):
        return self.call('PATCH', 'objects/' + collection, {'ops': [{'op': 'add_items', 'items': list(tasks)}]})

    # ---- tasks --------------------------------------------------------
    def set(self, task, **props):
        return self.call('PATCH', 'objects/%s?create_missing_options=true' % task,
                         {'ops': [{'op': 'set_properties', 'set': props}]})

    def get(self, task):
        return flatten(self.call('GET', 'objects/' + task).get('properties'))

    def body(self, task):
        blocks = self.call('GET', 'objects/' + task).get('blocks') or []
        return '\n'.join(b.get('text', '') for b in blocks if b.get('text')).strip()

    def tasks(self, table, kind='collections'):
        rows = self.call('GET', '%s/%s/objects?limit=200' % (kind, table)).get('data') or []
        return [{'id': row['id'], **self.get(row['id'])} for row in rows]

    def create(self, project, title, plan, agent='codex', priority='Medium', labels=(), collection=None,
               app=None, kind=None):
        props = {'task_project': project, 'task_status': 'Awaiting Approval', 'task_priority': priority,
                 'task_agent': agent, 'task_source': 'anytype', 'task_labels': list(labels), 'agent_run_count': 0}
        if app:
            props['task_app'] = app
        if kind:
            props['task_kind'] = kind
        made = self.call('POST', 'objects?create_missing_options=true', {
            'type': SCHEMA['type']['key'], 'name': titled(title, app, kind), 'template': 'none',
            'markdown': '## Plan\n\n' + plan.strip() + '\n', 'properties': props})
        if collection:
            self.add(collection, [made['id']])
        return made['id']

    def move(self, task, type_key):
        """Re-type a task in place: id, properties and discussion are kept."""
        return self.call('PATCH', 'objects/' + task, {'ops': [{'op': 'set_type', 'type': type_key}]})

    # ---- discussion ---------------------------------------------------
    def thread(self, task):
        return self.call('POST', 'objects/%s/discussion' % task, {})['id']

    def say(self, task, text, ask=False, reply_to=None):
        body = {'text': (ASK if ask else MARK) + ' ' + text}
        if reply_to:
            body['reply_to'] = reply_to
        return self.call('POST', 'chats/%s/messages' % self.thread(task), body)

    def messages(self, task):
        return self.call('GET', 'chats/%s/messages?limit=200' % self.thread(task)).get('messages') or []


def normalize(text):
    for code, emoji in SHORTCODES.items():
        text = text.replace(code, emoji)
    return text.strip()


def verdict_of(text):
    """One owner comment: 'approved' or 'rejected' only when it is nothing but an approval or a rejection
    ("👍", "ok", "lgtm, go ahead", "👎"); anything with more in it is 'feedback'. No phrasing rule decides what a
    reply with content means (owner, MST-60): the orchestrator agent reads it and records the verdict itself
    (`mstack board verdict`)."""
    tokens = [w.strip('.!') for w in text.lower().replace(',', ' ').split() if w]
    if text in REJECT or (tokens and all(t in REJECT for t in tokens)):
        return 'rejected'
    plain = text.lower().strip(' .!')
    if text in APPROVE or plain in APPROVE_WORDS or ONLY_APPROVE.match(plain):
        return 'approved'
    if tokens and all(t in APPROVE_WORDS or t in APPROVE or (t and all(c in ''.join(APPROVE) for c in t))
                      for t in tokens):
        return 'approved'
    return 'feedback'


def decide(messages):
    """Owner's verdict on the latest orchestrator ask in a discussion.

    Returns ('approved'|'rejected'|'feedback'|'pending', owner_text, ask_id). A 👎 reaction rejects; otherwise the
    owner's latest reply after the ask decides when it is a bare approval or rejection (earlier replies travel as
    notes), and any other reply is 'feedback' for the orchestrator to read and judge. With no reply, a 👍 reaction
    approves. Side notes (`board owner --side`) are never read here.
    """
    asks = [m for m in messages if m.get('text', '').startswith(ASK)]
    if not asks:
        return 'pending', '', None
    ask = asks[-1]
    reactions = set((ask.get('reactions') or {}).keys())
    if reactions & REJECT:
        return 'rejected', '', ask['id']
    after = [m for m in messages if m.get('order', '') > ask.get('order', '')
             and not m.get('text', '').startswith((MARK, SIDE))]
    texts = [t for t in (normalize(m.get('text', '')) for m in after) if t]
    if texts:
        last = verdict_of(texts[-1])
        return (last if last in ('approved', 'rejected') else 'feedback'), '\n'.join(texts), ask['id']
    if reactions & APPROVE:
        return 'approved', '', ask['id']
    return 'pending', '', None
