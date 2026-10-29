'use strict';
// Local tools-only HTTP facade, not an upstream HTTP server or SDK installation.
// Pinned upstream modules are private APIs: never silently upgrade this image.
const http = require('node:http');
const fs = require('node:fs');
const crypto = require('node:crypto');
const { TextDecoder } = require('node:util');
const { MCPEngine } = require('/opt/codegraph/lib/dist/mcp/engine.js');
const { MCPSession, SERVER_INFO } = require('/opt/codegraph/lib/dist/mcp/session.js');
const ROOT = '/home/developer/workspace/mcp-stack';
const PROTOCOL = '2025-06-18';
const BOOTSTRAP_PROTOCOLS = new Set(['2024-11-05', '2025-03-26', PROTOCOL, '2025-11-25']);
const TOOLS = new Set(['codegraph_explore', 'codegraph_status']);
const HOSTS = new Set(['codegraph-http', 'codegraph-http:8000', 'localhost:8000', '127.0.0.1:8000']);
const TTL = 600000, MAX_SESSIONS = 32, MAX_BODY = 65536;
const expected = JSON.parse(fs.readFileSync('/config/server.json', 'utf8')).api_key_sha256;
if (!/^[0-9a-f]{64}$/.test(expected) || SERVER_INFO.version !== '1.6.1' || process.version !== 'v24.16.0') {
  throw new Error('Pinned credential/runtime contract mismatch');
}
const engine = new MCPEngine({readOnly: true, watch: false, queryPool: false});
const sessions = new Map();
const record = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const has = (x, name) => Object.prototype.hasOwnProperty.call(x, name);
const rpcError = (id, code, message) => ({jsonrpc: '2.0', id, error: {code, message}});

class Transport {
  start(handler) { this.handler = handler; }
  stop() { this.handler = null; }
  send(response) {
    if (!this.response) this.response = response;
    else throw new Error('Unexpected second upstream response');
  }
  notify() { /* no advertised server notifications/SSE */ }
  request() { return Promise.reject(new Error('Server-to-client requests disabled')); }
  sendResult(id, result) { this.send({jsonrpc: '2.0', id, result}); }
  sendError(id, code, message) { this.send(rpcError(id, code, message)); }
  async dispatch(message) {
    if (!this.handler) throw new Error('Stopped session');
    this.response = null;
    await this.handler(message);
    if (!this.response && has(message, 'id')) throw new Error('No upstream response');
    return this.response;
  }
}

function remove(id) {
  const s = sessions.get(id);
  if (s) { sessions.delete(id); s.session.stop(); }
}
function cleanup() {
  const now = Date.now();
  for (const [id, s] of sessions) if (!s.busy && now - s.used > TTL) remove(id);
}
function header(req, name) {
  const matches = req.rawHeaders.filter((_, i) => i % 2 === 0 && req.rawHeaders[i].toLowerCase() === name);
  if (matches.length > 1) throw Object.assign(new Error('Duplicate header'), {status: name === 'authorization' ? 401 : 400});
  return req.headers[name];
}
function reply(res, status, data, headers = {}) {
  if (res.destroyed || res.writableEnded) return;
  let body = data === undefined ? '' : JSON.stringify(data);
  if (Buffer.byteLength(body) > 2097152) {
    status = 500;
    body = JSON.stringify(rpcError(null, -32603, 'Response size limit'));
  }
  res.writeHead(status, {'Cache-Control': 'no-store', ...headers,
    ...(body ? {'Content-Type': 'application/json; charset=utf-8'} : {})});
  res.end(body);
}
function fail(status, message) { throw Object.assign(new Error(message), {status}); }
async function body(req) {
  const chunks = []; let length = 0;
  for await (const chunk of req) {
    length += chunk.length;
    if (length > MAX_BODY) fail(413, 'Request size limit');
    chunks.push(chunk);
  }
  try { return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(Buffer.concat(chunks))); }
  catch { fail(400, 'Invalid JSON/UTF-8'); }
}

async function handle(req, res) {
  let id = null;
  try {
    const auth = header(req, 'authorization');
    if (typeof auth !== 'string' || !/^Bearer [0-9a-f]{64}$/.test(auth) ||
        !crypto.timingSafeEqual(Buffer.from(expected, 'hex'), crypto.createHash('sha256').update(auth.slice(7)).digest())) {
      reply(res, 401, {error: 'Unauthorized'}); return;
    }
    if (header(req, 'origin') !== undefined) fail(403, 'Browser Origin forbidden');
    if (!HOSTS.has(header(req, 'host'))) fail(421, 'Host forbidden');
    if (req.url === '/healthz' && req.method === 'GET') {
      reply(res, 200, {ready: engine.hasDefaultCodeGraph(), codegraph: SERVER_INFO.version, node: process.version}); return;
    }
    if (req.url !== '/mcp') fail(404, 'Unknown path');
    const version = header(req, 'mcp-protocol-version');
    // A sessionless initialize negotiates a supported fallback below. All
    // other methods retain strict validation against our sole supported version.
    if (req.method !== 'POST' && version !== undefined && version !== PROTOCOL) fail(400, 'Unsupported protocol');
    cleanup();
    const sid = header(req, 'mcp-session-id');
    if (sid !== undefined && (typeof sid !== 'string' || !/^[0-9a-f]{32}$/.test(sid) || !sessions.has(sid))) fail(404, 'Unknown session');
    if (req.method === 'DELETE') {
      if (!sid) fail(400, 'Missing session');
      if (sessions.get(sid).busy) fail(409, 'Session busy');
      remove(sid); reply(res, 204); return;
    }
    if (req.method === 'GET') { reply(res, 405, undefined, {Allow: 'POST, DELETE'}); return; }
    if (req.method !== 'POST') { reply(res, 405, undefined, {Allow: 'POST, DELETE'}); return; }
    if (!/^application\/json(?:\s*;.*)?$/i.test(header(req, 'content-type') || '')) fail(415, 'Expected JSON');
    const accept = header(req, 'accept') || '';
    if (!accept.includes('application/json') || !accept.includes('text/event-stream')) fail(406, 'Expected MCP Accept types');
    const msg = await body(req);
    if (!record(msg) || msg.jsonrpc !== '2.0' || typeof msg.method !== 'string' ||
        (has(msg, 'id') && !(typeof msg.id === 'string' || (typeof msg.id === 'number' && Number.isFinite(msg.id)))) ||
        (has(msg, 'params') && !record(msg.params))) fail(400, 'Invalid JSON-RPC message');
    id = has(msg, 'id') ? msg.id : null;
    if (version !== undefined && !(msg.method === 'initialize' && !sid
        ? BOOTSTRAP_PROTOCOLS.has(version) : version === PROTOCOL)) fail(400, 'Unsupported protocol');
    if (msg.method === 'initialize') {
      if (sid || !has(msg, 'id')) fail(400, 'Invalid initialization');
      const p = msg.params;
      if (!record(p) || typeof p.protocolVersion !== 'string' || !record(p.capabilities) ||
          !record(p.clientInfo) || typeof p.clientInfo.name !== 'string' || typeof p.clientInfo.version !== 'string') fail(400, 'Invalid initialization parameters');
      if (has(p, 'rootUri') || has(p, 'workspaceFolders') || has(p, 'projectPath')) {
        reply(res, 200, rpcError(id, -32602, 'mcp-stack gate: project selectors forbidden')); return;
      }
      if (sessions.size >= MAX_SESSIONS) fail(429, 'Session capacity');
      const transport = new Transport();
      const session = new MCPSession(transport, engine, {explicitProjectPath: ROOT});
      session.start();
      let result;
      try { result = await transport.dispatch({...msg, params: {...p, capabilities: {}}}); }
      catch (error) { session.stop(); throw error; }
      if (result.result?.serverInfo?.version !== '1.6.1' || result.result?.protocolVersion !== '2024-11-05') {
        session.stop(); throw new Error('Native handshake contract mismatch');
      }
      const newId = crypto.randomBytes(16).toString('hex');
      sessions.set(newId, {session, transport, ready: false, busy: false, used: Date.now()});
      // This facade owns the HTTP protocol and reduced capabilities; do not
      // describe the upstream's legacy stdio handshake as native HTTP support.
      reply(res, 200, {jsonrpc: '2.0', id, result: {protocolVersion: PROTOCOL,
        capabilities: {tools: {}}, serverInfo: {name: 'mcp-stack-codegraph-http', version: '1.0.1'},
        instructions: 'Read-only CodeGraph 1.6.1; partial index of two Python verification scripts and one synthetic fixture only. No watcher or automatic refresh. Index misses do not prove absent source. Use only relevant coding tasks; never auto-index or use all memory tools by default.'}}, {'Mcp-Session-Id': newId});
      return;
    }
    if (!sid) fail(400, 'Missing session');
    const s = sessions.get(sid);
    if (s.busy) fail(409, 'Session busy');
    s.used = Date.now();
    if (!has(msg, 'id')) {
      if (msg.method !== 'notifications/initialized' || s.ready) fail(400, 'Unsupported notification');
      s.ready = true; reply(res, 202); return;
    }
    if (!s.ready) fail(400, 'Session not initialized');
    if (msg.method === 'tools/call') {
      const p = msg.params;
      if (!record(p) || typeof p.name !== 'string' || (has(p, 'arguments') && !record(p.arguments))) {
        reply(res, 200, rpcError(id, -32602, 'mcp-stack gate: invalid tool arguments')); return;
      }
      if (!TOOLS.has(p.name) || has(p.arguments || {}, 'projectPath')) {
        reply(res, 200, rpcError(id, -32602, 'mcp-stack gate: tool/project forbidden')); return;
      }
    } else if (!['tools/list', 'ping', 'resources/list', 'resources/templates/list', 'prompts/list'].includes(msg.method)) {
      reply(res, 200, rpcError(id, -32601, 'mcp-stack gate: method forbidden')); return;
    }
    s.busy = true;
    let timer;
    try {
      const result = await Promise.race([s.transport.dispatch(msg), new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Request timeout')), 30000);
      })]);
      if (msg.method === 'tools/list' && result.result) {
        result.result.tools = result.result.tools.filter(t => TOOLS.has(t.name)).map(t => {
          const copy = structuredClone(t);
          if (copy.inputSchema?.properties) delete copy.inputSchema.properties.projectPath;
          if (Array.isArray(copy.inputSchema?.required)) copy.inputSchema.required = copy.inputSchema.required.filter(x => x !== 'projectPath');
          return copy;
        });
      }
      reply(res, 200, result);
    } catch {
      remove(sid); reply(res, 500, rpcError(id, -32603, 'Backend request failed; session terminated'));
    } finally { clearTimeout(timer); s.busy = false; }
  } catch (error) {
    reply(res, error.status || 500, rpcError(id, error.status ? -32600 : -32603,
      error.status ? error.message : 'Internal failure'));
  }
}

async function main() {
  engine.setProjectPathHint(ROOT);
  await engine.ensureInitialized(ROOT);
  if (!engine.hasDefaultCodeGraph()) throw new Error('Existing read-only index failed to open');
  const server = http.createServer((req, res) => { void handle(req, res); });
  server.requestTimeout = 35000; server.headersTimeout = 5000;
  const expiration = setInterval(cleanup, 60000); expiration.unref();
  server.listen(8000, '0.0.0.0', () => console.log('CodeGraph read-only HTTP test ready; no published port'));
  let stopping = false;
  const stop = () => {
    if (stopping) return; stopping = true;
    clearInterval(expiration);
    for (const id of sessions.keys()) remove(id);
    server.close(); server.closeAllConnections();
    void engine.stop().then(() => process.exit(0), () => process.exit(1));
  };
  process.on('SIGTERM', stop); process.on('SIGINT', stop);
}
main().catch(() => { console.error('CodeGraph HTTP startup failed; no fallback/re-indexing'); process.exit(1); });
