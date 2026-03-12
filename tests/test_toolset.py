"""Unit tests for MemoryToolset."""

import json

import pytest

from fastrr.agents.toolset import MemoryToolset


def test_list_files_empty(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    out = toolset.list_files()
    assert json.loads(out) == []


def test_list_files_after_write_file(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("preferences.md", "content")
    out = toolset.list_files()
    assert "preferences.md" in json.loads(out)


def test_write_file_read_file_round_trip(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("notes.txt", "hello world")
    out = toolset.read_file("notes.txt")
    assert out == "hello world"


def test_file_exists_true_false(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("x.txt", "x")
    assert json.loads(toolset.file_exists("x.txt"))["exists"] is True
    assert json.loads(toolset.file_exists("missing.txt"))["exists"] is False


def test_append_file(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("log.txt", "line1\n")
    toolset.append_file("log.txt", "line2\n")
    out = toolset.read_file("log.txt")
    assert out == "line1\nline2\n"


def test_delete_file(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("gone.txt", "content")
    out = toolset.delete_file("gone.txt")
    assert json.loads(out)["deleted"] == "gone.txt"
    assert json.loads(toolset.file_exists("gone.txt"))["exists"] is False


def test_sync_returns_expected_json(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    out = toolset.sync("msg")
    data = json.loads(out)
    assert data["status"] == "ok"


def test_forget_clears_workspace(
    fake_repo_manager,
) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("a.txt", "x")
    assert json.loads(toolset.file_exists("a.txt"))["exists"] is True
    out = toolset.forget()
    assert json.loads(out)["status"] == "ok"
    assert json.loads(toolset.file_exists("a.txt"))["exists"] is False


def test_read_file_missing_returns_error_json(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    out = toolset.read_file("nonexistent.md")
    data = json.loads(out)
    assert "error" in data
    assert "nonexistent.md" in data["error"]
