# Development

## Setup

```bash
# Clone and install in editable mode
git clone <repo>
cd fastrr
uv sync
# or: pip install -e .
```

Requires Python 3.12+.

## Running Tests

```bash
pytest
```

Tests use `pythonpath = ["src"]` so the package is found without installing. The `FakeRepoManager` fixture provides an in-memory storage backend (no Git) for fast, isolated tests.

## Project Structure

```
fastrr/
├── main.py                 # CLI entry (minimal)
├── pyproject.toml
├── src/fastrr/
│   ├── __init__.py         # Public exports
│   ├── client.py           # Fastrr class
│   ├── agents/
│   │   ├── reader.py       # ReaderAgent
│   │   ├── writer.py       # WriterAgent
│   │   ├── search.py       # SearchStrategy, RegexSearch
│   │   └── toolset.py      # MemoryToolset
│   ├── core/config/
│   │   └── config.py       # FastrrConfig
│   └── services/repo_manager/
│       ├── base.py         # RepoManager protocol
│       └── git_repo_manager.py
└── tests/
    ├── conftest.py         # FakeRepoManager fixture
    ├── test_client.py
    ├── test_config.py
    ├── test_repo_manager.py
    ├── test_search.py
    └── test_toolset.py
```

## Testing with FakeRepoManager

For tests that don't need Git, use the `FakeRepoManager`:

```python
from pathlib import Path
from fastrr import Fastrr
from fastrr.services.repo_manager import RepoManager

class FakeRepoManager(RepoManager):
    # In-memory implementation; sync_user is a no-op
    ...

@pytest.fixture
def fake_repo_manager(tmp_path):
    return FakeRepoManager(tmp_path)

def test_remember(memory_with_fake_repo):
    memory_with_fake_repo.remember("alice", "test")
    # ...
```

See `tests/conftest.py` for the full fixture.

## Evals

The `evals/` directory contains evaluation datasets (e.g. `locomo10.json`). See `evals/README.md` for how to run evals (when implemented).

## Dependencies

| Package | Purpose |
|---------|---------|
| `agno` | LLM agents (Reader, Writer) |
| `gitpython` | Git worktrees |
| `pydantic` / `pydantic-settings` | Config |
| `pytest` | Tests |
| `redis` / `redisvl` | Declared for future semantic search |
