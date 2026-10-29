"""Pinned Graphify 0.9.72 / MCP 1.29.0 adapter, not a new server framework.

Restricts native discovery AND dispatch to the approved graph-only surface.
Upgrades require revalidating the private factory and SDK handler contracts.
"""

import asyncio
import importlib.metadata
import sys
from pathlib import Path

from mcp import types
from mcp.server.stdio import stdio_server
from graphify.serve import _build_server


TOOLS = frozenset({
    "query_graph", "get_node", "get_neighbors", "get_community",
    "god_nodes", "graph_stats", "shortest_path",
})


def denied(reason):
    return types.ServerResult(types.CallToolResult(
        content=[types.TextContent(type="text", text=f"mcp-stack gate: {reason}")],
        isError=True,
    ))


def restricted_server(graph):
    server = _build_server(str(graph))
    original_list = server.request_handlers[types.ListToolsRequest]
    original_call = server.request_handlers[types.CallToolRequest]

    async def list_tools(request):
        result = await original_list(request)
        tools = [tool for tool in result.root.tools if tool.name in TOOLS]
        if {tool.name for tool in tools} != TOOLS:
            raise RuntimeError("Pinned upstream graph tool surface changed")
        # Do not advertise the upstream multi-project selector.
        for tool in tools:
            tool.inputSchema.get("properties", {}).pop("project_path", None)
        result.root.tools = tools
        return result

    async def call_tool(request):
        if request.params.name not in TOOLS:
            return denied("tool is not permitted")
        arguments = request.params.arguments or {}
        if arguments.get("project_path"):
            return denied("project_path overrides are not permitted")
        return await original_call(request)

    server.request_handlers[types.ListToolsRequest] = list_tools
    server.request_handlers[types.CallToolRequest] = call_tool
    return server


async def main():
    if importlib.metadata.version("graphifyy") != "0.9.72":
        raise RuntimeError("Unapproved Graphify version")
    if importlib.metadata.version("mcp") != "1.29.0":
        raise RuntimeError("Unapproved SDK version")
    graph = Path(sys.argv[1]).resolve(strict=True)
    if graph != Path("/state/graphify-out/graph.json"):
        raise RuntimeError("Unapproved default graph")
    server = restricted_server(graph)
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
