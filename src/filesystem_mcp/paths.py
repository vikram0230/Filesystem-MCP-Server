"""Allowed-directory path checks. This module does not import the MCP SDK."""

from __future__ import annotations

import os
from collections.abc import Sequence


class PathError(Exception):
    """The requested path cannot be used. The message names the caller's path."""


def resolve(path: str, roots: Sequence[str]) -> str:
    absolute = os.path.abspath(path)
    for root in roots:
        base = os.path.abspath(root)
        if absolute == base or absolute.startswith(base + os.sep):
            return os.path.realpath(absolute)
    raise PathError(f"{path} is outside the allowed directories")
