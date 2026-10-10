from pathlib import Path

import pytest

from filesystem_mcp.paths import PathError, resolve


def test_file_inside_root_resolves_to_canonical_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    note = root / "note.txt"
    note.write_text("hi", encoding="utf-8")

    assert resolve(str(note), [str(root)]) == str(note.resolve())


def test_sibling_with_shared_prefix_is_refused(tmp_path: Path) -> None:
    safe = tmp_path / "safe"
    sibling = tmp_path / "safe-but-secret"
    safe.mkdir()
    sibling.mkdir()
    secret = sibling / "secret.txt"
    secret.write_text("no", encoding="utf-8")

    with pytest.raises(PathError, match="outside the allowed directories"):
        resolve(str(secret), [str(safe)])


def test_parent_segment_that_stays_inside_resolves(tmp_path: Path) -> None:
    root = tmp_path / "root"
    sub = root / "sub"
    sub.mkdir(parents=True)
    note = sub / "note.txt"
    note.write_text("n", encoding="utf-8")
    via_parent = root / "sub" / ".." / "sub" / "note.txt"

    assert resolve(str(via_parent), [str(root)]) == str(note.resolve())


def test_parent_segment_that_leaves_the_root_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("no", encoding="utf-8")

    with pytest.raises(PathError, match="outside the allowed directories"):
        resolve(str(root / ".." / "outside.txt"), [str(root)])


def test_allowed_root_itself_resolves(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    assert resolve(str(root), [str(root)]) == str(root.resolve())
