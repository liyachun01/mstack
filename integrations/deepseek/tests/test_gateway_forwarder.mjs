// No listener, network, profile startup, credential read or package install.
import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { readFileSync } from 'node:fs';
import { APPROVED_CONFIG, validateConfig, resolveUpstream, wireConnection,
  startForwarder } from '../gateway_forwarder.mjs';

const config = () => structuredClone(APPROVED_CONFIG);
const dns = async () => [{ family: 4, address: '0.250.250.254' }];

class Clock {
  tasks = new Set();
  setTimeout(callback, ms) {
    const task = { callback, ms, unref() {} };
    this.tasks.add(task);
    return task;
  }
  clearTimeout(task) { this.tasks.delete(task); }
  fire(ms) {
    for (const task of [...this.tasks]) {
      if (task.ms !== ms) continue;
      this.tasks.delete(task);
      task.callback();
    }
  }
}

class Socket extends EventEmitter {
  destroyed = false;
  paused = false;
  pipes = [];
  ends = 0;
  idle = null;
  pause() { this.paused = true; }
  resume() { this.paused = false; }
  pipe(peer) {
    this.pipes.push(peer);
    const eof = () => peer.end();
    this.once('end', eof);
    this.eof = eof;
    return peer;
  }
  unpipe(peer) {
    this.pipes = this.pipes.filter((p) => p !== peer);
    if (this.eof) this.removeListener('end', this.eof);
  }
  end() { this.ends += 1; }
  setTimeout(ms, callback) { this.timeoutMs = ms; this.idle = ms ? callback : null; }
  destroy() {
    if (this.destroyed) return;
    this.destroyed = true;
    this.emit('close');
  }
}

class Server extends EventEmitter {
  closeCalls = 0;
  holdClose = false;
  listen(options) { this.listenOptions = options; queueMicrotask(() => this.emit('listening')); }
  close(done) { this.closeCalls += 1; this.done = done; if (!this.holdClose) done(); }
}

function fixture(options = {}) {
  const clock = new Clock();
  const server = new Server();
  const peers = [];
  let accept;
  const dependencies = {
    timers: clock, lookup: dns,
    createServer: (opts, handler) => { server.options = opts; accept = handler; return server; },
    connect: (opts) => { const s = new Socket(); s.connectOptions = opts; peers.push(s); return s; },
    ...options,
  };
  return { clock, server, peers, dependencies, accept: (s) => accept(s) };
}

test('tracked infra config exactly matches the approved boundaries', () => {
  const raw = JSON.parse(readFileSync(new URL(
    '../../../infra/harnesses/deepseek/gateway-forwarder.json', import.meta.url)));
  assert.deepEqual(validateConfig(raw), config());
});

test('config rejects every changed leaf, unknown property and wrong structure', () => {
  for (const [group, fields] of Object.entries(APPROVED_CONFIG)) {
    for (const [key, value] of Object.entries(fields)) {
      const raw = config();
      raw[group][key] = typeof value === 'number' ? value + 1 : 'unapproved';
      assert.throws(() => validateConfig(raw), /config_scope/);
    }
  }
  for (const raw of [null, [], { ...config(), extra: true },
    { ...config(), upstream: { ...config().upstream, extra: true } },
    { ...config(), listen: null }, { ...config(), limits: [] }]) {
    assert.throws(() => validateConfig(raw), /config_scope/);
  }
});

test('IPv4 resolution is exact, pinned, rejects empty/public/mixed/IPv6 results', async () => {
  let query;
  assert.equal(await resolveUpstream(config(), async (host, opts) => {
    query = [host, opts]; return dns();
  }), '0.250.250.254');
  assert.deepEqual(query, ['host.orb.internal', { family: 4, all: true, verbatim: true }]);
  for (const records of [[], null, [{ family: 4, address: '1.1.1.1' }],
    [{ family: 4, address: '127.0.0.1' }], [{ family: 6, address: '::1' }],
    [...await dns(), { family: 4, address: '1.1.1.1' }]]) {
    await assert.rejects(resolveUpstream(config(), async () => records), /dns_scope/);
  }
});

test('DNS failure is redacted; resolution timeout is bounded', async () => {
  await assert.rejects(resolveUpstream(config(), async () => {
    throw new Error('PRIVATE VENDOR DATA');
  }), { message: 'dns_lookup' });
  const clock = new Clock();
  const pending = resolveUpstream(config(), () => new Promise(() => {}), clock);
  const rejected = assert.rejects(pending, /dns_timeout/);
  clock.fire(5000);
  await rejected;
  assert.equal(clock.tasks.size, 0);
});

test('byte relay waits for connect, wires stream backpressure once and preserves half-close', () => {
  const client = new Socket(); const upstream = new Socket(); const clock = new Clock();
  let closed = 0;
  const close = wireConnection(client, upstream, config(), () => closed++, clock);
  assert.equal(client.paused, true);
  assert.equal(client.pipes.length, 0);
  assert.equal(client.timeoutMs, 600000);
  upstream.emit('connect'); upstream.emit('connect');
  assert.deepEqual(client.pipes, [upstream]);
  assert.deepEqual(upstream.pipes, [client]);
  assert.equal(client.paused, false);
  assert.equal(clock.tasks.size, 0);
  client.emit('end');
  assert.equal(upstream.ends, 1);
  assert.equal(client.destroyed, false);
  upstream.emit('end');
  assert.equal(client.ends, 1);
  close(); close();
  assert.equal(closed, 1);
  assert.equal(client.destroyed, true);
  assert.equal(upstream.destroyed, true);
  assert.equal(client.pipes.length, 0);
});

test('connect timeout, both idle timeouts, errors and closes clean both sockets once', () => {
  for (const action of ['connect-timeout', 'client-idle', 'upstream-idle',
    'client-error', 'upstream-error', 'client-close', 'upstream-close']) {
    const client = new Socket(); const upstream = new Socket(); const clock = new Clock();
    let closed = 0;
    wireConnection(client, upstream, config(), () => closed++, clock);
    if (action === 'connect-timeout') clock.fire(5000);
    else if (action.endsWith('-idle')) (action.startsWith('client') ? client : upstream).idle();
    else (action.startsWith('client') ? client : upstream).emit(action.split('-')[1]);
    assert.equal(closed, 1, action);
    assert.equal(client.destroyed, true, action);
    assert.equal(upstream.destroyed, true, action);
    assert.equal(clock.tasks.size, 0, action);
    upstream.emit('connect');
    client.emit('error'); upstream.emit('error');
    assert.equal(closed, 1, action);
  }
});

test('binds exact loopback, pins numeric upstream and rejects connection 33', async () => {
  const f = fixture();
  const running = await startForwarder(config(), f.dependencies);
  assert.deepEqual(f.server.listenOptions, { host: '127.0.0.1', port: 58081, exclusive: true });
  assert.deepEqual(f.server.options, { allowHalfOpen: true, pauseOnConnect: true });
  assert.equal(f.server.maxConnections, 32);
  for (let i = 0; i < 32; i++) f.accept(new Socket());
  const rejected = new Socket(); f.accept(rejected);
  assert.equal(rejected.destroyed, true);
  assert.equal(f.peers.length, 32);
  assert.deepEqual(f.peers[0].connectOptions,
    { host: '0.250.250.254', port: 58080, family: 4, allowHalfOpen: true });
  assert.equal(running.stats().activeConnections, 32);
  f.peers[0].emit('close');
  assert.equal(running.stats().activeConnections, 31);
  for (const peer of f.peers) peer.emit('close');
  assert.equal(running.stats().activeConnections, 0);
  await running.stop();
});

test('upstream creation failure does not consume capacity or leak private error text', async () => {
  const f = fixture({ connect() { throw new Error('PRIVATE VENDOR DATA'); } });
  const running = await startForwarder(config(), f.dependencies);
  const client = new Socket(); f.accept(client);
  assert.equal(client.destroyed, true);
  assert.equal(running.stats().activeConnections, 0);
  await running.stop();
});

test('shutdown is idempotent, refuses new connections and drains within the configured bound', async () => {
  const f = fixture();
  const running = await startForwarder(config(), f.dependencies);
  const client = new Socket(); f.accept(client); f.peers[0].emit('connect');
  f.server.holdClose = true;
  const stop = running.stop();
  assert.equal(running.stop(), stop);
  assert.equal(running.stats().closing, true);
  const rejected = new Socket(); f.accept(rejected);
  assert.equal(rejected.destroyed, true);
  f.clock.fire(5000);
  await stop;
  assert.equal(client.destroyed, true);
  assert.equal(f.peers[0].destroyed, true);
  assert.equal(running.stats().activeConnections, 0);
  assert.equal(f.server.closeCalls, 1);
  assert.equal(f.clock.tasks.size, 0);
  f.server.done();
});

test('failed DNS never creates a listener; occupied listener errors do not retry', async () => {
  let listeners = 0;
  await assert.rejects(startForwarder(config(), {
    lookup: async () => [{ family: 4, address: '8.8.8.8' }],
    createServer: () => { listeners++; },
  }), /dns_scope/);
  assert.equal(listeners, 0);
  const f = fixture();
  f.server.listen = () => { listeners++; queueMicrotask(() => f.server.emit('error')); };
  await assert.rejects(startForwarder(config(), f.dependencies), /listen_failed/);
  assert.equal(listeners, 1);
});
