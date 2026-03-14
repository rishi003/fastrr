"""Unit tests for MemoryToolset."""

import json

import pytest

from fastrr.agents.toolset import MemoryToolset


def test_read_tools_contains_only_read_file(fake_repo_manager) -> None:
    toolset = MemoryToolset(fake_repo_manager)
    assert toolset.read_tools == [toolset.read_file]


def test_write_file_read_file_round_trip(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("notes.txt", "hello world")
    out = toolset.read_file("notes.txt")
    assert out == "hello world"


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
    assert not (fake_repo_manager.get_workspace_path() / "gone.txt").exists()


def test_sync_returns_expected_json(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    out = toolset.sync("msg")
    data = json.loads(out)
    assert data["status"] == "ok"


def test_forget_clears_workspace(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("a.txt", "x")
    assert (fake_repo_manager.get_workspace_path() / "a.txt").exists()
    out = toolset.forget()
    assert json.loads(out)["status"] == "ok"
    assert not (fake_repo_manager.get_workspace_path() / "a.txt").exists()


def test_read_file_missing_returns_error_json(fake_repo_manager) -> None:
    fake_repo_manager.ensure_workspace()
    toolset = MemoryToolset(fake_repo_manager)
    out = toolset.read_file("nonexistent.md")
    data = json.loads(out)
    assert "error" in data
    assert "nonexistent.md" in data["error"]
