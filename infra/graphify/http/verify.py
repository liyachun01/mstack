"""Approved direct Graphify HTTP checks; stdlib only, no service auto-start."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
NAME = "mcp-stack-graphify-http-test"
IMAGE = "sha256:2b1aa01c926d16fb25e5a5c7db077df29cdca85654e4606a03768a345d606fac"
STATE = ROOT / "infra/graphify/state/mcp-stack"
SOURCES = {"scripts/verify-basic-memory.py", "scripts/verify-codegraph.py",
           "infra/graphify/fixtures/call-chain.py"}


PROBE = r'''
import http.client
import importlib.metadata
import json
import platform
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

SETTINGS = __SETTINGS__
TOKEN = SETTINGS["key"]
DEADLINE = time.monotonic() + 180
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

NO_REDIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

def request(path, payload=None, token="valid", extra=None, duplicate=False):
    if time.monotonic() >= DEADLINE:
        raise RuntimeError("Overall HTTP probe deadline exceeded")
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + (TOKEN if token == "valid" else "0" * 64)
    headers.update(extra or {})
    body = None if payload is None else json.dumps(payload).encode()
    if duplicate:
        connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=10)
        try:
            connection.putrequest("POST" if body is not None else "GET", path)
            for name, value in headers.items():
                connection.putheader(name, value)
            connection.putheader("Authorization", "Bearer " + TOKEN)
            connection.putheader("Content-Length", str(len(body or b"")))
            connection.endheaders(body)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read(1048577)
        finally:
            connection.close()
    req = urllib.request.Request("http://127.0.0.1:8000" + path, data=body, headers=headers)
    try:
        with NO_REDIRECT.open(req, timeout=10) as response:
            return response.status, dict(response.headers), response.read(1048577)
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read(1048577)


class Session:
    def __init__(self):
        self.sequence = 0
        self.protocol = "2025-11-25"
        result = self.rpc("initialize", {"protocolVersion": self.protocol, "capabilities": {},
            "clientInfo": {"name": "graphify-direct-http-verifier", "version": "1"}})
        assert result["serverInfo"] == {"name": "graphify", "version": "1.29.0"}, "Unexpected server identity"
        self.protocol = result["protocolVersion"]
        assert self.protocol in {"2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"}
        caps = result["capabilities"]
        assert set(caps) <= {"tools", "resources", "logging", "experimental"}, "Unexpected capabilities"
        assert not caps.get("experimental"), "Unexpected experimental capability"
        assert "tools" in caps and "resources" in caps
        self.rpc("notifications/initialized", notification=True)

    def rpc(self, method, params=None, notification=False, expect_gate=False):
        self.sequence += 1
        payload = {"jsonrpc": "2.0", "method": method}
        if not notification:
            payload["id"] = self.sequence
        if params is not None:
            payload["params"] = params
        status, _, body = request("/mcp/", payload, extra={"MCP-Protocol-Version": self.protocol})
        if notification:
            assert status == 202, "Initialized notification status mismatch"
            return None
        assert status == 200, "RPC HTTP status " + str(status)
        assert len(body) <= 1048576, "Oversized RPC response"
        result = json.loads(body)
        assert result.get("jsonrpc") == "2.0" and result.get("id") == self.sequence, "Invalid RPC envelope"
        if expect_gate:
            assert result.get("error", {}).get("code") == -32602
            assert result["error"]["message"] == "mcp-stack gate: resource not permitted"
            return None
        if method in ("prompts/list", "resources/templates/list") and "error" in result:
            assert result["error"]["code"] == -32601, "Unexpected optional-surface error"
            return None
        assert "error" not in result and "result" in result, "Unexpected RPC error"
        return result["result"]

    def call(self, name, arguments, denied=False):
        result = self.rpc("tools/call", {"name": name, "arguments": arguments})
        text = "\n".join(item.get("text", "") for item in result.get("content", []))
        if denied:
            assert result.get("isError") and text.startswith("mcp-stack gate:"), "Missing pre-dispatch gate rejection"
        else:
            assert not result.get("isError") and text and not text.startswith("Error executing"), "Tool failed"
        return text


def main():
    expected_versions = {"graphifyy": "0.9.72", "mcp": "1.29.0", "starlette": "1.3.1", "uvicorn": "0.47.0"}
    assert {p: importlib.metadata.version(p) for p in expected_versions} == expected_versions
    assert platform.python_version() == "3.12.14"
    ready = time.monotonic() + 30
    while True:
        try:
            if request("/healthz")[0] == 200:
                break
        except urllib.error.URLError:
            pass
        assert time.monotonic() < ready, "Authenticated health readiness timeout"
        time.sleep(0.5)
    initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "auth-probe", "version": "1"}}}
    for path, payload in (("/healthz", None), ("/mcp/", initialize), ("/mcp", initialize)):
        for token in (None, "invalid"):
            status, _, body = request(path, payload, token=token)
            assert status == 401 and not body, "Authentication failure"
        status, _, body = request(path, payload, duplicate=True)
        assert status == 401 and not body, "Duplicate authentication not rejected"
    status, headers, _ = request("/mcp", initialize)
    assert status == 307 and headers.get("location", headers.get("Location", "")).endswith("/mcp/")
    print("PASS authentication: missing/wrong/duplicate keys 401; canonical /mcp/; authenticated /mcp redirects 307")
    print("PASS runtime: Python 3.12.14 / Graphify 0.9.72 / MCP 1.29.0 / Starlette 1.3.1 / uvicorn 0.47.0")

    first = Session()
    tools = first.rpc("tools/list")["tools"]
    assert len(tools) == 7 and {t["name"] for t in tools} == {
        "query_graph", "get_node", "get_neighbors", "get_community", "god_nodes", "graph_stats", "shortest_path"}
    assert all("project_path" not in t["inputSchema"].get("properties", {}) for t in tools)
    for method, key in (("prompts/list", "prompts"), ("resources/templates/list", "resourceTemplates")):
        result = first.rpc(method)
        assert result is None or result[key] == [], "Unexpected extra surface"
    print("PASS initialization and exactly seven restricted tools; no prompts/templates or project selector")

    fixtures = SETTINGS["fixtures"]
    assert "fixture_handle_request" in first.call("query_graph", {"question": "fixture_handle_request", "token_budget": 1000})
    assert "fixture_handle_request" in first.call("get_node", {"node_id": fixtures["fixture_handle_request"]})
    assert "fixture_read_payload" in first.call("get_neighbors", {"label": "fixture_handle_request"})
    assert "fixture_handle_request" in first.call("get_community", {"community_id": SETTINGS["community"]})
    stats = first.call("graph_stats", {})
    assert "node" in stats.lower() and "edge" in stats.lower()
    for count in (SETTINGS["nodes"], SETTINGS["edges"]):
        assert re.search(r"\b" + str(count) + r"\b", stats), "Graph counts mismatch"
    assert first.call("god_nodes", {"top_n": 3})
    path = first.call("shortest_path", {"source": "fixture_handle_request", "target": "fixture_normalize_payload"})
    assert "fixture_handle_request" in path and "fixture_normalize_payload" in path
    print("PASS all seven tool results and scoped 37-node/48-edge graph")

    for name in ("list_prs", "get_pr_impact", "triage_prs"):
        first.call(name, {"pr_number": 1}, denied=True)
    first.call("graph_stats", {"project_path": "/foreign/project"}, denied=True)
    print("PASS three excluded PR tools and foreign project rejected by unchanged pre-dispatch gate")

    expected = {"graphify://" + name for name in ("report", "stats", "god-nodes", "surprises", "audit", "questions")}
    resources = first.rpc("resources/list")["resources"]
    assert len(resources) == 6 and {r["uri"] for r in resources} == expected
    for uri in sorted(expected):
        result = first.rpc("resources/read", {"uri": uri})
        texts = [item.get("text", "") for item in result["contents"]]
        assert texts and all(text and not text.startswith("Could not") for text in texts)
        if uri == "graphify://report":
            assert any("not found" in text for text in texts), "Expected retained missing-report result"
        if uri == "graphify://stats":
            assert any("node" in text.lower() for text in texts)
    for uri in ("graphify://unknown", "file:///foreign/project", "graphify://stats?project_path=/foreign/project"):
        first.rpc("resources/read", {"uri": uri}, expect_gate=True)
    print("PASS six scoped resources; unknown/file/selector URI calls rejected before upstream read")

    for host in ("graphify-http", "graphify-http:8000"):
        assert request("/mcp/", initialize, extra={"Host": host})[0] == 200
    assert request("/mcp/", initialize, extra={"Host": "invalid.example:8000"})[0] == 421
    assert request("/mcp/", initialize, extra={"Origin": "https://invalid.example"})[0] == 403
    print("PASS intended internal Hosts accepted; unrelated Host 421 / Origin 403")

    second = Session()
    assert second.call("graph_stats", {}) == stats
    with ThreadPoolExecutor(max_workers=2) as pool:
        stat_result = pool.submit(first.call, "graph_stats", {})
        query_result = pool.submit(second.call, "query_graph", {"question": "fixture_handle_request", "token_budget": 1000})
        assert stat_result.result(timeout=15) == stats
        assert "fixture_handle_request" in query_result.result(timeout=15)
    print("PASS fresh initialized caller/reconnect and concurrent read-only calls")

try:
    main()
except Exception as error:
    # No exception message/body/traceback: stdin includes a private backend key.
    print("FAIL direct HTTP probe: " + type(error).__name__)
    raise SystemExit(1) from None
'''


def command(args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True,
                          timeout=20, check=True).stdout


def hashes():
    paths = list(STATE.rglob("*")) + [ROOT / name for name in SOURCES]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="store_true",
                        help="Verify the separately approved persistent service instead of the temporary test")
    parser.add_argument("--gateway-connected", action="store_true",
                        help="Require the separately approved gateway as the sole additional network member")
    parser.add_argument("--codegraph-connected", action="store_true",
                        help="Require the separately approved combined gateway's exact three networks")
    args = parser.parse_args()
    if args.gateway_connected and not args.service:
        parser.error("--gateway-connected requires --service")
    if args.codegraph_connected and not (args.service and args.gateway_connected):
        parser.error("--codegraph-connected requires --service --gateway-connected")
    name = "mcp-stack-graphify-http" if args.service else NAME
    project = "mcp-stack" if args.service else "mcp-stack-graphify-http-test"
    restart = "unless-stopped" if args.service else "no"
    host_root = command(["macctl", "run", "pwd"]).strip()
    # Captured inspect is not printed and contains no backend token environment.
    info = json.loads(command(["macctl", "run", "docker", "inspect", name]))[0]
    labels = info["Config"]["Labels"]
    assert labels["com.docker.compose.project"] == project
    assert labels["com.docker.compose.service"] == "graphify-http"
    assert info["Name"] == "/" + name and info["State"]["Running"]
    assert info["Image"] == IMAGE and info["Config"]["User"] == "501:501"
    host = info["HostConfig"]
    assert host["ReadonlyRootfs"] and not host["Privileged"]
    assert host["CapDrop"] == ["ALL"] and "no-new-privileges:true" in host["SecurityOpt"]
    assert host["Memory"] == 512 * 1024 ** 2 and host["NanoCpus"] == 10 ** 9 and host["PidsLimit"] == 128
    assert host["RestartPolicy"]["Name"] == restart and "/tmp" in host["Tmpfs"]
    assert not info["NetworkSettings"].get("Ports")
    assert set(info["NetworkSettings"]["Networks"]) == {"mcp-stack-graphify-transport"}
    network = json.loads(command(["macctl", "run", "docker", "network", "inspect", "mcp-stack-graphify-transport"]))[0]
    members = {info["Id"]}
    if args.gateway_connected:
        gateway = json.loads(command(["macctl", "run", "docker", "inspect", "mcp-stack-agentgateway-1"]))[0]
        assert gateway["Name"] == "/mcp-stack-agentgateway-1" and gateway["State"]["Running"]
        assert gateway["Config"]["Labels"]["com.docker.compose.project"] == "mcp-stack"
        assert gateway["Config"]["Labels"]["com.docker.compose.service"] == "agentgateway"
        expected_networks = {"mcp-stack-gateway-local", "mcp-stack-graphify-transport"}
        if args.codegraph_connected:
            expected_networks.add("mcp-stack-codegraph-transport")
        assert set(gateway["NetworkSettings"]["Networks"]) == expected_networks
        members.add(gateway["Id"])
    assert network["Internal"] and set(network["Containers"]) == members
    mounts = {m["Source"]: (m["Destination"], m["RW"]) for m in info["Mounts"] if m["Type"] == "bind"}
    expected = {host_root + "/" + name: ("/home/developer/workspace/mcp-stack/" + name, False) for name in SOURCES}
    expected.update({host_root + "/" + source: (target, False) for source, target in [
        ("infra/graphify/http/serve_http.py", "/opt/mcp-stack/serve_http.py"),
        ("infra/graphify/serve_filtered.py", "/opt/mcp-stack/serve_filtered.py"),
        ("infra/graphify/state/http/server.json", "/config/server.json"),
        ("infra/graphify/state/mcp-stack", "/state")]})
    assert mounts == expected
    env = dict(value.split("=", 1) for value in info["Config"]["Env"])
    assert env["GRAPHIFY_NO_AUTO_REFRESH"] == env["GRAPHIFY_QUERY_LOG_DISABLE"] == "1"
    assert not any(name.endswith("API_KEY") for name in env)
    print("PASS isolation: exact image, non-root/read-only, seven approved mounts, no ports, sole internal network, bounded resources")

    graph = json.loads((STATE / "graphify-out/graph.json").read_text())
    analysis = json.loads((STATE / "graphify-out/.graphify_analysis.json").read_text())
    assert {n["source_file"] for n in graph["nodes"] if n.get("source_file")} == SOURCES
    fixtures = {n["label"].removesuffix("()"): n["id"] for n in graph["nodes"]
                if n.get("label", "").startswith("fixture_")}
    community = next(int(cid) for cid, members in analysis["communities"].items()
                     if fixtures["fixture_handle_request"] in members)
    assert len(graph["nodes"]) == 37 and len(graph.get("links", graph.get("edges", []))) == 48
    assert len(analysis["communities"]) == 6 and analysis["tokens"] == {"input": 0, "output": 0}
    key = (ROOT / ".secrets/graphify-http-backend-key").read_text().strip()
    assert re.fullmatch(r"[0-9a-f]{64}", key)
    config = json.loads((ROOT / "infra/graphify/state/http/server.json").read_text())
    assert config == {"api_key_sha256": hashlib.sha256(key.encode()).hexdigest()}
    settings = {"key": key, "fixtures": fixtures, "community": community, "nodes": 37, "edges": 48}
    before = hashes()
    result = subprocess.run(["macctl", "run", "docker", "exec", "-i", name, "python", "-"],
                            cwd=ROOT, input=PROBE.replace("__SETTINGS__", repr(settings)),
                            text=True, capture_output=True, timeout=190)
    assert hashes() == before, "Source/index changed during direct queries"
    print(result.stdout.replace(key, "[redacted]"), end="")
    if result.returncode:
        # Avoid raw server responses/tracebacks in routine diagnostics.
        raise SystemExit("FAIL: direct Graphify HTTP probe; source/index hashes unchanged; inspect sanitized diagnostics")
    print("PASS unchanged three-source/index hashes; no graph re-extraction or Basic Memory call")


if __name__ == "__main__":
    main()
