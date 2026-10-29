"""Direct CodeGraph stdio MCP test. No installs or harness registrations.

Requires the approved image and initialized source-projection index.
Starts two sequential offline test containers and verifies retained-index reads.
Only selected project scripts/fixtures are indexed, not the whole repository.
"""

import json
import queue
import sqlite3
import subprocess
import threading
import time
from collections import deque
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
HOST_REPO = "/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mcp-stack"
PROJECT_PATH = "/home/developer/workspace/mcp-stack"
CONTAINER = "mcp-stack-codegraph-mcp-test"
COMPOSE = [
    "macctl", "run", "docker", "compose",
    "--project-directory", HOST_REPO,
    "-f", f"{HOST_REPO}/compose.yaml",
    "-f", f"{HOST_REPO}/infra/codegraph/compose.yaml",
]


def existing_container():
    result = subprocess.run(
        ["macctl", "run", "docker", "ps", "-aq", "--filter", f"name=^{CONTAINER}$"],
        capture_output=True, text=True, timeout=15, check=True,
    )
    return bool(result.stdout.strip())


class Session:
    def __init__(self):
        if existing_container():
            raise RuntimeError(f"Refusing to reuse an existing container: {CONTAINER}")
        self.sequence = 0
        self.responses = queue.Queue()
        self.stderr = deque(maxlen=80)
        self.process = subprocess.Popen(
            COMPOSE + [
                "run", "--rm", "--no-deps", "-T", "--name", CONTAINER,
                # macctl translates standalone absolute path arguments for
                # macOS. Resolve '.' inside the container instead; JSON-RPC
                # projectPath values below remain the Ubuntu/container path.
                "codegraph", "serve", "--mcp", "--no-watch", "--path", ".",
            ],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        self.out_thread = threading.Thread(target=self.read_stdout, daemon=True)
        self.err_thread = threading.Thread(target=self.read_stderr, daemon=True)
        self.out_thread.start()
        self.err_thread.start()

    def read_stdout(self):
        for line in self.process.stdout:
            try:
                self.responses.put(json.loads(line))
            except json.JSONDecodeError:
                self.responses.put(RuntimeError(f"Non-JSON MCP stdout: {line[:300]!r}"))
        self.responses.put(RuntimeError("MCP stdout closed"))

    def read_stderr(self):
        for line in self.process.stderr:
            self.stderr.append(line.rstrip())

    def send(self, method, params=None, notification=False):
        self.sequence += 1
        payload = {"jsonrpc": "2.0", "method": method}
        if not notification:
            payload["id"] = self.sequence
        if params is not None:
            payload["params"] = params
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        if notification:
            return None
        deadline = time.monotonic() + 60
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"MCP response timeout: {method}")
            try:
                result = self.responses.get(timeout=remaining)
            except queue.Empty as error:
                raise TimeoutError(f"MCP response timeout: {method}") from error
            if isinstance(result, Exception):
                raise result
            if result.get("id") != payload["id"]:
                # Server notifications are legal and do not complete our request.
                continue
            if "error" in result:
                raise RuntimeError(f"MCP error: {result['error']}")
            return result["result"]

    def call(self, name, arguments):
        result = self.send("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(f"Tool failed: {name}: {result.get('content')}")
        return result

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            # Resolve and verify the exact test target before stopping it.
            inspected = subprocess.run(
                ["macctl", "run", "docker", "inspect", "--format",
                 '{{.Config.Image}}|{{index .Config.Labels "com.docker.compose.project"}}|'
                 '{{index .Config.Labels "com.docker.compose.service"}}', CONTAINER],
                capture_output=True, text=True, timeout=15,
            )
            if inspected.returncode == 0:
                identity = inspected.stdout.strip()
                if identity != "mcp-stack-codegraph:1.6.1|mcp-stack|codegraph":
                    raise RuntimeError(f"Refusing to stop an unexpected test target: {identity}")
                subprocess.run(
                    ["macctl", "run", "docker", "stop", "--time", "5", CONTAINER],
                    capture_output=True, text=True, timeout=15, check=True,
                )
            self.process.wait(timeout=15)
        self.out_thread.join(timeout=2)
        self.err_thread.join(timeout=2)
        if existing_container():
            raise RuntimeError(f"Test container did not clean up: {CONTAINER}")
        for stream in (self.process.stdout, self.process.stderr):
            stream.close()


def result_text(result):
    return "\n".join(item.get("text", "") for item in result.get("content", []))


def verify_container():
    inspected = subprocess.run(
        ["macctl", "run", "docker", "inspect", CONTAINER],
        capture_output=True, text=True, timeout=15, check=True,
    )
    container = json.loads(inspected.stdout)[0]
    config, host = container["Config"], container["HostConfig"]
    if config["Image"] != "mcp-stack-codegraph:1.6.1" or config["User"] != "501:501":
        raise RuntimeError("Unexpected image or container user")
    if host["NetworkMode"] != "none" or not host["ReadonlyRootfs"] or host["Privileged"]:
        raise RuntimeError("Container networking/root isolation differs from approval")
    if host["Memory"] != 2 * 1024 ** 3 or host["NanoCpus"] != 2 * 10 ** 9:
        raise RuntimeError("Container resource limits differ from approval")
    if container["NetworkSettings"].get("Ports"):
        raise RuntimeError("Unexpected published/exposed ports")
    environment = dict(item.split("=", 1) for item in config["Env"])
    expected = {
        "CODEGRAPH_TELEMETRY": "0", "DO_NOT_TRACK": "1",
        "CODEGRAPH_NO_UPDATE_CHECK": "1", "CODEGRAPH_NO_DAEMON": "1",
        "CODEGRAPH_NO_WATCH": "1", "CODEGRAPH_MCP_TOOLS": "explore,status",
        "NODE_COMPILE_CACHE": "/state/node-compile-cache",
    }
    if any(environment.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Container environment differs from approval")
    allowed = {
        f"{HOST_REPO}/scripts": False,
        f"{HOST_REPO}/infra/codegraph/fixtures": False,
        f"{HOST_REPO}/infra/codegraph/project.json": False,
        f"{HOST_REPO}/infra/codegraph/state/mcp-stack": True,
        f"{HOST_REPO}/infra/codegraph/state/runtime": True,
    }
    mounts = {item["Source"]: item["RW"] for item in container["Mounts"]
              if item["Type"] == "bind"}
    if mounts != allowed:
        raise RuntimeError("Container mounts differ from the approved source projection")
    if "/tmp" not in host.get("Tmpfs", {}):
        raise RuntimeError("Bounded temporary filesystem is missing")
    print("Container isolation: UID 501, read-only sources/root, offline, bounded CPU/RAM, no ports.")


def verify_index():
    database = REPO / "infra/codegraph/state/mcp-stack/codegraph.db"
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        files = list(connection.execute("SELECT DISTINCT file_path FROM nodes"))
        paths = {row[0] for row in files if row[0]}
        if not paths:
            raise RuntimeError("Index contains no source paths")
        for source_path in paths:
            relative = source_path.removeprefix(PROJECT_PATH + "/")
            if not relative.startswith(("scripts/", "infra/codegraph/fixtures/")):
                raise RuntimeError(f"Path outside the approved source projection: {source_path}")
        names = {row[0] for row in connection.execute("SELECT name FROM nodes")}
        required = {"fixture_handle_request", "fixture_read_payload", "fixture_normalize_payload"}
        if not required <= names:
            raise RuntimeError(f"Missing fixture symbols: {required - names}")
        edges = list(connection.execute(
            "SELECT a.name, b.name, e.kind FROM edges e "
            "JOIN nodes a ON e.source = a.id JOIN nodes b ON e.target = b.id "
            "WHERE a.name LIKE 'fixture_%' AND b.name LIKE 'fixture_%'"
        ))
        calls = {(row[0], row[1]) for row in edges if row[2] == "calls"}
        expected = {("fixture_handle_request", "fixture_read_payload"),
                    ("fixture_read_payload", "fixture_normalize_payload")}
        if not expected <= calls:
            raise RuntimeError(f"Missing fixture call edges; got {list(map(tuple, edges))}")
        nodes = connection.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_count = connection.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        print(f"Scoped SQLite index: {len(paths)} source files, {nodes} nodes, {edge_count} edges.")
        print("Synthetic caller/callee edges verified.")


def verify_session(number):
    session = Session()
    try:
        initialized = session.send("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "mcp-stack-verification", "version": "1.0"},
        })
        session.send("notifications/initialized", {}, notification=True)
        info = initialized.get("serverInfo", {})
        if info.get("version") != "1.6.1":
            raise RuntimeError(f"Unexpected server version: {info}")
        verify_container()
        tools = session.send("tools/list")
        names = {tool["name"] for tool in tools["tools"]}
        # Upstream's small-project gate hides status from tools/list even
        # with an explicit allowlist; its allowed handler remains callable.
        expected = {"codegraph_explore"}
        if names != expected:
            raise RuntimeError(f"Unexpected discoverable tool surface: {names}")
        fixture = result_text(session.call("codegraph_explore", {
            "query": "fixture_handle_request fixture_read_payload fixture_normalize_payload",
            "projectPath": PROJECT_PATH,
        }))
        if not all(name in fixture for name in (
            "fixture_handle_request", "fixture_read_payload", "fixture_normalize_payload",
        )):
            raise RuntimeError("MCP exploration did not return the fixture call chain")
        source = result_text(session.call("codegraph_explore", {
            "query": "scripts/verify-basic-memory.py Session.send",
            "projectPath": PROJECT_PATH,
        }))
        if "verify-basic-memory.py" not in source or "jsonrpc" not in source:
            raise RuntimeError("MCP exploration did not return the real script's source")
        status = result_text(session.call("codegraph_status", {"projectPath": PROJECT_PATH}))
        if not status:
            raise RuntimeError("MCP status returned no content")
        rejected = session.send("tools/call", {
            "name": "codegraph_search",
            "arguments": {"query": "fixture_handle_request", "projectPath": PROJECT_PATH},
        })
        if not rejected.get("isError") or "disabled via CODEGRAPH_MCP_TOOLS" not in result_text(rejected):
            raise RuntimeError("An explicitly disabled tool was not rejected at execution")
        print(f"Session {number}: initialized {info}; tools={sorted(names)}; source queries passed.")
        print("Explicit status call passed; disallowed search call was rejected.")
    except Exception:
        print("MCP stderr tail:", "\n".join(session.stderr))
        raise
    finally:
        session.close()


if __name__ == "__main__":
    verify_index()
    verify_session(1)
    verify_session(2)
    verify_index()
    print("Direct MCP, retained-index reconnect, and child-container cleanup passed.")
    print("Scope: source-only projection, not a full repository index or harness integration.")
