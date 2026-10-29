// The shared runtime chooses credentials from authenticated, server-owned tenants.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';

export function authenticate(registry, supplied) {
  if (!supplied || typeof supplied !== 'object' ||
      Object.keys(supplied).sort().join(',') !== 'tenant,token' ||
      typeof supplied.tenant !== 'string' || !/^[a-z][a-z0-9-]{0,62}$/.test(supplied.tenant) ||
      typeof supplied.token !== 'string' || !/^[a-f0-9]{64}$/.test(supplied.token) || registry.version !== 1)
    throw Error('Invalid tenant authentication');
  const entry = registry.tenants?.[supplied.tenant];
  const expected = entry?.token_sha256;
  const actual = crypto.createHash('sha256').update(supplied.token).digest();
  if (typeof expected !== 'string' || !/^[a-f0-9]{64}$/.test(expected) ||
      !crypto.timingSafeEqual(actual, Buffer.from(expected, 'hex')) || entry.enabled !== true)
    throw Error('Invalid tenant authentication');
  return {tenant: supplied.tenant, entry};
}

function bootstrap() {
  const bytes = [], byte = Buffer.alloc(1);
  while (bytes.length < 4096 && fs.readSync(0, byte, 0, 1, null)) {
    if (byte[0] === 10) return JSON.parse(Buffer.from(bytes).toString());
    bytes.push(byte[0]);
  }
  throw Error('Invalid tenant authentication');
}

export function tenantFile(root, tenant, name) {
  const folder = path.join(fs.realpathSync(root), 'tenants', tenant);
  const target = path.join(folder, name);
  if (fs.lstatSync(folder).isSymbolicLink() || fs.lstatSync(target).isSymbolicLink() ||
      !fs.statSync(target).isFile() || fs.realpathSync(target) !== target)
    throw Error('Invalid tenant file');
  return target;
}

export function validateGrant(grant, space) {
  if (grant?.all_spaces !== false || grant?.permission !== 'readwrite' ||
      grant?.spaces?.length !== 1 || grant.spaces[0].id !== space)
    throw Error('Anytype grant differs from tenant');
}

function whoami(headers) {
  // Node fetch ignores the explicit Host header here; the desktop API requires it.
  return new Promise((resolve, reject) => {
    const request = http.get({hostname:'host.docker.internal', port:31009,
      path:'/v2/auth/whoami?ids=full', headers}, response => {
      let data = '';
      response.setEncoding('utf8');
      response.on('data', chunk => { data += chunk; if (data.length > 65536) request.destroy(); });
      response.on('error', reject);
      response.on('end', () => {
        try {
          if (response.statusCode !== 200) throw Error('Anytype grant unavailable');
          resolve(JSON.parse(data).grant);
        } catch (error) { reject(error); }
      });
    });
    request.setTimeout(10000, () => request.destroy(new Error('Anytype grant timeout')));
    request.on('error', reject);
  });
}

async function main() {
  const root = '/runtime';
  const {tenant, entry} = authenticate(JSON.parse(fs.readFileSync(root + '/registry.json')), bootstrap());
  const keyPath = tenantFile(root, tenant, 'anytype_api_key');
  if (fs.statSync(keyPath).mode & 0o077) throw Error('Private credential required');
  const key = fs.readFileSync(keyPath, 'utf8').trim();
  const headers = {Authorization: 'Bearer ' + key, 'Anytype-Version': '2025-11-08', Host: '127.0.0.1:31009'};
  // Refuse startup if an owner has accidentally installed an all-spaces/wrong key.
  validateGrant(await whoami(headers), entry.space_id);
  const schema = tenantFile(root, tenant, 'openapi.json');
  const child = spawn(process.execPath, ['/app/node_modules/@anyproto/anytype-mcp/bin/cli.mjs', 'run', schema], {
    stdio: 'inherit', env: {...process.env, ANYTYPE_API_BASE_URL: 'http://host.docker.internal:31009',
      OPENAPI_MCP_HEADERS: JSON.stringify(headers)}
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
  child.on('error', () => { process.exitCode = 1; });
  child.on('exit', code => process.exit(code ?? 1));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(() => { console.error('mstack: tenant authentication or Anytype grant unavailable'); process.exitCode = 1; });
}
