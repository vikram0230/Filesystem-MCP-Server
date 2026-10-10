"""Construct the filesystem MCP server and run it from the command line."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from mcp.server import MCPServer

from filesystem_mcp.paths import RootError, normalize_roots
from filesystem_mcp.tools import register

INSTRUCTIONS = (
    "Call list_allowed_directories before guessing paths. "
    "Every path must stay inside those directories."
)


def build_server(roots: Sequence[str]) -> MCPServer:
    server = MCPServer("filesystem", instructions=INSTRUCTIONS)
    register(server, roots)
    return server


def main(argv: Sequence[str] | None = None) -> None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        roots = normalize_roots(arguments)
    except RootError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    build_server(roots).run()
