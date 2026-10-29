"""Explicit project document creation/readback; no overwrite, watcher or memory mirror."""
import hashlib
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"stack"))
import project_state


def sync(request, root, config=None):
    config = json.loads((root/'.mstack/stack.json').read_text())
    binding = project_state.anytype(root)
    space = binding['space_id']
    evidence = {'project': config['project'], 'transport': 'direct-stdio-MCP',
                'space_id': space, 'documents': {}}

    def call(name, arguments):
        if 'space_id' in arguments and arguments['space_id'] != space:
            raise ValueError('Document operation outside project Space')
        result = request('tools/call', {'name': 'API-' + name, 'arguments': arguments})
        if result.get('isError'):
            raise RuntimeError(result)
        return json.loads(result['content'][0]['text'])

    who = call('auth-whoami', {'ids': 'full'})
    grant = who['grant']
    if grant['all_spaces'] or grant['permission'] != 'readwrite' or [s['id'] for s in grant['spaces']] != [space]:
        raise ValueError('Expected exactly the project read/write grant')
    evidence['grant'] = {'all_spaces': False, 'permission': 'readwrite', 'space_ids': [space]}
    outside = request('tools/call', {'name': 'API-list-objects',
                                    'arguments': {'space_id': 'mstack-ungranted-probe', 'limit': 1}})
    if not outside.get('isError') or 'space_not_granted' not in json.dumps(outside):
        raise ValueError('Out-of-grant read did not fail with space_not_granted')
    evidence['out_of_scope_denied'] = True
    evidence['out_of_scope_result'] = outside
    evidence['discovered_tools'] = [t['name'] for t in request('tools/list', {})['tools']]
    rows = call('list-objects', {'space_id': space, 'limit': 100})
    if rows.get('has_more'):
        raise ValueError('Page through existing objects before document reconciliation')
    for key, doc in binding['document_objects'].items():
        draft = (root / doc['local_draft']).resolve()
        if not draft.is_relative_to((root / 'docs').resolve()):
            raise ValueError('Document draft must be inside project docs')
        content = draft.read_text().strip()
        if not content:
            raise ValueError('Document draft is empty')
        object_id = doc.get('object_id')
        if not object_id:
            matches = [r['id'] for r in rows['data'] if r['name'] == doc['name'] and r['type'] == 'page']
            if len(matches) > 1:
                raise ValueError('Ambiguous existing document')
            object_id = matches[0] if matches else None
        created = False
        if not object_id:
            result = call('create-object', {'space_id': space, 'body': {
                'type': 'page', 'name': doc['name'], 'template': 'none', 'markdown': content}})
            object_id = result['id']
            created = True
        # Persist identity before verification, so a failed read cannot duplicate a write.
        doc['object_id'] = object_id
        with project_state.edit(root) as state:
            state['documents'].setdefault('anytype',{}).setdefault(key,{})['object_id']=object_id
        identity = call('get-object', {'space_id': space, 'object_id': object_id})
        actual = call('get-object', {'space_id': space, 'object_id': object_id, 'format': 'md'})
        markdown = actual.get('markdown', '')
        if actual.get('id') != object_id or identity.get('properties', {}).get('name') != doc['name']:
            raise ValueError('Document identity readback differs')
        # Markdown exports escape literal punctuation such as symbol underscores.
        rendered = re.sub(r'\\([\\`*_{}\[\]()#+.!>-])', r'\1', markdown)
        if not all(line.strip() in rendered for line in content.splitlines() if line.strip()):
            raise ValueError('Document content differs; existing content preserved for review')
        evidence['documents'][key] = {'id': object_id, 'name': doc['name'], 'created': created,
                                      'readback_matches_draft': True,
                                      'draft_sha256': hashlib.sha256(content.encode()).hexdigest(),
                                      'readback_sha256': hashlib.sha256(markdown.encode()).hexdigest()}
    evidence['passed'] = True
    destination = root / '.mstack/evidence/anytype.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))
