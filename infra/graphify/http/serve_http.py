import hashlib
import hmac
import importlib.metadata
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

import mcp.types as types
import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import McpError
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount, Route
from serve_filtered import restricted_server

for package, version in {"graphifyy": "0.9.72", "mcp": "1.29.0",
                         "starlette": "1.3.1", "uvicorn": "0.47.0"}.items():
    if importlib.metadata.version(package) != version:
        raise RuntimeError("Unapproved HTTP runtime version")
graph = Path("/state/graphify-out/graph.json").resolve(strict=True)
if graph != Path("/state/graphify-out/graph.json"):
    raise RuntimeError("Unapproved graph path")
config = json.loads(Path("/config/server.json").read_text())
digest = config["api_key_sha256"]
if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
    raise RuntimeError("Invalid backend key hash")
server = restricted_server(graph)
resources = {"graphify://" + name for name in
             ("report", "stats", "god-nodes", "surprises", "audit", "questions")}
original_list = server.request_handlers[types.ListResourcesRequest]
original_read = server.request_handlers[types.ReadResourceRequest]

async def list_resources(request):
    result = await original_list(request)
    if {str(resource.uri) for resource in result.root.resources} != resources:
        raise RuntimeError("Pinned resource surface changed")
    return result

async def read_resource(request):
    if str(request.params.uri) not in resources:
        raise McpError(types.ErrorData(code=-32602, message="mcp-stack gate: resource not permitted"))
    return await original_read(request)

server.request_handlers[types.ListResourcesRequest] = list_resources
server.request_handlers[types.ReadResourceRequest] = read_resource
manager = StreamableHTTPSessionManager(
    server, json_response=True, stateless=True, max_request_body_size=262144,
    security_settings=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["graphify-http", "graphify-http:8000",
                       "127.0.0.1:8000", "localhost:8000"], allowed_origins=[]))

@asynccontextmanager
async def lifespan(app):
    async with manager.run():
        yield

async def health(request):
    return Response(status_code=200)

class BackendAuth:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            values = [value for name, value in scope["headers"] if name.lower() == b"authorization"]
            match = re.fullmatch(rb"Bearer ([0-9a-f]{64})", values[0]) if len(values) == 1 else None
            if match is None or not hmac.compare_digest(hashlib.sha256(match[1]).hexdigest(), digest):
                await Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})(scope, receive, send)
                return
        await self.app(scope, receive, send)

app = BackendAuth(Starlette(debug=False, lifespan=lifespan, routes=[
    Route("/healthz", health), Mount("/mcp", app=manager.asgi_app)]))
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False, log_level="warning")
