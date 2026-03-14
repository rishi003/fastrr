"""Abstract contract for a single memory workspace backend."""

from abc import ABC, abstractmethod
from pathlib import Path

from fastrr.history import RepoHistoryEntry


class RepoManager(ABC):
    """Contract for single-workspace storage. Implementations: Git (and others later)."""

    @abstractmethod
    def get_workspace_path(self) -> Path:
        """Path where the memory workspace lives."""
        ...

    @abstractmethod
    def ensure_workspace(self) -> str:
        """Ensure the workspace exists; return its absolute path."""
        ...

    @abstractmethod
    def sync(self, message: str = "sync") -> None:
        """Persist workspace changes."""
        ...

    @abstractmethod
    def forget(self) -> None:
        """Clear all stored memory from the workspace."""
        ...

    @abstractmethod
    def get_history(self, limit: int) -> list[RepoHistoryEntry]:
        """Return newest-first history entries for this workspace."""
        ...

    def initialize_workspace(self, template_files: list[str]) -> None:
        """Touch each template file in the workspace if it does not yet exist."""
        workspace = Path(self.ensure_workspace())
        for name in template_files:
            p = workspace / name
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.touch()
