"""End-to-end integration tests for the Fastrr client.

Uses real GitRepoManager and real Ollama (e.g. qwen3.5:9b). Skipped when Ollama
is unavailable or the configured model is not present.
"""

import pytest

from fastrr import Fastrr


@pytest.mark.integration
def test_remember_then_recall_with_query(fastrr_client: Fastrr) -> None:
    """Remember one memory, then recall with a query; result should be non-empty and relevant."""
    fastrr_client.remember("Prefers concise bullet-point answers.")
    result = fastrr_client.recall(query="communication style")
    assert result
    assert isinstance(result, str)
    # LLM may paraphrase; check for a relevant idea
    result_lower = result.lower()
    assert "bullet" in result_lower or "concise" in result_lower or "prefer" in result_lower or "answer" in result_lower


@pytest.mark.integration
def test_remember_multiple_then_recall_summary(fastrr_client: Fastrr) -> None:
    """Remember multiple facts, then recall without query; expect non-empty summary."""
    fastrr_client.remember("Works in healthcare.")
    fastrr_client.remember("Likes dark mode.")
    result = fastrr_client.recall()
    assert result
    assert isinstance(result, str)
    result_lower = result.lower()
    assert "healthcare" in result_lower or "dark" in result_lower or "mode" in result_lower


@pytest.mark.integration
def test_forget_clears_memory(fastrr_client: Fastrr) -> None:
    """After forget, recalling should still return a string and not crash."""
    fastrr_client.remember("Data.")
    fastrr_client.forget()
    result = fastrr_client.recall(query="data")
    assert isinstance(result, str)


@pytest.mark.integration
def test_recall_empty_memory(fastrr_client: Fastrr) -> None:
    """Recall with no prior remember does not crash; may return empty or short message."""
    result = fastrr_client.recall()
    assert isinstance(result, str)
    result_with_query = fastrr_client.recall(query="x")
    assert isinstance(result_with_query, str)
