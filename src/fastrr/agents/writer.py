"""WriterAgent: Agno agent responsible for storing and organising memory."""

from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.models.base import Model

from fastrr.agents.search import RegexSearch, SearchStrategy
from fastrr.agents.toolset import MemoryToolset

_WRITER_INSTRUCTIONS_TEMPLATE = """
You are a memory writer agent. Your job is to persist memory to disk.

Memory Files:
{memory_files}

PHASE 1 — ASSESS
Review the pre-filtered snippets provided in the user message
(format: [filename] matching line).
Determine whether similar information is already stored.
If no snippets were provided, proceed directly to PHASE 3.

PHASE 2 — READ
If snippets indicate existing similar content, call read_file on the
relevant file(s) to see the full current state before deciding what to write.

PHASE 3 — DECIDE
Choose exactly one action:
  - UPDATE: existing content covers the same fact or preference — read the
    file, merge new details, and rewrite the whole file with write_file.
  - WRITE NEW: no sufficiently similar content exists — use append_file
    or write_file as appropriate for the content type.
  - SKIP: the incoming content is identical to what is already stored —
    do nothing.

PHASE 4 — WRITE
Execute the chosen action. Use the Memory Files list above to pick the
right target file. Prefer markdown for prose notes, JSONL for structured
entries, and plain text for simple facts.
Never make up data. Only store what you are explicitly given.
Use short, clear filenames.

PHASE 5 — COMMIT
End your response with exactly one line summarising what you stored, in
the imperative mood, under 72 characters. Prefix it with "COMMIT: ".
Example: COMMIT: update preferred communication style in preferences.md
""".strip()

_COMMIT_PREFIX = "COMMIT: "


def _extract_commit_message(response) -> str:
    """Extract the COMMIT: summary line from the agent response, or fall back to 'remember'."""
    text = getattr(response, "content", None) or ""
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith(_COMMIT_PREFIX):
            return line[len(_COMMIT_PREFIX):].strip()[:72]
    return "remember"


_REMOVE_INSTRUCTIONS = """
You are a memory cleanup agent. Your job is to clear all memory files.
Call forget to remove all stored memory.
""".strip()


class WriterAgent:
    """Agno-powered agent that writes and organises memory for a user."""

    def __init__(
        self,
        toolset: MemoryToolset,
        model: Model,
        memory_files: str,
        search_strategy: Optional[SearchStrategy] = None,
    ):
        self._toolset = toolset
        self._model = model
        self._search = search_strategy or RegexSearch()
        instructions = _WRITER_INSTRUCTIONS_TEMPLATE.format(memory_files=memory_files)
        self._agent = Agent(
            model=model,
            tools=toolset.read_tools + toolset.write_tools,
            instructions=instructions,
            description="Stores and organises memory on disk.",
        )

    def store(self, content: str) -> None:
        """Ask the agent to store `content` in the workspace."""
        workspace = Path(self._toolset._repo.ensure_workspace())
        snippets = self._search.search(workspace, content)

        if snippets:
            snippet_text = "\n".join(snippets)
            prompt = (
                f"Store the following memory:\n\n{content}\n\n"
                f"Pre-filtered snippets of existing related content "
                f"(format: [filename] matching line):\n{snippet_text}"
            )
        else:
            prompt = f"Store the following memory:\n\n{content}"

        response = self._agent.run(prompt)
        commit_msg = _extract_commit_message(response)
        self._toolset.sync(message=commit_msg)

    def remove(self) -> None:
        """Clear all stored memory."""
        remove_agent = Agent(
            model=self._model,
            tools=[self._toolset.forget],
            instructions=_REMOVE_INSTRUCTIONS,
        )
        remove_agent.run("Clear all memory.")
        self._toolset.sync(message="forget memory")
