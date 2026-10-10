from pathlib import Path

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
