"""One authenticated tenant per native Graphify stdio session in a shared container."""
import asyncio
import importlib.metadata
import json
from pathlib import Path
import sys

from registry import authenticate, read_bootstrap, tenant_file


async def serve(root=Path('/runtime')):
    sys.path.insert(0, '/adapter')
    from mcp import types
    from mcp.server.stdio import stdio_server
    from mcp.shared.exceptions import McpError
    from serve_filtered import restricted_server, denied

    for package, version in {'graphifyy': '0.9.72', 'mcp': '1.29.0'}.items():
        if importlib.metadata.version(package) != version:
            raise ValueError('Unapproved Graphify runtime')
    registry = json.loads((root / 'registry.json').read_text())
    tenant, _ = authenticate(registry, read_bootstrap())
    graph = tenant_file(root, tenant, 'graph.json')
    server = restricted_server(graph)
    original_call = server.request_handlers[types.CallToolRequest]
    original_read = server.request_handlers[types.ReadResourceRequest]
    resources = {'graphify://' + name for name in
                 ('report', 'stats', 'god-nodes', 'surprises', 'audit', 'questions')}

    async def call(request):
        args = request.params.arguments or {}
        if {'tenant', 'tenant_id', 'project', 'project_id', 'project_path'} & args.keys():
            return denied('tenant is fixed by the authenticated session')
        return await original_call(request)

    async def read(request):
        if str(request.params.uri) not in resources:
            raise McpError(types.ErrorData(code=-32602, message='mstack: resource outside tenant'))
        return await original_read(request)

    server.request_handlers[types.CallToolRequest] = call
    server.request_handlers[types.ReadResourceRequest] = read
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except (ValueError, KeyError, OSError):
        print('mstack: tenant authentication or runtime unavailable', file=sys.stderr)
        raise SystemExit(1)
