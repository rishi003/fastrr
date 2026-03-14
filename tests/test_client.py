"""Unit tests for Fastrr client."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fastrr import Fastrr, MemoryHistoryEvent, RepoHistoryEntry
from fastrr.services.repo_manager import GitRepoManager


def test_memory_history_event_importable() -> None:
    event = MemoryHistoryEvent(
        commit="abc123",
        timestamp="2026-03-11T00:00:00Z",
        message="remember",
        changed_files=["preferences.md"],
        summary="added memory to preferences.md",
    )
    assert event.commit == "abc123"


@pytest.fixture
def mock_model() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_agent_run(fake_repo_manager):
    """Patch Agno Agent so run() returns a response with content; no real LLM calls.
    Writer run() side_effect clears memory on remove.
    """
    mock_instance = MagicMock()

    def run_side_effect(prompt: str):
        if "Clear all memory" in prompt:
            fake_repo_manager.forget()
        return MagicMock(content="mocked recall")

    mock_instance.run.side_effect = run_side_effect
    with patch("fastrr.agents.writer.Agent", return_value=mock_instance), patch(
        "fastrr.agents.reader.Agent", return_value=mock_instance
    ):
        yield mock_instance


def test_remember_writes_memory(
    fake_repo_manager,
    mock_model: MagicMock,
) -> None:
    mock_instance = MagicMock()
    mock_instance.run.return_value = MagicMock(
        content="Stored memory.\nCOMMIT: remember preference"
    )
    with patch("fastrr.agents.writer.Agent", return_value=mock_instance), patch(
        "fastrr.agents.reader.Agent", return_value=mock_instance
    ):
        memory = Fastrr(
            storage_path=Path("/tmp/s"),
            repo_manager=fake_repo_manager,
            model=mock_model,
        )
        memory.remember("some content")
    assert mock_instance.run.called


def test_remember_always_syncs(
    fake_repo_manager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    """sync is always called; falls back to 'remember' when no COMMIT: line."""
    from unittest.mock import patch as _patch

    with _patch.object(fake_repo_manager, "sync") as mock_sync:
        memory = Fastrr(
            storage_path=Path("/tmp/s"),
            repo_manager=fake_repo_manager,
            model=mock_model,
        )
        memory.remember("likes cats")
        mock_sync.assert_called_once_with(message="remember")


def test_remember_uses_commit_message_from_agent(
    fake_repo_manager,
    mock_model: MagicMock,
) -> None:
    """When the agent response contains a COMMIT: line it is used as the commit message."""
    from unittest.mock import MagicMock as _Mock, patch as _patch

    mock_instance = _Mock()
    mock_instance.run.return_value = _Mock(
        content="Stored preference.\nCOMMIT: add communication style to preferences.md"
    )

    with _patch("fastrr.agents.writer.Agent", return_value=mock_instance), _patch(
        "fastrr.agents.reader.Agent", return_value=mock_instance
    ), _patch.object(fake_repo_manager, "sync") as mock_sync:
        memory = Fastrr(
            storage_path=Path("/tmp/s"),
            repo_manager=fake_repo_manager,
            model=mock_model,
        )
        memory.remember("prefers bullet points")
        mock_sync.assert_called_once_with(
            message="add communication style to preferences.md"
        )


def test_recall_returns_mocked_string(
    fake_repo_manager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    fake_repo_manager.ensure_workspace()
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    result = memory.recall(query="x")
    assert result == "mocked recall"


def test_forget_clears_memory(
    fake_repo_manager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    fake_repo_manager.ensure_workspace()
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    fake_repo_manager.get_workspace_path().joinpath("note.txt").write_text("x")
    memory.forget()
    assert not fake_repo_manager.get_workspace_path().joinpath("note.txt").exists()


def test_history_limit_validation(
    fake_repo_manager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    with pytest.raises(ValueError, match="limit must be > 0"):
        memory.history(limit=0)


def test_history_maps_repo_entries(
    fake_repo_manager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    fake_repo_manager.get_history = MagicMock(
        return_value=[
            RepoHistoryEntry(
                commit="abc123",
                timestamp="2026-03-11T00:00:00Z",
                message="update preference",
                changed_files=["preferences.md"],
                diff_text="@@\n-old\n+new\n",
            )
        ]
    )
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    events = memory.history(limit=5)
    assert events[0].changed_files == ["preferences.md"]
    assert "updated" in events[0].summary.lower()


def test_history_empty(
    fake_repo_manager,
    mock_model: MagicMock,
    mock_agent_run: MagicMock,
) -> None:
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    assert memory.history(limit=10) == []


def test_history_empty_with_git_repo(
    tmp_path: Path,
    mock_model: MagicMock,
) -> None:
    storage = tmp_path / "repo"
    repo_manager = GitRepoManager(storage)
    with patch("fastrr.agents.writer.Agent", return_value=MagicMock()), patch(
        "fastrr.agents.reader.Agent", return_value=MagicMock()
    ):
        memory = Fastrr(
            storage_path=storage,
            repo_manager=repo_manager,
            model=mock_model,
        )
    assert memory.history(limit=10) == []


def test_init_creates_template_files(
    fake_repo_manager,
    mock_model: MagicMock,
) -> None:
    """Fastrr.__init__ touches default template files in the workspace."""
    with patch("fastrr.agents.writer.Agent", return_value=MagicMock()), patch(
        "fastrr.agents.reader.Agent", return_value=MagicMock()
    ):
        Fastrr(
            storage_path=Path("/tmp/s"),
            repo_manager=fake_repo_manager,
            model=mock_model,
        )
    workspace = fake_repo_manager.get_workspace_path()
    assert (workspace / "preferences.md").exists()
    assert (workspace / "history.jsonl").exists()
    assert (workspace / "facts.md").exists()


def test_init_does_not_overwrite_existing_template_files(
    fake_repo_manager,
    mock_model: MagicMock,
) -> None:
    """Template initialisation skips files that already have content."""
    fake_repo_manager.ensure_workspace()
    existing = fake_repo_manager.get_workspace_path() / "preferences.md"
    existing.write_text("saved preference")
    with patch("fastrr.agents.writer.Agent", return_value=MagicMock()), patch(
        "fastrr.agents.reader.Agent", return_value=MagicMock()
    ):
        Fastrr(
            storage_path=Path("/tmp/s"),
            repo_manager=fake_repo_manager,
            model=mock_model,
        )
    assert existing.read_text() == "saved preference"


def test_fastrr_passes_search_strategy_to_writer(
    fake_repo_manager,
    mock_model: MagicMock,
) -> None:
    """search_strategy passed to Fastrr is forwarded to WriterAgent."""
    from fastrr.agents.search import SearchStrategy

    custom_strategy = MagicMock(spec=SearchStrategy)
    with patch("fastrr.agents.writer.Agent"), patch("fastrr.agents.reader.Agent"):
        client = Fastrr(
            storage_path=Path("/tmp/s"),
            repo_manager=fake_repo_manager,
            model=mock_model,
            search_strategy=custom_strategy,
        )
    assert client._writer._search is custom_strategy
