"""Bounded synthetic fixture/gateway checks; requires the matching approved setup."""

import argparse
import json
import re
import subprocess
import time
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


# Executed via stdin in ONLY the approved, already-running fixture container.
# Uses the standard library and contains no credentials or real data.
DIRECT_PROBE = r'''
import importlib.metadata
import json
import platform
import time
import urllib.error
import urllib.request

deadline = time.monotonic() + 180
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
protocol = "2025-11-25"
sequence = 0

def request(path, data=None, extra=None):
    assert time.monotonic() < deadline, "Overall probe deadline exceeded"
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    headers.update(extra or {})
    encoded = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request("http://127.0.0.1:8000" + path,
                                 data=encoded, headers=headers)
    try:
        with opener.open(req, timeout=10) as response:
            return response.status, response.headers, response.read(1048577)
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read(1048577)

def rpc(target, method, params=None, notification=False, expected=200, extra=None):
    global sequence
    sequence += 1
    payload = {"jsonrpc": "2.0", "method": method}
    if not notification:
        payload["id"] = sequence
    if params is not None:
        payload["params"] = params
    headers = {"MCP-Protocol-Version": protocol}
    headers.update(extra or {})
    status, response_headers, body = request("/" + target + "/mcp", payload, headers)
    assert status == expected, f"{target} {method}: HTTP {status}, expected {expected}"
    if expected != 200 or notification:
        return None
    assert len(body) <= 1048576, "Oversized fixture response"
    result = json.loads(body)
    assert result.get("id") == sequence and result.get("jsonrpc") == "2.0"
    assert "error" not in result and "result" in result, "Unexpected fixture RPC error"
    return result["result"]

ready_deadline = time.monotonic() + 30
while True:
    try:
        status, _, body = request("/stats")
        if status == 200:
            break
    except urllib.error.URLError:
        pass
    assert time.monotonic() < ready_deadline, "Fixture readiness timeout"
    time.sleep(0.5)

versions = json.loads(body)["versions"]
assert versions == {"mcp": "1.29.0", "starlette": "1.3.1", "uvicorn": "0.47.0"}
assert platform.python_version() == "3.12.14"
print("PASS runtime: Python 3.12.14; MCP 1.29.0; Starlette 1.3.1; uvicorn 0.47.0")
assert request("/control", {"beta_enabled": True, "reset": True})[0] == 200

try:
    for target in ("alpha", "beta"):
        target_deadline = time.monotonic() + 30
        init = rpc(target, "initialize", {"protocolVersion": protocol,
            "capabilities": {}, "clientInfo": {"name": "synthetic-direct-probe", "version": "1"}})
        assert init["protocolVersion"] == protocol
        assert init["serverInfo"]["name"] == "synthetic-" + target
        rpc(target, "notifications/initialized", notification=True, expected=202)
        tools = rpc(target, "tools/list")["tools"]
        assert {tool["name"] for tool in tools} == {"echo", "blocked"}
        for name, text in (("echo", target + ":synthetic-text"),
                           ("blocked", target + ":blocked-dispatched")):
            result = rpc(target, "tools/call", {"name": name, "arguments": {"text": "synthetic-text"}})
            assert not result.get("isError") and result["content"][0]["text"] == text
        assert [p["name"] for p in rpc(target, "prompts/list")["prompts"]] == ["blocked_prompt"]
        result = rpc(target, "prompts/get", {"name": "blocked_prompt", "arguments": {}})
        assert result["messages"][0]["content"]["text"] == target + ":prompt"
        uri = "synthetic://" + target + "/blocked"
        assert [r["uri"] for r in rpc(target, "resources/list")["resources"]] == [uri]
        assert rpc(target, "resources/read", {"uri": uri})["contents"][0]["text"] == target + ":resource"
        assert len(rpc(target, "tools/list", extra={"Host": "fixture"})["tools"]) == 2
        rpc(target, "tools/list", expected=421, extra={"Host": "invalid.example:8000"})
        rpc(target, "tools/list", expected=403, extra={"Origin": "https://invalid.example"})
        assert time.monotonic() < target_deadline, "Target probe deadline exceeded"
        print("PASS " + target + ": initialize, discovery, dispatch, exact internal Host allowed; unrelated Host/Origin rejected")

    assert json.loads(request("/stats")[2])["counters"] == {
        target: {key: 1 for key in ("echo", "blocked", "prompt", "resource")}
        for target in ("alpha", "beta")}
    assert request("/control", {"beta_enabled": False})[0] == 200
    rpc("beta", "tools/list", expected=503)
    assert len(rpc("alpha", "tools/list")["tools"]) == 2
    assert request("/control", {"beta_enabled": True})[0] == 200
    assert len(rpc("beta", "tools/list")["tools"]) == 2
    print("PASS counters, isolated beta outage, alpha availability and beta recovery")
finally:
    assert request("/control", {"beta_enabled": True, "reset": True})[0] == 200

assert all(n == 0 for counters in json.loads(request("/stats")[2])["counters"].values()
           for n in counters.values())
print("PASS controls restored; counters reset; direct fixture only, no gateway tests")
'''


ROOT = Path(__file__).resolve().parents[3]
DEADLINE = 0.0
KEY = ""
EVENTS = []


@dataclass
class Reply:
    status: int
    headers: dict
    message: dict | None


def remaining(limit=15):
    value = min(limit, DEADLINE - time.monotonic())
    if value <= 0:
        raise RuntimeError("Overall verifier deadline exceeded")
    return value


def http(path, payload=None, credential="valid", headers=None):
    """Credential/data only on curl stdin, never process arguments or diagnostics."""
    config = []
    if credential is not None:
        value = KEY if credential == "valid" else "invalid-synthetic-key"
        config.append("header = " + json.dumps("Authorization: Bearer " + value))
    config.append('header = "Accept: application/json, text/event-stream"')
    for name, value in (headers or {}).items():
        config.append("header = " + json.dumps(name + ": " + value))
    if payload is not None:
        config.append('header = "Content-Type: application/json"')
        config.append("data = " + json.dumps(json.dumps(payload)))
    try:
        result = subprocess.run(
            ["macctl", "run", "curl", "--config", "-", "--silent", "--show-error",
             "--noproxy", "*", "--max-time", "10", "--dump-header", "-",
             "--output", "-", "--write-out", "\n__SYNTHETIC_STATUS__%{http_code}",
             "http://127.0.0.1:58081" + path],
            input="\n".join(config) + "\n", text=True, capture_output=True,
            timeout=remaining(), cwd=ROOT)
    except subprocess.TimeoutExpired:
        raise RuntimeError("curl subprocess timeout (not an authorization denial)") from None
    if result.returncode:
        raise RuntimeError("curl transport failure (not an authorization denial)")
    raw, marker, status = result.stdout.rpartition("\n__SYNTHETIC_STATUS__")
    if not marker or not status.strip().isdigit():
        raise RuntimeError("Missing HTTP status marker")
    header_block, boundary, body = raw.partition("\n\n")
    if not boundary:
        raise RuntimeError("Missing HTTP header boundary")
    # Consume optional interim HTTP 100 blocks, not SSE payload data.
    while re.match(r"HTTP/\S+ 1\d\d", header_block):
        header_block, boundary, body = body.partition("\n\n")
        if not boundary:
            raise RuntimeError("Malformed interim HTTP response")
    response_headers = {}
    for line in header_block.splitlines()[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            response_headers[name.lower()] = value.strip()
    code = int(status.strip())
    message = None
    if payload is not None and "id" in payload and code == 200:
        if len(body) > 1048576:
            raise RuntimeError("Oversized RPC response")
        try:
            if "text/event-stream" in response_headers.get("content-type", ""):
                candidates = [json.loads(line[5:].strip()) for line in body.splitlines()
                              if line.startswith("data:")]
                matches = [m for m in candidates if m.get("id") == payload["id"]]
                if len(matches) != 1:
                    raise ValueError("Missing/duplicate RPC event")
                message = matches[0]
            else:
                message = json.loads(body)
            if message.get("jsonrpc") != "2.0" or message.get("id") != payload["id"]:
                raise ValueError("Invalid RPC envelope")
            if ("result" in message) == ("error" in message):
                raise ValueError("Invalid RPC result/error")
        except (ValueError, TypeError, AttributeError):
            raise RuntimeError("Malformed/mismatched JSON-RPC response") from None
    return Reply(code, response_headers, message)


def fixture(path="/stats", data=None):
    code = (
        "import json,sys,urllib.request; p=json.load(sys.stdin); "
        "d=None if p['data'] is None else json.dumps(p['data']).encode(); "
        "r=urllib.request.Request('http://127.0.0.1:8000'+p['path'],data=d,"
        "headers={'Content-Type':'application/json'}); "
        "o=urllib.request.build_opener(urllib.request.ProxyHandler({})); "
        "print(o.open(r,timeout=5).read(1048576).decode())")
    result = subprocess.run(
        ["macctl", "run", "docker", "exec", "-i", "mcp-stack-gateway-fixture", "python", "-c", code],
        input=json.dumps({"path": path, "data": data}), text=True, capture_output=True,
        timeout=remaining(10), cwd=ROOT)
    if result.returncode:
        raise RuntimeError("Synthetic fixture control failed")
    return json.loads(result.stdout)


def counters():
    return fixture()["counters"]


def successful(reply):
    if reply.status != 200 or not reply.message or "error" in reply.message:
        raise RuntimeError("Expected successful RPC: " + describe(reply))
    result = reply.message["result"]
    if isinstance(result, dict) and result.get("isError"):
        raise RuntimeError("Unexpected tool-level error")
    return result


def describe(reply):
    detail = ""
    if reply.message and "error" in reply.message:
        detail = "/rpc=" + str(reply.message["error"].get("code"))
    elif reply.message and reply.message.get("result", {}).get("isError"):
        detail = "/tool-isError"
    return "HTTP=" + str(reply.status) + detail


def rejected(reply, permitted_http=(400, 401, 403, 404)):
    if reply.status in permitted_http:
        return
    if reply.status == 200 and reply.message:
        if "error" in reply.message or reply.message.get("result", {}).get("isError"):
            return
    raise RuntimeError("Expected explicit denial: " + describe(reply))


class Session:
    def __init__(self, path, initialize=True):
        self.path = path
        self.session = None
        self.protocol = "2025-11-25"
        self.sequence = 0
        if initialize:
            reply = self.rpc("initialize", {
                "protocolVersion": self.protocol, "capabilities": {},
                "clientInfo": {"name": "synthetic-gateway-probe", "version": "1"}})
            result = successful(reply)
            self.protocol = result["protocolVersion"]
            if self.protocol != "2025-11-25":
                raise RuntimeError("Unexpected negotiated protocol")
            self.session = reply.headers.get("mcp-session-id")
            if not self.session:
                raise RuntimeError("Missing stateful gateway session ID")
            reply = self.rpc("notifications/initialized", notification=True)
            if reply.status not in (200, 202, 204):
                raise RuntimeError("Initialized notification rejected")

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


@contextmanager
def check(name):
    started = time.monotonic()
    fixture("/control", {"beta_enabled": True, "reset": True})
    try:
        yield
        if time.monotonic() - started > 30:
            raise RuntimeError("Probe sequence exceeded 30 seconds")
    except (RuntimeError, AssertionError, KeyError, ValueError) as error:
        # Error strings contain only our bounded diagnostics/statuses, not raw responses.
        event = {"test": name, "passed": False, "detail": str(error) or "Assertion failed"}
    else:
        event = {"test": name, "passed": True}
    EVENTS.append(event)
    print(("PASS: " if event["passed"] else "FAIL: ") + name +
          (" — " + event["detail"] if "detail" in event else ""), flush=True)


def no_dispatch(session, method, params):
    before = counters()
    reply = session.rpc(method, params)
    rejected(reply)
    if counters() != before:
        raise RuntimeError("Denied request reached a fixture handler")
    print("  denial " + method + ": " + describe(reply), flush=True)


def gateway_checks():
    global KEY, DEADLINE
    DEADLINE = time.monotonic() + 180
    KEY = (ROOT / ".secrets/agentgateway-client-key").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", KEY):
        raise RuntimeError("Unexpected key format; value not printed")
    ready = time.monotonic() + 30
    while True:
        try:
            if http("/healthz").status == 200:
                break
        except RuntimeError:
            pass
        if time.monotonic() > ready:
            raise RuntimeError("Synthetic gateway readiness failed")
        time.sleep(0.5)

    try:
        with check("strict API-key authentication on every synthetic profile"):
            before = counters()
            for path in ("/aggregate", "/alpha-only", "/deny", "/policy-error"):
                for credential in (None, "invalid"):
                    s = Session(path, initialize=False)
                    reply = s.rpc("initialize", {
                        "protocolVersion": s.protocol, "capabilities": {},
                        "clientInfo": {"name": "fake", "version": "1"}}, credential=credential)
                    assert reply.status in (401, 403), describe(reply)
            assert counters() == before

        with check("aggregation, original-name collision prefixes and target-specific calls"):
            s = Session("/aggregate")
            assert {t["name"] for t in successful(s.rpc("tools/list"))["tools"]} == {"alpha_echo", "beta_echo"}
            for target in ("alpha", "beta"):
                before = counters()
                result = successful(s.rpc("tools/call", {"name": target + "_echo", "arguments": {"text": "fake"}}))
                assert result["content"][0]["text"] == target + ":fake"
                before[target]["echo"] += 1
                assert counters() == before

        with check("hidden tools and direct prompt/resource bypass denied before dispatch"):
            s = Session("/aggregate")
            assert successful(s.rpc("prompts/list"))["prompts"] == []
            assert successful(s.rpc("resources/list"))["resources"] == []
            for target in ("alpha", "beta"):
                no_dispatch(s, "tools/call", {"name": target + "_blocked", "arguments": {}})
                no_dispatch(s, "prompts/get", {"name": target + "_blocked_prompt", "arguments": {}})
                no_dispatch(s, "resources/read", {"uri": target + "+synthetic://" + target + "/blocked"})

        with check("alpha-only discovery and direct beta call rejection"):
            s = Session("/alpha-only")
            assert [t["name"] for t in successful(s.rpc("tools/list"))["tools"]] == ["alpha_echo"]
            assert successful(s.rpc("tools/call", {"name": "alpha_echo", "arguments": {"text": "fake"}}))["content"][0]["text"] == "alpha:fake"
            no_dispatch(s, "tools/call", {"name": "beta_echo", "arguments": {"text": "fake"}})

        with check("explicit deny-all filters discovery and rejects valid raw fixture operations"):
            s = Session("/deny")
            for method, key in (("tools/list", "tools"), ("prompts/list", "prompts"), ("resources/list", "resources")):
                assert successful(s.rpc(method))[key] == []
            for target in ("alpha", "beta"):
                no_dispatch(s, "tools/call", {"name": target + "_echo", "arguments": {}})
                no_dispatch(s, "prompts/get", {"name": target + "_blocked_prompt", "arguments": {}})
                no_dispatch(s, "resources/read", {"uri": target + "+synthetic://" + target + "/blocked"})

        with check("valid missing-JWT-claim policy denies at runtime, not configuration time"):
            s = Session("/policy-error")
            assert successful(s.rpc("tools/list"))["tools"] == []
            for target in ("alpha", "beta"):
                no_dispatch(s, "tools/call", {"name": target + "_echo", "arguments": {}})

        with check("concurrent session independence, route replay and unknown session rejection"):
            aggregate = Session("/aggregate")
            alpha = Session("/alpha-only")
            assert aggregate.session != alpha.session
            assert len(successful(aggregate.rpc("tools/list"))["tools"]) == 2
            assert len(successful(alpha.rpc("tools/list"))["tools"]) == 1
            before = counters()
            with ThreadPoolExecutor(max_workers=2) as pool:
                beta_call = pool.submit(aggregate.rpc, "tools/call", {
                    "name": "beta_echo", "arguments": {"text": "parallel"}})
                alpha_call = pool.submit(alpha.rpc, "tools/call", {
                    "name": "alpha_echo", "arguments": {"text": "parallel"}})
                assert successful(beta_call.result(timeout=remaining()))["content"][0]["text"] == "beta:parallel"
                assert successful(alpha_call.result(timeout=remaining()))["content"][0]["text"] == "alpha:parallel"
            before["alpha"]["echo"] += 1
            before["beta"]["echo"] += 1
            assert counters() == before
            replay = Session("/alpha-only", initialize=False)
            replay.session = aggregate.session
            reply = replay.rpc("tools/list")
            if reply.status == 200 and reply.message and "result" in reply.message:
                assert {t["name"] for t in successful(reply)["tools"]} <= {"alpha_echo"}
            else:
                rejected(reply)
            no_dispatch(replay, "tools/call", {"name": "beta_echo", "arguments": {}})
            unknown = Session("/aggregate", initialize=False)
            unknown.session = "00000000-0000-0000-0000-000000000000"
            before = counters()
            rejected(unknown.rpc("tools/list"))
            assert counters() == before

        with check("fail-closed backend outage: no successful partial inventory; fresh-session recovery"):
            s = Session("/aggregate")
            assert len(successful(s.rpc("tools/list"))["tools"]) == 2
            fixture("/control", {"beta_enabled": False})
            try:
                reply = s.rpc("tools/list")
                if reply.status == 200:
                    assert reply.message and "error" in reply.message, "Outage returned successful partial/full inventory"
                else:
                    assert 500 <= reply.status <= 599, "Outage failed for unrelated reason: " + describe(reply)
                print("  outage discovery: " + describe(reply), flush=True)
                fresh = Session("/aggregate", initialize=False)
                reply = fresh.rpc("initialize", {"protocolVersion": fresh.protocol, "capabilities": {},
                    "clientInfo": {"name": "outage", "version": "1"}})
                if reply.status == 200:
                    assert reply.message and "error" in reply.message, "Outage initialization unexpectedly succeeded"
                else:
                    assert 500 <= reply.status <= 599
                print("  outage initialize: " + describe(reply), flush=True)
            finally:
                fixture("/control", {"beta_enabled": True})
            recovered = Session("/aggregate")
            assert len(successful(recovered.rpc("tools/list"))["tools"]) == 2
            for target in ("alpha", "beta"):
                result = successful(recovered.rpc("tools/call", {"name": target + "_echo", "arguments": {"text": "recovered"}}))
                assert result["content"][0]["text"] == target + ":recovered"
    finally:
        fixture("/control", {"beta_enabled": True, "reset": True})
    return all(event["passed"] for event in EVENTS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-only", action="store_true")
    args = parser.parse_args()
    if not args.fixture_only:
        try:
            passed = gateway_checks()
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            print("FAIL: bounded gateway verifier: " + str(error), flush=True)
            raise SystemExit(1) from None
        print(json.dumps({"synthetic_gateway_tests": EVENTS}, separators=(",", ":")))
        raise SystemExit(0 if passed else 1)
    result = subprocess.run(
        ["macctl", "run", "docker", "exec", "-i", "mcp-stack-gateway-fixture", "python", "-"],
        input=DIRECT_PROBE, text=True, capture_output=True, timeout=190, cwd=ROOT)
    print(result.stdout, end="")
    if result.returncode:
        # Only synthetic data is present in the inner test; retain bounded diagnostics.
        print(result.stderr[-4000:])
        raise SystemExit("FAIL: direct fixture probe; clean up only approved fixture")


if __name__ == "__main__":
    main()
