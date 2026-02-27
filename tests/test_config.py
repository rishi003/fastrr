"""Unit tests for FastrrConfig."""

import pytest

from fastrr.core.config import FastrrConfig


def test_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defaults when env vars are set to expected values (or unset)."""
    monkeypatch.delenv("FASTRR_PROVIDER", raising=False)
    monkeypatch.delenv("FASTRR_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    config = FastrrConfig()
    assert config.provider == "ollama"
    assert config.model == "llama3.2"
    assert config.ollama_host == "http://localhost:11434"


def test_config_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env vars override defaults."""
    monkeypatch.setenv("FASTRR_PROVIDER", "openrouter")
    monkeypatch.setenv("FASTRR_MODEL", "openai/gpt-4o")
    config = FastrrConfig()
    assert config.provider == "openrouter"
    assert config.model == "openai/gpt-4o"
