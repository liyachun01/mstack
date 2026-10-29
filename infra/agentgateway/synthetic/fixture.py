"""Disposable fake MCP endpoints; no Graphify, real corpus or model imports."""

import importlib.metadata
import logging
from contextlib import AsyncExitStack, asynccontextmanager

import mcp.types as types
import uvicorn
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route


COUNTERS = {target: {key: 0 for key in ("echo", "blocked", "prompt", "resource")}
            for target in ("alpha", "beta")}
BETA_ENABLED = True
VERSIONS = {name: importlib.metadata.version(name)
            for name in ("mcp", "starlette", "uvicorn")}
if VERSIONS != {"mcp": "1.29.0", "starlette": "1.3.1", "uvicorn": "0.47.0"}:
    raise RuntimeError("Fixture runtime does not match approved versions")


def make_server(target):
    server = Server("synthetic-" + target, version="1.0.0")
    uri = "synthetic://" + target + "/blocked"

    @server.list_tools()
    async def list_tools():
        return [types.Tool(name=name, description="Fake fixture tool",
                           inputSchema={"type": "object", "properties": {
                               "text": {"type": "string"}}, "additionalProperties": False})
                for name in ("echo", "blocked")]

    @server.call_tool()
    async def call_tool(name, arguments):
        if name not in ("echo", "blocked"):
            raise ValueError("Unknown synthetic tool")
        COUNTERS[target][name] += 1
        text = str((arguments or {}).get("text", "")) if name == "echo" else "blocked-dispatched"
        return [types.TextContent(type="text", text=target + ":" + text)]

    @server.list_prompts()
    async def list_prompts():
        return [types.Prompt(name="blocked_prompt", description="Fake prompt", arguments=[])]

    @server.get_prompt()
    async def get_prompt(name, arguments):
        if name != "blocked_prompt":
            raise ValueError("Unknown synthetic prompt")
        COUNTERS[target]["prompt"] += 1
        return types.GetPromptResult(messages=[types.PromptMessage(
            role="user", content=types.TextContent(type="text", text=target + ":prompt"))])

    @server.list_resources()
    async def list_resources():
        return [types.Resource(uri=uri, name="blocked_resource", mimeType="text/plain")]

    @server.read_resource()
    async def read_resource(requested_uri):
        if str(requested_uri) != uri:
            raise ValueError("Unknown synthetic resource")
        COUNTERS[target]["resource"] += 1
        return [ReadResourceContents(content=target + ":resource", mime_type="text/plain")]

    return StreamableHTTPSessionManager(
        server, json_response=True, stateless=True,
        security_settings=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["fixture", "fixture:8000", "127.0.0.1:8000", "localhost:8000"],
            allowed_origins=[]))


MANAGERS = {target: make_server(target) for target in COUNTERS}


class BetaOutage:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not BETA_ENABLED:
            await Response("Synthetic beta outage", status_code=503)(scope, receive, send)
        else:
            await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app):
    async with AsyncExitStack() as stack:
        for manager in MANAGERS.values():
            await stack.enter_async_context(manager.run())
        yield


async def stats(request):
    return JSONResponse({"counters": COUNTERS, "beta_enabled": BETA_ENABLED,
                         "versions": VERSIONS})


async def control(request):
    global BETA_ENABLED
    data = await request.json()
    if not isinstance(data, dict) or set(data) - {"beta_enabled", "reset"}:
        return Response("Invalid synthetic control", status_code=400)
    if any(not isinstance(value, bool) for value in data.values()):
        return Response("Boolean controls required", status_code=400)
    if "beta_enabled" in data:
        BETA_ENABLED = data["beta_enabled"]
    if data.get("reset"):
        for counters in COUNTERS.values():
            for key in counters:
                counters[key] = 0
    return await stats(request)


app = Starlette(debug=False, lifespan=lifespan, routes=[
    Route("/stats", stats), Route("/control", control, methods=["POST"]),
    Mount("/alpha", app=MANAGERS["alpha"].asgi_app),
    Mount("/beta", app=BetaOutage(MANAGERS["beta"].asgi_app)),
])

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False, log_level="warning")
