"""Fastrr: semantic memory layer for AI applications.

Downstream apps call remember/recall/forget. Under the hood, Agno-powered
reader and writer agents use GitRepoManager as versioned storage.
"""

from pathlib import Path
from typing import Optional

from agno.models.base import Model

from fastrr.agents.reader import ReaderAgent
from fastrr.agents.search import SearchStrategy
from fastrr.agents.toolset import MemoryToolset
from fastrr.agents.writer import WriterAgent
from fastrr.core.config import FastrrConfig
from fastrr.services.repo_manager import GitRepoManager, RepoManager


def _build_model(config: FastrrConfig) -> Model:
    if config.provider == "openrouter":
        from agno.models.openrouter import OpenRouter

        return OpenRouter(id=config.model, api_key=config.openrouter_api_key)

    from agno.models.ollama import Ollama

    return Ollama(id=config.model, host=config.ollama_host)


class Fastrr:
    """
    Semantic memory layer for AI applications.

    Creates per-user, versioned workspaces on disk. Agents handle how
    memories are organised and retrieved; the caller only needs to use
    remember / recall / forget.

    LLM provider is configured via environment variables (see FastrrConfig).

    Example:
        from fastrr import Fastrr

        memory = Fastrr(storage_path="./data/repo", worktree_root="./data/users")
        memory.remember("alice", "Prefers concise bullet-point answers.")
        context = memory.recall("alice", query="communication style")
        memory.forget("alice")
    """

    def __init__(
        self,
        storage_path: str | Path,
        worktree_root: str | Path,
        *,
        repo_manager: Optional[RepoManager] = None,
        model: Optional[Model] = None,
        search_strategy: Optional[SearchStrategy] = None,
        config: Optional[FastrrConfig] = None,
    ):
        """
        Args:
            storage_path:     Path to the Git storage repo (created if missing).
            worktree_root:    Directory where per-user worktrees are mounted.
            repo_manager:     Override the default GitRepoManager (useful for tests).
            model:            Override the Agno Model (takes precedence over env config).
            search_strategy:  Override the memory search strategy (default: RegexSearch).
            config:           Override the FastrrConfig (default: loaded from env/.env).
        """
        cfg = config or FastrrConfig()
        resolved_model = model or _build_model(cfg)
        resolved_repo = repo_manager or GitRepoManager(
            Path(storage_path), Path(worktree_root)
        )

        toolset = MemoryToolset(resolved_repo)
        self._writer = WriterAgent(toolset, resolved_model)
        self._reader = ReaderAgent(toolset, resolved_model, search_strategy)
        self._repo = resolved_repo

    def remember(self, user_id: str, content: str) -> None:
        """
        Persist a memory for this user.
        The writer agent decides how to store and organise it on disk.
        """
        self._writer.store(user_id, content)

    def recall(self, user_id: str, query: Optional[str] = None) -> str:
        """
        Retrieve memory relevant to `query`, or summarise all memory if no query given.
        """
        return self._reader.search(user_id, query)

    def forget(self, user_id: str) -> None:
        """Remove all stored memory for this user."""
        self._writer.remove(user_id)

    def list_users(self) -> list[str]:
        """Return user IDs that have an active memory workspace."""
        return self._repo.list_users()
