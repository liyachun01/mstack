import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'agents'))
from anytype_documents import sync
import project_state


class DocumentSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'docs').mkdir(); (self.root / '.mstack').mkdir()
        (self.root / 'docs/BRIEF.md').write_text('A build_report example.')
        self.config = {'project': 'example', 'anytype': {
            'space_id': 'space-one', 'api_url':'http://127.0.0.1:31009',
            'credential_file':'.mstack/secrets/key',
            'documents': {'brief': {'name': 'Brief', 'local_draft': 'docs/BRIEF.md'}}}}
        (self.root/'.mstack/stack.json').write_text(json.dumps(self.config))
        self.objects = {}; self.writes = 0; self.all_spaces = False; self.corrupt = False

    def request(self, method, params):
        if method == 'tools/list': return {'tools': [{'name': 'API-get-object'}]}
        args = params['arguments']; name = params['name']
        if args.get('space_id') == 'mstack-ungranted-probe':
            return {'isError': True, 'content': [{'text': 'space_not_granted'}]}
        if name == 'API-auth-whoami':
            data = {'grant': {'all_spaces': self.all_spaces, 'permission': 'readwrite', 'spaces': [{'id': 'space-one'}]}}
        elif name == 'API-list-objects': data = {'data': [], 'has_more': False}
        elif name == 'API-create-object':
            self.writes += 1; self.objects['object-one'] = copy.deepcopy(args['body']); data = {'id': 'object-one'}
        elif name == 'API-get-object':
            body = self.objects[args['object_id']]
            data = {'id': args['object_id'], 'properties': {'name': body['name']}}
            if args.get('format') == 'md':
                data = {'id': args['object_id'], 'markdown': 'wrong' if self.corrupt else body['markdown'].replace('_', '\\_')}
        else: raise AssertionError(name)
        return {'content': [{'text': json.dumps(data)}]}

    def test_readback_and_repeat_do_not_duplicate(self):
        sync(self.request, self.root, self.config)
        sync(self.request, self.root, self.config)
        self.assertEqual(self.writes, 1)
        result = json.loads((self.root / '.mstack/evidence/anytype.json').read_text())
        self.assertTrue(result['documents']['brief']['readback_matches_draft'])

    def test_broad_grant_rejected_before_write(self):
        self.all_spaces = True
        with self.assertRaises(ValueError): sync(self.request, self.root, self.config)
        self.assertEqual(self.writes, 0)

    def test_failed_readback_retains_identity_without_success_receipt(self):
        self.corrupt = True
        with self.assertRaises(ValueError): sync(self.request, self.root, self.config)
        self.assertFalse((self.root / '.mstack/evidence/anytype.json').exists())
        saved = project_state.read(self.root)
        self.assertEqual(saved['documents']['anytype']['brief']['object_id'], 'object-one')
        self.assertEqual(json.loads((self.root/'.mstack/stack.json').read_text()),self.config)
        self.corrupt = False
        sync(self.request, self.root)
        self.assertEqual(self.writes, 1)
