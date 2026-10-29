"""Remove migration-only types while keeping native collections and their rows.

Run explicitly on macOS for the bound kase channel. Fresh private backups,
If-Match edits and readbacks protect content and concurrent owner changes.
Only exact type IDs created by this migration may be archived.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import copy, deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import threading

from anytype_bound import Client, atomic_json
from notion_apply import content_hash


def stamp():
    return datetime.now(timezone.utc).isoformat()


class Organizer:
    def __init__(self, config):
        self.config = config
        self.state = Path(config['state_directory'])
        self.directory = self.state / 'organization-cleanup'
        self.ledger = json.loads((self.state / 'ledger.json').read_text())
        self.owned_types = {r['id']: r['key'] for r in self.ledger['types'].values()}
        self.client = Client(config, archive_type_keys=self.owned_types.values())
        if self.ledger['space_id'] != self.client.space:
            raise ValueError('Cleanup ledger belongs to another Space')
        self.file = self.directory / 'checkpoint.json'
        self.checkpoint = json.loads(self.file.read_text()) if self.file.exists() else {}

    def save(self):
        atomic_json(self.file, self.checkpoint)

    def search(self, **body):
        rows, offset = [], 0
        while True:
            result = self.client.scoped('POST', f'search?ids=full&limit=1000&offset={offset}', body)
            if result.get('warnings'):
                raise ValueError('Search reported incomplete results')
            rows.extend(result['data'])
            if not result.get('has_more'):
                return rows
            if not result['data']:
                raise ValueError('Search pagination made no progress')
            offset += len(result['data'])

    def read(self, target):
        obj = self.client.scoped('GET', 'objects/' + target + '?ids=full')
        if obj.get('warnings'):
            raise ValueError('Object read reported incomplete data: ' + target)
        return obj, self.client.last_etag

    def backup(self, target):
        return json.loads((self.directory / 'before' / (target + '.json')).read_text())

    def prepare(self):
        if self.checkpoint.get('prepared_at'):
            print(json.dumps({'already_prepared': True, **self.checkpoint['counts']}), flush=True)
            return
        rows = self.search()
        collections = self.search(type='collection')
        plan = json.loads((self.state / 'corrected-transform.json').read_text())
        migrated_collections = {self.ledger['objects'][s]['id'] for s in plan['collections']}
        if not migrated_collections <= {r['id'] for r in collections}:
            raise ValueError('A migrated collection is absent')
        local = threading.local()
        def fetch(row):
            if not hasattr(local, 'client'):
                local.client = copy(self.client)
            obj = local.client.scoped('GET', 'objects/' + row['id'] + '?ids=full')
            if obj.get('warnings'):
                raise ValueError('Cannot back up incomplete object')
            atomic_json(self.directory / 'before' / (row['id'] + '.json'), obj)
            return row['id'], local.client.last_etag
        with ThreadPoolExecutor(max_workers=3) as pool:
            etags = dict(pool.map(fetch, rows))
        page = self.client.scoped('GET', 'types/page?ids=full')
        atomic_json(self.directory / 'page-type.json', page)
        type_etags = {}
        for target, key in self.owned_types.items():
            obj = self.client.scoped('GET', 'types/' + key + '?ids=full')
            if obj['id'] != target or obj['type_settings'].get('api_key') != key or obj['type_settings']['layout'] != 'basic':
                raise ValueError('Owned type identity or layout changed')
            atomic_json(self.directory / 'types-before' / (target + '.json'), obj)
            type_etags[target] = self.client.last_etag
        type_keys = set(self.owned_types.values())
        candidates = [r['id'] for r in rows if r['type'] in type_keys]
        view_owners = []
        view_count = 0
        for row in rows:
            obj = self.backup(row['id'])
            found = sum(v.get('default_type_id') in self.owned_types
                        for b in obj.get('blocks', []) for v in b.get('views', []))
            if found:
                view_owners.append(row['id'])
                view_count += found
        self.checkpoint = {'prepared_at': stamp(), 'space_id': self.client.space,
                           'page_type_id': page['id'], 'objects': [r['id'] for r in rows],
                           'retype_candidates': candidates, 'view_owners': view_owners,
                           'collections': sorted(migrated_collections), 'etags': etags,
                           'type_etags': type_etags, 'retyped': {}, 'defaults': {}, 'archived': {},
                           'counts': {'objects_backed_up': len(rows), 'collections': len(migrated_collections),
                                      'rows_to_retype': len(candidates), 'view_owners': len(view_owners),
                                      'views_to_update': view_count, 'types_to_archive': len(self.owned_types)}}
        self.save()
        print(json.dumps(self.checkpoint['counts']), flush=True)

    def expected(self, target, retyped=False, defaults=False):
        obj = deepcopy(self.backup(target))
        if retyped:
            obj['type'] = 'page'
        if defaults:
            for block in obj.get('blocks', []):
                for view in block.get('views', []):
                    if view.get('default_type_id') in self.owned_types:
                        view['default_type_id'] = self.checkpoint['page_type_id']
        return obj

    def patch(self, target, ops, label, expected_before, expected_after):
        current, etag = self.read(target)
        if content_hash(current) != content_hash(expected_before):
            raise ValueError('Owner edit after cleanup backup: ' + target)
        body = {'ops': ops}
        self.client.scoped('PATCH', 'objects/' + target + '?dry_run=true&ids=full', body, etag=etag)
        receipt = self.client.scoped('PATCH', 'objects/' + target + '?ids=full', body,
                                     identity='kase:organize-v1:' + label + ':' + target, etag=etag)
        actual, new_etag = self.read(target)
        atomic_json(self.directory / 'after' / (target + '.json'), actual)
        if content_hash(actual) != content_hash(expected_after):
            atomic_json(self.directory / 'difference.json', {'id': target, 'expected': expected_after, 'actual': actual})
            raise ValueError('Unexpected content difference after ' + label + ': ' + target)
        return {'receipt': receipt, 'etag': new_etag, 'verified_at': stamp()}

    def retype(self, limit=None):
        changed = 0
        for target in self.checkpoint['retype_candidates']:
            if target in self.checkpoint['retyped']:
                continue
            before = self.expected(target, defaults=target in self.checkpoint['defaults'])
            after = self.expected(target, retyped=True, defaults=target in self.checkpoint['defaults'])
            self.checkpoint['retyped'][target] = self.patch(target, [{'op': 'set_type', 'type': 'page'}], 'retype', before, after)
            self.save()
            changed += 1
            if changed % 50 == 0:
                print(json.dumps({'rows_retyped': len(self.checkpoint['retyped'])}), flush=True)
            if limit and changed >= limit:
                break
        print(json.dumps({'rows_retyped': len(self.checkpoint['retyped'])}), flush=True)

    def defaults(self):
        for target in self.checkpoint['view_owners']:
            if target in self.checkpoint['defaults']:
                continue
            before = self.expected(target, retyped=target in self.checkpoint['retyped'])
            after = self.expected(target, retyped=target in self.checkpoint['retyped'], defaults=True)
            ops = [{'op': 'update_view', 'block': b['id'], 'view': v['id'],
                    'set': {'default_type_id': self.checkpoint['page_type_id']}}
                   for b in before.get('blocks', []) for v in b.get('views', [])
                   if v.get('default_type_id') in self.owned_types]
            self.checkpoint['defaults'][target] = self.patch(target, ops, 'defaults', before, after)
            self.save()
        print(json.dumps({'view_owners_updated': len(self.checkpoint['defaults'])}), flush=True)

    def archive(self):
        if set(self.checkpoint['retyped']) != set(self.checkpoint['retype_candidates']) or set(self.checkpoint['defaults']) != set(self.checkpoint['view_owners']):
            raise ValueError('Rows and view defaults must be verified first')
        if any(r['type'] in set(self.owned_types.values()) for r in self.search()):
            raise ValueError('A live object still uses a migration type')
        # Recheck all view settings before archiving their previous defaults.
        for target in self.checkpoint['view_owners']:
            obj, _ = self.read(target)
            if any(v.get('default_type_id') in self.owned_types for b in obj.get('blocks', []) for v in b.get('views', [])):
                raise ValueError('A view still uses a migration type')
        for target, key in self.owned_types.items():
            if target in self.checkpoint['archived']:
                continue
            before = json.loads((self.directory / 'types-before' / (target + '.json')).read_text())
            existing, _ = self.read(target)
            if existing.get('properties', {}).get('is_archived'):
                expected = deepcopy(before)
                expected['properties']['is_archived'] = True
                if content_hash(existing) != content_hash(expected):
                    raise ValueError('Archived type differs from its backup: ' + target)
                self.checkpoint['archived'][target] = {'receipt': self.checkpoint.get('archive_receipts', {}).get(target),
                                                      'recovered_from_readback': True, 'verified_at': stamp()}
                self.save()
                continue
            obj = self.client.scoped('GET', 'types/' + key + '?ids=full')
            etag = self.client.last_etag
            if content_hash(obj) != content_hash(before):
                raise ValueError('Type was edited after cleanup backup: ' + target)
            receipt = self.client.scoped('DELETE', 'types/' + key,
                                          identity='kase:organize-v1:archive:' + target, etag=etag)
            self.checkpoint.setdefault('archive_receipts', {})[target] = receipt
            self.save()
            archived, _ = self.read(target)
            atomic_json(self.directory / 'types-after' / (target + '.json'), archived)
            if not archived.get('properties', {}).get('is_archived'):
                raise ValueError('Type archive was not read back: ' + target)
            self.checkpoint['archived'][target] = {'receipt': receipt, 'verified_at': stamp()}
            self.save()
        print(json.dumps({'types_archived': len(self.checkpoint['archived'])}), flush=True)

    def verify(self):
        issues = []
        for index, target in enumerate(self.checkpoint['objects'], 1):
            actual, _ = self.read(target)
            expected = self.expected(target, retyped=target in self.checkpoint['retyped'], defaults=target in self.checkpoint['defaults'])
            if content_hash(actual) != content_hash(expected):
                issues.append(target)
            atomic_json(self.directory / 'verified' / (target + '.json'), actual)
            if index % 100 == 0:
                print(json.dumps({'objects_verified': index, 'differences': len(issues)}), flush=True)
        live = self.client.scoped('GET', 'types?limit=1000')['data']
        rows = self.search()
        collections = self.search(type='collection')
        result = {'verified_at': stamp(), 'objects': len(self.checkpoint['objects']),
                  'rows_retyped': len(self.checkpoint['retyped']), 'view_owners_updated': len(self.checkpoint['defaults']),
                  'types_archived': len(self.checkpoint['archived']), 'differences': issues,
                  'migration_types_remaining': sum(t['key'] in set(self.owned_types.values()) for t in live),
                  'rows_using_migration_types': sum(r['type'] in set(self.owned_types.values()) for r in rows),
                  'migrated_collections_visible': sum(r['id'] in self.checkpoint['collections'] for r in collections)}
        atomic_json(self.directory / 'verification.json', result)
        print(json.dumps(result), flush=True)
        if issues or result['migration_types_remaining'] or result['rows_using_migration_types'] or result['migrated_collections_visible'] != len(self.checkpoint['collections']):
            raise ValueError('Cleanup verification has unresolved differences')
        self.checkpoint['verification'] = result
        self.checkpoint['completed_at'] = stamp()
        self.save()
        self.ledger['organization_cleanup'] = result
        atomic_json(self.state / 'ledger.json', self.ledger)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--stage', choices=['prepare', 'retype', 'defaults', 'archive', 'verify'], required=True)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    organizer = Organizer(json.loads(args.config.read_text()))
    if args.stage != 'prepare' and not organizer.checkpoint.get('prepared_at'):
        raise ValueError('Prepare fresh backups first')
    if args.stage == 'retype':
        organizer.retype(args.limit)
    else:
        getattr(organizer, args.stage)()
