"""Fake RepoManager for evals: no Git, faster for quick runs."""

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastrr.history import RepoHistoryEntry
from fastrr.services.repo_manager.base import RepoManager


class FakeRepoManager(RepoManager):
    """In-memory RepoManager: one workspace. No Git; history tracked in memory."""

    def __init__(self, root: Path):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._history: list[RepoHistoryEntry] = []

    def get_workspace_path(self) -> Path:
        return self._root

    def ensure_workspace(self) -> str:
        self._root.mkdir(parents=True, exist_ok=True)
        return str(self._root.resolve())

    def sync(self, message: str = "sync") -> None:
        changed_files = [
            str(p.relative_to(self._root))
            for p in self._root.rglob("*")
            if p.is_file()
        ]
        self._history.append(
            RepoHistoryEntry(
                commit=uuid.uuid4().hex[:8],
                timestamp=datetime.now(tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                message=message,
                changed_files=changed_files,
                diff_text="",
            )
        )

    def forget(self) -> None:
        if not self._root.exists():
            return
        for item in self._root.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink(missing_ok=True)
        self._history.clear()

    def get_history(self, limit: int) -> list[RepoHistoryEntry]:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        safe_limit = min(limit, 200)
        return list(reversed(self._history[-safe_limit:]))
