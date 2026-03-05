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


def test_remember_always_syncs(
    fake_repo_manager: FakeRepoManager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    """sync_user is always called; falls back to 'remember' when no COMMIT: line."""
    from unittest.mock import patch as _patch

    with _patch.object(fake_repo_manager, "sync_user") as mock_sync:
        memory = Fastrr(
            storage_path=Path("/tmp/s"),
            worktree_root=Path("/tmp/w"),
            repo_manager=fake_repo_manager,
            model=mock_model,
        )
        memory.remember("alice", "likes cats")
        mock_sync.assert_called_once_with("alice", message="remember")


def test_remember_uses_commit_message_from_agent(
    fake_repo_manager: FakeRepoManager,
    mock_model: MagicMock,
) -> None:
    """When the agent response contains a COMMIT: line it is used as the commit message."""
    from unittest.mock import MagicMock as _Mock, patch as _patch

    mock_instance = _Mock()
    mock_instance.run.return_value = _Mock(
        content="Stored alice's preference.\nCOMMIT: add alice communication style to preferences.md"
    )

    with _patch("fastrr.agents.writer.Agent", return_value=mock_instance), _patch(
        "fastrr.agents.reader.Agent", return_value=mock_instance
    ), _patch.object(fake_repo_manager, "sync_user") as mock_sync:
        memory = Fastrr(
            storage_path=Path("/tmp/s"),
            worktree_root=Path("/tmp/w"),
            repo_manager=fake_repo_manager,
            model=mock_model,
        )
        memory.remember("alice", "prefers bullet points")
        mock_sync.assert_called_once_with(
            "alice", message="add alice communication style to preferences.md"
        )


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
