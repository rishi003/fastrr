"""Unit tests for GitRepoManager."""

from pathlib import Path

import git
import pytest

from fastrr.services.repo_manager.git_repo_manager import GitRepoManager


@pytest.fixture
def git_repo_manager(tmp_path: Path) -> GitRepoManager:
    """Create a GitRepoManager with temp storage and worktree roots."""
    storage = tmp_path / "storage"
    worktrees = tmp_path / "worktrees"
    return GitRepoManager(storage, worktrees)


def test_get_worktree_path(git_repo_manager: GitRepoManager) -> None:
    path = git_repo_manager.get_worktree_path("alice")
    assert path == git_repo_manager.worktree_root / "alice"


def test_ensure_user_worktree_creates_worktree_and_branch(
    git_repo_manager: GitRepoManager,
) -> None:
    path_str = git_repo_manager.ensure_user_worktree("alice")
    path = Path(path_str)
    assert path.exists()
    # Worktree is a valid git repo (path is the worktree root)
    worktree_repo = git.Repo(path)
    assert (path / ".git").exists()
    # Worktree root matches get_worktree_path
    assert path == git_repo_manager.get_worktree_path("alice")


def test_list_users_after_ensure(git_repo_manager: GitRepoManager) -> None:
    assert git_repo_manager.list_users() == []
    git_repo_manager.ensure_user_worktree("alice")
    assert git_repo_manager.list_users() == ["alice"]


def test_list_users_empty_after_remove_user(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_user_worktree("alice")
    assert "alice" in git_repo_manager.list_users()
    git_repo_manager.remove_user("alice")
    assert git_repo_manager.list_users() == []


def test_sync_user_commits_after_adding_file(
    git_repo_manager: GitRepoManager,
) -> None:
    git_repo_manager.ensure_user_worktree("alice")
    worktree_path = git_repo_manager.get_worktree_path("alice")
    (worktree_path / "note.txt").write_text("hello")
    git_repo_manager.sync_user("alice", "msg")
    worktree_repo = git.Repo(worktree_path)
    assert not worktree_repo.is_dirty(untracked_files=True)


def test_remove_user_removes_worktree_and_branch(
    git_repo_manager: GitRepoManager,
) -> None:
    git_repo_manager.ensure_user_worktree("alice")
    worktree_path = git_repo_manager.get_worktree_path("alice")
    assert worktree_path.exists()
    git_repo_manager.remove_user("alice")
    assert not worktree_path.exists()
    branch_names = [h.name for h in git_repo_manager.repo.heads]
    assert "user/alice" not in branch_names
