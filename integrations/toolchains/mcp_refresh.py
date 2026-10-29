#!/usr/bin/python3
"""Inspect/reload MCP clients through an existing Codex Unix WebSocket socket.

No daemon start, model turn, configuration write, OAuth or MCP tool call occurs.
Status reuses loaded-thread connections and never creates a new thread/client.
Protocol: https://developers.openai.com/codex/app-server
Generated 0.159.2 schema defines reload with omitted/null params.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import time


MAX_MESSAGE = 16 * 1024 * 1024
ALLOWED_METHODS = {"initialize", "thread/loaded/list", "mcpServerStatus/list",
                   "config/mcpServer/reload"}


class ProtocolError(RuntimeError):
    pass


def masked_frame(payload, opcode=1):
    """Encode an RFC 6455 client frame, including mandatory fresh mask."""
    if len(payload) > MAX_MESSAGE:
        raise ProtocolError("message too large")
    mask = os.urandom(4)
    length = len(payload)
    if length < 126:
        header = bytes([0x80 | opcode, 0x80 | length])
    elif length < 65536:
        header = bytes([0x80 | opcode, 0xFE]) + struct.pack("!H", length)
    else:
        header = bytes([0x80 | opcode, 0xFF]) + struct.pack("!Q", length)
    return header + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(payload))


class ControlClient:
    def __init__(self, path, timeout=20):
        self.timeout = timeout
        self.deadline = time.monotonic() + timeout
        self.buffer = b""
        self.next_id = 0
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        try:
            self.sock.connect(str(path))
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            request = ("GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
                       "Connection: Upgrade\r\nSec-WebSocket-Key: " + key +
                       "\r\nSec-WebSocket-Version: 13\r\n\r\n")
            self.sock.sendall(request.encode("ascii"))
            while b"\r\n\r\n" not in self.buffer:
                if len(self.buffer) > 16384:
                    raise ProtocolError("oversize upgrade response")
                self.buffer += self._read()
            head, self.buffer = self.buffer.split(b"\r\n\r\n", 1)
            lines = head.decode("ascii").split("\r\n")
            headers = dict(line.lower().split(":", 1) for line in lines[1:] if ":" in line)
            accept = base64.b64encode(hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
            ).digest()).decode("ascii")
            # Header names are insensitive; accept value is case-sensitive.
            raw_headers = {line.split(":", 1)[0].lower(): line.split(":", 1)[1].strip()
                           for line in lines[1:] if ":" in line}
            if (not lines[0].startswith("HTTP/1.1 101 ") or
                    headers.get("upgrade", "").strip() != "websocket" or
                    raw_headers.get("sec-websocket-accept") != accept):
                raise ProtocolError("websocket upgrade rejected")
            self.rpc("initialize", {
                "clientInfo": {"name": "mcp_stack_migration", "version": "1.0"},
                "capabilities": {"experimentalApi": True},
            })
            self.send({"method": "initialized"})
        except BaseException:
            self.sock.close()
            raise

    def _read(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("control request timed out")
        self.sock.settimeout(remaining)
        data = self.sock.recv(65536)
        if not data:
            raise ProtocolError("control connection closed")
        return data

    def exact(self, length):
        while len(self.buffer) < length:
            self.buffer += self._read()
        result, self.buffer = self.buffer[:length], self.buffer[length:]
        return result

    def send(self, message):
        payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
        self.sock.sendall(masked_frame(payload))

    def receive(self):
        message = bytearray()
        started = False
        while True:
            first, second = self.exact(2)
            final, opcode, length = bool(first & 0x80), first & 15, second & 127
            if first & 0x70 or second & 0x80:
                raise ProtocolError("invalid server frame")
            if length == 126:
                length = struct.unpack("!H", self.exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self.exact(8))[0]
            if length + len(message) > MAX_MESSAGE:
                raise ProtocolError("oversize response")
            if opcode >= 8 and (not final or length > 125):
                raise ProtocolError("invalid control frame")
            payload = self.exact(length)
            if opcode == 8:
                raise ProtocolError("control connection closed")
            if opcode == 9:
                self.sock.sendall(masked_frame(payload, 10))
                continue
            if opcode == 10:
                continue
            if opcode == 1 and not started:
                started = True
            elif opcode != 0 or not started:
                raise ProtocolError("unexpected frame opcode")
            message.extend(payload)
            if final:
                parsed = json.loads(message)
                if not isinstance(parsed, dict):
                    raise ProtocolError("unexpected RPC response")
                return parsed

    def rpc(self, method, params=None):
        if method not in ALLOWED_METHODS:
            raise ValueError("operation is not allowed")
        self.deadline = time.monotonic() + self.timeout
        self.next_id += 1
        request = {"id": self.next_id, "method": method}
        if params is not None:
            request["params"] = params
        self.send(request)
        while True:
            message = self.receive()
            if message.get("id") != self.next_id:
                # Ignore other notifications/requests without responding/approving.
                continue
            if "error" in message:
                code = message["error"].get("code")
                raise ProtocolError("RPC rejected (code " + str(code) + ")")
            return message["result"]

    def close(self):
        self.sock.close()


def summarize_status(result):
    """Only names, counts, runtime state and a discovery-failure bit leave RPC."""
    return [{"name": item["name"], "tool_count": len(item.get("tools", {})),
             "runtime_status": item.get("runtimeStatus"),
             "discovery_failed": item.get("toolsError") is not None}
            for item in result.get("data", [])]


def paged(client, method, params):
    rows, cursor = [], None
    for _ in range(100):
        response = client.rpc(method, dict(params, cursor=cursor, limit=100))
        rows.extend(response.get("data", []))
        cursor = response.get("nextCursor")
        if not cursor:
            return rows
    raise ProtocolError("pagination limit exceeded")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "reload"))
    parser.add_argument("--socket", type=Path, default=Path.home() /
                        ".codex/app-server-control/app-server-control.sock")
    parser.add_argument("--thread", help="Reuse only this existing loaded thread")
    parser.add_argument("--server", help="Limit status to a configured server")
    parser.add_argument("--timeout", type=int, default=20, choices=range(1, 61))
    args = parser.parse_args(argv)
    client = None
    try:
        client = ControlClient(args.socket, args.timeout)
        if args.action == "reload":
            if args.thread or args.server:
                raise ValueError("reload is daemon-wide; scope flags apply only to status")
            client.rpc("config/mcpServer/reload")
            result = {"reload_queued": True, "daemon_restarted": False,
                      "completion_verified": False}
        else:
            threads = paged(client, "thread/loaded/list", {})
            if args.thread:
                if args.thread not in threads:
                    raise ValueError("requested thread is not loaded")
                threads = [args.thread]
            summaries = []
            for index, thread in enumerate(threads):
                params = {"threadId": thread, "detail": "toolsAndAuthOnly"}
                if args.server:
                    params["serverName"] = args.server
                rows = paged(client, "mcpServerStatus/list", params)
                summaries.append({"thread_index": index,
                                  "servers": summarize_status({"data": rows})})
            result = {"loaded_thread_count": len(threads), "threads": summaries}
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, ProtocolError):
        # Do not echo daemon errors, payloads, session IDs or auth material.
        print(json.dumps({"ok": False, "error": "control operation failed"}))
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
