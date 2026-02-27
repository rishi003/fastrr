"""Shared pytest fixtures for fastrr tests."""

import shutil
from pathlib import Path

import pytest

from fastrr.services.repo_manager.base import RepoManager


class FakeRepoManager(RepoManager):
    """
    In-memory RepoManager for tests: one subdir per user under a single root.
    No Git; sync_user is a no-op.
    """

    def __init__(self, root: Path):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def get_worktree_path(self, user_id: str) -> Path:
        return self._root / user_id

    def ensure_user_worktree(self, user_id: str) -> str:
        path = self.get_worktree_path(user_id)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())

    def sync_user(self, user_id: str, message: str = "sync") -> None:
        pass

    def remove_user(self, user_id: str, *, wipe_remote: bool = False) -> None:
        path = self.get_worktree_path(user_id)
        if path.exists():
            shutil.rmtree(path)

    def list_users(self) -> list[str]:
        if not self._root.exists():
            return []
        return [
            d.name
            for d in self._root.iterdir()
            if d.is_dir()
        ]


@pytest.fixture
def fake_repo_manager(tmp_path: Path) -> FakeRepoManager:
    """Provide a FakeRepoManager rooted at a temp directory."""
    return FakeRepoManager(tmp_path)
