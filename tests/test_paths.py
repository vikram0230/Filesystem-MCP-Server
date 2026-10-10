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


def test_tilde_inside_home_resolves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    note = tmp_path / "note.txt"
    note.write_text("hi", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))

    assert resolve("~/note.txt", [str(tmp_path)]) == str(note.resolve())


def test_tilde_outside_root_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    root = tmp_path / "root"
    home.mkdir()
    root.mkdir()
    (home / "secret.txt").write_text("no", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))

    with pytest.raises(PathError, match="outside the allowed directories"):
        resolve("~/secret.txt", [str(root)])


def test_relative_path_uses_the_allowed_root_not_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "root"
    elsewhere = tmp_path / "elsewhere"
    root.mkdir()
    elsewhere.mkdir()
    note = root / "note.txt"
    note.write_text("hi", encoding="utf-8")
    monkeypatch.chdir(elsewhere)

    assert resolve("note.txt", [str(root)]) == str(note.resolve())


def test_relative_path_uses_the_first_root_when_both_contain_it(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "note.txt").write_text("one", encoding="utf-8")
    (second / "note.txt").write_text("two", encoding="utf-8")

    assert resolve("note.txt", [str(first), str(second)]) == str((first / "note.txt").resolve())


def test_missing_intermediate_directory_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    with pytest.raises(PathError, match="parent directory does not exist"):
        resolve(str(root / "missing" / "note.txt"), [str(root)])


def test_symlink_to_outside_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("no", encoding="utf-8")
    link = root / "link.txt"
    link.symlink_to(secret)

    with pytest.raises(PathError, match="outside the allowed directories"):
        resolve(str(link), [str(root)])


def test_symlink_to_inside_file_resolves_to_target(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    note = root / "note.txt"
    note.write_text("hi", encoding="utf-8")
    link = root / "link.txt"
    link.symlink_to(note)

    assert resolve(str(link), [str(root)]) == str(note.resolve())


def test_link_and_realpath_spellings_of_a_root_both_resolve(tmp_path: Path) -> None:
    from filesystem_mcp.paths import normalize_roots

    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    note = real / "note.txt"
    note.write_text("hi", encoding="utf-8")
    roots = normalize_roots([str(link)])

    assert resolve(str(link / "note.txt"), roots) == str(note.resolve())
    assert resolve(str(note), roots) == str(note.resolve())


def test_normalize_roots_rejects_a_missing_directory(tmp_path: Path) -> None:
    from filesystem_mcp.paths import RootError, normalize_roots

    with pytest.raises(RootError, match="does not exist"):
        normalize_roots([str(tmp_path / "missing")])


def test_normalize_roots_rejects_an_empty_list() -> None:
    from filesystem_mcp.paths import RootError, normalize_roots

    with pytest.raises(RootError, match="Usage: filesystem-mcp"):
        normalize_roots([])
