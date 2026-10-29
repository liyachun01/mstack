"""Bounded CodeGraph gateway tests; no auto-start, secret output or memory writes."""

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("graphify_gateway_checks", ROOT / "infra/agentgateway/graphify/verify.py")
g = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = g
spec.loader.exec_module(g)
CHECKPOINT = "startup"
PATH = "/mcp/codegraph"
TOOL = "codegraph_codegraph_explore"
OWNED_SESSIONS = []


class Session(g.Session):
    def __init__(self, initialize=True, path=PATH):
        super().__init__(initialize=False, path=path)
        if initialize:
            reply = self.rpc("initialize", {"protocolVersion": self.protocol, "capabilities": {},
                "clientInfo": {"name": "mcp-stack-codegraph-gateway-verifier", "version": "1"}})
            print("  initialization HTTP=" + str(reply.status))
            self.session = reply.headers.get("mcp-session-id")
            if self.session:
                OWNED_SESSIONS.append(self)  # Track before validating a partial handshake.
            version = (reply.message or {}).get("result", {}).get("protocolVersion")
            supported = {"2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"}
            if version in supported:
                self.protocol = version
            result = g.successful(reply)
            assert result["protocolVersion"] in supported and self.session
            if path == PATH:
                assert self.protocol == "2025-06-18"
            print("  negotiated protocol=" + self.protocol)
            assert self.rpc("notifications/initialized", notification=True).status in (200, 202, 204)

    def delete_entry(self):
        assert self in OWNED_SESSIONS and self.session
        config = "\n".join((
            'header = "Accept: application/json, text/event-stream"',
            "header = " + json.dumps("Authorization: Bearer " + g.KEY),
            "header = " + json.dumps("Mcp-Session-Id: " + self.session),
            "header = " + json.dumps("MCP-Protocol-Version: " + self.protocol),
        )) + "\n"
        response = g.command(["macctl", "run", "curl", "--config", "-", "--request", "DELETE",
            "--silent", "--show-error", "--noproxy", "*", "--max-time", "10", "--output", "-",
            "--write-out", "\n__CODEGRAPH_DELETE_STATUS__%{http_code}",
            "http://127.0.0.1:58080" + self.path], config)
        body, marker, status = response.rpartition("\n__CODEGRAPH_DELETE_STATUS__")
        assert marker and status.strip().isdigit()
        print("  owned-session DELETE HTTP=" + status.strip())
        assert int(status.strip()) in (200, 202, 204)
        assert not any(key in body for key in credentials())

    def close(self):
        self.delete_entry()
        if self.path == PATH:
            replay = self.rpc("tools/list")
            g.rejected(replay)
            assert replay.status == 404  # Native CodeGraph session really was deleted.
            no_disclosure(replay, credentials())
        # Stateless Graphify tokens may resume; never POST after its final DELETE.
        OWNED_SESSIONS.remove(self)

    def explore(self, query):
        result = g.successful(self.rpc("tools/call", {"name": TOOL, "arguments": {"query": query}}))
        text = "\n".join(c.get("text", "") for c in result.get("content", []))
        assert text
        return text


def protected_hashes():
    paths = [ROOT / name for name in (
        ".secrets/agentgateway-client-key", ".secrets/codegraph-http-backend-key",
        ".secrets/graphify-http-backend-key", "infra/codegraph/http/serve_http.cjs",
        "infra/codegraph/http/compose.service.yaml", "infra/graphify/http/serve_http.py",
        "infra/graphify/serve_filtered.py", "scripts/verify-basic-memory.py", "scripts/verify-codegraph.py",
        "infra/codegraph/fixtures/call-chain.py", "infra/graphify/fixtures/call-chain.py",
        "infra/codegraph/state/http/server.json", "infra/graphify/state/http/server.json",
        "infra/agentgateway/state/graphify/config.json", "infra/agentgateway/state/graphify/backend.key")]
    paths += [p for folder in ("infra/codegraph/state/mcp-stack", "infra/graphify/state/mcp-stack")
              for p in (ROOT / folder).rglob("*") if p.is_file()]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def no_disclosure(reply, keys):
    assert not any(key in reply.body for key in keys)
    if reply.status != 200:
        assert not any(marker in reply.body for marker in ('"result"', '"contents"', 'fixture_'))
    else:
        assert reply.message and ("error" in reply.message or reply.message.get("result", {}).get("isError"))
        assert not any(marker in reply.body for marker in ("fixture_handle_request", "verify-basic-memory.py"))


def credentials():
    return [(ROOT / ".secrets" / name).read_text().strip() for name in (
        "agentgateway-client-key", "graphify-http-backend-key", "codegraph-http-backend-key")]


def deleted_token_auth(session, keys):
    previous_backend = g.BACKEND
    try:
        for backend in keys[1:]:
            g.BACKEND = backend
            for credential in (None, "invalid", "backend"):
                reply = session.rpc("tools/list", credential=credential)
                assert reply.status in (401, 403)
                no_disclosure(reply, keys)
    finally:
        g.BACKEND = previous_backend
    print("PASS deleted token still requires client authentication; both backend keys rejected")


def graphify_lifecycle(session, keys):
    session.delete_entry()
    deleted_token_auth(session, keys)
    reply = session.rpc("tools/list")
    assert not any(key in reply.body for key in keys)
    if reply.status == 200 and reply.message and "result" in reply.message and not reply.message["result"].get("isError"):
        result = g.successful(reply)
        assert set(result) == {"tools"}
        tools = result["tools"]
        assert len(tools) == 7 and {tool["name"] for tool in tools} == {"graphify_" + name for name in g.TOOLS}
        print("PASS Graphify same-route authenticated resumption: HTTP=200 shape=tools count=7 protocol=" + session.protocol)
        return "resumed"
    g.rejected(reply)
    no_disclosure(reply, keys)
    print("PASS Graphify same-route reuse explicitly denied: HTTP=" + str(reply.status))
    return "denied"


def run_diagnostic():
    global CHECKPOINT
    g.DEADLINE = time.monotonic() + 90
    keys = credentials()
    assert len(set(keys)) == 3 and all(re.fullmatch(r"[0-9a-f]{64}", key) for key in keys)
    g.KEY, g.BACKEND, g.CODEGRAPH_CONNECTED = keys[0], keys[1], False
    before = protected_hashes()
    CHECKPOINT = "Graphify-only runtime isolation"
    g.isolation()
    CHECKPOINT = "Graphify-only DELETE/resume characterization"
    graph = Session(path="/mcp/graphify")
    graphify_lifecycle(graph, keys)
    assert protected_hashes() == before
    print("PASS one owned Graphify session characterized without gateway recreation or protected-file changes")


def wrong_backend_credentials(client, graphify, codegraph):
    node = r'''const fs=require('node:fs'), http=require('node:http');
const keys=JSON.parse(fs.readFileSync(0,'utf8')).keys;
async function run(key){ return new Promise((resolve,reject)=>{
  const req=http.request({hostname:'127.0.0.1',port:8000,path:'/healthz',method:'GET',
    headers:{Host:'codegraph-http:8000',Authorization:'Bearer '+key}},res=>{res.resume();res.on('end',()=>resolve(res.statusCode));});
  req.on('error',reject);req.setTimeout(5000,()=>req.destroy(new Error('timeout')));req.end();});}
Promise.all(keys.map(run)).then(codes=>{if(codes.some(c=>c!==401))process.exitCode=1;else console.log('PASS cross-key backend rejection');},()=>{process.exitCode=1;});'''
    output = g.command(["macctl", "run", "docker", "exec", "-i", "mcp-stack-codegraph-http", "node", "-e", node],
                       json.dumps({"keys": [client, graphify]}))
    assert output.strip() == "PASS cross-key backend rejection"
    python = '''import json,sys,urllib.request,urllib.error
for key in json.load(sys.stdin)["keys"]:
    req=urllib.request.Request("http://127.0.0.1:8000/healthz",headers={"Authorization":"Bearer "+key})
    try: urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=5)
    except urllib.error.HTTPError as error: assert error.code==401
    else: raise SystemExit(1)
print("PASS cross-key backend rejection")
'''
    output = g.command(["macctl", "run", "docker", "exec", "-i", "mcp-stack-graphify-http", "python", "-c", python],
                       json.dumps({"keys": [client, codegraph]}))
    assert output.strip() == "PASS cross-key backend rejection"


def run_checks():
    global CHECKPOINT
    g.DEADLINE = time.monotonic() + 240
    keys = credentials()
    assert len(set(keys)) == 3 and all(re.fullmatch(r"[0-9a-f]{64}", key) for key in keys)
    client, graphify, codegraph = keys
    g.KEY, g.BACKEND, g.CODEGRAPH_CONNECTED = client, graphify, True
    before = protected_hashes()
    CHECKPOINT = "exact gateway isolation/key copies"
    g.isolation()
    state = ROOT / "infra/agentgateway/state/codegraph"
    assert (state / "backend.key").read_text() == codegraph
    host_root = g.command(["macctl", "run", "pwd"]).strip()
    assert g.command(["macctl", "run", "stat", "-f", "%u:%g %Lp", host_root + "/infra/agentgateway/state/codegraph/backend.key"]).strip() == "501:501 640"
    info = json.loads(g.command(["macctl", "run", "docker", "inspect", g.GATEWAY]))[0]
    assert all(key not in "\n".join(info["Config"]["Env"]) for key in keys)
    print("PASS exact three-network/three-RO-bind gateway, original credentials and protected CodeGraph key copy")
    CHECKPOINT = "client/backend/cross-backend credential separation"
    init = {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "negative-auth", "version": "1"}}
    for backend in (graphify, codegraph):
        g.BACKEND = backend
        for credential in (None, "invalid", "backend"):
            assert Session(initialize=False).rpc("initialize", init, credential=credential).status in (401, 403)
    wrong_backend_credentials(client, graphify, codegraph)
    print("PASS missing/wrong/backend-as-client and client/cross-backend keys rejected")
    CHECKPOINT = "real CodeGraph transport initialization/discovery"
    first = Session()
    tools = g.successful(first.rpc("tools/list"))["tools"]
    print("  discovered tool count=" + str(len(tools)))
    assert len(tools) == 1 and tools[0]["name"] == TOOL
    assert "projectPath" not in tools[0]["inputSchema"].get("properties", {})
    print("PASS real authenticated CodeGraph backend negotiation and exactly one prefixed explore tool")
    CHECKPOINT = "fixture and real-source queries"
    fixture = first.explore("fixture_handle_request fixture_read_payload fixture_normalize_payload")
    assert all(name in fixture for name in ("fixture_handle_request", "fixture_read_payload", "fixture_normalize_payload"))
    assert "jsonrpc" in first.explore("scripts/verify-basic-memory.py Session.send")
    print("PASS useful fixture and actual Python source via gateway; partial index remains read-only")
    CHECKPOINT = "tools-only gates and foreign project"
    assert g.successful(first.rpc("resources/list"))["resources"] == []
    for method, field in (("prompts/list", "prompts"), ("resources/templates/list", "resourceTemplates")):
        reply = first.rpc(method)
        if reply.status == 200 and reply.message and "error" in reply.message:
            assert reply.message["error"]["code"] == -32601
        else:
            assert g.successful(reply)[field] == []
    for name in ("codegraph_codegraph_status", "codegraph_codegraph_search", "codegraph_codegraph_sync",
                 "codegraph_unknown", "codegraph_explore", "graphify_graph_stats"):
        reply = first.rpc("tools/call", {"name": name, "arguments": {}})
        g.rejected(reply); no_disclosure(reply, keys)
    for method, params in (("resources/read", {"uri": "codegraph+file:///foreign"}),
                           ("prompts/get", {"name": "codegraph_unknown", "arguments": {}})):
        reply = first.rpc(method, params)
        g.rejected(reply); no_disclosure(reply, keys)
    for project in ("/foreign", "/home/developer/workspace/mcp-stack"):
        reply = first.rpc("tools/call", {"name": TOOL, "arguments": {"query": "fixture_handle_request", "projectPath": project}})
        g.rejected(reply); no_disclosure(reply, keys)
        if reply.message and "error" in reply.message:
            assert reply.message["error"]["message"].startswith("mcp-stack gate:")
    print("PASS hidden status/search/sync/unknown/unprefixed/wrong-target/resource/prompt and project-selector denials")
    CHECKPOINT = "independent fresh/concurrent gateway sessions"
    a, b = Session(), Session()
    assert len({first.session, a.session, b.session}) == 3
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda s: s.explore("scripts/verify-basic-memory.py Session.send"), (a, b)))
    assert all("jsonrpc" in result and "verify-basic-memory.py" in result for result in results)
    fresh = Session()
    assert "jsonrpc" in fresh.explore("scripts/verify-basic-memory.py Session.send")
    unknown = Session(initialize=False)
    unknown.session = "00000000-0000-0000-0000-000000000000"
    g.rejected(unknown.rpc("tools/list"))
    print("PASS concurrent independent fresh native-source sessions, reconnect and unknown session rejection")
    CHECKPOINT = "delete-one gateway session isolation"
    a.close()
    assert g.successful(b.rpc("tools/list"))["tools"][0]["name"] == TOOL
    print("PASS explicit deletion rejects reuse while another gateway session remains usable")
    CHECKPOINT = "bidirectional endpoint replay boundaries"
    graph = Session(path="/mcp/graphify")
    forward = Session(initialize=False, path="/mcp/graphify")
    forward.session, forward.protocol = first.session, graph.protocol
    backward = Session(initialize=False)
    backward.session, backward.protocol = graph.session, first.protocol
    for session, name in ((forward, TOOL), (forward, "graphify_graph_stats"),
                          (backward, "graphify_graph_stats"), (backward, TOOL)):
        reply = session.rpc("tools/call", {"name": name, "arguments": {"query": "fixture_handle_request"}})
        g.rejected(reply); no_disclosure(reply, keys)
    print("PASS bidirectional replay denies both source and destination tool names; no route cross-exposure")
    CHECKPOINT = "deleted-token lifecycle/authentication"
    first.close()
    deleted_token_auth(first, keys)
    graphify_lifecycle(graph, keys)
    CHECKPOINT = "after-DELETE cold bidirectional endpoint replay"
    graph.delete_entry()  # Remove the entry reconstructed by same-route tools/list.
    for session, name in ((forward, TOOL), (forward, "graphify_graph_stats"),
                          (backward, "graphify_graph_stats"), (backward, TOOL)):
        reply = session.rpc("tools/call", {"name": name, "arguments": {"query": "fixture_handle_request"}})
        g.rejected(reply); no_disclosure(reply, keys)
    print("PASS four cold bidirectional replay denials with destination protocol; no cross-route data")
    assert protected_hashes() == before
    print("PASS original source/index/WAL/SHM/config/key hashes unchanged; no lifecycle/index/model/Basic Memory calls")


def main():
    global CHECKPOINT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graphify-session-diagnostic", action="store_true",
                        help="Characterize one owned session on the existing Graphify-only gateway")
    args = parser.parse_args()
    try:
        if args.graphify_session_diagnostic:
            run_diagnostic()
        else:
            run_checks()
    except Exception as error:
        print("FAIL before cleanup at " + CHECKPOINT + ": " + type(error).__name__, flush=True)
        raise
    finally:
        # A bounded cleanup reserve applies even if the test deadline expired.
        # Only genuinely created sessions are tracked, never replay aliases.
        g.DEADLINE = time.monotonic() + 90
        failed = False
        for session in list(OWNED_SESSIONS):
            try:
                session.close()
            except Exception as error:
                failed = True
                print("FAIL owned-session cleanup: " + type(error).__name__, flush=True)
        if failed:
            CHECKPOINT = "owned-session cleanup"
            raise RuntimeError("Test-owned session cleanup failed") from None
        print("PASS all test-owned gateway sessions explicitly deleted; native capacity requires the separate direct suite")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL CodeGraph gateway verifier at " + CHECKPOINT + ": " + type(error).__name__, flush=True)
        raise SystemExit(1) from None
