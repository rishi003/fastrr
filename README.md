# Fastrr

A **semantic memory layer** for AI applications: one versioned workspace on disk.
Your app calls `remember`, `recall`, and `forget`; LLM-powered agents handle how
memories are stored and retrieved.

- **Single memory namespace**: One workspace per application instance.
- **Versioned**: Backed by Git commits, so you get history and rollback.
- **Agent-driven**: Writer and Reader agents (via [Agno](https://github.com/agno-agi/agno)) organise and retrieve memory intelligently.
- **Library-first**: Install and call from any Python app; no server required.

## Install

```bash
uv add fastrr
# or
pip install fastrr
```

## Quick Start

```python
from fastrr import Fastrr

# Point to a folder on disk (created if missing)
memory = Fastrr(
    storage_path="./data/repo",
)

# Store a memory — the writer agent decides how to organise it
memory.remember("Prefers concise bullet-point answers.")

# Retrieve memory relevant to a query
context = memory.recall(query="communication style")

# Or summarise all memory
summary = memory.recall()

# Remove all memory
memory.forget()
```

## API

| Method | Description |
|--------|-------------|
| `remember(content)` | Persist a memory. The writer agent stores and organises it on disk. |
| `recall(query=None)` | Retrieve memory relevant to `query`, or summarise all memory if no query given. |
| `history(limit=20)` | Return newest-first memory history events with commit metadata, changed files, and deterministic summaries. |
| `forget()` | Remove all stored memory. |

Storage is local only (no remote). You can plug in a custom backend by implementing the `RepoManager` protocol and passing it to `Fastrr(repo_manager=...)`.

## Configuration

Fastrr uses LLM agents for memory operations. Configure the provider via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `FASTRR_PROVIDER` | `ollama` or `openrouter` | `ollama` |
| `FASTRR_MODEL` | Model ID (e.g. `llama3.2`, `openai/gpt-4o`) | `llama3.2` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OPENROUTER_API_KEY` | Required when using `openrouter` | — |

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for details.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — How Fastrr works under the hood
- [Configuration](docs/CONFIGURATION.md) — LLM providers and environment variables
- [Usage](docs/USAGE.md) — Detailed usage examples and extensibility
- [Development](docs/DEVELOPMENT.md) — Contributing, testing, and running locally
- [Evals](evals/README.md) — Dataset download and memory evaluation
