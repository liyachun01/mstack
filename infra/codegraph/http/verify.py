"""Direct CodeGraph HTTP qualification; does not start services."""

import argparse
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOST = "/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack"
NAME = "mcp-stack-codegraph-http-test"
IMAGE = "sha256:4b8cb16b0c3b5bb7446c3f90b8fd2b12f099b0d0029f8bf30113ad482bf75420"
STATE = ROOT / "infra/codegraph/state/mcp-stack"
SOURCES = (
    "scripts/verify-basic-memory.py", "scripts/verify-codegraph.py",
    "infra/codegraph/fixtures/call-chain.py", "infra/codegraph/project.json",
)

PROBE = r'''
const http = require('node:http');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const cfg = JSON.parse(fs.readFileSync(0, 'utf8'));
let stage = 'readiness';
const defaults = {Authorization: 'Bearer ' + cfg.key, Host: 'codegraph-http:8000',
  Accept: 'application/json, text/event-stream', 'Content-Type': 'application/json',
  'MCP-Protocol-Version': '2025-06-18'};
function request(payload, options = {}) {
  return new Promise((resolve, reject) => {
    const headers = {...defaults, ...options.headers};
    for (const key of options.remove || []) delete headers[key];
    const req = http.request({hostname: '127.0.0.1', port: 8000, path: options.path || '/mcp',
      method: options.method || 'POST', headers}, res => {
      const chunks = []; let size = 0;
      res.on('data', chunk => { size += chunk.length; if (size > 2097152) req.destroy(new Error('response limit')); else chunks.push(chunk); });
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let body; try { body = text ? JSON.parse(text) : null; } catch { reject(new Error('non-JSON response')); return; }
        resolve({status: res.statusCode, headers: res.headers, body});
      });
      res.on('error', reject);
    });
    req.setTimeout(35000, () => req.destroy(new Error('timeout')));
    req.on('error', reject);
    req.end(options.raw !== undefined ? options.raw : payload ? JSON.stringify(payload) : undefined);
  });
}
const init = {jsonrpc: '2.0', id: 1, method: 'initialize', params: {
  protocolVersion: '2025-06-18', capabilities: {roots: {}}, clientInfo: {name: 'direct-qualification', version: '1.0'}}};
const sessions = [];
class Session {
  async start() {
    const r = await request(init);
    assert.equal(r.status, 200); assert.equal(r.body.result.protocolVersion, '2025-06-18');
    assert.deepEqual(r.body.result.capabilities, {tools: {}});
    assert.equal(r.body.result.serverInfo.name, 'mcp-stack-codegraph-http');
    assert.equal(r.body.result.serverInfo.version, '1.0.1');
    assert.match(r.body.result.instructions, /partial index/);
    this.id = r.headers['mcp-session-id']; assert.match(this.id, /^[0-9a-f]{32}$/);
    sessions.push(this); this.next = 1;
    const n = await request({jsonrpc: '2.0', method: 'notifications/initialized'}, {headers: {'Mcp-Session-Id': this.id}});
    assert.equal(n.status, 202); assert.equal(n.body, null); return this;
  }
  async rpc(method, params = {}, denied = false) {
    const id = ++this.next;
    const r = await request({jsonrpc: '2.0', id, method, params}, {headers: {'Mcp-Session-Id': this.id}});
    assert.equal(r.status, 200); assert.equal(r.body.id, id);
    if (denied) { assert.ok(r.body.error); assert.match(r.body.error.message, /^mcp-stack gate:/); return r.body; }
    assert.ok(!r.body.error); assert.ok(!r.body.result?.isError); return r.body.result;
  }
  async call(name, args = {}, denied = false) {
    const r = await this.rpc('tools/call', {name, arguments: args}, denied);
    return denied ? r : r.content.map(x => x.text || '').join('\n');
  }
  async close() { return request(undefined, {method: 'DELETE', headers: {'Mcp-Session-Id': this.id}}); }
}
async function main() {
  const health = await request(undefined, {path: '/healthz', method: 'GET'});
  assert.equal(health.status, 200); assert.deepEqual(health.body, {ready: true, codegraph: '1.6.1', node: 'v24.16.0'});
  console.log('PASS pinned bundled runtime/native exports and ready read-only index');
  stage = 'authentication and HTTP validation';
  assert.equal((await request(init, {remove: ['Authorization']})).status, 401);
  assert.equal((await request(init, {headers: {Authorization: 'Bearer ' + '0'.repeat(64)}})).status, 401);
  assert.equal((await request(init, {headers: {Authorization: ['Bearer ' + cfg.key, 'Bearer ' + cfg.key]}})).status, 401);
  for (const host of ['codegraph-http', 'codegraph-http:8000']) {
    assert.equal((await request(undefined, {path: '/healthz', method: 'GET', headers: {Host: host}})).status, 200);
  }
  assert.equal((await request(init, {headers: {Host: 'invalid.example:8000'}})).status, 421);
  assert.equal((await request(init, {headers: {Origin: 'https://invalid.example'}})).status, 403);
  assert.equal((await request(init, {headers: {Origin: 'null'}})).status, 403);
  const unknown = await request(init, {headers: {'MCP-Protocol-Version': '1900-01-01'}});
  assert.equal(unknown.status, 400); assert.ok(!unknown.headers['mcp-session-id']);
  assert.equal((await request(init, {headers: {Accept: 'application/json'}})).status, 406);
  assert.equal((await request(init, {headers: {'Content-Type': 'text/plain'}})).status, 415);
  assert.equal((await request(undefined, {raw: '{'})).status, 400);
  assert.equal((await request(undefined, {raw: JSON.stringify([init])})).status, 400);
  assert.equal((await request(undefined, {raw: Buffer.from([0xff])})).status, 400);
  assert.equal((await request(undefined, {raw: 'x'.repeat(65537)})).status, 413);
  assert.equal((await request(init, {path: '/foreign'})).status, 404);
  assert.equal((await request(undefined, {method: 'GET'})).status, 405);
  console.log('PASS missing/wrong/duplicate auth, Host/Origin, protocol/Accept/type/path/JSON/UTF-8/size limits');
  stage = 'bootstrap fallback and strict negotiated protocol';
  for (const preference of [null, '2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25']) {
    const preferredInit = {...init, params: {...init.params, protocolVersion: preference || '2025-11-25'}};
    const r = await request(preferredInit, preference === null
      ? {remove: ['MCP-Protocol-Version']} : {headers: {'MCP-Protocol-Version': preference}});
    assert.equal(r.status, 200); assert.equal(r.body.result.protocolVersion, '2025-06-18');
    assert.equal(r.body.result.serverInfo.version, '1.0.1');
    assert.deepEqual(r.body.result.capabilities, {tools: {}});
    const sid = r.headers['mcp-session-id']; assert.match(sid, /^[0-9a-f]{32}$/);
    const selected = {'Mcp-Session-Id': sid};
    try {
      assert.equal((await request({jsonrpc: '2.0', method: 'notifications/initialized'}, {headers: selected})).status, 202);
      assert.equal((await request(init, {headers: selected})).status, 400);
      for (const bad of ['2025-11-25', '1900-01-01']) {
        const headers = {...selected, 'MCP-Protocol-Version': bad};
        assert.equal((await request({jsonrpc: '2.0', id: 2, method: 'tools/list'}, {headers})).status, 400);
        assert.equal((await request(undefined, {method: 'GET', headers})).status, 400);
        assert.equal((await request(undefined, {method: 'DELETE', headers})).status, 400);
      }
      const list = await request({jsonrpc: '2.0', id: 3, method: 'tools/list'}, {headers: selected});
      assert.equal(list.status, 200); assert.deepEqual(list.body.result.tools.map(x => x.name), ['codegraph_explore']);
      const source = await request({jsonrpc: '2.0', id: 4, method: 'tools/call', params: {
        name: 'codegraph_explore', arguments: {query: 'scripts/verify-basic-memory.py Session.send'}}}, {headers: selected});
      assert.equal(source.status, 200); assert.ok(!source.body.error && !source.body.result.isError);
      const text = source.body.result.content.map(x => x.text || '').join('\n');
      assert.ok(text.includes('verify-basic-memory.py') && text.includes('jsonrpc'));
      const noHeader = await request({jsonrpc: '2.0', id: 5, method: 'ping'}, {headers: selected, remove: ['MCP-Protocol-Version']});
      assert.equal(noHeader.status, 200); assert.deepEqual(noHeader.body.result, {});
    } finally {
      assert.equal((await request(undefined, {method: 'DELETE', headers: selected})).status, 204);
    }
  }
  console.log('PASS five bootstrap preferences negotiate 2025-06-18; newer/unknown subsequent POST/GET/DELETE rejected without deleting sessions');
  stage = 'initialization scope';
  for (const params of [{rootUri: 'file:///foreign'}, {workspaceFolders: [{uri: 'file:///foreign', name: 'foreign'}]}, {projectPath: '/foreign'}]) {
    const r = await request({...init, params: {...init.params, ...params}});
    assert.equal(r.status, 200); assert.match(r.body.error.message, /^mcp-stack gate:/);
    assert.ok(!r.headers['mcp-session-id']);
  }
  assert.equal((await request({jsonrpc: '2.0', id: 7, method: 'tools/list'})).status, 400);
  assert.equal((await request(init, {headers: {'Mcp-Session-Id': '0'.repeat(32)}})).status, 404);
  const premature = await request(init);
  assert.equal((await request({jsonrpc: '2.0', id: 7, method: 'tools/list'}, {headers: {'Mcp-Session-Id': premature.headers['mcp-session-id']}})).status, 400);
  assert.equal((await request(undefined, {method: 'DELETE', headers: {'Mcp-Session-Id': premature.headers['mcp-session-id']}})).status, 204);
  const first = await new Session().start();
  const tools = (await first.rpc('tools/list')).tools;
  assert.deepEqual(tools.map(x => x.name), ['codegraph_explore']);
  assert.ok(!tools[0].inputSchema.properties.projectPath);
  assert.deepEqual(await first.rpc('ping'), {});
  for (const [method, key] of [['resources/list', 'resources'], ['resources/templates/list', 'resourceTemplates'], ['prompts/list', 'prompts']]) {
    assert.deepEqual((await first.rpc(method))[key], []);
  }
  console.log('PASS fixed-root initialization; actual small-project tool surface; empty resources/prompts');
  stage = 'tool and scope gates';
  for (const name of ['codegraph_search', 'codegraph_sync', 'unknown_tool']) await first.call(name, {}, true);
  for (const path of ['/foreign', '/home/developer/workspace/mcp-stack']) await first.call('codegraph_explore', {query: 'fixture_handle_request', projectPath: path}, true);
  for (const method of ['resources/read', 'prompts/get', 'roots/list', 'unknown/method']) await first.rpc(method, {uri: 'file:///foreign'}, true);
  console.log('PASS direct-call excluded/unknown tools, project override and resource/prompt/root-method gates');
  stage = 'useful results';
  const fixture = await first.call('codegraph_explore', {query: 'fixture_handle_request fixture_read_payload fixture_normalize_payload'});
  for (const name of ['fixture_handle_request', 'fixture_read_payload', 'fixture_normalize_payload']) assert.ok(fixture.includes(name));
  const source = await first.call('codegraph_explore', {query: 'scripts/verify-basic-memory.py Session.send'});
  assert.ok(source.includes('verify-basic-memory.py') && source.includes('jsonrpc'));
  const status = await first.call('codegraph_status'); assert.ok(status);
  console.log('PASS real source retrieval, synthetic call-chain query and explicitly permitted native status');
  stage = 'concurrent independent source sessions';
  const a = await new Session().start(), b = await new Session().start();
  assert.notEqual(a.id, b.id); assert.notEqual(first.id, a.id);
  const query = {query: 'scripts/verify-basic-memory.py Session.send'};
  const results = await Promise.all([a.call('codegraph_explore', query), b.call('codegraph_explore', query)]);
  assert.ok(results.every(x => x.includes('verify-basic-memory.py') && x.includes('jsonrpc')));
  const repeated = await a.call('codegraph_explore', query);
  assert.ok(repeated); // Native same-session dedup is allowed, never shared across callers.
  const fresh = await new Session().start();
  assert.ok((await fresh.call('codegraph_explore', query)).includes('jsonrpc'));
  assert.equal((await a.close()).status, 204);
  assert.equal((await request({jsonrpc: '2.0', id: 22, method: 'ping'}, {headers: {'Mcp-Session-Id': a.id}})).status, 404);
  assert.deepEqual(await b.rpc('ping'), {});
  console.log('PASS simultaneous fresh source calls, reconnect and delete-one-session isolation');
  stage = 'bounded session capacity';
  const extra = [];
  while (sessions.length - 1 + extra.length < 32) {
    const r = await request(init); assert.equal(r.status, 200); extra.push(r.headers['mcp-session-id']);
  }
  assert.equal((await request(init)).status, 429);
  for (const sid of extra) assert.equal((await request(undefined, {method: 'DELETE', headers: {'Mcp-Session-Id': sid}})).status, 204);
  for (const s of sessions.filter(x => x !== a)) assert.equal((await s.close()).status, 204);
  console.log('PASS 32-session bound and explicit session cleanup');
}
main().catch(error => { console.error('FAIL direct HTTP probe at ' + stage + ': ' + error.name); process.exitCode = 1; });
'''


def command(args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True,
                          timeout=25, check=True).stdout


def hashes():
    paths = list(STATE.rglob("*")) + [ROOT / name for name in SOURCES]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


def verify_container(name, project, restart, gateway_connected=False):
    c = json.loads(command(["macctl", "run", "docker", "inspect", name]))[0]
    config, host = c["Config"], c["HostConfig"]
    assert config["Image"] == IMAGE and c["Image"] == IMAGE
    assert config["User"] == "501:501"
    assert config["Labels"]["com.docker.compose.project"] == project
    assert config["Labels"]["com.docker.compose.service"] == "codegraph-http"
    assert config["Entrypoint"] == ["/opt/codegraph/node"]
    assert config["Cmd"] == ["--liftoff-only", "--disable-warning=ExperimentalWarning", "/opt/mcp-stack/serve_http.cjs"]
    assert host["ReadonlyRootfs"] and not host["Privileged"] and host["Init"]
    assert host["RestartPolicy"]["Name"] == restart and host["PidsLimit"] == 128
    assert host["Memory"] == 2 * 1024 ** 3 and host["NanoCpus"] == 2 * 10 ** 9
    assert "ALL" in host["CapDrop"] and "no-new-privileges:true" in host["SecurityOpt"]
    assert not c["NetworkSettings"].get("Ports") and not host.get("PortBindings")
    expected = {
        f"{HOST}/infra/codegraph/http/serve_http.cjs": "/opt/mcp-stack/serve_http.cjs",
        f"{HOST}/infra/codegraph/state/http/server.json": "/config/server.json",
        **{f"{HOST}/{p}": f"/home/developer/workspace/mcp-stack/{p}" for p in SOURCES[:3]},
        f"{HOST}/infra/codegraph/project.json": "/home/developer/workspace/mcp-stack/codegraph.json",
        f"{HOST}/infra/codegraph/state/mcp-stack": "/home/developer/workspace/mcp-stack/.codegraph",
    }
    binds = {m["Source"]: m["Destination"] for m in c["Mounts"] if m["Type"] == "bind"}
    assert binds == expected and all(not m["RW"] for m in c["Mounts"] if m["Type"] == "bind")
    assert "/tmp" in host["Tmpfs"] and "size=67108864" in host["Tmpfs"]["/tmp"]
    assert set(c["NetworkSettings"]["Networks"]) == {"mcp-stack-codegraph-transport"}
    n = json.loads(command(["macctl", "run", "docker", "network", "inspect", "mcp-stack-codegraph-transport"]))[0]
    members = {c["Id"]}
    if gateway_connected:
        gateway = json.loads(command(["macctl", "run", "docker", "inspect", "mcp-stack-agentgateway-1"]))[0]
        assert gateway["State"]["Running"]
        assert gateway["Config"]["Labels"]["com.docker.compose.project"] == "mcp-stack"
        assert gateway["Config"]["Labels"]["com.docker.compose.service"] == "agentgateway"
        assert set(gateway["NetworkSettings"]["Networks"]) == {
            "mcp-stack-gateway-local", "mcp-stack-graphify-transport", "mcp-stack-codegraph-transport"}
        members.add(gateway["Id"])
    assert n["Internal"] and set(n["Containers"]) == members
    env = dict(e.split("=", 1) for e in config["Env"])
    expected_env = {"CODEGRAPH_TELEMETRY": "0", "DO_NOT_TRACK": "1", "CODEGRAPH_NO_UPDATE_CHECK": "1",
                    "CODEGRAPH_NO_DAEMON": "1", "CODEGRAPH_NO_WATCH": "1", "CODEGRAPH_MCP_TOOLS": "explore,status",
                    "CODEGRAPH_QUERY_POOL_SIZE": "0", "NODE_COMPILE_CACHE": "/tmp/node-compile-cache",
                    "HOME": "/tmp/codegraph-home", "XDG_CACHE_HOME": "/tmp/codegraph-cache", "XDG_CONFIG_HOME": "/tmp/codegraph-config"}
    assert all(env.get(k) == v for k, v in expected_env.items())
    assert not any("KEY" in k or "TOKEN" in k for k in env)
    print("PASS exact image/UID/read-only mounts/root/internal-only network, no ports, bounded CPU/RAM/tmpfs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="store_true",
                        help="Verify the separately approved persistent backend")
    parser.add_argument("--gateway-connected", action="store_true",
                        help="Require the separately approved gateway as the sole additional network member")
    args = parser.parse_args()
    if args.gateway_connected and not args.service:
        parser.error("--gateway-connected requires --service")
    name = "mcp-stack-codegraph-http" if args.service else NAME
    project = "mcp-stack" if args.service else NAME
    restart = "unless-stopped" if args.service else "no"
    verify_container(name, project, restart, args.gateway_connected)
    before = hashes()
    # Immutable is safe ONLY here: no writer and an empty WAL, verified below.
    assert (STATE / "codegraph.db-wal").stat().st_size == 0
    assert not (STATE / "writer.pid").exists()
    with sqlite3.connect((STATE / "codegraph.db").as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        assert db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == 47
        assert db.execute("SELECT COUNT(*) FROM edges").fetchone()[0] == 98
        paths = {r[0] for r in db.execute("SELECT DISTINCT file_path FROM nodes")}
        assert paths == set(SOURCES[:3]), "Index source paths differ from the exact three-file projection"
        calls = set(db.execute("SELECT a.name,b.name FROM edges e JOIN nodes a ON e.source=a.id JOIN nodes b ON e.target=b.id WHERE e.kind='calls'"))
        assert {("fixture_handle_request", "fixture_read_payload"), ("fixture_read_payload", "fixture_normalize_payload")} <= calls
    print("PASS retained 3-file/47-node/98-edge index and fixture call edges (immutable diagnostic)")
    key_path = ROOT / ".secrets/codegraph-http-backend-key"
    assert key_path.stat().st_mode & 0o777 == 0o600
    key = key_path.read_text().strip()
    config = json.loads((ROOT / "infra/codegraph/state/http/server.json").read_text())
    assert hashlib.sha256(key.encode()).hexdigest() == config["api_key_sha256"]
    for other in ("agentgateway-client-key", "graphify-http-backend-key"):
        assert key != (ROOT / ".secrets" / other).read_text().strip()
    # Secrets travel over stdin only; never include them in argv/environment/output.
    program = "const fs=require('node:fs'); const input=JSON.parse(fs.readFileSync(0,'utf8')); " \
              "const child=require('node:child_process').spawnSync('node',['-e',input.program]," \
              "{input:JSON.stringify(input.settings),encoding:'utf8',timeout:120000,maxBuffer:1048576});" \
              "process.stdout.write(child.stdout||'');process.stderr.write(child.stderr||'');" \
              "process.exit(child.status===null?1:child.status);"
    result = subprocess.run(["macctl", "run", "docker", "exec", "-i", name, "node", "-e", program],
                            input=json.dumps({"program": PROBE, "settings": {"key": key}}),
                            cwd=ROOT, text=True, capture_output=True, timeout=130)
    print(result.stdout, end="")
    print(result.stderr, end="")
    if result.returncode:
        raise SystemExit("CodeGraph HTTP direct probe failed; no relaxed fallback")
    assert hashes() == before, "Source/index/WAL/SHM bytes changed during read-only test"
    print("PASS unchanged source/index/WAL/SHM hashes; credentials distinct and never mounted in plaintext")


if __name__ == "__main__":
    main()
