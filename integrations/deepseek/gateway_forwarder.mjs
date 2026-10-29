// Approval-gated local TCP adapter, not an MCP client or generic proxy.
// No credentials, payload inspection, HTTP rewriting, dependencies or retries.
import net from 'node:net';
import { lookup } from 'node:dns/promises';
import { lstatSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const APPROVED_CONFIG = Object.freeze({
  listen: Object.freeze({ host: '127.0.0.1', port: 58081 }),
  upstream: Object.freeze({
    host: 'host.orb.internal', port: 58080, address: '0.250.250.254',
  }),
  limits: Object.freeze({
    maxConnections: 32, connectTimeoutMs: 5000,
    idleTimeoutMs: 600000, shutdownTimeoutMs: 5000,
  }),
});

export class ForwarderError extends Error {
  constructor(stage) {
    // Caller-owned labels only; never serialize vendor exceptions or traffic.
    super(stage);
    this.stage = stage;
  }
}

function matchesApproved(actual, expected) {
  if (expected === null || typeof expected !== 'object') return actual === expected;
  if (actual === null || typeof actual !== 'object' || Array.isArray(actual)) return false;
  const keys = Object.keys(expected);
  return Object.keys(actual).length === keys.length
    && keys.every((key) => Object.hasOwn(actual, key)
      && matchesApproved(actual[key], expected[key]));
}

export function validateConfig(value) {
  if (!matchesApproved(value, APPROVED_CONFIG)) throw new ForwarderError('config_scope');
  // Changing a port, target, address or resource boundary needs fresh approval.
  return structuredClone(APPROVED_CONFIG);
}

export async function resolveUpstream(config, resolver = lookup, timers = globalThis) {
  let timer;
  try {
    const records = await Promise.race([
      Promise.resolve().then(() => resolver(config.upstream.host, {
        family: 4, all: true, verbatim: true,
      })),
      new Promise((_, reject) => {
        timer = timers.setTimeout(() => reject(new ForwarderError('dns_timeout')),
          config.limits.connectTimeoutMs);
      }),
    ]);
    if (!Array.isArray(records) || records.length === 0
        || records.some((r) => r.family !== 4
          || net.isIPv4(r.address) !== true || r.address !== config.upstream.address)) {
      throw new ForwarderError('dns_scope');
    }
    // Numeric connect address pins the checked resolution for this process.
    // OrbStack's observed reserved synthetic address is not a public target.
    return config.upstream.address;
  } catch (error) {
    if (error instanceof ForwarderError) throw error;
    throw new ForwarderError('dns_lookup');
  } finally {
    timers.clearTimeout(timer);
  }
}

export function wireConnection(client, upstream, config, onClosed, timers = globalThis) {
  let closed = false;
  let connected = false;
  const finish = () => {
    if (closed) return;
    closed = true;
    timers.clearTimeout(connectTimer);
    client.setTimeout(0);
    upstream.setTimeout(0);
    client.unpipe(upstream);
    upstream.unpipe(client);
    client.destroy();
    upstream.destroy();
    onClosed();
  };
  const connectTimer = timers.setTimeout(finish, config.limits.connectTimeoutMs);
  connectTimer.unref?.();
  client.pause();
  client.on('error', finish);
  upstream.on('error', finish);
  client.on('close', finish);
  upstream.on('close', finish);
  client.setTimeout(config.limits.idleTimeoutMs, finish);
  upstream.setTimeout(config.limits.idleTimeoutMs, finish);
  upstream.on('connect', () => {
    if (closed || connected) return;
    connected = true;
    timers.clearTimeout(connectTimer);
    // Node stream.pipe supplies backpressure and propagates each read-side EOF
    // to the other socket's write side. allowHalfOpen preserves the response
    // direction after a request EOF; close/error/idle bounds final cleanup.
    client.pipe(upstream);
    upstream.pipe(client);
    client.resume();
  });
  return finish;
}

export async function startForwarder(raw, dependencies = {}) {
  const config = validateConfig(raw);
  const timers = dependencies.timers ?? globalThis;
  const address = await resolveUpstream(config, dependencies.lookup ?? lookup, timers);
  const connect = dependencies.connect ?? ((options) => net.createConnection(options));
  const createServer = dependencies.createServer ?? ((options, accept) =>
    net.createServer(options, accept));
  const pairs = new Set();
  let closing = false;
  const server = createServer({ allowHalfOpen: true, pauseOnConnect: true }, (client) => {
    if (closing || pairs.size >= config.limits.maxConnections) {
      client.on('error', () => {});
      client.destroy();
      return;
    }
    let upstream;
    try {
      upstream = connect({ host: address, port: config.upstream.port,
        family: 4, allowHalfOpen: true });
    } catch {
      client.on('error', () => {});
      client.destroy();
      return;
    }
    let close;
    close = wireConnection(client, upstream, config, () => pairs.delete(close), timers);
    pairs.add(close);
  });
  server.maxConnections = config.limits.maxConnections;
  try {
    await new Promise((accept, reject) => {
      const failed = () => reject(new ForwarderError('listen_failed'));
      server.once('error', failed);
      server.once('listening', () => {
        server.removeListener('error', failed);
        accept();
      });
      server.listen({ host: config.listen.host, port: config.listen.port, exclusive: true });
    });
  } catch {
    throw new ForwarderError('listen_failed');
  }

  let stopPromise;
  const stop = () => {
    if (stopPromise) return stopPromise;
    closing = true;
    stopPromise = new Promise((accept) => {
      let finished = false;
      let timer;
      const done = () => {
        if (finished) return;
        finished = true;
        timers.clearTimeout(timer);
        accept();
      };
      timer = timers.setTimeout(() => {
        for (const close of [...pairs]) close();
        done();
      }, config.limits.shutdownTimeoutMs);
      server.close(done);
    });
    return stopPromise;
  };
  // A runtime listener error closes only this owned server; no retry/rebind.
  server.on('error', () => { void stop(); });
  return { server, stop, stats: () => ({ activeConnections: pairs.size, closing }) };
}

async function main() {
  if (process.version !== 'v24.19.0') throw new ForwarderError('node_version');
  if (process.argv.length !== 4 || process.argv[2] !== '--config') {
    throw new ForwarderError('arguments');
  }
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
  const file = resolve(process.argv[3]);
  if (process.cwd() !== root
      || file !== resolve(root, 'infra/harnesses/deepseek/gateway-forwarder.json')) {
    throw new ForwarderError('config_path');
  }
  const info = lstatSync(file);
  if (!info.isFile() || info.size > 4096) throw new ForwarderError('config_file');
  let raw;
  try { raw = JSON.parse(readFileSync(file, 'utf8')); }
  catch { throw new ForwarderError('config_parse'); }
  const forwarder = await startForwarder(raw);
  let stopping = false;
  const shutdown = () => {
    if (stopping) return;
    stopping = true;
    void forwarder.stop().then(() => {
      console.log('gateway-forwarder: stopped');
    });
  };
  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
  console.log('gateway-forwarder: ready on 127.0.0.1:58081');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error('gateway-forwarder: failed at '
      + (error instanceof ForwarderError ? error.stage : 'startup'));
    process.exit(1);
  });
}
