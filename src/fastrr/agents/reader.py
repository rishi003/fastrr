"""ReaderAgent: Agno agent responsible for retrieving and summarising memory."""

from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.models.base import Model

from fastrr.agents.search import RegexSearch, SearchStrategy
from fastrr.agents.toolset import MemoryToolset

_READER_INSTRUCTIONS = """
You are a memory reader agent. Your job is to retrieve relevant memory.

When asked to recall memory:
1. Call list_files to see what files exist in the workspace.
2. Call read_file for each file that might contain relevant information.
3. Synthesise and return only the content that is relevant to the query.
   If no query is given, summarise all memory.
4. Return plain text. Be concise. Do not invent information.
""".strip()


class ReaderAgent:
    """Agno-powered agent that searches and retrieves memory for a user."""

    def __init__(
        self,
        toolset: MemoryToolset,
        model: Model,
        search_strategy: Optional[SearchStrategy] = None,
    ):
        self._toolset = toolset
        self._model = model
        self._search = search_strategy or RegexSearch()
        self._agent = Agent(
            model=model,
            tools=toolset.read_tools,
            instructions=_READER_INSTRUCTIONS,
            description="Retrieves and summarises memory from disk.",
        )

    def search(self, query: Optional[str] = None) -> str:
        """
        Retrieve memory, optionally filtered by `query`.

        The search strategy pre-filters files to surface relevant snippets,
        which are then passed to the agent for synthesis.
        """
        workspace = Path(self._toolset._repo.ensure_workspace())

        if query:
            snippets = self._search.search(workspace, query)
            if snippets:
                snippet_text = "\n".join(snippets)
                prompt = (
                    f"Recall memory relevant to: '{query}'.\n\n"
                    f"Pre-filtered snippets from the workspace:\n{snippet_text}\n\n"
                    f"Read any additional files if needed and return a concise summary."
                )
            else:
                prompt = (
                    f"Recall memory relevant to: '{query}'. "
                    f"No pre-filtered matches found — read the files directly."
                )
        else:
            prompt = "Summarise all stored memory."

        result = self._agent.run(prompt)
        return result.content or ""
