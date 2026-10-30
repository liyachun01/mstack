"""The owner's "My tasks" status table (design 014): rows from the hub, one-way upsert into a fake Anytype.
Neither Anytype nor Postgres is reached."""
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli
import status_table as st
import test_linear_board as flow            # module import: its own tests are not collected twice here

NOW = time.mktime((2026, 10, 30, 12, 0, 0, 0, 0, 0))


def issue(board, ident, state_type='started', **kw):
    return {'board': board, 'identifier': ident, 'title': 'Title of ' + ident, 'state': kw.pop('state', None),
            'state_type': state_type, 'scopes': '', 'managed': False, 'agent_phase': None,
            'url': 'https://linear.app/x/issue/' + ident, 'updated_at': '2026-10-30T01:00:00Z', 'present': True, **kw}


class FakeAnytype:
    """Just enough of the channel API: properties, types, collections, objects. Records every call."""
    def __init__(self):
        self.calls, self.objects, self.items, self.n = [], {}, {}, 0
        self.fail_after = None

    def __call__(self, method, path, body=None):
        body = json.loads(json.dumps(body))           # a copy, as over the wire
        self.calls.append((method, path, body))
        if self.fail_after is not None and len(self.calls) > self.fail_after:
            raise RuntimeError('HTTP 500')
        base = path.split('?')[0]
        if method == 'GET' and base in ('properties', 'types'):
            return {'data': []}
        if method == 'GET' and base.endswith('/views'):
            return {'data': [{'id': 'v-all', 'name': 'All'}, {'id': 'v-table', 'name': 'Table'}, {'id': 'v-board', 'name': 'Board'}]}
        if method == 'POST' and base in ('collections', 'objects'):
            self.n += 1
            ident = 'obj-%d' % self.n
            self.objects[ident] = dict(body)
            return {'id': ident}
        if method == 'POST' and base == 'widgets':
            return {'id': 'widget-1'}
        if method == 'PATCH':
            ident = base.split('/', 1)[1]
            for op in body['ops']:
                if op['op'] == 'set_properties':
                    obj = self.objects[ident]
                    obj['name'] = op['set'].get('name', obj['name'])
                    obj['properties'] = {**obj['properties'], **{k: v for k, v in op['set'].items() if k != 'name'}}
                elif op['op'] == 'add_items':
                    self.items.setdefault(ident, []).extend(op['items'])
            return {}
        if method == 'DELETE':
            self.objects.pop(base.split('/', 1)[1], None)
            return {}
        return {}

    def writes(self):
        return [c for c in self.calls if c[0] != 'GET']


class Rows(unittest.TestCase):
    def test_columns_status_worker_scope_and_links(self):
        state = {'runs': {'t1': {'table': 'mstack', 'issue': 'MST-40', 'session': 'local_w', 'scope': None},
                          't2': {'table': '{{mstack:CLIENT_REPO}}', 'issue': 'IRO-1', 'session': 'local_old', 'scope': 'customer-api',
                                 'dispatched_at': '2026-10-29T10:00:00+0800'},
                          't3': {'table': '{{mstack:CLIENT_REPO}}', 'issue': 'IRO-1', 'session': 'local_new', 'scope': 'customer-api',
                                 'dispatched_at': '2026-10-30T10:00:00+0800'}},
                 'task_tables': {'CAN-9': {'table': '{{mstack:CLIENT_REPO}}', 'scope': 'staff-web'}}}
        rows = st.desired([issue('mstack', 'MST-40', managed=True, agent_phase='In Review'),
                           issue('{{mstack:CLIENT_REPO}}', 'IRO-1', state='In Review'),
                           issue('{{mstack:CLIENT_REPO}}', 'CAN-9', 'unstarted')],
                          state, {'mstack': False, '{{mstack:CLIENT_REPO}}': True}, NOW)
        mst = rows['mstack/MST-40']
        self.assertEqual(mst['name'], 'MST-40 Title of MST-40')
        self.assertEqual(mst['properties'], {
            'my_task_issue': 'MST-40', 'my_task_project': 'mstack', 'my_task_status': 'In Review',
            'my_task_worker': 'local_w', 'my_task_updated': '2026-10-30T01:00:00Z',
            'my_task_link': 'https://linear.app/x/issue/MST-40'})
        iro = rows['{{mstack:CLIENT_REPO}}/IRO-1']['properties']
        self.assertEqual((iro['my_task_worker'], iro['my_task_scope'], iro['my_task_status']),
                         ('local_new', 'customer-api', 'In Review'))           # latest dispatch wins
        self.assertNotIn('my_task_link', iro)                                  # private board: no Linear link
        self.assertEqual(rows['{{mstack:CLIENT_REPO}}/CAN-9']['properties']['my_task_scope'], 'staff-web')
        self.assertEqual(rows['{{mstack:CLIENT_REPO}}/CAN-9']['properties']['my_task_status'], 'Todo')

    def test_unknown_board_gets_no_link_and_closed_wins(self):
        rows = st.desired([issue('other', 'X-1', 'completed', managed=True, agent_phase='In Review')], {}, {}, NOW)
        props = rows['other/X-1']['properties']
        self.assertEqual(props['my_task_status'], 'Done')
        self.assertNotIn('my_task_link', props)

    def test_which_closed_issues_are_shown(self):
        old = '2026-08-01T00:00:00Z'
        issues = [issue('b', 'A-1', 'completed', updated_at=old),                      # old history: hidden
                  issue('b', 'A-2', 'completed'),                                      # closed recently: shown
                  issue('b', 'A-3', 'canceled', updated_at=old, managed=True),         # the board handled it
                  issue('b', 'A-4', 'completed', updated_at=old),                      # already in the table
                  issue('b', 'A-5', 'started', present=False),                         # left the source, never shown
                  issue('b', 'A-6', 'started', present=False)]                         # left the source, shown before
        shown = {st.STATE_KEY: {'rows': {'b/A-4': {'id': 'o4', 'hash': 'h'}, 'b/A-6': {'id': 'o6', 'hash': 'h'}}}}
        self.assertEqual(sorted(st.desired(issues, shown, {}, NOW)), ['b/A-2', 'b/A-3', 'b/A-4', 'b/A-6'])


class Upsert(unittest.TestCase):
    def setUp(self):
        self.any = FakeAnytype()
        self.table = st.StatusTable(self.any)
        self.rows = st.desired([issue('mstack', 'MST-1'), issue('mstack', 'MST-2')], {}, {'mstack': False}, NOW)

    def test_first_pass_builds_the_table_then_only_changes_are_written(self):
        known, counts = self.table.sync(self.rows, {})
        self.assertEqual(counts, {'created': 2, 'updated': 0, 'unchanged': 0})
        posted = [b['name'] for m, p, b in self.any.calls if m == 'POST' and p == 'collections']
        self.assertEqual(posted, ['My tasks'])
        props = [b['key'] for m, p, b in self.any.calls if m == 'POST' and p == 'properties']
        self.assertEqual(props, st.COLUMNS)
        self.assertEqual(sorted(self.any.items[known['collection']]), sorted(r['id'] for r in known['rows'].values()))
        self.assertIn(('PATCH', 'objects/' + known['collection'],
                       {'ops': [{'op': 'delete_view', 'view': 'v-all'}]}),
                      [(m, p, {'ops': [o for o in b['ops'] if o['op'] == 'delete_view']}) for m, p, b in self.any.writes()
                       if m == 'PATCH' and any(o['op'] == 'delete_view' for o in b['ops'])])
        before = len(self.any.calls)
        known, counts = self.table.sync(self.rows, known)
        self.assertEqual((counts['unchanged'], len(self.any.calls)), (2, before))   # nothing to do: no calls at all
        self.rows['mstack/MST-2']['properties']['my_task_status'] = 'Done'
        known, counts = self.table.sync(self.rows, known)
        self.assertEqual((counts['updated'], counts['unchanged']), (1, 1))
        obj = self.any.objects[known['rows']['mstack/MST-2']['id']]
        self.assertEqual(obj['properties']['my_task_status'], 'Done')

    def test_a_full_pass_overwrites_hand_edits(self):
        known, _ = self.table.sync(self.rows, {})
        ident = known['rows']['mstack/MST-1']['id']
        self.any.objects[ident]['properties']['my_task_status'] = 'Canceled'          # owner edits in Anytype
        self.any.objects[ident]['properties']['my_task_worker'] = 'typed by hand'
        self.any.objects[ident]['name'] = 'renamed'
        _, counts = self.table.sync(self.rows, known, full=True)
        self.assertEqual(counts['updated'], 2)
        obj = self.any.objects[ident]
        self.assertEqual((obj['name'], obj['properties']['my_task_status'], obj['properties']['my_task_worker']),
                         ('MST-1 Title of MST-1', 'In Progress', ''))

    def test_a_failure_keeps_what_was_written_and_never_makes_a_second_table(self):
        self.any.fail_after = 12                       # the table is built; the first row is written, then failure
        with self.assertRaises(RuntimeError):
            self.table.sync(self.rows, {})
        partial = self.table.partial
        self.assertTrue(partial['collection'])
        self.any.fail_after = None
        known, counts = self.table.sync(self.rows, partial)
        self.assertEqual([b['name'] for m, p, b in self.any.calls if m == 'POST' and p == 'collections'], ['My tasks'])
        self.assertEqual(counts['created'] + counts['unchanged'], 2)
        self.assertEqual(len(self.any.items[known['collection']]), 2)


class HubStep(unittest.TestCase):
    """Through the CLI: `status-table sync`, the hub tick step, its schedule and the off switch."""
    F = flow.LinearBoardFlow
    setUp, cli = F.setUp, F.cli

    def wire(self, issues):
        self.any = FakeAnytype()
        sql = lambda q, fetch=False: '\n'.join(json.dumps(i) for i in issues)
        for name, value in (('STATUS_CALL', self.any), ('STATUS_SQL', sql), ('MIRROR_EVERY', 10 ** 9)):
            p = patch.object(cli, name, value); p.start(); self.addCleanup(p.stop)
        with cli.state() as s:
            s.setdefault('last_mirror', {})['repo'] = time.time()

    def test_manual_sync_and_show(self):
        self.wire([issue('repo', 'MST-7')])
        out = self.cli('status-table', 'sync')
        self.assertEqual((out['rows'], out['created'], out['full']), (1, 1, True))
        again = self.cli('status-table', 'sync')
        self.assertEqual((again['unchanged'], again['full']), (1, False))          # full only once an hour
        shown = self.cli('status-table', 'show')
        self.assertEqual((shown['rows'], bool(shown['collection']), bool(shown['last_pass'])), (1, True, True))
        row = next(o for o in self.any.objects.values() if o.get('type') == st.TYPE['key'])
        self.assertEqual(row['properties']['my_task_link'], 'https://linear.app/x/issue/MST-7')

    def test_off_switch_refuses_manual_sync(self):
        self.wire([issue('repo', 'MST-7')])
        with patch.object(cli, 'hub_settings', lambda: {'status_table': False}):
            self.assertEqual(cli.main(['status-table', 'sync'], cli.anyboard.Board(call=None)), 1)
            self.assertFalse(self.cli('status-table', 'show')['on'])
        self.assertEqual(self.any.calls, [])

    def test_hub_tick_runs_it_on_schedule_and_survives_anytype_being_closed(self):
        self.wire([issue('repo', 'MST-7')])
        self.any.fail_after = 0                                                    # Anytype app not running
        with patch.object(cli, 'status_table_on', lambda: True), patch.object(cli, 'LINEAR_EVERY', 0):
            out = self.cli('tick', '--hub')
            self.assertIn('HTTP 500', out['status_table_error'])
            calls = len(self.any.calls)
            self.assertNotIn('status_table', self.cli('tick', '--hub'))            # not again before EVERY
            self.assertEqual(len(self.any.calls), calls)
            self.any.fail_after = None
            with patch.object(st, 'EVERY', 0):
                self.assertEqual(self.cli('tick', '--hub')['status_table']['created'], 1)
        with patch.object(st, 'EVERY', 0), patch.object(cli, 'LINEAR_EVERY', 0):
            self.assertNotIn('status_table', self.cli('tick', '--hub'))            # off: tests' default

    def test_stale_boards_are_mirrored_before_the_pass(self):
        self.wire([])
        with cli.state() as s:
            s['last_mirror']['repo'] = 0
        with patch.object(cli, 'MIRROR_EVERY', 300):
            out = self.cli('status-table', 'sync')
        self.assertEqual(out['mirrored'], {'repo': 0})
        self.assertTrue(any('orchestrator.issues' in q for q in self.sql))


if __name__ == '__main__':
    unittest.main()
