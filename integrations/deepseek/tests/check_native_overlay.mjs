// Offline validation with the installed official parser, patch composer and
// MCP Config schema and SDK handshake with stubbed fetch. Never prepare a
// profile, evaluate !!js, boot, read credentials or use a real network.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync, realpathSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { Script } from 'node:vm';

assert.equal(process.argv.length, 3, 'Pass the existing CLI root; never auto-install it.');
// Match Node's normal module resolution for symlinked mise/Aube packages.
const cliRoot = realpathSync(resolve(process.argv[2]));
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const metadata = JSON.parse(readFileSync(join(cliRoot, 'package.json'), 'utf8'));
assert.equal(metadata.name, '@deepseek-ai/dsh');
assert.equal(metadata.version, '0.2.0-rc.2');
assert.equal(process.version, 'v24.19.0');
const require = createRequire(join(cliRoot, 'package.json'));
const pluginRoot = dirname(require.resolve('@deepseek-ai/dsh-mcp-client/package.json'));
assert.equal(JSON.parse(readFileSync(join(pluginRoot, 'package.json'))).version, '0.2.0-rc.2');
assert.equal(createHash('sha256').update(readFileSync(join(pluginRoot, 'lib/index.js'))).digest('hex'),
             '758d8fc473b700b5d351158d06ce9f9e92c16e8b25497b08bb7bd2122a87f5dd');
const { loadOverlayPatches, renderConfigDump } = await import(
  pathToFileURL(require.resolve('@deepseek-ai/dsh-app-boot')).href);
const { Config } = await import(pathToFileURL(join(pluginRoot, 'lib/index.js')).href);
const { Client, StreamableHTTPClientTransport } = await import(
  pathToFileURL(require.resolve('@modelcontextprotocol/client')).href);

// Exercise the same SDK and negotiation options as the official plugin,
// rather than proving compatibility with a different HTTP client.
const nativeFetch = globalThis.fetch;
globalThis.fetch = () => assert.fail('Offline SDK test attempted real network');
try {
  for (const denied of [false, true]) {
    const methods = [];
    const fetchStub = async (url, init) => {
      assert.equal(new URL(url).hostname, 'offline.invalid');
      if (init.method === 'GET') return new Response(null, { status: 405 });
      if (init.method === 'DELETE') return new Response(null, { status: 202 });
      const message = JSON.parse(init.body);
      methods.push(message.method);
      const headers = { 'Content-Type': 'application/json',
        'Mcp-Session-Id': 'OFFLINE_SESSION' };
      if (message.method === 'server/discover') return new Response(JSON.stringify({
        jsonrpc: '2.0', id: message.id,
        error: { code: -32601, message: 'Method not found' },
      }), { status: denied ? 403 : 400, headers });
      if (message.method === 'initialize') return new Response(JSON.stringify({
        jsonrpc: '2.0', id: message.id, result: {
          protocolVersion: '2025-11-25', capabilities: { tools: {} },
          serverInfo: { name: 'offline', version: '1' },
        },
      }), { status: 200, headers });
      if (message.method === 'notifications/initialized') {
        return new Response(null, { status: 202 });
      }
      if (message.method === 'tools/list') return new Response(JSON.stringify({
        jsonrpc: '2.0', id: message.id, result: { tools: [{
          name: 'codegraph_codegraph_explore',
          inputSchema: { type: 'object', properties: { query: { type: 'string' } } },
        }] },
      }), { status: 200, headers });
      assert.fail('Unexpected offline method: ' + message.method);
    };
    const client = new Client({ name: 'dsh-mcp-client', version: '0.0.1' }, {
      capabilities: {}, versionNegotiation: { mode: 'auto' },
    });
    const transport = new StreamableHTTPClientTransport(new URL('http://offline.invalid/mcp'), {
      fetch: fetchStub, requestInit: { headers: { Authorization: 'Bearer OFFLINE_PLACEHOLDER' } },
    });
    try {
      if (denied) {
        await assert.rejects(client.connect(transport), (error) => error?.data?.status === 403);
        assert.deepEqual(methods, ['server/discover']);
      } else {
        await client.connect(transport);
        assert.equal(transport.protocolVersion, '2025-11-25');
        assert.equal((await client.listTools()).tools.length, 1);
        assert.deepEqual(methods, ['server/discover', 'initialize',
          'notifications/initialized', 'tools/list']);
        await transport.terminateSession();
      }
    } finally {
      await client.close();
    }
  }
} finally {
  globalThis.fetch = nativeFetch;
}
console.log('PASS: 2 offline SDK regressions: legacy negotiation/discovery; terminal auth denial without retry.');
const overlay = join(root, 'infra/harnesses/deepseek/mcp-stack.cordis.yml');
const patches = loadOverlayPatches('mcp-stack-offline', overlay);
const rows = patches[0].insert;
assert.equal(rows.length, 2);
assert.deepEqual(rows.map((row) => row.config.url).sort(), [
  'http://127.0.0.1:58081/mcp/codegraph',
  'http://127.0.0.1:58081/mcp/graphify',
]);
for (const row of rows) {
  assert.deepEqual(Object.keys(row.config.headers), ['Authorization']);
  const expr = row.config.headers.Authorization.__jsExpr;
  assert.equal(typeof expr, 'string');
  new Script(`(${expr});`); // Syntax compilation only: deliberately never run.
  const config = structuredClone(row.config);
  // Validate non-secret shape; expression resolution is a later live gate.
  config.headers.Authorization = 'Bearer OFFLINE_PLACEHOLDER_NOT_A_KEY';
  assert.equal(Config(config).transport, 'streamable-http');
}
const fixture = join(root, 'integrations/deepseek/tests/fixtures/empty.cordis.yml');
const layers = ['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-web-app'].map((name) => {
  const packageRoot = dirname(require.resolve(name + '/package.json'));
  return { label: name, patches: loadOverlayPatches('mcp-stack-offline', join(packageRoot, 'cordis.patch.yml')) };
});
// Synthetic vision row validates the disable patch without touching user state.
layers.push({ label: 'synthetic vision row', patches: [{ insert: [
  { id: 'vision-toolkit', name: '@anionex/dsh-vision-toolkit' },
] }] });
layers.push({ label: overlay, patches });
const noVision = join(root, 'infra/harnesses/deepseek/no-vision.cordis.yml');
layers.push({ label: noVision, patches: loadOverlayPatches('mcp-stack-offline', noVision) });
const warnings = [];
const dump = renderConfigDump('mcp-stack-offline', fixture, layers, (line) => warnings.push(line));
assert.deepEqual(warnings, []);
assert.match(dump, /id: mcp-stack-graphify/);
assert.match(dump, /id: mcp-stack-codegraph/);
assert.match(dump, /id: vision-toolkit[\s\S]*?disabled: true/);
assert.match(dump, /MCP_STACK_GATEWAY_KEY_FILE/);
console.log('PASS: native parse/composition, JS syntax, MCP schema with inert auth placeholder; no boot, expression evaluation or network.');
