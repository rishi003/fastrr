"""Git-backed implementation of RepoManager: one storage repo, one worktree per user (local only)."""

import shutil
from datetime import timezone
from pathlib import Path
from threading import RLock

import git

from fastrr.history import RepoHistoryEntry
from fastrr.services.repo_manager.base import RepoManager


class GitRepoManager(RepoManager):
    """
    One local storage repo, one worktree per user (branch user/{user_id}).
    Repo-mutating operations are serialized to avoid Git lock contention.
    """

    def __init__(self, storage_path: str | Path, worktree_root: str | Path):
        self.storage_path = Path(storage_path)
        self.worktree_root = Path(worktree_root)
        self._lock = RLock()
        self._branch_cache: set[str] = set()
        self._cache_valid = False

        self.worktree_root.mkdir(parents=True, exist_ok=True)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        try:
            self.repo = git.Repo(self.storage_path)
        except git.exc.InvalidGitRepositoryError:
            self.repo = git.Repo.init(self.storage_path)
        self._refresh_branch_cache()

    def _refresh_branch_cache(self) -> None:
        self._branch_cache = {r.name for r in self.repo.references}
        self._cache_valid = True

    def _user_branch(self, user_id: str) -> str:
        return f"user/{user_id}"

    def get_worktree_path(self, user_id: str) -> Path:
        return self.worktree_root / user_id

    def ensure_user_worktree(self, user_id: str) -> str:
        path = self.get_worktree_path(user_id)
        if path.exists():
            try:
                git.Repo(path)
                return str(path.resolve())
            except git.exc.InvalidGitRepositoryError:
                shutil.rmtree(path)

        with self._lock:
            if path.exists():
                try:
                    git.Repo(path)
                    return str(path.resolve())
                except git.exc.InvalidGitRepositoryError:
                    shutil.rmtree(path)

            if not self._cache_valid:
                self._refresh_branch_cache()

            branch = self._user_branch(user_id)
            has_local = branch in self._branch_cache

            if has_local:
                self._worktree_add(str(path), branch, orphan=False)
            else:
                self._worktree_add(str(path), branch, orphan=True)
                self._branch_cache.add(branch)

        return str(path.resolve())

    def _worktree_add(self, path: str, branch: str, *, orphan: bool) -> None:
        try:
            if orphan:
                self.repo.git.worktree("add", "--orphan", "-b", branch, path)
            else:
                self.repo.git.worktree("add", path, branch)
        except git.exc.GitCommandError as e:
            if "already registered" in str(e):
                self.repo.git.worktree("prune")
                if orphan:
                    self.repo.git.worktree(
                        "add", "--force", "--orphan", "-b", branch, path
                    )
                else:
                    self.repo.git.worktree("add", "--force", path, branch)
            else:
                raise

    def sync_user(self, user_id: str, message: str = "sync") -> None:
        path = self.get_worktree_path(user_id)
        if not path.exists():
            raise ValueError(f"No worktree for {user_id}")
        worktree_repo = git.Repo(path)
        if worktree_repo.is_dirty(untracked_files=True):
            worktree_repo.git.add(A=True)
            worktree_repo.index.commit(message)

    def remove_user(self, user_id: str, *, wipe_remote: bool = False) -> None:
        path = self.get_worktree_path(user_id)
        branch = self._user_branch(user_id)
        with self._lock:
            if path.exists():
                try:
                    self.repo.git.worktree("remove", "--force", str(path))
                except Exception:
                    if path.exists():
                        shutil.rmtree(path)
            try:
                if branch in (h.name for h in self.repo.heads):
                    self.repo.git.branch("-D", branch)
            except Exception:
                pass
            self._branch_cache.discard(branch)
        self._cache_valid = False

    def list_users(self) -> list[str]:
        if not self.worktree_root.exists():
            return []
        return [
            d.name
            for d in self.worktree_root.iterdir()
            if d.is_dir() and (d / ".git").exists()
        ]

    def get_user_history(self, user_id: str, limit: int) -> list[RepoHistoryEntry]:
        if limit <= 0:
            raise ValueError("limit must be > 0")

        branch = self._user_branch(user_id)
        if branch not in (h.name for h in self.repo.heads):
            return []

        safe_limit = min(limit, 200)
        commits = list(self.repo.iter_commits(branch, max_count=safe_limit))

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
