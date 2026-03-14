"""Unit tests for FastrrConfig."""

from pathlib import Path

import pytest

from fastrr.core.config import FastrrConfig


def test_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defaults when env vars are set to expected values (or unset)."""
    monkeypatch.delenv("FASTRR_PROVIDER", raising=False)
    monkeypatch.delenv("FASTRR_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("FASTRR_MEMORY_TEMPLATE_PATH", raising=False)
    config = FastrrConfig()
    assert config.provider == "ollama"
    assert config.model == "llama3.2"
    assert config.ollama_host == "http://localhost:11434"
    assert config.memory_template_path is None


def test_config_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env vars override defaults."""
    monkeypatch.setenv("FASTRR_PROVIDER", "openrouter")
    monkeypatch.setenv("FASTRR_MODEL", "openai/gpt-4o")
    config = FastrrConfig()
    assert config.provider == "openrouter"
    assert config.model == "openai/gpt-4o"


def test_config_memory_template_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """FASTRR_MEMORY_TEMPLATE_PATH is parsed as a Path."""
    template_file = tmp_path / "my_template.json"
    monkeypatch.setenv("FASTRR_MEMORY_TEMPLATE_PATH", str(template_file))
    config = FastrrConfig()
    assert config.memory_template_path == template_file
