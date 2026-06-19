"""Tests for the structured file editor tool."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.tool.file_editor import (
    StrReplaceEditor,
    allowed_roots,
    ensure_allowed,
    is_path_allowed,
)
from core.tool.file_editor.safety import PROJECT_ROOT


# -----------------------------------------------------------------------
# safety: allowed_roots / ensure_allowed
# -----------------------------------------------------------------------


def test_project_root_is_always_allowed():
    assert PROJECT_ROOT in allowed_roots()


def test_ensure_allowed_accepts_project_subpath():
    target = PROJECT_ROOT / "core" / "agent" / "base.py"
    assert ensure_allowed(target) == target.resolve()


def test_ensure_allowed_accepts_desktop():
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        pytest.skip("no Desktop on this machine")
    target = desktop / "some_imaginary_file.txt"
    # 解析后仍在 Desktop 下 → 允许
    assert ensure_allowed(target) == target.resolve()


@pytest.mark.parametrize(
    "bad",
    [
        "C:/Windows/System32/config",
        "/etc/passwd",
        "~/.ssh/id_rsa",          # leading ~
        "%USERPROFILE%/secret",   # env var ref
        "$HOME/secret",           # env var ref
    ],
)
def test_ensure_allowed_rejects(bad):
    with pytest.raises(ValueError):
        ensure_allowed(Path(bad))


def test_is_path_allowed_bool_form():
    assert is_path_allowed(PROJECT_ROOT) is True
    assert is_path_allowed("C:/Windows/System32") is False


# -----------------------------------------------------------------------
# editor end-to-end on a real temp file inside the project root
# -----------------------------------------------------------------------


@pytest.fixture
def tmp_project_file(tmp_path_factory):
    # 把 tmp_path 放到项目根的 .tmp_tests 下，确保它落在 allowed_roots 内。
    base = PROJECT_ROOT / ".tmp_tests"
    base.mkdir(exist_ok=True)
    subdir = base / f"editor_{tmp_path_factory.mktemp('x').name}"
    subdir.mkdir(parents=True, exist_ok=True)
    target = subdir / "story.txt"
    yield target
    # cleanup
    try:
        if target.exists():
            target.unlink()
        subdir.rmdir()
    except OSError:
        pass


async def test_create_and_view_roundtrip(tmp_project_file):
    ed = StrReplaceEditor()
    res = await ed.execute(
        command="create",
        path=str(tmp_project_file),
        file_text="燃え上がれ\n青空に\n",
    )
    assert res.error is None
    assert "created" in res.output

    res = await ed.execute(command="view", path=str(tmp_project_file))
    assert res.error is None
    assert "燃え上がれ" in res.output
    assert "青空" in res.output
    # cat -n 风格的行号
    assert "     1\t" in res.output


async def test_create_refuses_existing(tmp_project_file):
    ed = StrReplaceEditor()
    tmp_project_file.write_text("already here", encoding="utf-8")
    res = await ed.execute(
        command="create",
        path=str(tmp_project_file),
        file_text="should fail",
    )
    assert res.error is not None
    assert "already exists" in res.error


async def test_str_replace_requires_unique_match(tmp_project_file):
    tmp_project_file.write_text("foo\nfoo\nbar\n", encoding="utf-8")
    ed = StrReplaceEditor()
    res = await ed.execute(
        command="str_replace",
        path=str(tmp_project_file),
        old_str="foo",
        new_str="baz",
    )
    assert res.error is not None
    assert "appears 2 times" in res.error or "appears" in res.error


async def test_str_replace_succeeds_with_unique_context(tmp_project_file):
    tmp_project_file.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    ed = StrReplaceEditor()
    res = await ed.execute(
        command="str_replace",
        path=str(tmp_project_file),
        old_str="beta",
        new_str="BETA",
    )
    assert res.error is None
    assert tmp_project_file.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"


async def test_insert_at_position(tmp_project_file):
    tmp_project_file.write_text("a\nb\nc\n", encoding="utf-8")
    ed = StrReplaceEditor()
    res = await ed.execute(
        command="insert",
        path=str(tmp_project_file),
        insert_line=2,
        new_str="INSERTED",
    )
    assert res.error is None
    assert tmp_project_file.read_text(encoding="utf-8") == "a\nb\nINSERTED\nc\n"


async def test_undo_create_deletes_file(tmp_project_file):
    ed = StrReplaceEditor()
    await ed.execute(
        command="create",
        path=str(tmp_project_file),
        file_text="hello",
    )
    assert tmp_project_file.exists()
    res = await ed.execute(command="undo_edit", path=str(tmp_project_file))
    assert res.error is None
    assert not tmp_project_file.exists()


async def test_undo_str_replace_restores_content(tmp_project_file):
    tmp_project_file.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    ed = StrReplaceEditor()
    await ed.execute(
        command="str_replace",
        path=str(tmp_project_file),
        old_str="beta",
        new_str="BETA",
    )
    res = await ed.execute(command="undo_edit", path=str(tmp_project_file))
    assert res.error is None
    assert tmp_project_file.read_text(encoding="utf-8") == "alpha\nbeta\ngamma\n"


async def test_path_outside_allowed_root_rejected():
    ed = StrReplaceEditor()
    res = await ed.execute(
        command="create",
        path="C:/Windows/System32/should_not_create.txt",
        file_text="payload",
    )
    assert res.error is not None
    assert "outside" in res.error or "allowed" in res.error


async def test_view_directory_lists_entries(tmp_path_factory):
    base = PROJECT_ROOT / ".tmp_tests"
    base.mkdir(exist_ok=True)
    subdir = base / f"viewdir_{tmp_path_factory.mktemp('y').name}"
    subdir.mkdir(parents=True, exist_ok=True)
    (subdir / "a.txt").write_text("a", encoding="utf-8")
    (subdir / "b.txt").write_text("b", encoding="utf-8")

    ed = StrReplaceEditor()
    res = await ed.execute(command="view", path=str(subdir))
    assert res.error is None
    assert "a.txt" in res.output
    assert "b.txt" in res.output

    # cleanup
    (subdir / "a.txt").unlink()
    (subdir / "b.txt").unlink()
    subdir.rmdir()
