"""Unit tests for GitRepoManager."""

from pathlib import Path
import git
import pytest

from fastrr.services.repo_manager.git_repo_manager import GitRepoManager


@pytest.fixture
def git_repo_manager(tmp_path: Path) -> GitRepoManager:
    """Create a GitRepoManager with a temp storage root."""
    storage = tmp_path / "storage"
    return GitRepoManager(storage)


def test_get_workspace_path(git_repo_manager: GitRepoManager) -> None:
    path = git_repo_manager.get_workspace_path()
    assert path == git_repo_manager.storage_path


def test_ensure_workspace_returns_repo_path(git_repo_manager: GitRepoManager) -> None:
    path_str = git_repo_manager.ensure_workspace()
    path = Path(path_str)
    assert path.exists()
    workspace_repo = git.Repo(path)
    assert (path / ".git").exists()
    assert workspace_repo.working_tree_dir == str(path)


def test_sync_commits_after_adding_file(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_workspace()
    workspace = git_repo_manager.get_workspace_path()
    (workspace / "note.txt").write_text("hello")
    git_repo_manager.sync("msg")
    repo = git.Repo(workspace)
    assert not repo.is_dirty(untracked_files=True)


def test_forget_removes_workspace_files(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_workspace()
    workspace = git_repo_manager.get_workspace_path()
    (workspace / "a.md").write_text("hello")
    (workspace / "nested").mkdir()
    (workspace / "nested" / "b.md").write_text("world")
    git_repo_manager.forget()
    assert not (workspace / "a.md").exists()
    assert not (workspace / "nested").exists()
    assert (workspace / ".git").exists()


def test_get_history_newest_first(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_workspace()
    workspace = git_repo_manager.get_workspace_path()
    (workspace / "a.md").write_text("first")
    git_repo_manager.sync("first commit")
    (workspace / "a.md").write_text("second")
    git_repo_manager.sync("second commit")

    events = git_repo_manager.get_history(limit=10)
    assert len(events) == 2
    assert events[0].message == "second commit"
    assert events[1].message == "first commit"


def test_get_history_empty_repo_returns_empty(git_repo_manager: GitRepoManager) -> None:
    assert git_repo_manager.get_history(limit=10) == []


def test_get_history_invalid_limit_raises(git_repo_manager: GitRepoManager) -> None:
    with pytest.raises(ValueError, match="limit must be > 0"):
        git_repo_manager.get_history(limit=0)


def test_initialize_workspace_creates_files(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.initialize_workspace(["preferences.md", "history.jsonl", "facts.md"])
    workspace = git_repo_manager.get_workspace_path()
    assert (workspace / "preferences.md").exists()
    assert (workspace / "history.jsonl").exists()
    assert (workspace / "facts.md").exists()


def test_initialize_workspace_skips_existing(git_repo_manager: GitRepoManager) -> None:
    workspace = git_repo_manager.get_workspace_path()
    git_repo_manager.ensure_workspace()
    (workspace / "preferences.md").write_text("existing content")
    git_repo_manager.initialize_workspace(["preferences.md"])
    assert (workspace / "preferences.md").read_text() == "existing content"


def test_get_history_limit_is_capped(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_workspace()
    workspace = git_repo_manager.get_workspace_path()
    for i in range(205):
        (workspace / "a.md").write_text(f"v{i}")
        git_repo_manager.sync(f"commit-{i}")

    events = git_repo_manager.get_history(limit=500)
    assert len(events) == 200
    assert events[0].message == "commit-204"
    assert events[-1].message == "commit-5"
