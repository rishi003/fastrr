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
from fastrr.history import MemoryHistoryEvent
from fastrr.history_summary import summarize_memory_change
from fastrr.services.repo_manager import GitRepoManager, RepoManager
from fastrr.template import format_template, load_template


def _build_model(config: FastrrConfig) -> Model:
    if config.provider == "openrouter":
        from agno.models.openrouter import OpenRouter

        return OpenRouter(id=config.model, api_key=config.openrouter_api_key)

    from agno.models.ollama import Ollama

    return Ollama(id=config.model, host=config.ollama_host)


class Fastrr:
    """
    Semantic memory layer for AI applications.

    Creates one versioned workspace on disk. Agents handle how memories are
    organised and retrieved; the caller only needs to use remember / recall /
    forget.

    LLM provider is configured via environment variables (see FastrrConfig).
    The memory workspace is initialised from a template (default: preferences.md,
    history.jsonl, facts.md) on first use. A custom template JSON can be supplied
    via FASTRR_MEMORY_TEMPLATE_PATH or the config object.

    Example:
        from fastrr import Fastrr

        memory = Fastrr(storage_path="./data/repo")
        memory.remember("Prefers concise bullet-point answers.")
        context = memory.recall(query="communication style")
        memory.forget()
    """

    def __init__(
        self,
        storage_path: str | Path,
        *,
        repo_manager: Optional[RepoManager] = None,
        model: Optional[Model] = None,
        search_strategy: Optional[SearchStrategy] = None,
        config: Optional[FastrrConfig] = None,
    ):
        """
        Args:
            storage_path:     Path to the Git storage repo (created if missing).
            repo_manager:     Override the default GitRepoManager (useful for tests).
            model:            Override the Agno Model (takes precedence over env config).
            search_strategy:  Override the memory search strategy (default: RegexSearch).
            config:           Override the FastrrConfig (default: loaded from env/.env).
        """
        cfg = config or FastrrConfig()
        resolved_model = model or _build_model(cfg)
        resolved_repo = repo_manager or GitRepoManager(Path(storage_path))

        template = load_template(cfg.memory_template_path)
        memory_files_text = format_template(template)
        resolved_repo.initialize_workspace([f.name for f in template])

        toolset = MemoryToolset(resolved_repo)
        self._writer = WriterAgent(toolset, resolved_model, memory_files=memory_files_text)
        self._reader = ReaderAgent(
            toolset, resolved_model, search_strategy, memory_files=memory_files_text
        )
        self._repo = resolved_repo

    def remember(self, content: str) -> None:
        """
        Persist a memory.
        The writer agent decides how to store and organise it on disk.
        """
        self._writer.store(content)

    def recall(self, query: Optional[str] = None) -> str:
        """
        Retrieve memory relevant to `query`, or summarise all memory if no query given.
        """
        return self._reader.search(query)

    def forget(self) -> None:
        """Remove all stored memory."""
        self._writer.remove()

    def history(self, limit: int = 20) -> list[MemoryHistoryEvent]:
        """Return newest-first memory history entries."""
        if limit <= 0:
            raise ValueError("limit must be > 0")

        entries = self._repo.get_history(limit=limit)
        return [
            MemoryHistoryEvent(
                commit=entry.commit,
                timestamp=entry.timestamp,
                message=entry.message,
                changed_files=entry.changed_files,
                summary=summarize_memory_change(
                    entry.message,
                    entry.changed_files,
                    entry.diff_text,
                ),
            )
            for entry in entries
        ]
