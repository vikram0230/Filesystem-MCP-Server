"""Allowed-directory path checks. This module does not import the MCP SDK."""

from __future__ import annotations

import os
from collections.abc import Sequence


class PathError(Exception):
    """The requested path cannot be used. The message names the caller's path."""


class RootError(Exception):
    """No usable allowed directory was given."""


def normalize_roots(raw_roots: Sequence[str]) -> tuple[str, ...]:
    if len(raw_roots) == 0:
        raise RootError(
            "Usage: filesystem-mcp <allowed-directory> [additional-directories...]"
        )
    stored: list[str] = []
    for raw in raw_roots:
        expanded = os.path.expanduser(raw)
        absolute = os.path.abspath(expanded)
        if not os.path.isdir(absolute):
            raise RootError(f"{raw} does not exist or is not a directory")
        resolved = os.path.realpath(absolute)
        stored.append(absolute)
        if resolved != absolute:
            stored.append(resolved)
    return tuple(stored)


def resolve(path: str, roots: Sequence[str]) -> str:
    if len(roots) == 0:
        raise PathError(f"{path} is outside the allowed directories")

    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        candidates = [(expanded, None)]
    else:
        candidates = [(os.path.join(root, expanded), root) for root in roots]

    for candidate, joined_root in candidates:
        canonical, parent_missing = _canonicalize(candidate)
        allowed = (
            _inside_any(canonical, roots)
            if joined_root is None
            else _inside_one(canonical, joined_root)
        )
        if not allowed:
            continue
        if parent_missing:
            raise PathError(f"{path} parent directory does not exist")
        return canonical

    raise PathError(f"{path} is outside the allowed directories")


def _canonicalize(candidate: str) -> tuple[str, bool]:
    absolute = os.path.abspath(candidate)
    try:
        if os.path.islink(absolute) or os.path.exists(absolute):
            canonical = os.path.realpath(absolute)
            if os.path.exists(canonical):
                return canonical, False
            parent = os.path.dirname(canonical)
            return canonical, not os.path.isdir(parent)
    except OSError:
        return absolute, True

    parent = os.path.dirname(absolute)
    missing: list[str] = []
    cursor = parent
    while not os.path.exists(cursor):
        parent_of_cursor = os.path.dirname(cursor)
        if parent_of_cursor == cursor:
            return absolute, True
        missing.append(os.path.basename(cursor))
        cursor = parent_of_cursor
    if not os.path.isdir(cursor):
        return absolute, True
    canonical = os.path.join(
        os.path.realpath(cursor),
        *reversed(missing),
        os.path.basename(absolute),
    )
    return canonical, bool(missing)


def _bases(root: str) -> set[str]:
    absolute = os.path.abspath(root)
    bases = {absolute}
    if os.path.exists(absolute):
        bases.add(os.path.realpath(absolute))
    return bases


def _inside_one(canonical: str, root: str) -> bool:
    for base in _bases(root):
        if canonical == base or canonical.startswith(base + os.sep):
            return True
    return False


def _inside_any(canonical: str, roots: Sequence[str]) -> bool:
    return any(_inside_one(canonical, root) for root in roots)
