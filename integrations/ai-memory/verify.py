#!/usr/bin/env python3
"""Read-only direct MCP qualification; private bearer stays on curl stdin."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
URL = "http://127.0.0.1:58092"


def request(path, token=None, body=None, session=None, method=None):
    config = [f"url = {json.dumps(URL + path)}", "noproxy = \"*\"",
              "silent", "show-error", "include", "max-time = 10",
              'header = "Accept: application/json, text/event-stream"']
    if token:
        config.append("header = " + json.dumps("Authorization: Bearer " + token))
    if session:
        config.append("header = " + json.dumps("Mcp-Session-Id: " + session))
        config.append('header = "MCP-Protocol-Version: 2025-03-26"')
    if body is not None:
        config.extend(['header = "Content-Type: application/json"',
                       "data = " + json.dumps(json.dumps(body))])
    if method:
        config.append("request = " + json.dumps(method))
    result = subprocess.run(["macctl", "run", "curl", "--config", "-"],
                            input="\n".join(config) + "\n", text=True,
                            capture_output=True, timeout=15, check=True)
    headers, payload = result.stdout.replace("\r\n", "\n").split("\n\n", 1)
    status = int(headers.splitlines()[0].split()[1])
    fields = dict(line.split(":", 1) for line in headers.splitlines()[1:] if ":" in line)
    fields = {k.lower(): v.strip() for k, v in fields.items()}
    if payload.startswith("event:") or payload.startswith("data:"):
        chunks = [line[5:].strip() for line in payload.splitlines() if line.startswith("data:")]
        data = json.loads(chunks[-1]) if chunks else None
    else:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = None
    return status, fields, data


def main():
    private = ROOT / "infra/ai-memory/state/runtime.env"
    assert private.stat().st_mode & 0o777 == 0o600
    token = private.read_text().strip().split("=", 1)[1]
    assert request("/healthz")[0] == 200
    assert request("/mcp", body={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[0] == 401
    assert request("/mcp", token="invalid-synthetic-token",
                   body={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[0] == 401
    status, headers, data = request("/mcp", token, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "mcp-stack-direct-readonly-check", "version": "1"}}})
    assert status == 200 and "result" in data, (status, data)
    session = headers.get("mcp-session-id")
    try:
        status, _, _ = request("/mcp", token, {
            "jsonrpc": "2.0", "method": "notifications/initialized"}, session)
        assert status in (200, 202, 204), status
        status, _, listing = request("/mcp", token, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/list"}, session)
        assert status == 200 and "result" in listing, (status, listing)
        tools = listing["result"]["tools"]
        wire = json.dumps(tools, separators=(",", ":"), ensure_ascii=False)
        query_wire = json.dumps([t for t in tools if t["name"] == "memory_query"],
                                separators=(",", ":"), ensure_ascii=False)
        receipt = {"date": "2026-10-06", "health": 200,
                   "anonymous_mcp": 401, "wrong_token_mcp": 401,
                   "mcp_initialize": 200, "protocol": data["result"]["protocolVersion"],
                   "server": data["result"]["serverInfo"],
                   "tools": [tool["name"] for tool in tools],
                   "tool_count": len(tools), "tool_definition_chars": len(wire),
                   "tool_definition_utf8_bytes": len(wire.encode()),
                   "query_only_definition_chars": len(query_wire),
                   "tool_calls": 0, "model_requests": 0,
                   "scope": "direct-install-qualification; no hooks, imports or registrations"}
    finally:
        if session:
            status, _, _ = request("/mcp", token, session=session, method="DELETE")
            assert status in (200, 202, 204, 404, 405), status
    output = ROOT / "infra/ai-memory/state/direct-qualification.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    output.chmod(0o600)
    print(json.dumps({key: value for key, value in receipt.items() if key != "tools"}, indent=2))


if __name__ == "__main__":
    main()
