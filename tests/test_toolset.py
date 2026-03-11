"""Unit tests for MemoryToolset."""

import json

import pytest

from fastrr.agents.toolset import MemoryToolset


def test_list_files_empty(fake_repo_manager) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    toolset = MemoryToolset(fake_repo_manager)
    out = toolset.list_files("alice")
    assert json.loads(out) == []


def test_list_files_after_write_file(fake_repo_manager) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("alice", "preferences.md", "content")
    out = toolset.list_files("alice")
    assert "preferences.md" in json.loads(out)


def test_write_file_read_file_round_trip(fake_repo_manager) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("alice", "notes.txt", "hello world")
    out = toolset.read_file("alice", "notes.txt")
    assert out == "hello world"


def test_file_exists_true_false(fake_repo_manager) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("alice", "x.txt", "x")
    assert json.loads(toolset.file_exists("alice", "x.txt"))["exists"] is True
    assert json.loads(toolset.file_exists("alice", "missing.txt"))["exists"] is False


def test_append_file(fake_repo_manager) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("alice", "log.txt", "line1\n")
    toolset.append_file("alice", "log.txt", "line2\n")
    out = toolset.read_file("alice", "log.txt")
    assert out == "line1\nline2\n"


def test_delete_file(fake_repo_manager) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    toolset = MemoryToolset(fake_repo_manager)
    toolset.write_file("alice", "gone.txt", "content")
    out = toolset.delete_file("alice", "gone.txt")
    assert json.loads(out)["deleted"] == "gone.txt"
    assert json.loads(toolset.file_exists("alice", "gone.txt"))["exists"] is False


def test_sync_returns_expected_json(fake_repo_manager) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    toolset = MemoryToolset(fake_repo_manager)
    out = toolset.sync("alice", "msg")
    data = json.loads(out)
    assert data["status"] == "ok"
    assert data["user_id"] == "alice"


def test_remove_user_then_list_users_excludes_user(
    fake_repo_manager,
) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    toolset = MemoryToolset(fake_repo_manager)
    assert "alice" in json.loads(toolset.list_users())
    out = toolset.remove_user("alice")
    assert json.loads(out)["removed"] == "alice"
    assert "alice" not in json.loads(toolset.list_users())


def test_read_file_missing_returns_error_json(fake_repo_manager) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    toolset = MemoryToolset(fake_repo_manager)
    out = toolset.read_file("alice", "nonexistent.md")
    data = json.loads(out)
    assert "error" in data
    assert "nonexistent.md" in data["error"]
