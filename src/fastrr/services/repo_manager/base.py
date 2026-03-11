"""Abstract contract for per-user workspace storage (Git and future VCS backends)."""

from abc import ABC, abstractmethod
from pathlib import Path

from fastrr.history import RepoHistoryEntry


class RepoManager(ABC):
    """Contract for per-user workspace storage. Implementations: Git (and others later)."""

    @abstractmethod
    def get_worktree_path(self, user_id: str) -> Path:
        """Path where this user's workspace lives (directory may not exist yet)."""
        ...

    @abstractmethod
    def ensure_user_worktree(self, user_id: str) -> str:
        """Ensure the user has a workspace; return its absolute path."""
        ...

    @abstractmethod
    def sync_user(self, user_id: str, message: str = "sync") -> None:
        """Persist and optionally push user's changes."""
        ...

    @abstractmethod
    def remove_user(self, user_id: str, *, wipe_remote: bool = False) -> None:
        """Remove workspace and optionally remote data for this user."""
        ...

    @abstractmethod
    def list_users(self) -> list[str]:
        """List user IDs that have an active workspace."""
        ...

    @abstractmethod
    def get_user_history(self, user_id: str, limit: int) -> list[RepoHistoryEntry]:
        """Return newest-first history entries for this user."""
        ...
