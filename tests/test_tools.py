import os
from pathlib import Path

import pytest
from mcp import Client

from filesystem_mcp.paths import normalize_roots
from filesystem_mcp.server import build_server


def _text(result: object) -> str:
    return result.content[0].text  # type: ignore[attr-defined]


async def test_list_allowed_directories_returns_each_stored_root(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    roots = normalize_roots([str(link)])
    server = build_server(roots)

    async with Client(server) as client:
        result = await client.call_tool("list_allowed_directories", {})

    assert not result.is_error
    assert _text(result).splitlines() == list(roots)


async def test_list_directory_on_the_root_lists_immediate_children(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("a", encoding="utf-8")
    (root / ".hidden").write_text("h", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "leak").symlink_to(outside, target_is_directory=True)
    inside = root / "sub"
    (root / "alias").symlink_to(inside, target_is_directory=True)
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("list_directory", {"path": str(root)})

    assert not result.is_error
    assert _text(result).splitlines() == [
        "[FILE] .hidden",
        "[FILE] a.txt",
        "[DIR] alias",
        "[FILE] leak",
        "[DIR] sub",
    ]


async def test_list_directory_on_a_file_is_a_tool_error(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    note = root / "note.txt"
    note.write_text("hi", encoding="utf-8")
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("list_directory", {"path": str(note)})

    assert result.is_error
    assert "is a file" in _text(result)


async def test_list_directory_outside_the_root_is_a_tool_error(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("list_directory", {"path": str(outside)})

    assert result.is_error
    assert "outside the allowed directories" in _text(result)


async def test_read_text_file_returns_utf8_text(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    note = root / "note.txt"
    note.write_text("hello", encoding="utf-8")
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(note)})

    assert not result.is_error
    assert _text(result) == "hello"


async def test_read_text_file_accepts_exactly_one_mebibyte(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    note = root / "exact.txt"
    note.write_bytes(b"a" * 1_048_576)
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(note)})

    assert not result.is_error
    assert _text(result) == "a" * 1_048_576


async def test_read_text_file_refuses_one_byte_over_the_limit(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    note = root / "big.txt"
    note.write_bytes(b"a" * 1_048_577)
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(note)})

    assert result.is_error
    assert "larger than 1 MiB" in _text(result)
    assert "a" * 1_048_577 not in _text(result)


async def test_read_text_file_refuses_a_directory(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(root)})

    assert result.is_error
    assert "is a directory" in _text(result)


async def test_read_text_file_refuses_a_missing_file(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(root / "missing.txt")})

    assert result.is_error
    assert "does not exist" in _text(result)


async def test_read_text_file_refuses_invalid_utf8(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    note = root / "bad.txt"
    note.write_bytes(b"\xff")
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(note)})

    assert result.is_error
    assert "not valid UTF-8" in _text(result)


async def test_read_text_file_refuses_a_path_outside_the_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("no", encoding="utf-8")
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(outside)})

    assert result.is_error
    assert "outside the allowed directories" in _text(result)


async def test_read_text_file_reports_permission_denied(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("root ignores mode 0o000")
    root = tmp_path / "root"
    root.mkdir()
    note = root / "locked.txt"
    note.write_text("hi", encoding="utf-8")
    note.chmod(0o000)
    server = build_server([str(root)])

    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(note)})

    assert result.is_error
    assert "Permission denied" in _text(result)
