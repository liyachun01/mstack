"""Where the board keeps its state, journals and event queue (design 011, phase 1).

Two backends, picked by `hub.store` in mstack's own `.mstack/stack.json`:
  file      the JSON state file (`.mstack/evidence/taskboard-test.json`) and each private project's
            `.mstack/journal.json`; events live in the state file too. The default.
  postgres  Postgres `mstack_orchestrator` (schema in schema.sql): board_state, journal, queue.
            The JSON files are still written on every change and are the fallback: when Postgres is
            unreachable, reads come from them and a `.pg-dirty` marker is left; the next time Postgres
            answers, the file is pushed back (it is the newer copy) before anything else.

Only the real state file uses Postgres; a test that points the CLI at another state file always gets
the file backend, so tests never touch the database.

Events move new → sent → resolved. `next` hands out new events, and sent ones older than
`hub.resend_minutes`, grouped by the orchestrator session registered for their (board, scope).
"""
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SCHEMA = HERE/'schema.sql'
PG = {'host': 'host.orb.internal', 'port': '55322', 'db': 'mstack_orchestrator', 'user': 'mstack_orchestrator',
      'password_file': HERE.parents[1]/'.secrets/postgres/mstack_orchestrator.password'}
RESEND_MINUTES = 5
LOCAL_ONLY = ('events', 'events_seq', 'events_spool')      # never part of board_state in Postgres
PG_ERRORS = (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError)


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def psql(sql, fetch=False):
    """Run SQL against mstack_orchestrator; with fetch, return the unaligned output."""
    env = dict(os.environ, PGPASSWORD=Path(PG['password_file']).read_text().strip())
    done = subprocess.run(['psql', '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-h', PG['host'], '-p', PG['port'],
                           '-U', PG['user'], '-d', PG['db']], input=sql, text=True, env=env, check=True,
                          capture_output=True, timeout=30)
    return done.stdout if fetch else None


def lit(value):
    """A JSON value as a dollar-quoted jsonb literal (no escaping games)."""
    text = json.dumps(value, ensure_ascii=False)
    tag = '$j%s$' % hashlib.sha256(text.encode()).hexdigest()[:8]
    return '%s%s%s::jsonb' % (tag, text, tag)


def text_lit(value):
    return 'NULL' if value is None else "'%s'" % str(value).replace("'", "''")


def route_key(board, scope=None):
    return '%s/%s' % (board, scope or '')


def warn(message):
    print('mstack store: ' + message, file=sys.stderr, flush=True)


class FileQueue:
    """The event queue kept in a key of the state dict (file backend, or the spool when Postgres is down)."""
    def __init__(self, store, key='events'):
        self.store, self.key = store, key

    def add(self, events):
        ids = []
        with self.store.locked() as s:
            rows = s.setdefault(self.key, [])
            by_key = {r['dedupe']: r for r in rows if r.get('dedupe')}
            for e in events:
                if e.get('dedupe') and e['dedupe'] in by_key:
                    ids.append(by_key[e['dedupe']]['id'])
                    continue
                s['events_seq'] = s.get('events_seq', 0) + 1
                row = {'id': ('local-%d' if self.key == 'events_spool' else '%d') % s['events_seq'],
                       'created_at': now_iso(), 'status': 'new', 'session': None, 'sends': 0, 'sent_at': None,
                       'resolved_at': None, 'resolved_by': None, 'note': None, **e}
                rows.append(row)
                if row.get('dedupe'):
                    by_key[row['dedupe']] = row
                ids.append(row['id'])
            cutoff = time.time() - 7 * 86400                        # resolved events are kept a week
            s[self.key] = [r for r in rows if r['status'] != 'resolved' or stamp(r['resolved_at']) > cutoff]
        return ids

    def take(self, routes, resend, peek=False):
        due, cutoff = [], time.time() - resend * 60
        with self.store.locked() as s:
            for r in s.get(self.key, []):
                if r['status'] == 'new' or r['status'] == 'sent' and stamp(r['sent_at']) < cutoff:
                    session = routes.get(route_key(r['board'], r['scope'])) or routes.get(route_key(r['board']))
                    if session and not peek:
                        r.update(status='sent', session=session, sends=r['sends'] + 1, sent_at=now_iso())
                    due.append(dict(r, session=session))
        return due

    def resolve(self, ids, by, note):
        done = []
        with self.store.locked() as s:
            for r in s.get(self.key, []):
                if str(r['id']) in ids and r['status'] != 'resolved':
                    r.update(status='resolved', resolved_at=now_iso(), resolved_by=by, note=note)
                    done.append(r['id'])
        return done

    def list(self, status=None):
        return [r for r in self.store.read().get(self.key, []) if not status or r['status'] == status]


def stamp(iso):
    if not iso:
        return 0
    return datetime.strptime(iso[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc).timestamp()


class PgQueue:
    """orchestrator.queue in Postgres. Each call is one psql run; next is a single UPDATE … RETURNING."""
    FIELDS = ("id::text AS id, to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') AS created_at, "
              "board, scope, kind, task, issue, dedupe, payload, status, session, sends, "
              "to_char(sent_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') AS sent_at, resolved_by, note")

    def __init__(self, run_sql):
        self.sql = run_sql

    def rows(self, sql):
        out = self.sql(sql, fetch=True) or ''
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    def add(self, events):
        if not events:
            return []
        rows, keys = [], set()
        for e in events:                     # ON CONFLICT can't touch one row twice: one row per dedupe key
            if e.get('dedupe') and e['dedupe'] in keys:
                continue
            keys.add(e.get('dedupe'))
            rows.append({'board': e['board'], 'scope': e.get('scope') or '', 'kind': e['kind'], 'task': e.get('task'),
                         'issue': e.get('issue'), 'dedupe': e.get('dedupe'), 'payload': e.get('payload') or {}})
        found = self.rows(
            "WITH incoming AS (SELECT * FROM jsonb_to_recordset(%s) AS x(board text, scope text, kind text, task text, "
            "issue text, dedupe text, payload jsonb)), ins AS (INSERT INTO orchestrator.queue "
            "(board, scope, kind, task, issue, dedupe, payload) SELECT board, scope, kind, task, issue, dedupe, payload "
            "FROM incoming ON CONFLICT (dedupe) DO UPDATE SET dedupe = EXCLUDED.dedupe RETURNING id, dedupe) "
            "SELECT json_build_object('id', id::text, 'dedupe', dedupe) FROM ins;\n" % lit(rows))
        by_key = {r['dedupe']: r['id'] for r in found if r['dedupe']}
        plain = iter([r['id'] for r in found if not r['dedupe']])
        return [by_key[e['dedupe']] if e.get('dedupe') else next(plain) for e in events]

    def take(self, routes, resend, peek=False):
        due = ("(status = 'new' OR status = 'sent' AND sent_at < now() - make_interval(mins => %d))" % int(resend))
        route = ("(SELECT value #>> '{}' FROM jsonb_each(%s) WHERE key IN (q.board || '/' || q.scope, q.board || '/') "
                 "ORDER BY length(key) DESC LIMIT 1)" % lit(routes))
        if peek:
            return [dict(r, session=r.pop('route')) for r in self.rows(
                "SELECT row_to_json(t) FROM (SELECT %s, %s AS route FROM orchestrator.queue q WHERE %s ORDER BY id) t;\n"
                % (self.FIELDS, route, due))]
        # Mark routable events sent in the same statement that reads them; unroutable ones stay new.
        return self.rows(
            "WITH due AS (SELECT q.id, %s AS route FROM orchestrator.queue q WHERE %s ORDER BY q.id FOR UPDATE SKIP LOCKED), "
            "sent AS (UPDATE orchestrator.queue q SET status = 'sent', session = due.route, sends = q.sends + 1, sent_at = now() "
            "FROM due WHERE q.id = due.id AND due.route IS NOT NULL RETURNING q.id) "
            "SELECT row_to_json(t) FROM (SELECT %s FROM orchestrator.queue q WHERE q.id IN (SELECT id FROM sent)) t "
            "UNION ALL SELECT row_to_json(t) FROM (SELECT %s FROM orchestrator.queue q JOIN due ON due.id = q.id "
            "WHERE due.route IS NULL) t;\n" % (route, due, self.FIELDS, self.FIELDS))

    def resolve(self, ids, by, note):
        numeric = [int(i) for i in ids if str(i).isdigit()]
        local = [str(i) for i in ids if not str(i).isdigit()]          # spooled before Postgres came back
        if not numeric and not local:
            return []
        return [r['id'] for r in self.rows(
            "UPDATE orchestrator.queue SET status = 'resolved', resolved_at = now(), resolved_by = %s, note = %s "
            "WHERE status <> 'resolved' AND (id = ANY(ARRAY[%s]::bigint[]) OR payload->>'local_id' = ANY(ARRAY[%s]::text[])) "
            "RETURNING json_build_object('id', id::text);\n"
            % (text_lit(by), text_lit(note), ','.join(map(str, numeric)), ','.join(text_lit(i) for i in local)))]

    def list(self, status=None):
        where = "WHERE status = %s" % text_lit(status) if status else "WHERE status <> 'resolved' OR resolved_at > now() - interval '1 day'"
        return self.rows("SELECT row_to_json(t) FROM (SELECT %s FROM orchestrator.queue %s ORDER BY id) t;\n"
                         % (self.FIELDS, where))


class Store:
    def __init__(self, path, backend='file', resend=RESEND_MINUTES, run_sql=None):
        self.path, self.backend, self.resend = Path(path), backend, resend
        self.sql = run_sql or psql
        self.dirty = self.path.with_suffix('.pg-dirty')
        self.synced = self.path.with_suffix('.pg-synced')
        self._cache, self._cached_at = None, 0
        self.pg_error = None

    # ---- board state ------------------------------------------------------
    def _file(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def _pg_read(self):
        out = self.sql("SELECT coalesce(jsonb_object_agg(key, value), '{}'::jsonb) FROM orchestrator.board_state;\n",
                       fetch=True)
        return json.loads(out.strip() or '{}')

    def _pg_push(self, data, keys=None, removed=()):
        """Write keys of `data` (all of them when keys is None) and delete `removed`, in one transaction."""
        keys = [k for k in (data if keys is None else keys) if k not in LOCAL_ONLY]
        sql = ['BEGIN;']
        if keys:
            sql.append("INSERT INTO orchestrator.board_state (key, value, updated_at) SELECT key, value, now() "
                       "FROM jsonb_each(%s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now();"
                       % lit({k: data[k] for k in keys}))
        gone = [k for k in removed if k not in LOCAL_ONLY]
        if gone:
            sql.append("DELETE FROM orchestrator.board_state WHERE key IN (%s);" % ', '.join(text_lit(k) for k in gone))
        sql.append('COMMIT;')
        if len(sql) > 2:
            self.sql('\n'.join(sql) + '\n')

    def _needs_sync(self):
        return self.dirty.exists() or not self.synced.exists()

    def _resync(self):
        """The local file is newer (first use, or a write while Postgres was down): push all of it."""
        data = self._file()
        known = self._pg_read()
        self._pg_push(data, removed=[k for k in known if k not in data])
        self._flush_spool(data)
        self.dirty.unlink(missing_ok=True)
        self.synced.touch()

    def _flush_spool(self, data):
        spool = [r for r in data.get('events_spool', []) if r['status'] != 'resolved']
        if not spool:
            return
        PgQueue(self.sql).add([{**r, 'payload': {**(r.get('payload') or {}), 'local_id': r['id']}} for r in spool])
        with self._file_locked() as s:
            s.pop('events_spool', None)

    def _pg_ok(self, action):
        try:
            if self._needs_sync():
                self._resync()
            result = action()
            self.pg_error = None
            return True, result
        except PG_ERRORS as error:
            if self.pg_error is None:
                warn('Postgres unreachable, using %s: %s' % (self.path.name, str(error)[:200]))
            self.pg_error = str(error)[:200]
            return False, None

    def read(self):
        if self.backend != 'postgres':
            return self._file()
        if self._cache is not None and time.time() - self._cached_at < 2:
            return json.loads(json.dumps(self._cache))
        ok, data = self._pg_ok(self._pg_read)
        if not ok:
            return self._file()
        data.update({k: v for k, v in self._file().items() if k in LOCAL_ONLY})
        self._cache, self._cached_at = data, time.time()
        return json.loads(json.dumps(data))

    @contextlib.contextmanager
    def _file_locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_suffix('.lock'), 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = self._file()
            yield data
            self.path.write_text(json.dumps(data, indent=2) + '\n')

    @contextlib.contextmanager
    def locked(self):
        """Read-modify-write under the local lock. Postgres (when used) gets only the keys that changed;
        the file is always written, so it is the fallback copy."""
        if self.backend != 'postgres':
            with self._file_locked() as data:
                yield data
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path.with_suffix('.lock'), 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            ok, data = self._pg_ok(self._pg_read)
            local = self._file()
            data = {**data, **{k: v for k, v in local.items() if k in LOCAL_ONLY}} if ok else local
            before = json.loads(json.dumps(data))
            yield data
            self.path.write_text(json.dumps(data, indent=2) + '\n')
            changed = [k for k in data if k not in before or before[k] != data[k]]
            removed = [k for k in before if k not in data]
            if ok:
                try:
                    self._pg_push(data, changed, removed)
                except PG_ERRORS as error:
                    ok = False
                    warn('Postgres write failed, kept in %s: %s' % (self.path.name, str(error)[:200]))
            if not ok:
                self.dirty.touch()
            self._cache = None

    # ---- events -------------------------------------------------------------
    def queue(self):
        return PgQueue(self.sql) if self.backend == 'postgres' else FileQueue(self)

    def enqueue(self, events):
        """Add events (dedupe keys make repeats return the existing id). Postgres down: spooled locally."""
        if self.backend != 'postgres':
            return FileQueue(self).add(events)
        ok, ids = self._pg_ok(lambda: PgQueue(self.sql).add(events))
        return ids if ok else FileQueue(self, 'events_spool').add(events)

    def _routes(self):
        return {k: v['session'] for k, v in self.read().get('orchestrators', {}).items() if v.get('session')}

    def take(self, peek=False):
        routes = self._routes()
        if self.backend != 'postgres':
            return FileQueue(self).take(routes, self.resend, peek)
        ok, rows = self._pg_ok(lambda: PgQueue(self.sql).take(routes, self.resend, peek))
        if not ok:
            raise RuntimeError('Postgres unreachable (%s); %d event(s) are spooled locally and wait for it. '
                               'Act on the watcher output meanwhile.' % (self.pg_error, len(self.read().get('events_spool', []))))
        return rows

    def resolve(self, ids, by=None, note=None):
        ids = [str(i) for i in ids]
        if self.backend != 'postgres':
            return FileQueue(self).resolve(ids, by, note)
        ok, done = self._pg_ok(lambda: PgQueue(self.sql).resolve(ids, by, note))
        if not ok:
            raise RuntimeError('Postgres unreachable (%s); resolve again once it is back' % self.pg_error)
        return done

    def events(self, status=None):
        if self.backend != 'postgres':
            return FileQueue(self).list(status)
        ok, rows = self._pg_ok(lambda: PgQueue(self.sql).list(status))
        if not ok:
            raise RuntimeError('Postgres unreachable (%s)' % self.pg_error)
        return rows


class PgJournal:
    """orchestrator.journal rows for one project; loaded once per board instance."""
    def __init__(self, project, run_sql):
        self.project, self.sql, self._rows = str(project), run_sql, None

    def comments(self, issue):
        if self._rows is None:
            out = self.sql("SELECT json_build_object('issue', issue, 'id', id, 'body', body, 'createdAt', "
                           "to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.MS\"Z\"'), 'reactionData', reactions) "
                           "FROM orchestrator.journal WHERE project = %s ORDER BY created_at, id;\n" % text_lit(self.project),
                           fetch=True) or ''
            self._rows = {}
            for line in out.splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._rows.setdefault(row.pop('issue'), []).append(row)
        return list(self._rows.get(issue, []))

    def add_all(self, data):
        rows = [{'project': self.project, 'issue': issue, 'id': c['id'], 'body': c['body'], 'created_at': c['createdAt'],
                 'reactions': c.get('reactionData') or []} for issue, comments in data.items() for c in comments]
        if rows:
            self.sql("INSERT INTO orchestrator.journal (id, project, issue, body, created_at, reactions) "
                     "SELECT id, project, issue, body, created_at, reactions FROM jsonb_to_recordset(%s) AS x("
                     "id text, project text, issue text, body text, created_at timestamptz, reactions jsonb) "
                     "ON CONFLICT (id) DO NOTHING;\n" % lit(rows))
        self._rows = None


ACTIVE = None        # the Store the CLI is using; journals follow its backend


def journal_backend(project):
    """PgJournal for a project when the active store is Postgres, else None (file journal only)."""
    if ACTIVE is None or ACTIVE.backend != 'postgres':
        return None
    return PgJournal(Path(project).resolve(), ACTIVE.sql)
