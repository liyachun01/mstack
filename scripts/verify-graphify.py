"""Approved direct/offline Graphify MCP smoke and reconnect tests.

Stdlib only. No installation, harness registration, or corpus expansion.
Existing test scripts are intentionally not imported or changed.
"""

import hashlib
import json
import queue
import subprocess
import threading
import time
from collections import deque
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
HOST_REPO = subprocess.run(
    ["macctl", "run", "pwd"], cwd=REPO, capture_output=True,
    text=True, timeout=15, check=True,
).stdout.strip()
COMPOSE = [
    "macctl", "run", "docker", "compose", "--project-directory", HOST_REPO,
    "-f", f"{HOST_REPO}/compose.yaml",
    "-f", f"{HOST_REPO}/infra/graphify/compose.yaml",
]
TOOLS = {
    "query_graph", "get_node", "get_neighbors", "get_community",
    "god_nodes", "graph_stats", "shortest_path",
}
STATE = REPO / "infra/graphify/state/mcp-stack"
GRAPH = STATE / "graphify-out/graph.json"
SOURCES = {
    "scripts/verify-basic-memory.py", "scripts/verify-codegraph.py",
    "infra/graphify/fixtures/call-chain.py",
}


def command(args):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True,
                          timeout=20, check=True).stdout


def exists(name):
    return bool(command(["macctl", "run", "docker", "ps", "-aq",
                         "--filter", f"name=^{name}$"]).strip())


def hashes():
    files = list(STATE.rglob("*")) + [REPO / path for path in SOURCES]
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files if path.is_file()}


class Session:
    def __init__(self, name):
        self.name = name
        if exists(name):
            raise RuntimeError(f"Refusing to reuse existing container: {name}")
        self.sequence = 0
        self.responses = queue.Queue()
        self.stderr = deque(maxlen=80)
        self.process = subprocess.Popen(
            COMPOSE + ["run", "--rm", "--no-deps", "-T", "--name", name, "graphify"],
            cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
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
                raise TimeoutError(f"MCP timeout: {method}")
            result = self.responses.get(timeout=remaining)
            if isinstance(result, Exception):
                raise result
            if result.get("id") != payload["id"]:
                continue
            if "error" in result:
                raise RuntimeError(f"MCP error: {result['error']}")
            return result["result"]

    def call(self, tool, arguments, expect_error=False):
        result = self.send("tools/call", {"name": tool, "arguments": arguments})
        text = "\n".join(item.get("text", "") for item in result.get("content", []))
        if expect_error:
            if not result.get("isError") or not text.startswith("mcp-stack gate:"):
                raise RuntimeError(f"Expected pre-dispatch rejection: {result}")
        elif result.get("isError") or not text or text.startswith("Error executing"):
            raise RuntimeError(f"Tool failed: {tool}: {result}")
        return text

    def close(self):
        if not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            inspected = command(["macctl", "run", "docker", "inspect", "--format",
                                 '{{.Config.Image}}|{{index .Config.Labels "com.docker.compose.project"}}|'
                                 '{{index .Config.Labels "com.docker.compose.service"}}', self.name]).strip()
            if inspected != "mcp-stack-graphify:0.9.72|mcp-stack|graphify":
                raise RuntimeError(f"Refusing to stop unexpected target: {inspected}")
            command(["macctl", "run", "docker", "stop", "--time", "5", self.name])
            self.process.wait(timeout=15)
        self.out_thread.join(timeout=2)
        self.err_thread.join(timeout=2)
        if exists(self.name):
            raise RuntimeError(f"Test container not cleaned up: {self.name}")
        if self.process.returncode:
            raise RuntimeError(f"MCP process exited {self.process.returncode}: {list(self.stderr)}")
        self.process.stdout.close()
        self.process.stderr.close()


def verify_container(name):
    container = json.loads(command(["macctl", "run", "docker", "inspect", name]))[0]
    config, host = container["Config"], container["HostConfig"]
    assert config["Image"] == "mcp-stack-graphify:0.9.72"
    assert config["User"] == "501:501"
    assert host["NetworkMode"] == "none" and host["ReadonlyRootfs"]
    assert not host["Privileged"] and not container["NetworkSettings"].get("Ports")
    assert host["Memory"] == 2 * 1024 ** 3 and host["NanoCpus"] == 2 * 10 ** 9
    assert host["RestartPolicy"]["Name"] == "no" and "/tmp" in host["Tmpfs"]
    expected = {f"{HOST_REPO}/{path}": False for path in SOURCES}
    expected[f"{HOST_REPO}/infra/graphify/state/mcp-stack"] = False
    expected[f"{HOST_REPO}/infra/graphify/serve_filtered.py"] = False
    actual = {mount["Source"]: mount["RW"] for mount in container["Mounts"]
              if mount["Type"] == "bind"}
    assert actual == expected, actual
    env = dict(item.split("=", 1) for item in config["Env"])
    assert env["GRAPHIFY_NO_AUTO_REFRESH"] == env["GRAPHIFY_QUERY_LOG_DISABLE"] == "1"
    assert not any(key.endswith("API_KEY") for key in env)
    print("Isolation: offline, UID 501, read-only sources/state/root, bounded CPU/RAM, no ports.")


def verify_graph():
    graph = json.loads(GRAPH.read_text())
    nodes = graph["nodes"]
    edges = graph.get("links", graph.get("edges", []))
    node_ids = {node["id"] for node in nodes}
    assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in edges)
    paths = {node.get("source_file") for node in nodes if node.get("source_file")}
    assert paths == SOURCES, paths
    fixture = {node["label"].removesuffix("()"): node for node in nodes
               if node.get("label", "").startswith("fixture_")}
    required = {"fixture_handle_request", "fixture_read_payload", "fixture_normalize_payload"}
    assert required <= fixture.keys(), fixture.keys()
    pairs = {(edge["source"], edge["target"]) for edge in edges
             if edge.get("relation") == "calls" and edge.get("confidence") == "EXTRACTED"}
    for source, target in [("fixture_handle_request", "fixture_read_payload"),
                           ("fixture_read_payload", "fixture_normalize_payload")]:
        assert (fixture[source]["id"], fixture[target]["id"]) in pairs
    analysis = json.loads((GRAPH.parent / ".graphify_analysis.json").read_text())
    assert analysis["tokens"] == {"input": 0, "output": 0}, analysis["tokens"]
    assert analysis["communities"]
    community = next(int(cid) for cid, members in analysis["communities"].items()
                     if fixture["fixture_handle_request"]["id"] in members)
    print(f"Scoped JSON graph: {len(paths)} files, {len(nodes)} nodes, {len(edges)} edges, "
          f"{len(analysis['communities'])} communities; zero LLM tokens.")
    return fixture, community


def verify_session(name, fixture, community):
    session = Session(name)
    try:
        initialized = session.send("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "mcp-stack-graphify-verification", "version": "1.0"},
        })
        print(f"MCP initialization: {initialized['serverInfo']}")
        session.send("notifications/initialized", notification=True)
        verify_container(name)
        tools = session.send("tools/list")["tools"]
        assert {tool["name"] for tool in tools} == TOOLS and len(tools) == 7
        assert all("project_path" not in tool["inputSchema"].get("properties", {}) for tool in tools)
        query = session.call("query_graph", {"question": "fixture_handle_request", "token_budget": 1000})
        assert "fixture_handle_request" in query, query
        node = session.call("get_node", {"node_id": fixture["fixture_handle_request"]["id"]})
        assert "fixture_handle_request" in node, node
        neighbors = session.call("get_neighbors", {"label": "fixture_handle_request"})
        assert "fixture_read_payload" in neighbors, neighbors
        comm = session.call("get_community", {"community_id": community})
        assert "fixture_handle_request" in comm, comm
        stats = session.call("graph_stats", {})
        ranking = session.call("god_nodes", {"top_n": 3})
        assert "node" in stats.lower() and ranking
        path = session.call("shortest_path", {
            "source": "fixture_handle_request", "target": "fixture_normalize_payload",
        })
        assert "fixture_handle_request" in path and "fixture_normalize_payload" in path, path
        for tool in ["list_prs", "get_pr_impact", "triage_prs"]:
            session.call(tool, {"pr_number": 1}, expect_error=True)
        session.call("graph_stats", {"project_path": "/foreign/project"}, expect_error=True)
        resources = session.send("resources/list")["resources"]
        expected_uris = {f"graphify://{name}" for name in
                         ["report", "stats", "god-nodes", "surprises", "audit", "questions"]}
        assert {resource["uri"] for resource in resources} == expected_uris
        resource = session.send("resources/read", {"uri": "graphify://stats"})
        assert any("node" in item.get("text", "").lower() for item in resource["contents"])
        # The minimal extraction intentionally does not generate GRAPH_REPORT.md.
        report = session.send("resources/read", {"uri": "graphify://report"})
        assert any("not found" in item.get("text", "") for item in report["contents"])
        for uri in expected_uris - {"graphify://stats", "graphify://report"}:
            result = session.send("resources/read", {"uri": uri})
            texts = [item.get("text", "") for item in result["contents"]]
            assert texts and all(text and not text.startswith("Could not") for text in texts), result
        print("Seven graph tools, three blocked PR tools, blocked foreign project and scoped resources verified.")
        return stats
    except Exception:
        print("Recent MCP stderr:", "\n".join(session.stderr))
        raise
    finally:
        session.close()


def main():
    fixture, community = verify_graph()
    before = hashes()
    first = verify_session("mcp-stack-graphify-mcp-smoke", fixture, community)
    second = verify_session("mcp-stack-graphify-mcp-reconnect", fixture, community)
    assert first == second, "Graph stats changed across reconnect"
    assert hashes() == before, "Source or state changed during read-only query sessions"
    print("PASS: reconnect persistence, unchanged source/state hashes, test containers removed.")


if __name__ == "__main__":
    main()
