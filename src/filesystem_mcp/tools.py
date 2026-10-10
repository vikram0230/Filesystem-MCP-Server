"""Filesystem tools. Every path goes through resolve before use."""

from __future__ import annotations

import os
from collections.abc import Sequence

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from filesystem_mcp.paths import PathError, resolve

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


def register(server: MCPServer, roots: Sequence[str]) -> None:
    @server.tool(annotations=READ_ONLY)
    def list_allowed_directories() -> str:
        """Return the directories this server is allowed to access, one per line."""
        return "\n".join(roots)

    @server.tool(annotations=READ_ONLY)
    def list_directory(path: str) -> str:
        """List the immediate children of a directory inside an allowed root."""
        canonical = _resolved(path, roots)
        if not os.path.isdir(canonical):
            raise ToolError(f"{path} is a file")
        try:
            names = sorted(os.listdir(canonical))
        except OSError as exc:
            raise ToolError(str(exc)) from exc
        return "\n".join(_label(os.path.join(canonical, name), roots) + " " + name for name in names)


def _resolved(path: str, roots: Sequence[str]) -> str:
    try:
        return resolve(path, roots)
    except PathError as exc:
        raise ToolError(str(exc)) from exc


def _label(entry: str, roots: Sequence[str]) -> str:
    try:
        canonical = resolve(entry, roots)
    except PathError:
        return "[FILE]"
    if os.path.isdir(canonical):
        return "[DIR]"
    return "[FILE]"
