"""Construct the filesystem MCP server. Running it is main()'s job."""

from __future__ import annotations

from collections.abc import Sequence

from mcp.server import MCPServer

from filesystem_mcp.tools import register

INSTRUCTIONS = (
    "Call list_allowed_directories before guessing paths. "
    "Every path must stay inside those directories."
)


def build_server(roots: Sequence[str]) -> MCPServer:
    server = MCPServer("filesystem", instructions=INSTRUCTIONS)
    register(server, roots)
    return server
