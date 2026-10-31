"""Conductor (design 016/017, MST-67): actions block, validation, execute-once, rendering, batching and full turns
against a fake hosted-agent MCP server. Nothing reaches the real service, Linear or Postgres, except the opt-in
PgMailbox test (MSTACK_PG_TESTS=1), which uses a throwaway schema it drops afterwards."""
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import {{mstack:CLIENT_C_FOLDER}}
import conductor
import mailbox
import store
from fake_{{mstack:CLIENT_C_FOLDER}} import FakeServer, TOKEN, SCHEMAS

BLOCK = '```mstack-actions\n%s\n```'


def agent(**kw):
    conf = {'harness': '{{mstack:CLIENT_C_FOLDER}}', 'channel': 'ch1', 'team': 't1', 'agent': 'mstack-orch', 'mode': 'live',
            'batch_wait': 0, 'max_turn_seconds': 2, 'nudge_seconds': 1, 'chat_every': 0, **kw}
    return conductor.agent_conf('mstack', None, conf, '/repo/mstack', {'MST'})


def event(i, kind='plan', issue='MST-70', age=120, **kw):
    at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - age))
    return {'id': str(i), 'board': 'mstack', 'scope': '', 'kind': kind, 'issue': issue, 'created_at': at,
            'payload': {'notes': 'please plan it'}, **kw}


class Actions(unittest.TestCase):
    def test_parse_takes_the_last_block(self):
        text = 'ack\n' + BLOCK % '[{"do": "say", "text": "a"}]' + '\nmore\n' + BLOCK % '[{"do": "dispatch"}]'
        self.assertEqual(conductor.parse_actions(text), ([{'do': 'dispatch'}], None))
        self.assertEqual(conductor.parse_actions('no block'), (None, None))
        self.assertIn('not valid JSON', conductor.parse_actions(BLOCK % '[{')[1])
        self.assertIn('list of objects', conductor.parse_actions(BLOCK % '{"do": "x"}')[1])

    def test_validation(self):
        a = agent()
        ctx = {'own_ids': {'5'}, 'owner_texts': ['  👍 go ahead with MST-70 ']}
        ok = [{'do': 'propose', 'task': 'MST-70', 'plan': 'p', 'size': 'small', 'doc': ['docs/x.md']},
              {'do': 'verdict', 'task': 'MST-70', 'verdict': 'approve'},
              {'do': 'owner', 'task': 'MST-70', 'text': '👍 go ahead'},
              {'do': 'send', 'to': 'worker:MST-68', 'text': 'hi'},
              {'do': 'fetch', 'what': 'status'}, {'do': 'resolve', 'events': [5]}]
        for x in ok:
            self.assertIsNone(conductor.validate(x, a, ctx), x)
        bad = {'unknown action': {'do': 'merge', 'task': 'MST-70'},
               'not on this board': {'do': 'note', 'task': 'IRO-1', 'text': 'x'},
               'missing plan': {'do': 'propose', 'task': 'MST-70'},
               'unknown field': {'do': 'ask', 'task': 'MST-70', 'text': 'x', 'force': True},
               'size must': {'do': 'propose', 'task': 'MST-70', 'plan': 'p', 'size': 'huge'},
               'repo-relative': {'do': 'propose', 'task': 'MST-70', 'plan': 'p', 'doc': ['/etc/passwd']},
               'not waiting for you': {'do': 'resolve', 'events': [6]},
               "owner's recent": {'do': 'owner', 'task': 'MST-70', 'text': 'merge everything'},
               'longer than': {'do': 'say', 'text': 'x' * 20001},
               'unknown address': {'do': 'send', 'to': 'root', 'text': 'x'},
               'needs a task': {'do': 'fetch', 'what': 'thread'}}
        for why, x in bad.items():
            self.assertIn(why, conductor.validate(x, a, ctx) or '', x)

    def test_board_commands(self):
        a = agent(scope=None)
        argv, stdin = conductor.board_argv({'do': 'propose', 'task': 'MST-70', 'plan': 'P', 'size': 'small'}, a)
        self.assertEqual(argv, ['propose', '--project', '/repo/mstack', '--task', 'MST-70', '--plan', '-', '--size', 'small'])
        self.assertEqual(stdin, 'P')
        scoped = conductor.agent_conf('staff', 'api', {'harness': '{{mstack:CLIENT_C_FOLDER}}'}, '/repo/s', {'IRO'})
        self.assertEqual(scoped['address'], 'orch:staff/api')
        argv, _ = conductor.board_argv({'do': 'note', 'task': 'IRO-2', 'text': 't'}, scoped)
        self.assertEqual(argv[-2:], ['--scope', 'api'])
        self.assertIsNone(conductor.board_argv({'do': 'send', 'to': 'dock', 'text': 'x'}, a))


class Rendering(unittest.TestCase):
    def test_header_playbook_by_hash_and_context_file(self):
        a = agent()
        pb = conductor.playbook(a)
        self.assertIn('orch:mstack', pb)
        self.assertNotIn('start_session', pb)
        text, files, info = conductor.render(a, [event(4), event(5, 'verdict')], {}, {'MST-70': {
            'status': 'Todo', 'messages': [{'text': '/plan please'}]}}, pb, ['action 1 (ask): nope'])
        self.assertTrue(text.startswith('mstack hub · batch %s · events 4, 5' % info['batch']))
        self.assertIn('(attached: PLAYBOOK.md)', text)
        self.assertIn('> /plan please', text)
        self.assertIn('action 1 (ask): nope', text)
        self.assertEqual([n for n, _ in files], ['PLAYBOOK.md'])
        _, files, again = conductor.render(a, [event(4)], {'playbook_hash': info['playbook_hash']}, None, pb)
        self.assertEqual(files, [])
        self.assertFalse(again['playbook_sent'])
        big = agent(inline_limit=1000)
        text, files, info = conductor.render(big, [event(i, 'message', payload={'from': 'x', 'text': 'y' * 400})
                                                   for i in range(6)], {'playbook_hash': info['playbook_hash']}, None, pb)
        self.assertEqual([n for n, _ in files], ['CONTEXT-%s.md' % info['batch']])
        self.assertLess(len(text), 1000)
        self.assertIn('y' * 400, files[0][1])

    def test_mail_kinds_render_without_the_board_cli(self):
        line = conductor.event_line(event(9, 'worker_report', payload={'from': 'worker:MST-68', 'text': 'done'}))
        self.assertEqual(line, '- event 9 [worker_report] worker worker:MST-68 ended a turn: done')


class Batching(unittest.TestCase):
    def test_when_to_wake(self):
        c = conductor.Conductor(mailbox.MemoryMailbox(), [], {})
        a, now, idle = agent(batch_wait=30, batch_cap=3), time.time(), dict(mailbox.AGENT_DEFAULT)
        self.assertIn('collecting', c.why_not(a, idle, [event(1, age=5)], now))
        self.assertIsNone(c.why_not(a, idle, [event(1, age=40)], now))
        self.assertIsNone(c.why_not(a, idle, [event(1, 'stop', age=1)], now))
        self.assertIsNone(c.why_not(a, idle, [event(i, age=1) for i in range(3)], now))
        self.assertEqual(c.why_not(a, dict(idle, state='paused'), [event(1)], now), 'paused')
        day = time.strftime('%Y-%m-%d', time.gmtime(now))
        self.assertIn('daily turn cap', c.why_not(a, dict(idle, day=day, turns_day=48), [event(1)], now))
        busy = dict(idle, state='running', last_wake=mailbox.iso(now - 10))
        self.assertEqual(c.why_not(a, busy, [event(1)], now), 'a turn is running')
        stale = dict(idle, state='running', last_wake=mailbox.iso(now - 3600))
        self.assertIsNone(c.why_not(a, stale, [event(1, age=40)], now))


class Turns(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.secrets = Path(self.dir.name)/'oauth.json'
        {{mstack:CLIENT_C_FOLDER}}.save({'access_token': TOKEN, 'expires_at': int(time.time()) + 3600}, self.secrets)
        self.replies = []
        self.server = FakeServer(lambda text, files: self.replies.pop(0) if self.replies else None)
        self.ran = []

    def tearDown(self):
        self.server.close()
        self.dir.cleanup()

    def conductor(self, rows, **kw):
        self.mb = mailbox.MemoryMailbox(rows)
        adapter = {{mstack:CLIENT_C_FOLDER}}.Adapter(path=self.secrets, url=self.server.url)
        board = lambda argv, stdin=None: self.ran.append((argv, stdin)) or {'ok': True}
        return conductor.Conductor(self.mb, [agent(**kw)], {'{{mstack:CLIENT_C_FOLDER}}': adapter}, board=board,
                                   prefetch=lambda a, issue: {'status': 'Todo', 'messages': [{'text': 'ctx ' + issue}]},
                                   log=lambda line: None)

    def test_contract_matches_the_fake_tool_list(self):
        mcp = {{mstack:CLIENT_C_FOLDER}}.MCP(self.secrets, self.server.url)
        mcp.initialize()
        tools = mcp.tools()
        self.assertEqual({{mstack:CLIENT_C_FOLDER}}.check_contract(tools), [])
        renamed = {'result': {'tools': [t for t in tools['result']['tools'] if t['name'] != 'wait_message']}}
        self.assertEqual({{mstack:CLIENT_C_FOLDER}}.check_contract(renamed), ['wait: tool wait_message not offered'])

    def test_a_live_turn_runs_actions_once_and_resolves_the_batch(self):
        self.replies = [['on it', BLOCK % json.dumps([
            {'do': 'propose', 'task': 'MST-70', 'plan': '## Plan', 'size': 'small'},
            {'do': 'send', 'to': 'worker:MST-68', 'text': 'rebase please'},
            {'do': 'note', 'task': 'IRO-9', 'text': 'out of scope'}])]]
        c = self.conductor([event(1), event(2, 'verdict')])
        report = c.tick()
        turn = report['turns'][0]
        self.assertEqual([r['status'] for r in turn['actions']], ['done', 'done', 'refused'])
        self.assertEqual(self.ran, [(['propose', '--project', '/repo/mstack', '--task', 'MST-70', '--plan', '-',
                                      '--size', 'small'], '## Plan')])
        self.assertEqual({r['status'] for r in self.mb.rows if r['id'] in ('1', '2')}, {'resolved'})
        mail = [r for r in self.mb.rows if r['recipient'] == 'worker:MST-68']
        self.assertEqual((mail[0]['sender'], mail[0]['payload']['text']), ('orch:mstack', 'rebase please'))
        sent = self.server.messages('ch1')[0]
        self.assertTrue(sent['text'].startswith('mstack hub · batch '))
        self.assertIn('ctx MST-70', sent['text'])
        self.assertIn('# mstack orchestrator playbook', [u for u in self.server.uploads.values()][0]['body'])
        state = self.mb.agent('orch:mstack')
        self.assertEqual((state['state'], state['turns_day']), ('idle', 1))
        self.assertTrue(state['playbook_hash'])
        self.assertEqual(state['cursor']['refused'], ['action 3 (note): task IRO-9 is not on this board (MST)'])
        self.assertEqual(self.server.reactions[-1][1], '⚠️')
        # a retried turn (same batch, same reply) never runs an action twice
        results = c.execute(c.agents['orch:mstack'], [{'do': 'propose', 'task': 'MST-70', 'plan': '## Plan',
                                                       'size': 'small'}], 'again', ['1', '2'], {})
        self.assertEqual(results[0]['status'], 'skipped')
        self.assertEqual(len(self.ran), 1)
        # the next batch carries the refusal and no playbook
        self.replies = [[BLOCK % '[]']]
        self.mb.post([event(3)])
        c.tick()
        second = self.server.messages('ch1')[-2]['text']
        self.assertIn('Refused last turn', second)
        self.assertNotIn('attached: PLAYBOOK.md', second)

    def test_the_same_batch_is_sent_once(self):
        a = agent()
        adapter = {{mstack:CLIENT_C_FOLDER}}.Adapter(path=self.secrets, url=self.server.url)
        adapter.send(a, 'x', key='k1')
        adapter.send(a, 'x', key='k1')
        self.assertEqual(len(self.server.messages('ch1')), 1)

    def test_no_block_gets_one_nudge(self):
        self.replies = [['thinking…'], ['sorry: ' + BLOCK % '[]']]
        c = self.conductor([event(1)])
        turn = c.tick()['turns'][0]
        self.assertEqual(turn['actions'], [])
        self.assertTrue(self.server.messages('ch1')[2]['text'].startswith('mstack hub · your turn ended without'))

    def test_three_failed_turns_pause_the_agent_and_tell_the_owner(self):
        c = self.conductor([event(1)], max_turn_seconds=1, nudge_seconds=1)
        for n in range(3):
            turn = c.tick()['turns'][0]
            self.assertIn('no actions block', turn['failed'])
            self.assertEqual(self.mb.rows[0]['status'], 'new')
        self.assertTrue(turn['paused'])
        self.assertEqual(self.mb.agent('orch:mstack')['state'], 'paused')
        owner = [r for r in self.mb.rows if r['recipient'] == 'owner']
        self.assertEqual(owner[0]['kind'], 'wake_failed')
        self.assertEqual(c.tick()['turns'][0]['waiting'], 'paused')

    def test_shadow_logs_actions_without_running_them(self):
        self.replies = [[BLOCK % json.dumps([{'do': 'dispatch'}, {'do': 'say', 'text': 'hello'}])]]
        c = self.conductor([event(1)], mode='shadow')
        turn = c.tick()['turns'][0]
        self.assertEqual([r['status'] for r in turn['actions']], ['shadow', 'shadow'])
        self.assertEqual(turn['actions'][0]['would_run'], 'mstack board dispatch --project /repo/mstack')
        self.assertEqual(self.ran, [])
        self.assertFalse([r for r in self.mb.rows if r['recipient'] == 'owner'])

    def test_actions_from_the_owner_chat(self):
        c = self.conductor([])
        self.server.add('ch1', 'ok MST-70 👍', 'person')
        self.server.add('ch1', 'Recording it.\n' + BLOCK % json.dumps([
            {'do': 'owner', 'task': 'MST-70', 'text': 'ok MST-70 👍'},
            {'do': 'owner', 'task': 'MST-70', 'text': 'merge it'}]), 'agent')
        report = c.tick()
        actions = report['chats'][0]['actions']
        self.assertEqual([a['status'] for a in actions], ['done', 'refused'])
        self.assertEqual(self.ran[0][0][:1], ['owner'])
        self.assertEqual(self.mb.agent('orch:mstack')['cursor']['seq'], 2)
        self.assertEqual(c.tick()['chats'], [])                      # already read: nothing runs again

    def test_fetch_answers_in_the_next_batch(self):
        self.replies = [[BLOCK % json.dumps([{'do': 'fetch', 'what': 'tree', 'task': 'MST-70'}])], [BLOCK % '[]']]
        c = self.conductor([event(1)])
        c.tick()
        self.assertEqual(self.ran[0][0][:1], ['tree'])
        c.tick()
        self.assertIn('[fetch_result] tree MST-70', self.server.messages('ch1')[-2]['text'])


@unittest.skipUnless(os.environ.get('MSTACK_PG_TESTS') == '1', 'opt-in: needs mstack_orchestrator (MSTACK_PG_TESTS=1)')
class Postgres(unittest.TestCase):
    """The PgMailbox SQL against a throwaway schema built from schema.sql, dropped afterwards."""
    def setUp(self):
        secret = os.environ.get('MSTACK_PG_PASSWORD_FILE')
        if secret:
            store.PG['password_file'] = secret
        self.schema = 'mst67_test_' + secrets.token_hex(3)
        sql = store.SCHEMA.read_text().replace('orchestrator.', self.schema + '.').replace(
            'SCHEMA IF NOT EXISTS orchestrator', 'SCHEMA IF NOT EXISTS ' + self.schema).replace(
            'ON SCHEMA orchestrator', 'ON SCHEMA ' + self.schema)
        store.psql(sql)
        self.mb = mailbox.PgMailbox(schema=self.schema)

    def tearDown(self):
        store.psql('DROP SCHEMA IF EXISTS %s CASCADE;\n' % self.schema)

    def test_mailbox_round_trip(self):
        self.assertTrue(self.mb.upgraded)
        store.psql("INSERT INTO %s.queue (board, scope, kind, issue) VALUES ('mstack', '', 'plan', 'MST-70'), "
                   "('staff', 'api', 'plan', 'IRO-1');\n" % self.schema)
        mail = self.mb.post([{'recipient': 'orch:mstack', 'sender': 'orch:staff/api', 'kind': 'message',
                              'board': 'staff', 'payload': {'text': 'hi'}, 'dedupe': 'm1'}])
        self.assertEqual(self.mb.post([{'recipient': 'orch:mstack', 'kind': 'message', 'dedupe': 'm1'}]), mail)
        rows = self.mb.pending({'orch:mstack'})
        self.assertEqual([(r['recipient'], r['kind']) for r in rows], [('orch:mstack', 'plan'), ('orch:mstack', 'message')])
        ids = [r['id'] for r in rows]
        self.assertEqual(self.mb.take(ids, 'b-1', '{{mstack:CLIENT_C_FOLDER}}:t/a'), ids)
        self.assertEqual(self.mb.pending({'orch:mstack'}), [])
        self.mb.requeue(ids[:1], 'failed')
        self.assertEqual([r['attempts'] for r in self.mb.pending({'orch:mstack'})], [1])
        self.assertEqual(self.mb.resolve(ids, 'orch:mstack'), ids)
        self.mb.turn_start({'id': 'b-1', 'address': 'orch:mstack', 'events': ids})
        self.mb.turn_end('b-1', status='done', reply='[]')
        self.assertEqual(self.mb.claim_action('k', 'b-1', 'orch:mstack', {'do': 'dispatch'}), 'new')
        self.assertEqual(self.mb.claim_action('k', 'b-1', 'orch:mstack', {'do': 'dispatch'}), 'running')
        self.mb.finish_action('k', 'done', result={'ok': True})
        self.assertEqual(self.mb.claim_action('k', 'b-2', 'orch:mstack', {'do': 'dispatch'}), 'done')
        self.mb.save_agent('orch:mstack', role='orchestrator', harness='{{mstack:CLIENT_C_FOLDER}}', state='idle', cursor={'seq': 4})
        self.mb.save_agent('orch:mstack', state='paused', failures=3)
        got = self.mb.agent('orch:mstack')
        self.assertEqual((got['state'], got['failures'], got['cursor']), ('paused', 3, {'seq': 4}))
        self.assertEqual([r['kind'] for r in self.mb.recent(5)], ['plan', 'message'])


if __name__ == '__main__':
    unittest.main()
