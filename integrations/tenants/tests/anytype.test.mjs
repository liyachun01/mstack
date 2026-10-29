import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {authenticate, tenantFile, validateGrant} from '../anytype.mjs';
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const registry = {version: 1, tenants: {
  'project-a': {enabled: true, token_sha256: hash('a'.repeat(64)), space_id: 'space-a'},
  'project-b': {enabled: true, token_sha256: hash('b'.repeat(64)), space_id: 'space-b'},
}};
test('valid clients select their own channel binding', () => {
  assert.equal(authenticate(registry, {tenant:'project-a',token:'a'.repeat(64)}).entry.space_id, 'space-a');
});
test('another tenant cannot be selected with the same credential', () => {
  assert.throws(() => authenticate(registry, {tenant:'project-b',token:'a'.repeat(64)}));
});
test('unknown tenant, traversal and injected config fail closed', () => {
  for (const supplied of [{tenant:'../project-a',token:'a'.repeat(64)},
    {tenant:'missing',token:'a'.repeat(64)}, {tenant:'project-a',token:'a'.repeat(64),space_id:'space-b'}])
    assert.throws(() => authenticate(registry, supplied));
});
test('a credential symlink cannot escape the registered tenant directory', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'mstack-tenant-'));
  try {
    fs.mkdirSync(path.join(root,'tenants/project-a'), {recursive:true});
    fs.writeFileSync(path.join(root,'outside'), 'test');
    fs.symlinkSync(path.join(root,'outside'),path.join(root,'tenants/project-a/anytype_api_key'));
    assert.throws(() => tenantFile(root,'project-a','anytype_api_key'));
  } finally { fs.rmSync(root,{recursive:true}); }
});
test('Anytype requires the exact single-channel grant and rejects broad or foreign keys', () => {
  const valid = {all_spaces:false,permission:'readwrite',spaces:[{id:'space-a'}]};
  validateGrant(valid,'space-a');
  assert.throws(() => validateGrant(valid,'space-b'));
  assert.throws(() => validateGrant({...valid,all_spaces:true},'space-a'));
  assert.throws(() => validateGrant({...valid,spaces:[{id:'space-a'},{id:'space-b'}]},'space-a'));
});
