"""The owner's "My tasks" status table (design 014): rows from the hub, one-way upsert into a fake Anytype.
Neither Anytype nor Postgres is reached."""
import contextlib
import io
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
        self.properties, self.types = [], {}          # existing property keys; type key → its property keys

    def __call__(self, method, path, body=None):
        body = json.loads(json.dumps(body))           # a copy, as over the wire
        self.calls.append((method, path, body))
        if self.fail_after is not None and len(self.calls) > self.fail_after:
            raise RuntimeError('HTTP 500')
        base = path.split('?')[0]
        if method == 'GET' and base == 'properties':
            return {'data': [{'key': k} for k in self.properties]}
        if method == 'GET' and base == 'types':
            return {'data': [{'key': k} for k in self.types]}
        if method == 'GET' and base.startswith('types/'):
            return {'kind': 'object_type', 'properties': {'name': base[6:]},           # the live API's shape
                    'type_settings': {'api_key': base[6:], 'property_definitions': [
                        {'property': k, 'section': 'hidden'} for k in self.types[base[6:]]]}}
        if method == 'POST' and base == 'properties':
            self.properties.append(body['key'])
            return {}
        if method == 'POST' and base == 'types':
            self.types[body['api_key']] = [d['property'] for d in body['property_definitions']]
            return {}
        if method == 'PATCH' and base.startswith('types/'):
            self.types[base[6:]] += [op['property'] for op in body['ops']]
            return {}
        if method == 'PATCH' and base == '.':
            self.channel = body['name']
            return {}
        if method == 'POST' and base == 'search':
            out = [{'id': i, 'name': o.get('name'), 'type': o.get('type'),
                    'properties': {f: [o['properties'][f]] for f in body.get('fields', []) if f in o.get('properties', {})}}
                   for i, o in self.objects.items() if o.get('type') == body.get('type')]
            offset = int(dict(x.split('=') for x in path.split('?')[1].split('&')).get('offset', 0))
            return {'data': out[offset:offset + 200]}
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
    STATE = {'runs': {'t1': {'table': 'mstack', 'issue': 'MST-40', 'session': 'local_w', 'scope': None,
                             'runner': 'claude-desktop', 'report': {'kind': 'done', 'text': 'Built it.\n  Tests pass.'}},
                      't2': {'table': '{{mstack:CLIENT_REPO}}', 'issue': 'IRO-1', 'session': 'local_old', 'scope': 'customer-api',
                             'runner': 'codex', 'dispatched_at': '2026-10-29T10:00:00+0800'},
                      't3': {'table': '{{mstack:CLIENT_REPO}}', 'issue': 'IRO-1', 'session': 'local_new', 'scope': 'customer-api',
                             'dispatched_at': '2026-10-30T10:00:00+0800'},
                      't4': {'table': 'test-market', 'issue': None, 'session': None}},      # never had a session
             'related': {'t3': [{'session': 'local_rel', 'scope': 'customer-api', 'note': 'obsolete'}]},
             'orchestrators': {'{{mstack:CLIENT_REPO}}/customer-api': {'project': '{{mstack:CLIENT_REPO}}', 'scope': 'customer-api', 'session': 'local_api'},
                               '{{mstack:CLIENT_REPO}}/': {'project': '{{mstack:CLIENT_REPO}}', 'scope': None, 'session': 'local_sk'}},
             'task_tables': {'CAN-9': {'table': '{{mstack:CLIENT_REPO}}', 'scope': 'staff-web'}},
             'sessions_seen': {'local_old': {'state': 'archived'}, 'local_new': {'state': 'active'}}}
    ROLES = {'mstack': {'local_morch': {'role': 'orchestrator'},
                        'local_help': {'role': 'helper', 'task': 'MST-40', 'worker': 'local_w'}}}
    ISSUES = [issue('mstack', 'MST-40', managed=True, agent_phase='In Review'),
              issue('{{mstack:CLIENT_REPO}}', 'IRO-1', state='In Review'), issue('{{mstack:CLIENT_REPO}}', 'CAN-9', 'unstarted')]

    BOARDS = {'mstack': {'teams': {'MST': 'yyyymmdd'}},
              '{{mstack:CLIENT_REPO}}': {'teams': {'CAN': '{{mstack:CLIENT_ORG_B}}', 'IRO': '{{mstack:CLIENT_ORG_A_SHORT}}'},
                           'scopes': {'customer-api': {'apps': ['API'], 'exclude': ['IRO-91']}, 'staff-web': {'apps': ['*']},
                                      'portal-web': {'apps': ['API'], 'focus': ['IRO-91']}}}}

    def rows(self, state=None, issues=None):
        return st.desired(issues or self.ISSUES, state or self.STATE, self.BOARDS, NOW, self.ROLES)

    def test_spawned_cli_session_row_links_its_run_log(self):
        dsh = {'table': 'mstack', 'issue': 'MST-40', 'runner': 'dsh', 'session': 'dsh:session-1', 'native_session': 'session-1',
               'log': '/w/.mstack/cache/runs/mst-40.log', 'live': True, 'dispatched_at': '2026-10-30T11:00:00+0800'}
        state = {**self.STATE, 'runs': {'t9': dsh}, 'sessions_seen': {'dsh:session-1': {'state': 'deleted'}}}
        props = self.rows(state)[0]['session/dsh:session-1']['properties']
        self.assertEqual((props['session_agent'], props['session_state'], props['source_url']),
                         ('deepseek', 'active', 'file:///w/.mstack/cache/runs/mst-40.log'))
        ended = self.rows({**state, 'runs': {'t9': {**dsh, 'live': False}}})[0]['session/dsh:session-1']['properties']
        self.assertEqual(ended['session_state'], 'active')         # MST-40 waits for review: shown active
        stopped = self.rows({**state, 'runs': {'t9': {**dsh, 'stopped': 'x'}}})[0]['session/dsh:session-1']['properties']
        self.assertEqual(stopped['session_state'], 'archived')
        self.assertEqual([st.agent_of(r) for r in ('dsh', 'opencode', 'codex', None)], ['deepseek', 'other', 'codex', 'claude'])

    def test_one_row_per_session_with_its_issue(self):
        rows, _, _ = self.rows()
        self.assertEqual(sorted(rows), ['session/local_api', 'session/local_help', 'session/local_morch', 'session/local_new',
                                        'session/local_old', 'session/local_rel', 'session/local_sk', 'session/local_w',
                                        '{{mstack:CLIENT_REPO}}/CAN-9'])
        w = rows['session/local_w']
        self.assertEqual(w['name'], 'MST-40 Title of MST-40')
        self.assertEqual(w['properties'], {
            'linear_identifier': 'MST-40', 'task_project': 'mstack', 'task_status': 'In Review',
            'item_source': 'yyyymmdd/MST', 'source_url': 'claude://claude.ai/epitaxy/local_w', 'task_scope': '—',
            'linear_updated_at': '2026-10-30T01:00:00Z', 'linear_url': 'https://linear.app/x/issue/MST-40',
            'agent_session': 'local_w', 'session_type': 'worker', 'session_agent': 'claude',
            'session_parent': 'local_morch', 'session_state': 'active', 'session_report': 'Built it. Tests pass.'})
        old, new = rows['session/local_old']['properties'], rows['session/local_new']['properties']
        self.assertEqual((old['session_agent'], old['session_state'], old['session_parent']), ('codex', 'archived', 'local_api'))
        self.assertEqual((new['task_scope'], new['session_state'], new['task_status']), ('customer-api', 'active', 'In Review'))
        self.assertEqual(new['linear_url'], 'https://linear.app/x/issue/IRO-1')   # private boards too (owner, MST-42)
        self.assertEqual(new['item_source'], '{{mstack:CLIENT_ORG_A_SHORT}}/IRO')
        # Never observed (local_w), or observed active: active; only archived/deleted show otherwise.
        self.assertEqual(rows['session/local_rel']['properties']['session_state'], 'active')
        gone = dict(self.STATE, sessions_seen={'local_rel': {'state': 'deleted'}, 'local_w': {'state': 'odd'}})
        rows2, _, _ = self.rows(gone)
        self.assertEqual(rows2['session/local_rel']['properties']['session_state'], 'deleted')
        self.assertEqual(rows2['session/local_w']['properties']['session_state'], 'active')
        # Idle: last seen not running, unless its issue waits for review (local_w's MST-40 is In Review).
        idle = dict(self.STATE, sessions_seen={'local_sk': {'state': 'idle'}, 'local_w': {'state': 'idle'}})
        rows3, _, _ = self.rows(idle)
        self.assertEqual(rows3['session/local_sk']['properties']['session_state'], 'idle')
        self.assertEqual(rows3['session/local_w']['properties']['session_state'], 'active')
        self.assertIn('obsolete', rows['session/local_rel']['properties']['session_report'])
        orch = rows['session/local_api']
        self.assertEqual((orch['name'], orch['properties']['session_type']), ('Orchestrator {{mstack:CLIENT_REPO}}/customer-api', 'orchestrator'))
        self.assertNotIn('session_parent', orch['properties'])               # orchestrators have no parent
        self.assertEqual((orch['properties']['item_source'], rows['session/local_sk']['properties']['task_scope']),
                         ('hub', '—'))
        self.assertEqual(rows['session/local_help']['properties']['session_parent'], 'local_morch')
        self.assertEqual(rows['{{mstack:CLIENT_REPO}}/CAN-9']['properties'],               # an issue nobody works on yet
                         {'linear_identifier': 'CAN-9', 'task_project': '{{mstack:CLIENT_REPO}}', 'task_scope': 'staff-web',
                          'item_source': '{{mstack:CLIENT_ORG_B}}/CAN', 'task_status': 'Todo', 'linear_updated_at': '2026-10-30T01:00:00Z',
                          'linear_url': 'https://linear.app/x/issue/CAN-9', 'source_url': 'https://linear.app/x/issue/CAN-9'})

    def test_a_session_row_links_to_its_chat_as_listed(self):
        seen = dict(self.STATE, sessions_seen={'local_w': {'state': 'active', 'link': 'claude://claude.ai/epitaxy/w-1'}})
        rows, _, _ = self.rows(seen)
        self.assertEqual(rows['session/local_w']['properties']['source_url'], 'claude://claude.ai/epitaxy/w-1')
        self.assertEqual(rows['session/local_api']['properties']['source_url'], 'claude://claude.ai/epitaxy/local_api')

    def test_rows_of_retired_or_unregistered_boards_are_left_out_and_retired(self):
        state = dict(self.STATE, runs={**self.STATE['runs'], 't5': {'table': 'test-market', 'issue': 'TM-1',
                                                                     'session': 'local_tm'}},
                     status_table={'rows': {'session/local_tm': {'id': 'o1'}, 'test-market/TM-2': {'id': 'o2'},
                                            'session/local_w': {'id': 'o3'}}})
        issues = self.ISSUES + [issue('test-market', 'TM-2')]
        rows, _, retire = st.desired(issues, state, self.BOARDS, NOW, self.ROLES,
                                     boards={'mstack', '{{mstack:CLIENT_REPO}}'})
        self.assertFalse([k for k in rows if 'tm' in k.lower() or k.startswith('test-market')])
        self.assertEqual(retire, ['session/local_tm', 'test-market/TM-2'])
        everything, _, kept = st.desired(issues, state, {}, NOW, self.ROLES)     # no filter: as before
        self.assertIn('session/local_tm', everything)
        self.assertEqual(kept, [])

    def test_a_session_started_outside_dispatch_gets_a_row_from_its_title(self):
        state = dict(self.STATE, sessions_seen={
            'local_84': {'state': 'idle', 'title': 'CAN-9 storage: plans'},           # no run: matched by title
            'local_gone': {'state': 'archived', 'title': 'CAN-9: older chat'},
            'local_x': {'state': 'active', 'title': 'XYZ-1: not on any board'},
            'local_t': {'state': 'active', 'title': 'Track CAN-9: not at the start'}},
            status_table={'rows': {'{{mstack:CLIENT_REPO}}/CAN-9': {'id': 'o9'}}})
        rows, takes, _ = st.desired(self.ISSUES, state, self.BOARDS, NOW, self.ROLES)
        w = rows['session/local_84']['properties']
        self.assertEqual((w['linear_identifier'], w['session_type'], w['task_scope'], w['session_state']),
                         ('CAN-9', 'worker', 'staff-web', 'idle'))
        self.assertEqual((w['linear_url'], w['item_source']), ('https://linear.app/x/issue/CAN-9', '{{mstack:CLIENT_ORG_B}}/CAN'))
        self.assertNotIn('{{mstack:CLIENT_REPO}}/CAN-9', rows)                                   # its issue row is taken over
        self.assertEqual(takes, {'session/local_84': '{{mstack:CLIENT_REPO}}/CAN-9'})
        self.assertFalse({'session/local_gone', 'session/local_x', 'session/local_t'} & set(rows))
        # A worker adopted for one issue (local_new: IRO-1) whose title names another shown issue: the title wins.
        named = dict(state, sessions_seen={'local_new': {'state': 'active', 'title': 'CAN-9: the parent issue'}})
        rows2, _, _ = st.desired(self.ISSUES, named, self.BOARDS, NOW, self.ROLES)
        self.assertEqual(rows2['session/local_new']['properties']['linear_identifier'], 'CAN-9')
        self.assertNotIn('{{mstack:CLIENT_REPO}}/CAN-9', rows2)
        plain, _, _ = st.desired(self.ISSUES, self.STATE, {}, NOW, self.ROLES)
        self.assertNotIn('session_state', plain['{{mstack:CLIENT_REPO}}/CAN-9']['properties'])  # issue-only rows: no state

    def test_an_old_issue_row_becomes_its_newest_workers_row(self):
        state = dict(self.STATE, **{st.STATE_KEY: {'rows': {'{{mstack:CLIENT_REPO}}/IRO-1': {'id': 'o1', 'hash': 'h'},
                                                            'mstack/MST-40': {'id': 'o2', 'hash': 'h'},
                                                            'session/local_w': {'id': 'o3', 'hash': 'h'}}}})
        _, takes, retire = self.rows(state)
        self.assertEqual(takes, {'session/local_new': '{{mstack:CLIENT_REPO}}/IRO-1'})
        self.assertEqual(retire, ['mstack/MST-40'])                           # its worker already had a row

    def test_unknown_board_keeps_its_link_and_team_and_closed_wins(self):
        rows, _, _ = st.desired([issue('other', 'X-1', 'completed', managed=True, agent_phase='In Review')], {}, {}, NOW)
        props = rows['other/X-1']['properties']
        self.assertEqual((props['task_status'], props['item_source'], props['task_scope']), ('Done', 'X', '—'))
        self.assertEqual(props['linear_url'], 'https://linear.app/x/issue/X-1')

    def test_scope_comes_from_the_route_when_nothing_else_names_it(self):
        issues = [issue('{{mstack:CLIENT_REPO}}', 'IRO-5', team='IRO', app='API'), issue('{{mstack:CLIENT_REPO}}', 'IRO-91', team='IRO', app='API'),
                  issue('{{mstack:CLIENT_REPO}}', 'IRO-6', team='IRO', app='API', scopes='portal-web'), issue('{{mstack:CLIENT_REPO}}', 'CAN-3')]
        rows, _, _ = st.desired(issues, {}, self.BOARDS, NOW)
        self.assertEqual({k: r['properties']['task_scope'] for k, r in rows.items()},
                         {'{{mstack:CLIENT_REPO}}/IRO-5': 'customer-api',       # app code API → customer-api
                          '{{mstack:CLIENT_REPO}}/IRO-91': '—',                 # excluded there; portal-web only focuses (mirror's job)
                          '{{mstack:CLIENT_REPO}}/IRO-6': 'portal-web',         # the mirror's scopes come first
                          '{{mstack:CLIENT_REPO}}/CAN-3': 'staff-web'})         # no app code → the * scope

    def test_the_issue_hierarchy_is_shown(self):
        old = '2026-08-01T00:00:00Z'
        issues = self.ISSUES + [issue('mstack', 'MST-1', 'completed', updated_at=old),        # hidden on its own …
                                issue('mstack', 'MST-2', 'completed', updated_at=old, parent='MST-1'),
                                issue('mstack', 'MST-3', parent='MST-2'),                    # … but its grandchild is open
                                issue('mstack', 'MST-41', parent='MST-40'),                  # parent has a worker row
                                issue('mstack', 'MST-50', parent='MST-999')]                 # parent not in the mirror
        rows, _, _ = self.rows(None, issues)
        self.assertEqual((rows['mstack/MST-3']['properties']['parent_issue'], rows['mstack/MST-3']['parent']),
                         ('MST-2', 'mstack/MST-2'))
        self.assertEqual(rows['mstack/MST-2']['parent'], 'mstack/MST-1')
        self.assertNotIn('parent', rows['mstack/MST-1'])
        self.assertEqual(rows['mstack/MST-41']['parent'], 'session/local_w')
        self.assertEqual((rows['mstack/MST-50']['properties']['parent_issue'], rows['mstack/MST-50'].get('parent')),
                         ('MST-999', None))
        self.assertEqual(st.parents_first(rows).index('mstack/MST-1') < st.parents_first(rows).index('mstack/MST-2')
                         < st.parents_first(rows).index('mstack/MST-3'), True)

    def test_no_row_lacks_issue_link_source_or_scope_when_the_data_exists(self):
        issues = self.ISSUES + [issue('{{mstack:CLIENT_REPO}}', 'IRO-7', team='IRO', app='API', parent='IRO-1'),
                                issue('{{mstack:CLIENT_REPO}}', 'IRO-8', team='IRO', app='API', parent='IRO-7')]
        state = dict(self.STATE, sessions_seen={'local_8': {'state': 'active', 'title': 'IRO-8: titled, no run'}})
        rows, _, _ = self.rows(state, issues)
        self.assertEqual(rows['session/local_8']['parent'], '{{mstack:CLIENT_REPO}}/IRO-7')     # a titled worker row is complete too
        for key, row in rows.items():
            p = row['properties']
            self.assertTrue(p.get('item_source') and p.get('task_scope'), key)          # every row
            self.assertEqual(p['source_url'], 'claude://claude.ai/epitaxy/' + p['agent_session']
                             if key.startswith('session/') else p['linear_url'], key)
            if p.get('session_type') == 'orchestrator':
                continue
            if p.get('linear_identifier') or not key.startswith('session/'):
                ident = '%s/%s' % (p['task_project'], p['linear_identifier'])
                found = next(i for i in issues if '%s/%s' % (i['board'], i['identifier']) == ident)
                self.assertEqual(p.get('linear_url'), found['url'], key)                # issue, worker and helper rows
                self.assertEqual(p.get('parent_issue'), found.get('parent'), key)
            else:
                self.assertEqual(p['item_source'], 'session', key)

    def test_which_closed_issues_are_shown(self):
        old = '2026-08-01T00:00:00Z'
        issues = [issue('b', 'A-1', 'completed', updated_at=old),                      # old history: hidden
                  issue('b', 'A-2', 'completed'),                                      # closed recently: shown
                  issue('b', 'A-3', 'canceled', updated_at=old, managed=True),         # the board handled it
                  issue('b', 'A-4', 'completed', updated_at=old),                      # already in the table
                  issue('b', 'A-5', 'started', present=False),                         # left the source, never shown
                  issue('b', 'A-6', 'started', present=False)]                         # left the source, shown before
        shown = {st.STATE_KEY: {'rows': {'b/A-4': {'id': 'o4', 'hash': 'h'}, 'b/A-6': {'id': 'o6', 'hash': 'h'}}}}
        self.assertEqual(sorted(st.desired(issues, shown, {}, NOW)[0]), ['b/A-2', 'b/A-3', 'b/A-4', 'b/A-6'])


class Upsert(unittest.TestCase):
    def setUp(self):
        self.any = FakeAnytype()
        self.table = st.StatusTable(self.any)
        self.rows = st.desired([issue('mstack', 'MST-1'), issue('mstack', 'MST-2')], {}, {}, NOW)[0]

    def test_first_pass_builds_the_table_then_only_changes_are_written(self):
        known, counts = self.table.sync(self.rows, {})
        self.assertEqual(counts, {'created': 2, 'updated': 0, 'unchanged': 0, 'pending': 0, 'removed': 0})
        posted = [b['name'] for m, p, b in self.any.calls if m == 'POST' and p == 'collections']
        self.assertEqual(posted, ['My tasks'])
        props = [b['key'] for m, p, b in self.any.calls if m == 'POST' and p == 'properties']
        self.assertEqual(props, [p['key'] for p in st.SCHEMA['properties']])   # an empty channel gets the schema
        self.assertTrue(set(st.COLUMNS) <= set(self.any.types['agent_task']))
        self.assertEqual(sorted(self.any.items[known['collection']]), sorted(r['id'] for r in known['rows'].values()))
        self.assertIn(('PATCH', 'objects/' + known['collection'],
                       {'ops': [{'op': 'delete_view', 'view': 'v-all'}]}),
                      [(m, p, {'ops': [o for o in b['ops'] if o['op'] == 'delete_view']}) for m, p, b in self.any.writes()
                       if m == 'PATCH' and any(o['op'] == 'delete_view' for o in b['ops'])])
        before = len(self.any.calls)
        known, counts = self.table.sync(self.rows, known)
        self.assertEqual((counts['unchanged'], len(self.any.calls)), (2, before))   # nothing to do: no calls at all
        self.rows['mstack/MST-2']['properties']['task_status'] = 'Done'
        known, counts = self.table.sync(self.rows, known)
        self.assertEqual((counts['updated'], counts['unchanged']), (1, 1))
        obj = self.any.objects[known['rows']['mstack/MST-2']['id']]
        self.assertEqual(obj['properties']['task_status'], 'Done')

    def test_the_existing_agent_task_type_is_reused_and_gets_the_missing_columns(self):
        keys = [p['key'] for p in st.SCHEMA['properties'] if p['key'] != 'task_scope']
        self.any.properties, self.any.types = list(keys), {'agent_task': [k for k in keys if k != 'linear_updated_at']}
        known, _ = self.table.sync(self.rows, {})
        self.assertEqual([b['key'] for m, p, b in self.any.calls if m == 'POST' and p == 'properties'], ['task_scope'])
        self.assertFalse([c for c in self.any.calls if c[:2] == ('POST', 'types')])          # no second type
        added = [b['ops'][0]['property'] for m, p, b in self.any.calls if m == 'PATCH' and p == 'types/agent_task']
        self.assertEqual(sorted(added), ['linear_updated_at', 'task_scope'])
        self.assertEqual({o['type'] for o in self.any.objects.values() if 'type' in o}, {'agent_task'})

    def test_parent_task_points_at_the_parents_row_and_clears_when_it_goes(self):
        rows = st.desired([issue('mstack', 'MST-2', parent='MST-1'), issue('mstack', 'MST-1')], {}, {}, NOW)[0]
        known, _ = self.table.sync(rows, {}, limit=1)                   # the parent is written first, even batched
        self.assertEqual(list(known['rows']), ['mstack/MST-1'])
        known, _ = self.table.sync(rows, known)
        child = self.any.objects[known['rows']['mstack/MST-2']['id']]['properties']
        self.assertEqual((child['parent_issue'], child['task_parent']), ('MST-1', [known['rows']['mstack/MST-1']['id']]))
        rows = st.desired([issue('mstack', 'MST-2'), issue('mstack', 'MST-1')], {}, {}, NOW)[0]   # re-parented away
        known, counts = self.table.sync(rows, known)
        child = self.any.objects[known['rows']['mstack/MST-2']['id']]['properties']
        self.assertEqual((counts['updated'], child['parent_issue'], child['task_parent']), (1, '', []))

    def test_rename_channel_patches_the_space_itself(self):
        self.table.rename_channel('mstack')
        self.assertEqual((self.any.calls[-1][:2], self.any.channel), (('PATCH', '.'), 'mstack'))

    def test_an_issue_row_taken_over_by_a_session_gets_a_noop_cta(self):
        known, _ = self.table.sync(self.rows, {})
        ident = known['rows']['mstack/MST-1']['id']
        del self.any.objects[ident]['properties']['session_cta']                  # a row from before the CTA column
        row = {'name': 'MST-1 Title of MST-1', 'properties': {'agent_session': 'local_w', 'session_type': 'worker'}}
        known, counts = self.table.sync({'session/local_w': row, 'mstack/MST-2': self.rows['mstack/MST-2']}, known,
                                        takes={'session/local_w': 'mstack/MST-1'})
        self.assertEqual((counts['created'], counts['updated']), (0, 1))
        self.assertEqual(known['rows']['session/local_w']['id'], ident)
        self.assertEqual(self.any.objects[ident]['properties']['session_cta'], 'noop')

    def test_a_full_pass_overwrites_hand_edits(self):
        known, _ = self.table.sync(self.rows, {})
        ident = known['rows']['mstack/MST-1']['id']
        self.any.objects[ident]['properties']['task_status'] = 'Canceled'          # owner edits in Anytype
        self.any.objects[ident]['properties']['agent_session'] = 'typed by hand'
        self.any.objects[ident]['name'] = 'renamed'
        _, counts = self.table.sync(self.rows, known, full=True)
        self.assertEqual(counts['updated'], 2)
        obj = self.any.objects[ident]
        self.assertEqual((obj['name'], obj['properties']['task_status'], obj['properties']['agent_session']),
                         ('MST-1 Title of MST-1', 'In Progress', ''))

    def test_a_failure_keeps_what_was_written_and_never_makes_a_second_table(self):
        probe = FakeAnytype()
        st.StatusTable(probe).sync(self.rows, {})
        first_row = next(i for i, c in enumerate(probe.calls) if c[2] and 'add_items' in json.dumps(c[2]))
        self.any.fail_after = first_row + 1            # the table is built and the first row written, then failure
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
    setUp, cli, auto = F.setUp, F.cli, F.auto

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
        self.assertEqual(row['properties']['linear_url'], 'https://linear.app/x/issue/MST-7')

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

    def test_the_watcher_builds_a_big_table_in_batches_without_a_manual_run(self):
        self.wire([issue('repo', 'MST-%d' % n) for n in range(1, 6)])
        on = patch.object(cli, 'status_table_on', lambda: True)
        with on, patch.object(st, 'BATCH', 2), patch.object(cli, 'LINEAR_EVERY', 0):
            first = self.cli('tick', '--hub')['status_table']
            self.assertEqual((first['created'], first['pending']), (2, 3))
            self.assertNotIn('status_table', self.cli('tick', '--hub'))            # backlog waits BACKLOG_EVERY
            with patch.object(st, 'BACKLOG_EVERY', 0):
                self.assertEqual(self.cli('tick', '--hub')['status_table']['pending'], 1)
                done = self.cli('tick', '--hub')['status_table']
            self.assertEqual((done['created'], done['pending']), (1, 0))
            self.assertNotIn('status_table', self.cli('tick', '--hub'))            # caught up: back to EVERY
            with cli.state() as s:                                                 # an hour later: full rewrite
                s[st.STATE_KEY]['last_full'] = 0
                s[st.STATE_KEY]['last_try'] = 0
            with patch.object(st, 'BACKLOG_EVERY', 0):
                passes = [self.cli('tick', '--hub')['status_table'] for _ in range(3)]
        self.assertEqual([(p['updated'], p['pending']) for p in passes], [(2, 3), (2, 1), (1, 0)])
        self.assertEqual(self.cli('status-table', 'show')['rows'], 5)

    def test_only_the_hub_watcher_runs_the_pass(self):
        self.wire([issue('repo', 'MST-7')])
        self.auto()
        with patch.object(cli, 'status_table_on', lambda: True), patch.object(st, 'EVERY', 0), \
                patch.object(cli, 'LINEAR_EVERY', 0):
            self.assertNotIn('status_table', self.cli('tick'))                       # a per-project watcher
            self.assertNotIn('status_table', self.cli('tick', '--project', 'repo'))
            self.assertEqual(self.any.calls, [])
            self.assertEqual(self.cli('tick', '--hub')['status_table']['created'], 1)

    def test_a_second_pass_while_one_runs_is_skipped_not_doubled(self):
        self.wire([issue('repo', 'MST-7')])
        inner = []

        def call(method, path, body=None):                    # a manual sync starts in the middle of the hub's pass
            if method == 'POST' and path.startswith('objects') and not inner:
                inner.append(self.cli('status-table', 'sync'))
            return self.any(method, path, body)
        with patch.object(cli, 'STATUS_CALL', call):
            outer = self.cli('status-table', 'sync')
        self.assertEqual(inner, [{'skipped': 'another status-table pass is running'}])
        self.assertEqual(outer['created'], 1)
        rows = [o for o in self.any.objects.values() if o.get('type') == st.TYPE['key']]
        self.assertEqual(len(rows), 1)

    def sessions(self):
        """A worker on MST-7 under a registered orchestrator, synced once; returns {session: object id}."""
        self.wire([issue('repo', 'MST-7')])
        with cli.state() as s:
            s['runs'] = {'t1': {'table': 'repo', 'issue': 'MST-7', 'session': 'local_w', 'runner': 'claude-desktop'}}
            s['orchestrators'] = {'repo/': {'project': 'repo', 'scope': None, 'session': 'local_o'}}
        cli.record_report('t1', 'note', 'Halfway: parser done.')
        self.cli('status-table', 'sync')
        rows = cli.read_state()[st.STATE_KEY]['rows']
        return {k[len('session/'):]: v['id'] for k, v in rows.items() if k.startswith('session/')}

    def owner_sets(self, object_id, cta):
        self.any.objects[object_id]['properties']['session_cta'] = cta

    def test_archive_cta_goes_to_the_hub_chat_and_comes_back_as_last_action(self):
        ids = self.sessions()
        w = self.any.objects[ids['local_w']]['properties']
        self.assertEqual((w['session_type'], w['session_parent'], w['session_report'], w['session_cta']),
                         ('worker', 'local_o', 'Halfway: parser done.', 'noop'))
        self.owner_sets(ids['local_w'], 'archive')
        self.assertEqual(self.cli('status-table', 'sync')['ctas'], 1)
        todo = self.cli('sessions', 'todo')
        self.assertEqual([(c['session'], c['cta'], c['type']) for c in todo['ctas']], [('local_w', 'archive', 'worker')])
        self.assertEqual(self.cli('sessions', 'todo')['ctas'], [])                 # handed out: not again at once
        done = self.cli('sessions', 'done', '--session', 'local_w', '--result', 'archived', '--state', 'archived')
        self.assertIn('archive: archived', done['recorded'])
        self.assertEqual(self.any.objects[ids['local_w']]['properties']['session_cta'], 'noop')   # reset at once
        self.cli('status-table', 'sync')
        w = self.any.objects[ids['local_w']]['properties']
        self.assertEqual(w['session_state'], 'archived')
        self.assertIn('archive: archived', w['session_action'])
        self.assertEqual(self.cli('sessions', 'list')['ctas'], {})

    def test_forbidden_protects_and_noop_cancels(self):
        ids = self.sessions()
        self.owner_sets(ids['local_w'], 'forbidden')
        self.cli('status-table', 'sync')
        self.assertEqual(self.cli('sessions', 'list')['protected'], ['local_w'])
        self.assertEqual(self.cli('sessions', 'todo')['ctas'], [])                  # never acted on
        self.owner_sets(ids['local_w'], 'delete')
        self.cli('status-table', 'sync')
        self.assertEqual(self.cli('sessions', 'list')['protected'], [])
        self.assertEqual(list(self.cli('sessions', 'list')['ctas']), ['local_w'])
        self.owner_sets(ids['local_w'], 'noop')                                    # changed their mind
        self.cli('status-table', 'sync')
        self.assertEqual(self.cli('sessions', 'list')['ctas'], {})

    def test_an_orchestrator_with_active_workers_is_never_archived(self):
        ids = self.sessions()
        self.owner_sets(ids['local_o'], 'archive')
        self.cli('status-table', 'sync')
        todo = self.cli('sessions', 'todo')
        self.assertEqual(todo['ctas'], [])
        self.assertIn('refused', todo['refused'][0]['recorded'])
        self.assertEqual(self.any.objects[ids['local_o']]['properties']['session_cta'], 'noop')
        self.cli('sessions', 'observe', '--complete', stdin=json.dumps([{'sessionId': 'local_o', 'isArchived': False}]))
        self.assertEqual(self.cli('sessions', 'list')['states'], {'local_o': 'idle', 'local_w': 'deleted'})
        self.cli('sessions', 'observe', stdin=json.dumps([{'sessionId': 'local_o', 'isArchived': False, 'isRunning': True}]))
        self.assertEqual(self.cli('sessions', 'list')['states'], {'local_o': 'active', 'local_w': 'deleted'})
        self.cli('sessions', 'observe', stdin=json.dumps([{'sessionId': 'local_o', 'link': 'claude://claude.ai/epitaxy/o'}]))
        self.cli('sessions', 'observe', stdin=json.dumps([{'sessionId': 'local_o', 'isRunning': True}]))   # link kept
        self.assertEqual(cli.read_state()['sessions_seen']['local_o']['link'], 'claude://claude.ai/epitaxy/o')
        self.owner_sets(ids['local_o'], 'archive')                                 # its worker is gone now
        self.cli('status-table', 'sync')
        self.assertEqual([c['session'] for c in self.cli('sessions', 'todo')['ctas']], ['local_o'])

    def test_a_complete_observe_never_mass_deletes_by_mistake(self):
        self.sessions()
        with cli.state() as s:                           # five more live sessions of ours
            s[st.STATE_KEY]['sessions'].update({'local_%d' % n: {} for n in range(5)})
        before = self.cli('sessions', 'list')['states']
        main = lambda *a: cli.main(['sessions', 'observe', '--complete', *a], cli.anyboard.Board(call=None))
        with patch.object(sys, 'stdin', io.StringIO('[]')), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertNotEqual(main(), 0)
        self.assertIn('empty listing', err.getvalue())
        partial = json.dumps([{'sessionId': 'local_o'}, {'sessionId': 'local_w'}, {'sessionId': 'local_0'}])
        with patch.object(sys, 'stdin', io.StringIO(partial)), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertNotEqual(main(), 0)   # 4 of 7 live sessions missing: a partial listing
        self.assertIn('would mark 4 of 7', err.getvalue())
        self.assertEqual(self.cli('sessions', 'list')['states'], before)           # nothing changed
        out = self.cli('sessions', 'observe', '--complete', '--force', stdin=partial)
        self.assertEqual(sorted(out['deleted']), ['local_1', 'local_2', 'local_3', 'local_4'])

    def test_a_cta_on_an_issue_row_is_reset(self):
        self.wire([issue('repo', 'MST-8')])
        self.cli('status-table', 'sync')
        object_id = cli.read_state()[st.STATE_KEY]['rows']['repo/MST-8']['id']
        self.owner_sets(object_id, 'archive')
        self.assertEqual(self.cli('status-table', 'sync')['ctas'], 0)
        self.assertEqual(self.any.objects[object_id]['properties']['session_cta'], 'noop')

    def test_the_hub_watcher_wakes_the_hub_chat_for_ctas_and_session_states(self):
        ids = self.sessions()
        with cli.state() as s:
            s['sessions_observed'] = {'at': time.time(), 'asked': time.time()}
        on = patch.object(cli, 'status_table_on', lambda: True)
        with on, patch.object(st, 'EVERY', 0), patch.object(cli, 'LINEAR_EVERY', 0):
            self.assertNotIn('hub_work', self.cli('watch', '--hub', '--max-ticks', '1', '--interval', '0'))
            self.owner_sets(ids['local_w'], 'continue')
            out = self.cli('watch', '--hub', '--max-ticks', '1', '--interval', '0')
            self.assertEqual(out['hub_work'], {'ctas': 1, 'observe_sessions': False})
            with cli.state() as s:
                s['sessions_observed'] = {'at': 0, 'asked': 0}
            self.cli('sessions', 'done', '--session', 'local_w', '--result', 'sent "Continue"')
            out = self.cli('watch', '--hub', '--max-ticks', '1', '--interval', '0')
            self.assertEqual(out['hub_work'], {'ctas': 0, 'observe_sessions': True})
            self.assertTrue(self.cli('sessions', 'todo')['observe_sessions'])
            self.assertNotIn('hub_work', self.cli('watch', '--hub', '--max-ticks', '1', '--interval', '0'))

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
