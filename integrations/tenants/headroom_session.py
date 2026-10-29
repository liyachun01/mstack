"""Authenticated tenant session around the pinned native Headroom MCP server."""
import asyncio
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys

from registry import authenticate, read_bootstrap, tenant_file

TOOLS = {'headroom_compress': {'content'}, 'headroom_retrieve': {'hash'}, 'headroom_stats': set()}


def valid_call(name, arguments):
    if name not in TOOLS or not isinstance(arguments, dict) or set(arguments) != TOOLS[name]:
        return False
    if name == 'headroom_compress':
        content = arguments['content']
        return isinstance(content, str) and 0 < len(content.encode()) <= 8 * 1024 * 1024
    if name == 'headroom_retrieve':
        return isinstance(arguments['hash'], str) and bool(re.fullmatch('[a-f0-9]{1,64}', arguments['hash']))
    return True


def configure(root, supplied):
    tenant, _ = authenticate(json.loads((root/'registry.json').read_text()), supplied)
    marker = tenant_file(root, tenant, 'tenant.json')
    if json.loads(marker.read_text()) != {'version': 1, 'tenant': tenant}:
        raise ValueError('Tenant marker differs from registry')
    folder = marker.parent
    os.umask(0o077)
    for name in ['workspace', 'config']:
        path = folder/name
        if path.is_symlink():
            raise ValueError('Tenant storage must not be a symlink')
        path.mkdir(exist_ok=True, mode=0o700)
    # Configure before importing Headroom: several native modules capture these
    # paths at import time. Caller environment is not an alternate path selector.
    for name in list(os.environ):
        if name.startswith('HEADROOM_'):
            del os.environ[name]
    os.environ.update({
        'HEADROOM_WORKSPACE_DIR': str(folder/'workspace'),
        'HEADROOM_CONFIG_DIR': str(folder/'config'),
        'HEADROOM_CCR_SQLITE_PATH': str(folder/'workspace/ccr_store.db'),
        'HEADROOM_CCR_BACKEND': 'sqlite', 'HEADROOM_MCP_READ': 'off',
        'HEADROOM_OFFLINE': '1', 'HEADROOM_BEACON': 'off', 'DO_NOT_TRACK': '1',
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
        'LITELLM_LOCAL_MODEL_COST_MAP': 'True',
    })
    return tenant, folder


async def serve(root=Path('/runtime')):
    configure(root, read_bootstrap())
    for package, version in {'headroom-ai': '0.34.0', 'mcp': '1.29.0'}.items():
        if importlib.metadata.version(package) != version:
            raise ValueError('Unapproved Headroom runtime')
    from mcp import types
    from headroom.ccr.mcp_server import HeadroomMCPServer
    from headroom.cache.backends.sqlite import SQLiteBackend
    from headroom.cache.compression_store import get_compression_store

    # Explicit backend initialization must succeed; no in-memory fallback that
    # could silently lose originals when a harness reconnects.
    backend = SQLiteBackend()
    native = HeadroomMCPServer(check_proxy=False)
    native._local_store = get_compression_store(backend=backend)
    server = native.server
    original_list = server.request_handlers[types.ListToolsRequest]
    original_call = server.request_handlers[types.CallToolRequest]

    async def list_tools(request):
        result = await original_list(request)
        result.root.tools = [tool for tool in result.root.tools if tool.name in TOOLS]
        if {tool.name for tool in result.root.tools} != set(TOOLS):
            raise ValueError('Pinned native Headroom tool surface changed')
        for tool in result.root.tools:
            tool.inputSchema['additionalProperties'] = False
        return result

    async def call(request):
        if not valid_call(request.params.name, request.params.arguments or {}):
            return types.ServerResult(types.CallToolResult(isError=True, content=[
                types.TextContent(type='text', text='mstack: tool/arguments denied; tenant is fixed by authentication')]))
        return await original_call(request)

    server.request_handlers[types.ListToolsRequest] = list_tools
    server.request_handlers[types.CallToolRequest] = call
    try:
        await native.run_stdio()
    finally:
        await native.cleanup()


if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except (ValueError, KeyError, OSError):
        print('mstack: tenant authentication or Headroom storage unavailable', file=sys.stderr)
        raise SystemExit(1)
