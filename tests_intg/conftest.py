"""Shared pytest fixtures for fastrr integration tests.

Uses real GitRepoManager and real Ollama (model qwen3.5:9b by default).
Skips all client e2e tests when Ollama is unavailable or the model is not present.
"""

import json
import os
import urllib.request
from pathlib import Path

import pytest

from fastrr import Fastrr
from fastrr.core.config import FastrrConfig


def pytest_configure(config: pytest.Config) -> None:
    """Register the integration marker."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration (requires Ollama with configured model).",
    )


def _ollama_available() -> tuple[bool, str]:
    """Return (available, reason). If not available, reason describes why."""
    cfg = FastrrConfig()
    if cfg.provider != "ollama":
        return False, "provider is not ollama"
    model = os.environ.get("FASTRR_MODEL", "qwen3.5:9b")
    try:
        req = urllib.request.Request(
            f"{cfg.ollama_host.rstrip('/')}/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        return False, f"Ollama unreachable: {e}"
    models = data.get("models") or []
    names = []
    for m in models:
        name = m.get("name") if isinstance(m, dict) else getattr(m, "name", None)
        if name:
            names.append(name)
    for n in names:
        if n == model or n.startswith(model + ":"):
            return True, ""
    return False, f"model {model!r} not found (available: {names})"


@pytest.fixture(scope="session")
def ollama_available() -> None:
    """Skip the entire integration run if Ollama is not available or model is missing."""
    ok, reason = _ollama_available()
    if not ok:
        pytest.skip(f"Ollama not available: {reason}")


@pytest.fixture
def fastrr_config() -> FastrrConfig:
    """FastrrConfig for integration tests: Ollama with qwen3.5:9b (or FASTRR_MODEL)."""
    model = os.environ.get("FASTRR_MODEL", "qwen3.5:9b")
    return FastrrConfig(provider="ollama", model=model)


@pytest.fixture
def fastrr_client(tmp_path: Path, ollama_available: None, fastrr_config: FastrrConfig) -> Fastrr:
    """Fastrr client with real Git repo and real Ollama; isolated per test via tmp_path."""
    storage_path = tmp_path / "repo"
    return Fastrr(
        storage_path=storage_path,
        config=fastrr_config,
    )
