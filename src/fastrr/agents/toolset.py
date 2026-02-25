"""MemoryToolset: plain Python callables for file-level memory operations.

No AI framework dependency. These methods are registered as tools in Agno agents
but can also be called directly or adapted to any other framework.
"""

import json
from pathlib import Path

from fastrr.services.repo_manager.base import RepoManager


class MemoryToolset:
    """
    Plain Python tool callables wrapping RepoManager file operations.
    All methods return str so they can be used directly as LLM tool outputs.
    """

    def __init__(self, repo: RepoManager):
        self._repo = repo

    def _workspace(self, user_id: str) -> Path:
        return Path(self._repo.ensure_user_worktree(user_id))

    # ── Read tools ─────────────────────────────────────────────────────────

    def list_users(self) -> str:
        """List all user IDs that have an active memory workspace."""
        return json.dumps(self._repo.list_users())

    def list_files(self, user_id: str) -> str:
        """
        List all files in a user's memory workspace.

        Args:
            user_id: The user whose workspace to inspect.
        """
        root = self._workspace(user_id)
        files = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
        return json.dumps(files)

    def read_file(self, user_id: str, relative_path: str) -> str:
        """
        Read the full contents of a file from a user's memory workspace.

        Args:
            user_id: The user whose workspace to read from.
            relative_path: Path relative to the workspace root (e.g. "preferences.md").
        """
        path = self._workspace(user_id) / relative_path
        if not path.exists():
            return json.dumps({"error": f"File not found: {relative_path}"})
        return path.read_text()

    def file_exists(self, user_id: str, relative_path: str) -> str:
        """
        Check whether a file exists in a user's memory workspace.

        Args:
            user_id: The user whose workspace to check.
            relative_path: Path relative to the workspace root.
        """
        exists = (self._workspace(user_id) / relative_path).exists()
        return json.dumps({"exists": exists})

    # ── Write tools ────────────────────────────────────────────────────────

    def write_file(self, user_id: str, relative_path: str, content: str) -> str:
        """
        Write (or overwrite) a file in a user's memory workspace.

        Args:
            user_id: The user whose workspace to write to.
            relative_path: Path relative to the workspace root (e.g. "preferences.md").
            content: Full content to write.
        """
        path = self._workspace(user_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return json.dumps({"status": "ok", "path": str(relative_path)})

    def append_file(self, user_id: str, relative_path: str, content: str) -> str:
        """
        Append content to an existing file (or create it) in a user's memory workspace.

        Args:
            user_id: The user whose workspace to append to.
            relative_path: Path relative to the workspace root.
            content: Content to append.
        """
        path = self._workspace(user_id) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(content)
        return json.dumps({"status": "ok", "path": str(relative_path)})

    def delete_file(self, user_id: str, relative_path: str) -> str:
        """
        Delete a file from a user's memory workspace.

        Args:
            user_id: The user whose workspace to delete from.
            relative_path: Path relative to the workspace root.
        """
        path = self._workspace(user_id) / relative_path
        path.unlink(missing_ok=True)
        return json.dumps({"status": "ok", "deleted": str(relative_path)})

    def sync(self, user_id: str, message: str = "sync") -> str:
        """
        Persist (commit) all pending changes in a user's memory workspace.

        Args:
            user_id: The user whose workspace to commit.
            message: Commit message describing what changed.
        """
        self._repo.sync_user(user_id, message=message)
        return json.dumps({"status": "ok", "user_id": user_id})

    def remove_user(self, user_id: str) -> str:
        """
        Remove a user's workspace and branch entirely.

        Args:
            user_id: The user whose workspace to remove.
        """
        self._repo.remove_user(user_id, wipe_remote=False)
        return json.dumps({"status": "ok", "removed": user_id})

    # ── Convenience groups ─────────────────────────────────────────────────

    @property
    def read_tools(self) -> list:
        """All read-only callables."""
        return [self.list_users, self.list_files, self.read_file, self.file_exists]

    @property
    def write_tools(self) -> list:
        """All write callables (includes sync and remove)."""
        return [
            self.write_file,
            self.append_file,
            self.delete_file,
            self.sync,
            self.remove_user,
        ]

    @property
    def all_tools(self) -> list:
        return self.read_tools + self.write_tools
