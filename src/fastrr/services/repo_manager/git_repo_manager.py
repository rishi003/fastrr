"""Git-backed implementation of RepoManager using one local repository."""

import shutil
from datetime import timezone
from pathlib import Path

import git

from fastrr.history import RepoHistoryEntry
from fastrr.services.repo_manager.base import RepoManager


class GitRepoManager(RepoManager):
    """Single-repo storage manager for memory files."""

    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        try:
            self.repo = git.Repo(self.storage_path)
        except git.exc.InvalidGitRepositoryError:
            self.repo = git.Repo.init(self.storage_path)

    def get_workspace_path(self) -> Path:
        return self.storage_path

    def ensure_workspace(self) -> str:
        self.storage_path.mkdir(parents=True, exist_ok=True)
        return str(self.storage_path.resolve())

    def sync(self, message: str = "sync") -> None:
        self.ensure_workspace()
        if self.repo.is_dirty(untracked_files=True):
            self.repo.git.add(A=True)
            self.repo.index.commit(message)

    def forget(self) -> None:
        self.ensure_workspace()
        for item in self.storage_path.iterdir():
            if item.name == ".git":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink(missing_ok=True)

    def get_history(self, limit: int) -> list[RepoHistoryEntry]:
        if limit <= 0:
            raise ValueError("limit must be > 0")

        safe_limit = min(limit, 200)
        if not self.repo.head.is_valid():
            return []

        commits = list(self.repo.iter_commits("HEAD", max_count=safe_limit))

        entries: list[RepoHistoryEntry] = []
        for commit in commits:
            timestamp = (
                commit.committed_datetime.astimezone(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
            changed_files = list(commit.stats.files.keys())
            diff_text = self.repo.git.show(
                commit.hexsha,
                "--pretty=format:",
                "--unified=0",
            )
            entries.append(
                RepoHistoryEntry(
                    commit=commit.hexsha,
                    timestamp=timestamp,
                    message=commit.message.strip(),
                    changed_files=changed_files,
                    diff_text=diff_text,
                )
            )
        return entries
