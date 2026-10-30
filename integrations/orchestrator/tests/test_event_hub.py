"""Event hub phase 1 (design 011): the store, the event queue, the orchestrator registry and the hub tick.
Postgres is never reached: the file backend is used, or a fake psql runner."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli
import linear_board
import store
import test_linear_board as flow            # module import: its own tests are not collected twice here


class QueueAndRegistry(unittest.TestCase):
    F = flow.LinearBoardFlow
    setUp, cli, old_issue, auto, tick, scoped = F.setUp, F.cli, F.old_issue, F.auto, F.tick, F.scoped

    def test_tests_never_use_postgres(self):
        self.assertEqual(cli.board_store().backend, 'file')          # STATE is patched: always the plain file

    def test_plan_trigger_becomes_an_event_routed_to_the_registered_session(self):
        self.auto()
        old = self.old_issue()
        self.fake.comment(old, '/plan keep it small')
        need = self.tick()['needs_orchestrator']
        self.assertEqual(need[0]['event'], '1')                       # the watcher output names its event
        out = self.cli('events', 'next')
        self.assertEqual(out['deliver'], [])
        self.assertEqual([(u['route'], u['kind'], u['issue']) for u in out['unrouted']], [('repo/', 'plan', 'MST-500')])
        self.cli('orchestrators', 'register', '--project', str(self.repo), '--session', 'local_orch')
        self.assertEqual([o['session'] for o in self.cli('orchestrators', 'list')['orchestrators']], ['local_orch'])
        out = self.cli('events', 'next')
        group = out['deliver'][0]
        self.assertEqual((group['session'], group['routes']), ('local_orch', ['repo/']))
        self.assertIn('event 1 [plan] MST-500: owner asked for a plan: keep it small', group['message'])
        self.assertIn('events resolve --id <N>', group['message'])
        self.assertEqual(self.cli('events', 'next')['deliver'], [])          # sent: not again until resend time
        cli.board_store().resend = 0
        again = self.cli('events', 'next')['deliver'][0]['events'][0]
        self.assertEqual((again['status'], again['sends']), ('sent', 2))
        self.assertEqual(self.cli('events', 'resolve', '--id', '1', '--note', 'planned')['resolved'], ['1'])
        self.assertEqual(self.cli('events', 'next')['deliver'], [])          # resolved: never again
        self.assertEqual(self.cli('events', 'list', '--status', 'resolved')['events'][0]['note'], 'planned')

    def test_scopes_route_to_their_own_sessions_and_a_handoff_is_one_event(self):
        self.scoped(**{'api': {'apps': ['*'], 'focus': ['MST-1']}, 'web': {'apps': ['*'], 'focus': ['MST-2']}})
        a = self.cli('plan', '--project', 'repo', '--scope', 'api', '--title', 'A', '--agent', 'claude-desktop',
                     '--plan', '-', stdin='p')['task']
        b = self.cli('plan', '--project', 'repo', '--scope', 'web', '--title', 'B', '--agent', 'claude-desktop',
                     '--plan', '-', stdin='p')['task']
        self.cli('orchestrators', 'register', '--project', 'repo', '--scope', 'api', '--session', 'local_api')
        self.cli('orchestrators', 'register', '--project', 'repo', '--scope', 'web', '--session', 'local_web')
        self.fake.comment(a, '👍'); self.fake.comment(b, '👍')
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9):
            hub = self.cli('tick', '--hub')
            self.cli('tick', '--hub')                                          # handoffs repeat; events do not
        self.assertEqual(sorted(v['now'] for v in hub['verdicts']), ['Todo', 'Todo'])
        out = self.cli('events', 'next')
        got = {g['session']: sorted(e['kind'] for e in g['events']) for g in out['deliver']}
        self.assertEqual(got, {'local_api': ['handoff', 'verdict'], 'local_web': ['handoff', 'verdict']})
        self.assertEqual(out['unrouted'], [])

    def test_verdicts_are_delivered_once_and_never_resent(self):
        self.scoped(**{'api': {'apps': ['*'], 'focus': ['MST-1']}})
        a = self.cli('plan', '--project', 'repo', '--scope', 'api', '--title', 'A', '--agent', 'claude-desktop',
                     '--plan', '-', stdin='p')['task']
        self.cli('orchestrators', 'register', '--project', 'repo', '--scope', 'api', '--session', 'local_api')
        self.fake.comment(a, '👍')
        with patch.object(cli, 'LINEAR_EVERY', 0), patch.object(cli, 'MIRROR_EVERY', 10 ** 9):
            self.cli('tick', '--hub')
        self.cli('events', 'next')
        cli.board_store().resend = 0
        again = [e['kind'] for g in self.cli('events', 'next')['deliver'] for e in g['events']]
        self.assertEqual(again, ['handoff'])                               # the verdict was information only

    def test_register_checks_the_scope_and_replaces_the_session(self):
        with self.assertRaises(AssertionError):                          # main() returns 1: unknown scope
            self.cli('orchestrators', 'register', '--project', 'repo', '--scope', 'nope', '--session', 's')
        self.cli('orchestrators', 'register', '--project', 'repo', '--session', 'local_a')
        out = self.cli('orchestrators', 'register', '--project', 'repo', '--session', 'local_b')
        self.assertEqual(out['replaced'], 'local_a')
        self.assertEqual(self.cli('orchestrators', 'remove', '--project', 'repo')['removed']['session'], 'local_b')

    def test_hub_watch_exits_when_events_wait(self):
        self.auto()
        self.cli('orchestrators', 'register', '--project', 'repo', '--session', 'local_orch')
        self.fake.comment(self.old_issue(), '/plan')
        with patch.object(cli, 'LINEAR_EVERY', 0):
            out = self.cli('watch', '--hub', '--max-ticks', '1')
        self.assertEqual(out['events_waiting'], 1)
        self.cli('events', 'next')
        with patch.object(cli, 'LINEAR_EVERY', 0):
            self.assertEqual(self.cli('watch', '--hub', '--max-ticks', '1'), {'stopped': 'max ticks reached'})


class FakePg:
    """Enough of orchestrator.board_state / queue / journal to drive Store's SQL; `down` makes it fail."""
    def __init__(self):
        self.state, self.queue, self.journal, self.down, self.calls = {}, [], {}, False, []

    @staticmethod
    def literal(sql):
        found = re.search(r'\$(j[0-9a-f]{8})\$(.*?)\$\1\$', sql, re.S)
        return json.loads(found.group(2)) if found else None

    def __call__(self, sql, fetch=False):
        self.calls.append(sql)
        if self.down:
            raise subprocess.CalledProcessError(2, 'psql', stderr='connection refused')
        if 'jsonb_object_agg' in sql:
            return json.dumps(self.state)
        if 'INSERT INTO orchestrator.board_state' in sql:
            self.state.update(self.literal(sql))
        if 'DELETE FROM orchestrator.board_state' in sql:
            for key in re.findall(r"'([^']+)'", sql.split('DELETE FROM orchestrator.board_state')[1]):
                self.state.pop(key, None)
        if 'INSERT INTO orchestrator.queue' in sql:
            out = []
            for row in self.literal(sql):
                self.queue.append(row)
                out.append(json.dumps({'id': str(len(self.queue)), 'dedupe': row['dedupe']}))
            return '\n'.join(out)
        if 'INSERT INTO orchestrator.journal' in sql:
            for row in self.literal(sql):
                self.journal.setdefault(row['id'], row)
        if 'FROM orchestrator.journal' in sql:
            return '\n'.join(json.dumps({'issue': r['issue'], 'id': r['id'], 'body': r['body'],
                                         'createdAt': r['created_at'], 'reactionData': r['reactions']})
                             for r in self.journal.values())
        return ''


class PostgresFallback(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.pg = FakePg()
        self.store = store.Store(self.dir/'state.json', 'postgres', run_sql=self.pg)
        p = patch.object(store, 'ACTIVE', self.store); p.start(); self.addCleanup(p.stop)

    def test_first_use_pushes_the_file_then_postgres_is_the_store(self):
        (self.dir/'state.json').write_text(json.dumps({'tables': {'repo': {'path': '/r'}}, 'runs': {}}))
        self.assertEqual(self.store.read()['tables'], {'repo': {'path': '/r'}})
        self.assertEqual(self.pg.state['tables'], {'repo': {'path': '/r'}})
        with self.store.locked() as s:
            s['runs']['t1'] = {'table': 'repo'}
        self.assertEqual(self.pg.state['runs'], {'t1': {'table': 'repo'}})
        self.assertNotIn('"tables"', self.pg.calls[-1])                     # only changed keys are written
        self.assertEqual(json.loads((self.dir/'state.json').read_text())['runs'], {'t1': {'table': 'repo'}})

    def test_postgres_down_uses_the_file_and_catches_up_later(self):
        self.store.read()
        self.pg.down = True
        with self.store.locked() as s:
            s['attention_seen'] = ['trigger:c1']
        self.assertTrue(self.store.dirty.exists())
        self.store._cache = None
        self.assertEqual(self.store.read()['attention_seen'], ['trigger:c1'])   # from the file
        ids = self.store.enqueue([{'board': 'repo', 'scope': '', 'kind': 'plan', 'dedupe': 'k1', 'payload': {}}])
        self.assertEqual(ids, ['local-1'])                                     # spooled locally
        with self.assertRaises(RuntimeError):
            self.store.take()                                                   # the hub is told why
        self.pg.down = False
        self.store._cache = None
        self.assertEqual(self.store.read()['attention_seen'], ['trigger:c1'])
        self.assertEqual(self.pg.state['attention_seen'], ['trigger:c1'])      # pushed back
        self.assertFalse(self.store.dirty.exists())
        self.assertEqual([(q['dedupe'], q['payload']['local_id']) for q in self.pg.queue], [('k1', 'local-1')])
        self.assertNotIn('events_spool', json.loads((self.dir/'state.json').read_text()))

    def test_private_journal_lives_in_postgres_with_the_file_as_fallback(self):
        project = self.dir/'proj'
        journal = linear_board.Journal(project)
        journal.add('issue-1', 'first')
        self.assertEqual([r['body'] for r in self.pg.journal.values()], ['first'])
        self.assertEqual([c['body'] for c in linear_board.Journal(project).comments('issue-1')], ['first'])
        self.pg.down = True
        down = linear_board.Journal(project)
        down.add('issue-1', 'second')                                           # still recorded in the file
        self.assertEqual([c['body'] for c in down.comments('issue-1')], ['first', 'second'])
        self.pg.down = False
        self.assertEqual([c['body'] for c in linear_board.Journal(project).comments('issue-1')], ['first', 'second'])
        self.assertEqual(len(self.pg.journal), 2)                              # caught up

    def test_catching_up_inside_a_write_does_not_wait_on_its_own_lock(self):
        self.store.read()
        self.pg.down = True
        self.store.enqueue([{'board': 'repo', 'scope': '', 'kind': 'plan', 'dedupe': 'k1', 'payload': {}}])
        self.pg.down = False
        done = []
        def write():                         # the spool flush runs inside locked(): used to flock twice and hang
            with self.store.locked() as s:
                s['attention_seen'] = ['x']
            done.append(True)
        import threading
        t = threading.Thread(target=write, daemon=True); t.start(); t.join(5)
        self.assertEqual(done, [True])
        self.assertEqual([q['dedupe'] for q in self.pg.queue], ['k1'])
        self.assertEqual(self.pg.state['attention_seen'], ['x'])

    def test_a_missing_state_file_is_restored_from_postgres_not_pushed_over_it(self):
        self.pg.state = {'tables': {'repo': {'path': '/r'}}}
        self.assertEqual(self.store.read()['tables'], {'repo': {'path': '/r'}})
        self.assertEqual(self.pg.state, {'tables': {'repo': {'path': '/r'}}})
        self.assertEqual(json.loads((self.dir/'state.json').read_text())['tables'], {'repo': {'path': '/r'}})

    def test_schema_covers_every_table_the_store_uses(self):
        sql = store.SCHEMA.read_text()
        for table in ('board_state', 'journal', 'queue', 'issues'):
            self.assertIn('CREATE TABLE IF NOT EXISTS orchestrator.%s' % table, sql)


if __name__ == '__main__':
    unittest.main()
