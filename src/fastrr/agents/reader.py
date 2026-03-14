"""ReaderAgent: Agno agent responsible for retrieving and summarising memory."""

from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.models.base import Model

from fastrr.agents.search import RegexSearch, SearchStrategy
from fastrr.agents.toolset import MemoryToolset

_READER_INSTRUCTIONS_TEMPLATE = """
You are a memory reader agent. Your job is to retrieve relevant memory.

Memory Files:
{memory_files}

PHASE 1 — REVIEW
Examine the pre-filtered snippets provided in the user message.
Snippets are formatted as [filename] matching line.
The filename tells you which file to call read_file on for fuller context.
Note which files contain potentially relevant content.
If no snippets were provided, proceed to PHASE 2 and read files directly.

PHASE 2 — EXPAND (optional)
Call read_file when:
  (a) snippets for a file are sparse (fewer than 3 lines) and the query
      needs fuller context, or
  (b) the query asks for a complete summary of a topic.
Do not call read_file if the snippets already fully answer the query.

PHASE 3 — SYNTHESISE
Return only content relevant to the query in plain text.
Be concise. Do not invent information not found in the files.
If no relevant memory is found, say so plainly.
""".strip()


class ReaderAgent:
    """Agno-powered agent that searches and retrieves memory for a user."""

    def __init__(
        self,
        toolset: MemoryToolset,
        model: Model,
        search_strategy: Optional[SearchStrategy] = None,
        memory_files: str = "",
    ):
        self._toolset = toolset
        self._model = model
        self._search = search_strategy or RegexSearch()
        instructions = _READER_INSTRUCTIONS_TEMPLATE.format(memory_files=memory_files)
        self._agent = Agent(
            model=model,
            tools=toolset.read_tools,
            instructions=instructions,
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
