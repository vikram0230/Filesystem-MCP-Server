"""Filesystem tools. Every path goes through resolve before use."""

from __future__ import annotations

import os
from collections.abc import Sequence

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from filesystem_mcp.paths import PathError, resolve

MAX_BYTES = 1_048_576

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

    @server.tool(annotations=READ_ONLY)
    def read_text_file(path: str) -> str:
        """Read a UTF-8 text file inside an allowed root."""
        canonical = _resolved(path, roots)
        if os.path.isdir(canonical):
            raise ToolError(f"{path} is a directory")
        try:
            size = os.path.getsize(canonical)
        except FileNotFoundError as exc:
            raise ToolError(f"{path} does not exist") from exc
        except OSError as exc:
            raise ToolError(str(exc)) from exc
        if size > MAX_BYTES:
            raise ToolError(f"{path} is larger than 1 MiB")
        try:
            with open(canonical, encoding="utf-8") as handle:
                return handle.read()
        except UnicodeDecodeError as exc:
            raise ToolError(f"{path} is not valid UTF-8") from exc
        except FileNotFoundError as exc:
            raise ToolError(f"{path} does not exist") from exc
        except OSError as exc:
            raise ToolError(str(exc)) from exc


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
