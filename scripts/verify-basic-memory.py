"""Direct Streamable HTTP MCP checks; run with the container's existing Python.

Create mode writes one clearly labeled setup note, refusing to overwrite it.
Read-only mode checks that same note after a scoped service restart.
No credentials, package installs, or cloud APIs are involved.
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path


TITLE = "MCP Stack Setup Verification 2026-10-01"
TOKEN = "mcpstackverification20261001"
CONTENT = (
    "# MCP Stack Setup Verification\n\n"
    "This sample note verifies the local MCP integration.\n\n"
    "- [verification] PostgreSQL backend and readable Markdown are working.\n"
    "- [verification] 本地记忆层测试，保留此测试笔记用于检查持久化。\n\n"
    f"Verification marker: {TOKEN}\n"
)


class Session:
    def __init__(self, url):
        self.url = url
        self.session_id = None
        self.sequence = 0
        self.protocol = "2025-03-26"

    def send(self, method, params=None, notification=False):
        self.sequence += 1
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notification:
            payload["id"] = self.sequence
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.protocol,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(), headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            self.session_id = response.headers.get("Mcp-Session-Id", self.session_id)
            if notification:
                return None
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                result = None
                for raw_line in response:
                    line = raw_line.decode().strip()
                    if line.startswith("data:"):
                        event = json.loads(line[5:].strip())
                        if event.get("id") == payload["id"]:
                            result = event
                            break
                if result is None:
                    raise RuntimeError("No matching JSON-RPC result in SSE response")
            else:
                result = json.loads(response.read())
        if "error" in result:
            raise RuntimeError(f"JSON-RPC error: {result['error']}")
        return result["result"]

    def call(self, name, arguments):
        result = self.send("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(f"Tool failed: {name}: {result.get('content')}")
        return result


def result_text(result):
    return json.dumps(result, ensure_ascii=False)


def verify(url, read_only):
    session = Session(url)
    initialized = session.send(
        "initialize",
        {
            "protocolVersion": session.protocol,
            "capabilities": {},
            "clientInfo": {"name": "mcp-stack-verification", "version": "1.0"},
        },
    )
    session.protocol = initialized["protocolVersion"]
    session.send("notifications/initialized", notification=True)
    names = {tool["name"] for tool in session.send("tools/list")["tools"]}
    assert {"write_note", "read_note", "search_notes"} <= names, names
    print(f"MCP initialized; {len(names)} tools available.")

    if not read_only:
        written = session.call(
            "write_note",
            {
                "title": TITLE,
                "directory": "setup",
                "project": "main",
                "content": CONTENT,
                "tags": ["setup", "verification"],
                "overwrite": False,
                "output_format": "json",
            },
        )
        print("write_note accepted:", result_text(written))

    for attempt in range(20):
        read = session.call("read_note", {"identifier": TITLE, "project": "main"})
        if TOKEN in result_text(read):
            break
        if attempt == 19:
            raise RuntimeError("Verification note content did not materialize")
        time.sleep(1)
    print("read_note returned the verification marker.")

    search = session.call(
        "search_notes", {"query": TOKEN, "project": "main", "search_type": "text"}
    )
    if TITLE not in result_text(search):
        raise RuntimeError(f"Text search did not find the note: {result_text(search)}")
    print("Text search found the verification note.")

    matches = [
        path for path in Path("/app/data/main/setup").glob("*.md")
        if TOKEN in path.read_text(encoding="utf-8")
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one materialized Markdown note, found {len(matches)}")
    print("Readable Markdown verified:", matches[0])
    print("Post-restart persistence passed." if read_only else "Direct MCP workflow passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    args = parser.parse_args()
    verify(args.url, args.read_only)
