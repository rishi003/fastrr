"""WriterAgent: Agno agent responsible for storing and organising memory."""

from agno.agent import Agent
from agno.models.base import Model

from fastrr.agents.toolset import MemoryToolset

_WRITER_INSTRUCTIONS = """
You are a memory writer agent. Your job is to persist memory to disk.

When asked to store a memory:
1. Call list_files to see what files already exist in the workspace.
2. Decide the best file to store this memory in (e.g. "preferences.md",
   "history.jsonl", "facts.md") based on the content type and existing files.
3. If the file exists and the new content belongs with existing content, use
   append_file to add to it. If starting fresh, use write_file.

Use short, clear filenames. Prefer markdown for prose notes, JSONL for
structured entries, and plain text for simple facts.
Never make up data. Only store what you are explicitly given.

End your response with exactly one line that summarises what you stored, in
the imperative mood and under 72 characters. Prefix it with "COMMIT: ".
Example: COMMIT: add preferred communication style to preferences.md
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

    def __init__(self, toolset: MemoryToolset, model: Model):
        self._toolset = toolset
        self._model = model
        self._agent = Agent(
            model=model,
            tools=toolset.write_tools + [toolset.list_files],
            instructions=_WRITER_INSTRUCTIONS,
            description="Stores and organises memory on disk.",
        )

    def store(self, content: str) -> None:
        """Ask the agent to store `content` in the workspace."""
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
