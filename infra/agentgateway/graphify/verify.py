"""Bounded, stdlib-only checks of the approved Graphify gateway connection.

No service auto-start/lifecycle action; no model, extraction or Basic Memory call.
Credential and response diagnostics must never be printed.
"""

import argparse
import hashlib
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GATEWAY = "mcp-stack-agentgateway-1"
GRAPHIFY = "mcp-stack-graphify-http"
IMAGE = "ghcr.io/agentgateway/agentgateway@sha256:bf2f339ef326d32def2aaeb44b1b4549801293c19b89e764a4228667d97d9896"
TOOLS = {"query_graph", "get_node", "get_neighbors", "get_community", "god_nodes", "graph_stats", "shortest_path"}
DEADLINE = 0.0
KEY = ""
BACKEND = ""
CHECKPOINT = "startup"
CODEGRAPH_CONNECTED = False


@dataclass
class Reply:
    status: int
    headers: dict
    message: dict | None
    body: str


def remaining(limit=15):
    value = min(limit, DEADLINE - time.monotonic())
    if value <= 0:
        raise RuntimeError("Overall verifier deadline exceeded")
    return value


def command(args, data=None):
    return subprocess.run(args, input=data, cwd=ROOT, text=True, capture_output=True,
                          timeout=remaining(20), check=True).stdout


def http(path, payload=None, credential="valid", headers=None):
    config = ['header = "Accept: application/json, text/event-stream"']
    if credential is not None:
        value = KEY if credential == "valid" else BACKEND if credential == "backend" else "invalid-graphify-client-key"
        config.append("header = " + json.dumps("Authorization: Bearer " + value))
    for name, value in (headers or {}).items():
        config.append("header = " + json.dumps(name + ": " + value))
    if payload is not None:
        config.extend(['header = "Content-Type: application/json"', "data = " + json.dumps(json.dumps(payload))])
    result = command(["macctl", "run", "curl", "--config", "-", "--silent", "--show-error",
        "--noproxy", "*", "--max-time", "10", "--dump-header", "-", "--output", "-",
        "--write-out", "\n__GRAPHIFY_STATUS__%{http_code}", "http://127.0.0.1:58080" + path],
        "\n".join(config) + "\n")
    raw, marker, status = result.rpartition("\n__GRAPHIFY_STATUS__")
    assert marker and status.strip().isdigit()
    header_block, boundary, body = raw.partition("\n\n")
    assert boundary
    while re.match(r"HTTP/\S+ 1\d\d", header_block):
        header_block, boundary, body = body.partition("\n\n")
        assert boundary
    response_headers = {name.lower(): value.strip() for line in header_block.splitlines()[1:]
                        if ":" in line for name, value in [line.split(":", 1)]}
    assert len(body) <= 1048576
    code = int(status.strip())
    message = None
    if payload is not None and "id" in payload and code == 200:
        if "text/event-stream" in response_headers.get("content-type", ""):
            candidates = [json.loads(line[5:].strip()) for line in body.splitlines() if line.startswith("data:")]
            matches = [m for m in candidates if m.get("id") == payload["id"]]
            assert len(matches) == 1
            message = matches[0]
        else:
            message = json.loads(body)
        assert message.get("jsonrpc") == "2.0" and message.get("id") == payload["id"]
        assert ("result" in message) != ("error" in message)
    return Reply(code, response_headers, message, body)


def successful(reply):
    assert reply.status == 200 and reply.message and "error" not in reply.message
    result = reply.message["result"]
    assert not isinstance(result, dict) or not result.get("isError")
    return result


def rejected(reply):
    assert reply.status in (400, 401, 403, 404) or (
        reply.status == 200 and reply.message and (
            "error" in reply.message or reply.message.get("result", {}).get("isError")))
    print("  denial HTTP=" + str(reply.status) +
          (" RPC=" + str(reply.message["error"].get("code")) if reply.message and "error" in reply.message else ""))


class Session:
    def __init__(self, initialize=True, path="/mcp/graphify"):
        self.path, self.session, self.protocol, self.sequence = path, None, "2025-11-25", 0
        if initialize:
            reply = self.rpc("initialize", {"protocolVersion": self.protocol, "capabilities": {},
                "clientInfo": {"name": "mcp-stack-graphify-gateway-verifier", "version": "1"}})
            self.protocol = successful(reply)["protocolVersion"]
            assert self.protocol in {"2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"}
            self.session = reply.headers.get("mcp-session-id")
            assert self.session
            assert self.rpc("notifications/initialized", notification=True).status in (200, 202, 204)

    def rpc(self, method, params=None, notification=False, credential="valid"):
        self.sequence += 1
        payload = {"jsonrpc": "2.0", "method": method}
        if not notification:
            payload["id"] = self.sequence
        if params is not None:
            payload["params"] = params
        headers = {"MCP-Protocol-Version": self.protocol}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        return http(self.path, payload, credential, headers)

    def call(self, name, arguments):
        result = successful(self.rpc("tools/call", {"name": "graphify_" + name, "arguments": arguments}))
        text = "\n".join(item.get("text", "") for item in result.get("content", []))
        assert text and not text.startswith(("Error executing", "mcp-stack gate:"))
        return text


def protected_hashes():
    sources = [ROOT / name for name in ("scripts/verify-basic-memory.py", "scripts/verify-codegraph.py",
        "infra/graphify/fixtures/call-chain.py", "infra/graphify/http/serve_http.py", "infra/graphify/serve_filtered.py",
        ".secrets/agentgateway-client-key", ".secrets/graphify-http-backend-key",
        "infra/agentgateway/state/config.json", "infra/graphify/state/http/server.json")]
    sources += [p for p in (ROOT / "infra/graphify/state/mcp-stack").rglob("*") if p.is_file()]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}


def isolation():
    info = json.loads(command(["macctl", "run", "docker", "inspect", GATEWAY]))[0]
    assert info["Name"] == "/" + GATEWAY and info["State"]["Running"]
    assert info["Config"]["Image"] == IMAGE and info["Config"]["User"] == "65532:65532"
    assert info["Config"]["Labels"]["com.docker.compose.project"] == "mcp-stack"
    assert info["Config"]["Labels"]["com.docker.compose.service"] == "agentgateway"
    image = json.loads(command(["macctl", "run", "docker", "image", "inspect", IMAGE]))[0]
    assert info["Image"] == image["Id"] and image["Architecture"] == "arm64"
    host = info["HostConfig"]
    assert host["GroupAdd"] == ["501"] and host["ReadonlyRootfs"] and not host["Privileged"]
    assert host["CapDrop"] == ["ALL"] and "no-new-privileges:true" in host["SecurityOpt"]
    assert host["Memory"] == 512 * 1024 ** 2 and host["NanoCpus"] == 10 ** 9 and host["PidsLimit"] == 128
    assert host["RestartPolicy"]["Name"] == "unless-stopped"
    assert host["PortBindings"] == {"4000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "58080"}]}
    assert host["LogConfig"] == {"Type": "json-file", "Config": {"max-file": "2", "max-size": "5m"}}
    assert set(host["Tmpfs"]) == {"/tmp"}
    networks = {"mcp-stack-gateway-local", "mcp-stack-graphify-transport"}
    if CODEGRAPH_CONNECTED:
        networks.add("mcp-stack-codegraph-transport")
    assert set(info["NetworkSettings"]["Networks"]) == networks
    graphify = json.loads(command(["macctl", "run", "docker", "inspect", GRAPHIFY]))[0]
    assert graphify["Config"]["Labels"]["com.docker.compose.project"] == "mcp-stack"
    assert graphify["Config"]["Labels"]["com.docker.compose.service"] == "graphify-http"
    assert graphify["State"]["Running"] and set(graphify["NetworkSettings"]["Networks"]) == {"mcp-stack-graphify-transport"}
    network = json.loads(command(["macctl", "run", "docker", "network", "inspect", "mcp-stack-graphify-transport"]))[0]
    assert network["Internal"] and set(network["Containers"]) == {info["Id"], graphify["Id"]}
    external = json.loads(command(["macctl", "run", "docker", "network", "inspect", "mcp-stack-gateway-local"]))[0]
    assert not external["Internal"] and set(external["Containers"]) == {info["Id"]}
    host_root = command(["macctl", "run", "pwd"]).strip()
    mounts = {m["Source"]: (m["Destination"], m["RW"]) for m in info["Mounts"]}
    profile = "codegraph" if CODEGRAPH_CONNECTED else "graphify"
    expected_mounts = {
        host_root + f"/infra/agentgateway/state/{profile}/config.json": ("/config/config.json", False),
        host_root + "/infra/agentgateway/state/graphify/backend.key": ("/run/secrets/graphify-backend-key", False)}
    if CODEGRAPH_CONNECTED:
        expected_mounts[host_root + "/infra/agentgateway/state/codegraph/backend.key"] = ("/run/secrets/codegraph-backend-key", False)
        codegraph = json.loads(command(["macctl", "run", "docker", "inspect", "mcp-stack-codegraph-http"]))[0]
        assert codegraph["State"]["Running"]
        assert codegraph["Config"]["Labels"]["com.docker.compose.project"] == "mcp-stack"
        assert codegraph["Config"]["Labels"]["com.docker.compose.service"] == "codegraph-http"
        assert set(codegraph["NetworkSettings"]["Networks"]) == {"mcp-stack-codegraph-transport"}
        net = json.loads(command(["macctl", "run", "docker", "network", "inspect", "mcp-stack-codegraph-transport"]))[0]
        assert net["Internal"] and set(net["Containers"]) == {info["Id"], codegraph["Id"]}
    assert mounts == expected_mounts
    metadata = command(["macctl", "run", "stat", "-f", "%u:%g %Lp",
        host_root + "/infra/agentgateway/state/graphify/backend.key"]).strip()
    assert metadata == "501:501 640"
    state = ROOT / "infra/agentgateway/state/graphify"
    assert state.stat().st_mode & 0o777 == 0o700
    assert (state / "backend.key").read_text() == BACKEND
    live_state = ROOT / f"infra/agentgateway/state/{profile}"
    template_dir = ROOT / f"infra/agentgateway/{profile}"
    assert live_state.stat().st_mode & 0o777 == 0o700
    assert json.loads((live_state / "config.json").read_text()) == json.loads(
        (template_dir / "config.template.json").read_text().replace(
            "__CLIENT_KEY_SHA256__", hashlib.sha256(KEY.encode()).hexdigest()))
    assert all(key not in "\n".join(info["Config"]["Env"]) for key in (KEY, BACKEND))
    print("PASS pinned ARM64 gateway, non-root/read-only limits, exact RO binds, protected key-copy and exact network isolation")


def main():
    global KEY, BACKEND, DEADLINE, CHECKPOINT, CODEGRAPH_CONNECTED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codegraph-connected", action="store_true",
                        help="Verify the separately approved combined gateway; defaults preserve Graphify-only checks")
    CODEGRAPH_CONNECTED = parser.parse_args().codegraph_connected
    DEADLINE = time.monotonic() + 240
    KEY = (ROOT / ".secrets/agentgateway-client-key").read_text().strip()
    BACKEND = (ROOT / ".secrets/graphify-http-backend-key").read_text().strip()
    assert all(re.fullmatch(r"[0-9a-f]{64}", k) for k in (KEY, BACKEND)) and KEY != BACKEND
    before = protected_hashes()
    CHECKPOINT = "runtime isolation"
    isolation()
    CHECKPOINT = "client/backend authentication separation"
    for credential in (None, "invalid", "backend"):
        reply = Session(initialize=False).rpc("initialize", {"protocolVersion": "2025-11-25",
            "capabilities": {}, "clientInfo": {"name": "negative-auth", "version": "1"}}, credential=credential)
        assert reply.status in (401, 403)
    direct = '''import json,sys,urllib.request,urllib.error
key=json.load(sys.stdin)["key"]
payload={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"wrong-client-key","version":"1"}}}
req=urllib.request.Request("http://127.0.0.1:8000/mcp/",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Accept":"application/json, text/event-stream","Content-Type":"application/json"})
try:
    urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=5)
except urllib.error.HTTPError as error:
    assert error.code==401
    print("PASS client credential rejected directly by Graphify backend")
else:
    raise SystemExit(1)
'''
    output = command(["macctl", "run", "docker", "exec", "-i", GRAPHIFY, "python", "-c", direct], json.dumps({"key": KEY}))
    assert output.strip() == "PASS client credential rejected directly by Graphify backend"
    print("PASS missing/wrong/backend-as-client credentials denied; client key rejected directly by backend")
    CHECKPOINT = "gateway initialization and discovery"
    first = Session()
    tools = successful(first.rpc("tools/list"))["tools"]
    assert len(tools) == 7 and {t["name"] for t in tools} == {"graphify_" + name for name in TOOLS}
    assert all("project_path" not in t["inputSchema"].get("properties", {}) for t in tools)
    print("PASS real inter-container backend authentication, initialize and exactly seven prefixed tools")
    graph = json.loads((ROOT / "infra/graphify/state/mcp-stack/graphify-out/graph.json").read_text())
    analysis = json.loads((ROOT / "infra/graphify/state/mcp-stack/graphify-out/.graphify_analysis.json").read_text())
    fixtures = {n["label"].removesuffix("()"): n["id"] for n in graph["nodes"] if n.get("label", "").startswith("fixture_")}
    community = next(int(cid) for cid, members in analysis["communities"].items() if fixtures["fixture_handle_request"] in members)
    CHECKPOINT = "seven useful tool calls"
    assert "fixture_handle_request" in first.call("query_graph", {"question": "fixture_handle_request", "token_budget": 1000})
    assert "fixture_handle_request" in first.call("get_node", {"node_id": fixtures["fixture_handle_request"]})
    assert "fixture_read_payload" in first.call("get_neighbors", {"label": "fixture_handle_request"})
    assert "fixture_handle_request" in first.call("get_community", {"community_id": community})
    stats = first.call("graph_stats", {})
    assert "node" in stats.lower() and "edge" in stats.lower()
    assert all(re.search(r"\b" + str(n) + r"\b", stats) for n in (37, 48))
    assert first.call("god_nodes", {"top_n": 3})
    path = first.call("shortest_path", {"source": "fixture_handle_request", "target": "fixture_normalize_payload"})
    assert "fixture_handle_request" in path and "fixture_normalize_payload" in path
    print("PASS all seven useful gateway tool calls; retained 37-node/48-edge fixture graph")
    CHECKPOINT = "excluded surfaces and scoped arguments"
    assert successful(first.rpc("resources/list"))["resources"] == []
    for method, key in (("prompts/list", "prompts"), ("resources/templates/list", "resourceTemplates")):
        optional = first.rpc(method)
        # The pinned upstream does not implement these optional MCP surfaces.
        # Explicit method-not-found is also closed; other errors never count.
        if optional.status == 200 and optional.message and "error" in optional.message:
            assert optional.message["error"]["code"] == -32601
        else:
            assert successful(optional)[key] == []
    for name in ("graphify_list_prs", "graphify_get_pr_impact", "graphify_triage_prs", "graph_stats", "graphify_unknown"):
        rejected(first.rpc("tools/call", {"name": name, "arguments": {}}))
    for uri in ("graphify+graphify://stats", "graphify+file:///foreign/project"):
        rejected(first.rpc("resources/read", {"uri": uri}))
    rejected(first.rpc("prompts/get", {"name": "graphify_unknown", "arguments": {}}))
    reply = first.rpc("tools/call", {"name": "graphify_graph_stats", "arguments": {"project_path": "/foreign/project"}})
    rejected(reply)
    if reply.status == 200 and reply.message and "result" in reply.message:
        assert reply.message["result"].get("isError")
        assert reply.message["result"]["content"][0]["text"].startswith("mcp-stack gate:")
    print("PASS tools-only discovery; direct PR/unprefixed/unknown/resource/prompt calls and foreign-project arguments denied")
    CHECKPOINT = "malformed URI routing limitation (not authorization denial)"
    malformed = first.rpc("resources/read", {"uri": "graphify://stats"})
    # Pinned handler.rs:529-558 rejects a missing target+ prefix before
    # session.rs:623-641 reaches authorization or send_single. The official
    # runtime maps this InvalidRequest to HTTP 500. Never allow 5xx in rejected().
    assert malformed.status == 500 and malformed.message is None
    assert not any(marker in malformed.body for marker in ('"contents"', '"result"', 'fixture_', KEY, BACKEND))
    print("KNOWN LIMITATION: malformed unprefixed resource URI returns HTTP 500 before dispatch; not counted as authorization denial")
    CHECKPOINT = "fresh and concurrent independent gateway sessions"
    second, third = Session(), Session()
    assert len({first.session, second.session, third.session}) == 3
    assert second.call("graph_stats", {}) == stats
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(second.call, "graph_stats", {})
        b = pool.submit(third.call, "query_graph", {"question": "fixture_handle_request", "token_budget": 1000})
        assert a.result(timeout=remaining()) == stats
        assert "fixture_handle_request" in b.result(timeout=remaining())
    unknown = Session(initialize=False)
    unknown.session = "00000000-0000-0000-0000-000000000000"
    rejected(unknown.rpc("tools/list"))
    replay = Session(initialize=False, path="/mcp")
    replay.session = first.session
    assert replay.rpc("tools/list").status == 503
    assert protected_hashes() == before
    print("PASS fresh/reconnected and actual concurrent independent sessions; unknown session denied; placeholder route replay remains 503")
    print("PASS source/index/original key/config hashes unchanged; no lifecycle, extraction, models or Basic Memory calls")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL Graphify gateway verifier at " + CHECKPOINT + ": " + type(error).__name__, flush=True)
        raise SystemExit(1) from None
