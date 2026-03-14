# Agent Prompt Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give WriterAgent a `read_file` tool and a SearchStrategy pre-filter so it can detect and update existing memory instead of blindly appending, and restructure both agent prompts into named execution phases for reliable LLM behaviour.

**Architecture:** `WriterAgent` gains a `search_strategy` parameter (defaulting to `RegexSearch`, mirroring `ReaderAgent`) and `read_file` in its tool list. `store()` runs the search before calling the agent, injecting snippets into the prompt. Both prompts are replaced with numbered phase blocks. `Fastrr.__init__` passes `search_strategy` to `WriterAgent` as well as `ReaderAgent`.

**Tech Stack:** Python 3.11+, pytest, unittest.mock, agno

---

## Task 1: Add `search_strategy` to `WriterAgent` and give it `read_file`

**Files:**
- Modify: `src/fastrr/agents/writer.py`
- Create: `tests/test_agents.py`

---

**Step 1: Write the failing tests**

Create `tests/test_agents.py` with:

```python
"""Unit tests for WriterAgent and ReaderAgent."""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from fastrr.agents.search import RegexSearch, SearchStrategy
from fastrr.agents.toolset import MemoryToolset
from fastrr.agents.writer import WriterAgent
from fastrr.agents.reader import ReaderAgent


@pytest.fixture
def fake_toolset(fake_repo_manager):
    return MemoryToolset(fake_repo_manager)


# ── WriterAgent ────────────────────────────────────────────────────────────────

class TestWriterAgentInit:
    def test_accepts_optional_search_strategy(self, fake_toolset, mock_model):
        strategy = MagicMock(spec=SearchStrategy)
        with patch("fastrr.agents.writer.Agent"):
            agent = WriterAgent(
                fake_toolset, mock_model,
                memory_files="",
                search_strategy=strategy,
            )
        assert agent._search is strategy

    def test_defaults_to_regex_search(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent"):
            agent = WriterAgent(fake_toolset, mock_model, memory_files="")
        assert isinstance(agent._search, RegexSearch)

    def test_agent_receives_read_and_write_tools(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="")
        tools_arg = MockAgent.call_args.kwargs["tools"]
        tool_names = [t.__name__ for t in tools_arg]
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "append_file" in tool_names


@pytest.fixture
def mock_model():
    return MagicMock()
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_agents.py -v
```

Expected: 3 failures — `WriterAgent.__init__` does not accept `search_strategy` and does not include `read_file` in tools.

---

**Step 3: Implement the minimal changes in `writer.py`**

Update `WriterAgent.__init__` signature and internals:

```python
from typing import Optional

from fastrr.agents.search import RegexSearch, SearchStrategy

class WriterAgent:
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
```

Add the two imports at the top of the file:
```python
from typing import Optional
from fastrr.agents.search import RegexSearch, SearchStrategy
```

**Step 4: Run to verify tests pass**

```bash
pytest tests/test_agents.py::TestWriterAgentInit -v
```

Expected: 3 PASS.

**Step 5: Commit**

```bash
git add src/fastrr/agents/writer.py tests/test_agents.py
git commit -m "feat: add search_strategy and read_file to WriterAgent"
```

---

## Task 2: Update `WriterAgent.store()` to inject pre-filtered snippets

**Files:**
- Modify: `src/fastrr/agents/writer.py`
- Modify: `tests/test_agents.py`

---

**Step 1: Write the failing tests**

Add to `tests/test_agents.py`:

```python
class TestWriterAgentStore:
    def test_store_calls_search_with_content(self, fake_toolset, mock_model, fake_repo_manager):
        fake_repo_manager.ensure_workspace()
        strategy = MagicMock(spec=SearchStrategy)
        strategy.search.return_value = []
        mock_agno = MagicMock()
        mock_agno.run.return_value = MagicMock(content="COMMIT: remember")
        with patch("fastrr.agents.writer.Agent", return_value=mock_agno):
            writer = WriterAgent(
                fake_toolset, mock_model,
                memory_files="",
                search_strategy=strategy,
            )
            writer.store("likes cats")
        strategy.search.assert_called_once()
        _, query = strategy.search.call_args.args
        assert "likes cats" in query

    def test_store_injects_snippets_into_prompt_when_found(self, fake_toolset, mock_model, fake_repo_manager):
        fake_repo_manager.ensure_workspace()
        strategy = MagicMock(spec=SearchStrategy)
        strategy.search.return_value = ["[preferences.md] likes dogs"]
        mock_agno = MagicMock()
        mock_agno.run.return_value = MagicMock(content="COMMIT: update pet preference")
        with patch("fastrr.agents.writer.Agent", return_value=mock_agno):
            writer = WriterAgent(
                fake_toolset, mock_model,
                memory_files="",
                search_strategy=strategy,
            )
            writer.store("likes cats")
        prompt = mock_agno.run.call_args.args[0]
        assert "[preferences.md] likes dogs" in prompt

    def test_store_omits_snippets_block_when_none_found(self, fake_toolset, mock_model, fake_repo_manager):
        fake_repo_manager.ensure_workspace()
        strategy = MagicMock(spec=SearchStrategy)
        strategy.search.return_value = []
        mock_agno = MagicMock()
        mock_agno.run.return_value = MagicMock(content="COMMIT: remember")
        with patch("fastrr.agents.writer.Agent", return_value=mock_agno):
            writer = WriterAgent(
                fake_toolset, mock_model,
                memory_files="",
                search_strategy=strategy,
            )
            writer.store("likes cats")
        prompt = mock_agno.run.call_args.args[0]
        assert "Pre-filtered snippets" not in prompt
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_agents.py::TestWriterAgentStore -v
```

Expected: all 3 fail — `store()` does not run a search.

---

**Step 3: Update `store()` in `writer.py`**

```python
from pathlib import Path

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
```

Add `from pathlib import Path` at the top if not already present.

**Step 4: Run to verify tests pass**

```bash
pytest tests/test_agents.py::TestWriterAgentStore -v
```

Expected: 3 PASS.

**Step 5: Run full test suite to check for regressions**

```bash
pytest -v
```

Expected: all existing tests still pass.

**Step 6: Commit**

```bash
git add src/fastrr/agents/writer.py tests/test_agents.py
git commit -m "feat: inject pre-filtered snippets into WriterAgent.store() prompt"
```

---

## Task 3: Rewrite WriterAgent prompt to 5-phase structure

**Files:**
- Modify: `src/fastrr/agents/writer.py`
- Modify: `tests/test_agents.py`

---

**Step 1: Write the failing tests**

Add to `tests/test_agents.py`:

```python
class TestWriterAgentPrompt:
    def test_prompt_contains_all_five_phases(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        for phase in ["PHASE 1", "PHASE 2", "PHASE 3", "PHASE 4", "PHASE 5"]:
            assert phase in instructions, f"Missing {phase} in writer instructions"

    def test_prompt_contains_decide_actions(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        for action in ["UPDATE", "WRITE NEW", "SKIP"]:
            assert action in instructions

    def test_prompt_contains_commit_prefix(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "COMMIT: " in instructions
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_agents.py::TestWriterAgentPrompt -v
```

Expected: all 3 fail — current prompt has no PHASE markers.

---

**Step 3: Replace `_WRITER_INSTRUCTIONS_TEMPLATE` in `writer.py`**

```python
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
```

**Step 4: Run to verify tests pass**

```bash
pytest tests/test_agents.py::TestWriterAgentPrompt -v
```

Expected: 3 PASS.

**Step 5: Run full suite**

```bash
pytest -v
```

Expected: all pass.

**Step 6: Commit**

```bash
git add src/fastrr/agents/writer.py tests/test_agents.py
git commit -m "feat: restructure WriterAgent prompt into 5 named phases"
```

---

## Task 4: Rewrite ReaderAgent prompt to 3-phase structure

**Files:**
- Modify: `src/fastrr/agents/reader.py`
- Modify: `tests/test_agents.py`

---

**Step 1: Write the failing tests**

Add to `tests/test_agents.py`:

```python
class TestReaderAgentPrompt:
    def test_prompt_contains_all_three_phases(self, fake_toolset, mock_model):
        with patch("fastrr.agents.reader.Agent") as MockAgent:
            ReaderAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        for phase in ["PHASE 1", "PHASE 2", "PHASE 3"]:
            assert phase in instructions, f"Missing {phase} in reader instructions"

    def test_prompt_explains_snippet_format(self, fake_toolset, mock_model):
        with patch("fastrr.agents.reader.Agent") as MockAgent:
            ReaderAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "[filename]" in instructions

    def test_prompt_contains_expand_guidance(self, fake_toolset, mock_model):
        with patch("fastrr.agents.reader.Agent") as MockAgent:
            ReaderAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "read_file" in instructions
        assert "sparse" in instructions.lower() or "fewer" in instructions.lower()
```

**Step 2: Run to verify they fail**

```bash
pytest tests/test_agents.py::TestReaderAgentPrompt -v
```

Expected: all 3 fail — current prompt has no PHASE markers and no snippet format explanation.

---

**Step 3: Replace `_READER_INSTRUCTIONS_TEMPLATE` in `reader.py`**

```python
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
```

**Step 4: Run to verify tests pass**

```bash
pytest tests/test_agents.py::TestReaderAgentPrompt -v
```

Expected: 3 PASS.

**Step 5: Run full suite**

```bash
pytest -v
```

Expected: all pass.

**Step 6: Commit**

```bash
git add src/fastrr/agents/reader.py tests/test_agents.py
git commit -m "feat: restructure ReaderAgent prompt into 3 named phases"
```

---

## Task 5: Pass `search_strategy` to `WriterAgent` in `Fastrr.__init__`

**Files:**
- Modify: `src/fastrr/client.py`
- Modify: `tests/test_client.py`

---

**Step 1: Write the failing test**

Add to `tests/test_client.py`:

```python
def test_fastrr_passes_search_strategy_to_writer(
    fake_repo_manager,
    mock_model: MagicMock,
) -> None:
    """search_strategy passed to Fastrr is forwarded to WriterAgent."""
    from fastrr.agents.search import SearchStrategy

    custom_strategy = MagicMock(spec=SearchStrategy)

    with patch("fastrr.agents.writer.Agent") as MockWriterAgent, \
         patch("fastrr.agents.reader.Agent"):
        Fastrr(
            storage_path=Path("/tmp/s"),
            repo_manager=fake_repo_manager,
            model=mock_model,
            search_strategy=custom_strategy,
        )
    # WriterAgent is constructed; check its _search is the custom strategy
    # We verify by inspecting the WriterAgent instance via the client
    # Reconstruct to access internal state:

with patch("fastrr.agents.writer.Agent"), patch("fastrr.agents.reader.Agent"):
    client = Fastrr(
        storage_path=Path("/tmp/s"),
        repo_manager=fake_repo_manager,
        model=mock_model,
        search_strategy=custom_strategy,
    )
assert client._writer._search is custom_strategy
```

Note: fix the indentation — this is one test function. Here is the corrected form:

```python
def test_fastrr_passes_search_strategy_to_writer(
    fake_repo_manager,
    mock_model: MagicMock,
) -> None:
    """search_strategy passed to Fastrr is forwarded to WriterAgent."""
    from fastrr.agents.search import SearchStrategy

    custom_strategy = MagicMock(spec=SearchStrategy)
    with patch("fastrr.agents.writer.Agent"), patch("fastrr.agents.reader.Agent"):
        client = Fastrr(
            storage_path=Path("/tmp/s"),
            repo_manager=fake_repo_manager,
            model=mock_model,
            search_strategy=custom_strategy,
        )
    assert client._writer._search is custom_strategy
```

**Step 2: Run to verify it fails**

```bash
pytest tests/test_client.py::test_fastrr_passes_search_strategy_to_writer -v
```

Expected: FAIL — `WriterAgent.__init__` is called without `search_strategy`.

---

**Step 3: Update `client.py` line 82**

Change:
```python
self._writer = WriterAgent(toolset, resolved_model, memory_files=memory_files_text)
```

To:
```python
self._writer = WriterAgent(
    toolset,
    resolved_model,
    memory_files=memory_files_text,
    search_strategy=search_strategy,
)
```

**Step 4: Run to verify test passes**

```bash
pytest tests/test_client.py::test_fastrr_passes_search_strategy_to_writer -v
```

Expected: PASS.

**Step 5: Run full suite**

```bash
pytest -v
```

Expected: all pass.

**Step 6: Commit**

```bash
git add src/fastrr/client.py tests/test_client.py
git commit -m "feat: forward search_strategy to WriterAgent in Fastrr.__init__"
```

---

## Task 6: Update ARCHITECTURE.md to reflect WriterAgent changes

**Files:**
- Modify: `docs/ARCHITECTURE.md`

---

**Step 1: Update the WriterAgent component description**

Find the `### WriterAgent` section in `docs/ARCHITECTURE.md`. Update it to:

```markdown
### WriterAgent

An [Agno](https://github.com/agno-agi/agno) agent that:

- **Store**: Receives content, runs `SearchStrategy.search()` to pre-filter
  existing related snippets, then calls the agent with those snippets injected
  into the prompt. The agent follows five named phases (ASSESS → READ → DECIDE
  → WRITE → COMMIT) to detect duplicates, update existing entries, or write new
  ones.
- **Remove**: Calls `forget` to clear memory files from the workspace.
```

Also update the data flow section for `remember(content)` to add the search step:

```markdown
### remember(content)

1. Client calls `WriterAgent.store(content)`.
2. `SearchStrategy.search(workspace, content)` pre-filters related snippets.
3. Agent receives the content and snippets (if any) and runs five phases:
   ASSESS (review snippets) → READ (read file if needed) → DECIDE
   (UPDATE / WRITE NEW / SKIP) → WRITE → COMMIT.
4. Agent calls `append_file`, `write_file`, or nothing depending on DECIDE.
5. `GitRepoManager` commits to the current branch.
```

Update the toolset table to clarify that WriterAgent now also uses `read_file`:

```markdown
| Agent | Read tools | Write tools |
|-------|------------|-------------|
| ReaderAgent | `read_file` | — |
| WriterAgent | `read_file` | `write_file`, `append_file`, `delete_file`, `sync`, `forget` |
```

**Step 2: Commit**

```bash
git add docs/ARCHITECTURE.md
git commit -m "docs: update ARCHITECTURE.md for WriterAgent search + read_file"
```

---

## Verification

After all tasks are complete, run:

```bash
pytest -v
```

All tests must pass. No new linter errors. Confirm the following behaviours manually with a quick smoke test if desired:

- `Fastrr.remember("likes cats")` followed by `Fastrr.remember("likes dogs")` should result in the agent detecting the prior pet preference entry and updating it rather than creating a second one.
- `Fastrr.recall("pet preference")` should return a single synthesised answer, not both raw entries.
