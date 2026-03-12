"""Shared pytest fixtures for fastrr tests."""

import shutil
from pathlib import Path

import pytest

from fastrr.history import RepoHistoryEntry
from fastrr.services.repo_manager.base import RepoManager


class FakeRepoManager(RepoManager):
    """
    In-memory RepoManager for tests: one workspace under a single root.
    No Git; sync is a no-op.
    """

    def __init__(self, root: Path):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def get_workspace_path(self) -> Path:
        return self._root

    def ensure_workspace(self) -> str:
        self._root.mkdir(parents=True, exist_ok=True)
        return str(self._root.resolve())

    def sync(self, message: str = "sync") -> None:
        pass

    def forget(self) -> None:
        if not self._root.exists():
            return
        for item in self._root.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink(missing_ok=True)

    def get_history(self, limit: int) -> list[RepoHistoryEntry]:
        return []


@pytest.fixture
def fake_repo_manager(tmp_path: Path) -> FakeRepoManager:
    """Provide a FakeRepoManager rooted at a temp directory."""
    return FakeRepoManager(tmp_path)
