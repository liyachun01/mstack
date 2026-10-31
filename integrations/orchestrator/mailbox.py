"""The hub queue as a mailbox, plus the conductor's agent, turn and action records (design 016 §2, 017 M1).

Two implementations with one interface:
  PgMailbox      orchestrator.queue / agents / turns / actions in mstack_orchestrator (schema.sql).
                 Works read-only on the pre-mailbox schema too (recipient derived, no agents table), so
                 `conductor run --dry-run --peek` can read the live queue before the migration is applied.
  MemoryMailbox  the same in dicts, for tests and dry runs that replay rows.

Addresses: orch:<board>[/<scope>], worker:<ISSUE>, owner, dock. A queue row without a recipient (written by the
hub tick before the migration) belongs to orch:<board>[/<scope>].
"""
from datetime import datetime, timezone
import json
import time

import store

URGENT = ('stop', 'owner_message')            # never wait for a batch to fill
INFO_ONLY = ('verdict',)                      # resolved in code once delivered (011)
OWNER = 'owner'


def address(board, scope=None):
    return 'orch:%s/%s' % (board, scope) if scope else 'orch:%s' % board


def recipient_of(row):
    return row.get('recipient') or address(row['board'], row.get('scope'))


def epoch(stamp):
    return datetime.strptime(stamp[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc).timestamp()


def age_seconds(row, now=None):
    created = row.get('created_at')
    return (now or time.time()) - epoch(created) if created else 0


def iso(ts=None):
    return datetime.fromtimestamp(ts or time.time(), timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


AGENT_DEFAULT = {'state': 'idle', 'mode': 'shadow', 'cursor': {}, 'turns_day': 0, 'failures': 0, 'day': None,
                 'playbook_hash': None, 'session': None, 'last_wake': None, 'last_result': None}


class MemoryMailbox:
    upgraded = True

    def __init__(self, rows=()):
        self.rows, self.agents, self.turns, self.actions, self.seq = [], {}, {}, {}, 0
        for r in rows:
            self.post([r])

    # ---- mail -----------------------------------------------------------
    def post(self, mails):
        ids = []
        for m in mails:
            dup = next((r for r in self.rows if m.get('dedupe') and r.get('dedupe') == m['dedupe']), None)
            if dup:
                ids.append(dup['id'])
                continue
            self.seq += 1
            row = {'id': str(m.get('id') or self.seq), 'created_at': iso(), 'board': '', 'scope': '', 'task': None,
                   'issue': None, 'dedupe': None, 'payload': {}, 'status': 'new', 'session': None, 'sends': 0,
                   'sent_at': None, 'recipient': None, 'sender': None, 'turn': None, 'attempts': 0, **m}
            row['id'] = str(row['id'])
            self.rows.append(row)
            ids.append(row['id'])
        return ids

    def pending(self, addresses, resend_minutes=5):
        cutoff = time.time() - resend_minutes * 60
        out = []
        for r in self.rows:
            if recipient_of(r) not in addresses:
                continue
            stale = r['status'] == 'sent' and (r.get('sent_at_ts') or 0) < cutoff
            if r['status'] == 'new' or stale:
                out.append(dict(r, recipient=recipient_of(r)))
        return sorted(out, key=lambda r: int(r['id']) if r['id'].isdigit() else 0)

    def recent(self, limit=20, status='resolved'):
        rows = [dict(r, recipient=recipient_of(r)) for r in self.rows if r['status'] == status]
        return rows[-limit:]

    def _by_id(self, ids):
        ids = {str(i) for i in ids}
        return [r for r in self.rows if r['id'] in ids]

    def take(self, ids, turn, session=None):
        got = []
        for r in self._by_id(ids):
            if r['status'] in ('new', 'sent'):
                r.update(status='sent', turn=turn, session=session, sends=r['sends'] + 1, sent_at=iso(),
                         sent_at_ts=time.time())
                got.append(r['id'])
        return got

    def resolve(self, ids, by, note=None):
        done = []
        for r in self._by_id(ids):
            if r['status'] != 'resolved':
                r.update(status='resolved', resolved_by=by, note=note, turn=None)
                done.append(r['id'])
        return done

    def requeue(self, ids, note=None):
        for r in self._by_id(ids):
            if r['status'] == 'sent':
                r.update(status='new', turn=None, attempts=r['attempts'] + 1, note=note)

    # ---- agents, turns, actions ----------------------------------------------
    def agent(self, addr):
        return {**AGENT_DEFAULT, 'address': addr, **self.agents.get(addr, {})}

    def save_agent(self, addr, **fields):
        self.agents.setdefault(addr, {}).update(fields)

    def turn_start(self, turn):
        self.turns[turn['id']] = dict(turn, status='running')

    def turn_end(self, turn_id, **fields):
        self.turns[turn_id].update(fields)

    def claim_action(self, key, turn, addr, action):
        """'new' when this call recorded it (the caller runs it), else the status already recorded."""
        if key in self.actions:
            return self.actions[key]['status']
        self.actions[key] = {'key': key, 'turn': turn, 'address': addr, 'action': action, 'status': 'running'}
        return 'new'

    def finish_action(self, key, status, result=None, reason=None):
        self.actions[key].update(status=status, result=result, reason=reason)


class PgMailbox:
    """The same over psql. Each method is one statement, so a crash leaves a consistent row set."""
    FIELDS = store.PgQueue.FIELDS

    def __init__(self, run_sql=None, schema='orchestrator'):
        self.sql, self.schema = run_sql or store.psql, schema
        self._upgraded = None

    def q(self, text):
        return text.replace('orchestrator.', self.schema + '.')

    def rows(self, text):
        out = self.sql(self.q(text), fetch=True) or ''
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    @property
    def upgraded(self):
        """The mailbox migration is applied (recipient column and agents table exist)."""
        if self._upgraded is None:
            out = self.sql("SELECT count(*) FROM information_schema.columns WHERE table_schema = %s AND "
                           "((table_name = 'queue' AND column_name = 'recipient') OR table_name = 'agents' AND "
                           "column_name = 'address');\n" % store.text_lit(self.schema), fetch=True)
            self._upgraded = (out or '').strip() == '2'
        return self._upgraded

    def _fields(self):
        extra = ", recipient, sender, turn, attempts" if self.upgraded else ""
        return self.FIELDS + extra

    def post(self, mails):
        if not self.upgraded:
            raise RuntimeError('the mailbox migration is not applied yet (mstack events schema --apply)')
        rows = [{'board': m.get('board') or '', 'scope': m.get('scope') or '', 'kind': m['kind'], 'task': m.get('task'),
                 'issue': m.get('issue'), 'dedupe': m.get('dedupe'), 'payload': m.get('payload') or {},
                 'recipient': m['recipient'], 'sender': m.get('sender')} for m in mails]
        if not rows:
            return []
        return [r['id'] for r in self.rows(
            "WITH incoming AS (SELECT * FROM jsonb_to_recordset(%s) AS x(board text, scope text, kind text, task text, "
            "issue text, dedupe text, payload jsonb, recipient text, sender text)), ins AS (INSERT INTO orchestrator.queue "
            "(board, scope, kind, task, issue, dedupe, payload, recipient, sender) SELECT board, scope, kind, task, issue, "
            "dedupe, payload, recipient, sender FROM incoming ON CONFLICT (dedupe) DO UPDATE SET dedupe = EXCLUDED.dedupe "
            "RETURNING id) SELECT json_build_object('id', id::text) FROM ins;\n" % store.lit(rows))]

    def _recipient_sql(self):
        derived = "CASE WHEN scope = '' THEN 'orch:' || board ELSE 'orch:' || board || '/' || scope END"
        return "coalesce(recipient, %s)" % derived if self.upgraded else derived

    def pending(self, addresses, resend_minutes=5):
        if not addresses:
            return []
        rcpt = self._recipient_sql()
        return normalise(self.rows(
            "SELECT row_to_json(t) FROM (SELECT %s, %s AS recipient_addr FROM orchestrator.queue WHERE "
            "(status = 'new' OR status = 'sent' AND sent_at < now() - make_interval(mins => %d)) AND %s = ANY(%s) "
            "ORDER BY id) t;\n" % (self._fields(), rcpt, int(resend_minutes), rcpt, self._array(addresses))))

    def recent(self, limit=20, status='resolved'):
        return normalise(self.rows("SELECT row_to_json(t) FROM (SELECT * FROM (SELECT %s, %s AS recipient_addr FROM orchestrator.queue "
                         "WHERE status = %s ORDER BY id DESC LIMIT %d) r ORDER BY id::bigint) t;\n"
                         % (self._fields(), self._recipient_sql(), store.text_lit(status), int(limit))))

    @staticmethod
    def _array(values):
        return 'ARRAY[%s]::text[]' % ','.join(store.text_lit(v) for v in values)

    @staticmethod
    def _sorted(rows):
        return sorted((r['id'] for r in rows), key=int)

    @staticmethod
    def _ids(ids):
        return 'ARRAY[%s]::bigint[]' % ','.join(str(int(i)) for i in ids if str(i).isdigit())

    def take(self, ids, turn, session=None):
        return self._sorted(self.rows(
            "UPDATE orchestrator.queue SET status = 'sent', turn = %s, session = %s, sends = sends + 1, sent_at = now() "
            "WHERE id = ANY(%s) AND status IN ('new', 'sent') RETURNING json_build_object('id', id::text);\n"
            % (store.text_lit(turn), store.text_lit(session), self._ids(ids))))

    def resolve(self, ids, by, note=None):
        return self._sorted(self.rows(
            "UPDATE orchestrator.queue SET status = 'resolved', resolved_at = now(), resolved_by = %s, note = %s, turn = NULL "
            "WHERE id = ANY(%s) AND status <> 'resolved' RETURNING json_build_object('id', id::text);\n"
            % (store.text_lit(by), store.text_lit(note), self._ids(ids))))

    def requeue(self, ids, note=None):
        self.sql(self.q("UPDATE orchestrator.queue SET status = 'new', turn = NULL, attempts = attempts + 1, note = %s "
                        "WHERE id = ANY(%s) AND status = 'sent';\n" % (store.text_lit(note), self._ids(ids))))

    def agent(self, addr):
        if not self.upgraded:
            return dict(AGENT_DEFAULT, address=addr)
        found = self.rows("SELECT row_to_json(a) FROM orchestrator.agents a WHERE address = %s;\n" % store.text_lit(addr))
        return {**AGENT_DEFAULT, 'address': addr, **{k: v for k, v in (found[0] if found else {}).items() if v is not None}}

    def save_agent(self, addr, **fields):
        """Update the fields given; a new address is inserted (role and harness default when not given)."""
        types = {'cursor': 'jsonb', 'turns_day': 'integer', 'failures': 'integer', 'day': 'date',
                 'last_wake': 'timestamptz'}
        new = {'role': 'orchestrator', 'harness': 'unknown', **fields, 'address': addr}
        cols = list(new)
        sets = ', '.join('%s = x.%s' % (c, c) for c in fields) or 'address = x.address'
        self.sql(self.q(
            "WITH x AS (SELECT * FROM jsonb_to_record(%s) AS x(%s)), up AS (UPDATE orchestrator.agents a SET %s, "
            "updated_at = now() FROM x WHERE a.address = x.address RETURNING 1) INSERT INTO orchestrator.agents (%s) "
            "SELECT %s FROM x WHERE NOT EXISTS (SELECT 1 FROM up) ON CONFLICT (address) DO NOTHING;\n" % (
                store.lit(new), ', '.join('%s %s' % (c, types.get(c, 'text')) for c in cols), sets,
                ', '.join(cols), ', '.join(cols))))

    def turn_start(self, turn):
        self.sql(self.q("INSERT INTO orchestrator.turns (id, address, events, attempt, status, sent_ref) VALUES "
                        "(%s, %s, %s, %d, 'running', %s) ON CONFLICT (id) DO NOTHING;\n" % (
                            store.text_lit(turn['id']), store.text_lit(turn['address']), self._ids(turn['events']),
                            int(turn.get('attempt', 1)), store.text_lit(turn.get('sent_ref')))))

    def turn_end(self, turn_id, **fields):
        sets = ', '.join('%s = %s' % (k, store.text_lit(v)) for k, v in fields.items())
        self.sql(self.q("UPDATE orchestrator.turns SET %s, ended_at = now() WHERE id = %s;\n"
                        % (sets, store.text_lit(turn_id))))

    def claim_action(self, key, turn, addr, action):
        got = self.rows(
            "WITH ins AS (INSERT INTO orchestrator.actions (key, turn, address, action, status) VALUES (%s, %s, %s, %s, "
            "'running') ON CONFLICT (key) DO NOTHING RETURNING key) SELECT json_build_object('status', 'new') FROM ins "
            "UNION ALL SELECT json_build_object('status', status) FROM orchestrator.actions WHERE key = %s AND NOT EXISTS "
            "(SELECT 1 FROM ins);\n" % (store.text_lit(key), store.text_lit(turn), store.text_lit(addr), store.lit(action),
                                         store.text_lit(key)))
        return got[0]['status'] if got else 'new'

    def finish_action(self, key, status, result=None, reason=None):
        self.sql(self.q("UPDATE orchestrator.actions SET status = %s, result = %s, reason = %s, done_at = now() "
                        "WHERE key = %s;\n" % (store.text_lit(status), store.lit(result), store.text_lit(reason),
                                               store.text_lit(key))))


def normalise(rows):
    """PgMailbox rows carry recipient_addr; give every row a `recipient`."""
    for r in rows:
        r['recipient'] = r.pop('recipient_addr', None) or recipient_of(r)
    return rows
