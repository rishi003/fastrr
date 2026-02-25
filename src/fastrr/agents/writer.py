"""WriterAgent: Agno agent responsible for storing and organising memory."""

from agno.agent import Agent
from agno.models.base import Model

from fastrr.agents.toolset import MemoryToolset

_WRITER_INSTRUCTIONS = """
You are a memory writer agent. Your job is to persist user memory to disk.

When asked to store a memory for a user:
1. Call list_files to see what files already exist in the workspace.
2. Decide the best file to store this memory in (e.g. "preferences.md",
   "history.jsonl", "facts.md") based on the content type and existing files.
3. If the file exists and the new content belongs with existing content, use
   append_file to add to it. If starting fresh, use write_file.
4. Always call sync after writing to persist changes.

Use short, clear filenames. Prefer markdown for prose notes, JSONL for
structured entries, and plain text for simple facts.
Never make up data. Only store what you are explicitly given.
""".strip()

_REMOVE_INSTRUCTIONS = """
You are a memory cleanup agent. Your job is to remove a user's workspace entirely.
Call remove_user with the given user_id to delete all their memory.
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
            description="Stores and organises per-user memory on disk.",
        )

    def store(self, user_id: str, content: str) -> None:
        """Ask the agent to store `content` in the user's workspace."""
        prompt = f"Store the following memory for user '{user_id}':\n\n{content}"
        self._agent.run(prompt)

    def remove(self, user_id: str) -> None:
        """Remove the user's workspace entirely."""
        remove_agent = Agent(
            model=self._model,
            tools=[self._toolset.remove_user],
            instructions=_REMOVE_INSTRUCTIONS,
        )
        remove_agent.run(f"Remove all memory for user '{user_id}'.")
