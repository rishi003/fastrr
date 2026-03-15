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


@pytest.fixture
def mock_model():
    return MagicMock()


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


class TestWriterAgentPrompt:
    def test_prompt_contains_all_five_phases(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        for phase in ["PHASE 1", "PHASE 2", "PHASE 3", "PHASE 4", "PHASE 5"]:
            assert phase in instructions, f"Missing {phase} in writer instructions"

    def test_prompt_plan_phase_contains_per_file_routing(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "PLAN" in instructions
        for action in ["append", "update", "skip"]:
            assert action in instructions

    def test_prompt_requires_distilled_content(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "verbatim" in instructions.lower()

    def test_prompt_allows_multiple_file_writes(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "multiple" in instructions.lower() or "zero, one" in instructions.lower()

    def test_prompt_contains_commit_prefix(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "COMMIT: " in instructions


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
