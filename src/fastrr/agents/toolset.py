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

    def _workspace(self) -> Path:
        return Path(self._repo.ensure_workspace())

    # ── Read tools ─────────────────────────────────────────────────────────

    def list_files(self) -> str:
        """
        List all files in the memory workspace.
        """
        root = self._workspace()
        files = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
        return json.dumps(files)

    def read_file(self, relative_path: str) -> str:
        """
        Read the full contents of a file from the memory workspace.
        """
        path = self._workspace() / relative_path
        if not path.exists():
            return json.dumps({"error": f"File not found: {relative_path}"})
        return path.read_text()

    def file_exists(self, relative_path: str) -> str:
        """
        Check whether a file exists in the memory workspace.
        """
        exists = (self._workspace() / relative_path).exists()
        return json.dumps({"exists": exists})

    # ── Write tools ────────────────────────────────────────────────────────

    def write_file(self, relative_path: str, content: str) -> str:
        """
        Write (or overwrite) a file in the memory workspace.
        """
        path = self._workspace() / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return json.dumps({"status": "ok", "path": str(relative_path)})

    def append_file(self, relative_path: str, content: str) -> str:
        """
        Append content to an existing file (or create it) in the memory workspace.
        """
        path = self._workspace() / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(content)
        return json.dumps({"status": "ok", "path": str(relative_path)})

    def delete_file(self, relative_path: str) -> str:
        """
        Delete a file from the memory workspace.
        """
        path = self._workspace() / relative_path
        path.unlink(missing_ok=True)
        return json.dumps({"status": "ok", "deleted": str(relative_path)})

    def sync(self, message: str = "sync") -> str:
        """
        Persist (commit) all pending changes in the memory workspace.
        """
        self._repo.sync(message=message)
        return json.dumps({"status": "ok"})

    def forget(self) -> str:
        """
        Clear all memory files from the workspace.
        """
        self._repo.forget()
        return json.dumps({"status": "ok"})

    # ── Convenience groups ─────────────────────────────────────────────────

    @property
    def read_tools(self) -> list:
        """All read-only callables."""
        return [self.list_files, self.read_file, self.file_exists]

    @property
    def write_tools(self) -> list:
        """All write callables (includes sync and remove)."""
        return [
            self.write_file,
            self.append_file,
            self.delete_file,
            self.sync,
            self.forget,
        ]

    @property
    def all_tools(self) -> list:
        return self.read_tools + self.write_tools
