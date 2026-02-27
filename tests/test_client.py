"""Unit tests for Fastrr client."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fastrr import Fastrr

from conftest import FakeRepoManager


@pytest.fixture
def mock_model() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_agent_run(fake_repo_manager: FakeRepoManager):
    """Patch Agno Agent so run() returns a response with content; no real LLM calls.
    Writer run() side_effect ensures worktree for 'alice' on store and calls remove_user on remove.
    """
    mock_instance = MagicMock()

    def run_side_effect(prompt: str):
        if "Store" in prompt and "alice" in prompt:
            fake_repo_manager.ensure_user_worktree("alice")
        elif "Remove" in prompt and "alice" in prompt:
            fake_repo_manager.remove_user("alice")
        return MagicMock(content="mocked recall")

    mock_instance.run.side_effect = run_side_effect
    with patch("fastrr.agents.writer.Agent", return_value=mock_instance), patch(
        "fastrr.agents.reader.Agent", return_value=mock_instance
    ):
        yield mock_instance


def test_list_users_empty(
    fake_repo_manager: FakeRepoManager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        worktree_root=Path("/tmp/w"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    assert memory.list_users() == []


def test_remember_then_list_users_includes_user(
    fake_repo_manager: FakeRepoManager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        worktree_root=Path("/tmp/w"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    memory.remember("alice", "some content")
    assert "alice" in memory.list_users()


def test_recall_returns_mocked_string(
    fake_repo_manager: FakeRepoManager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        worktree_root=Path("/tmp/w"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    result = memory.recall("alice", query="x")
    assert result == "mocked recall"


def test_forget_then_list_users_excludes_user(
    fake_repo_manager: FakeRepoManager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    fake_repo_manager.ensure_user_worktree("alice")
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        worktree_root=Path("/tmp/w"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    assert "alice" in memory.list_users()
    memory.forget("alice")
    assert "alice" not in memory.list_users()
