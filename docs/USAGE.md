# Usage

## Basic Usage

### remember

Store a memory. The writer agent decides how to organise it (e.g.
`preferences.md`, `history.jsonl`).

```python
from fastrr import Fastrr

memory = Fastrr(storage_path="./data/repo")

memory.remember("Prefers concise bullet-point answers.")
memory.remember("Works in the healthcare industry.")
memory.remember("Likes dark mode and minimal UIs.")
```

### recall

Retrieve memory. With a `query`, returns content relevant to that query. Without a query, summarises all memory.

```python
# Query-specific recall
context = memory.recall(query="communication style")
# → "Prefers concise bullet-point answers."

# Full summary
summary = memory.recall()
# → Synthesised summary of all stored memory
```

### forget

Remove all stored memory.

```python
memory.forget()
```

### history

Inspect memory changes over time.

```python
events = memory.history(limit=20)
for event in events:
    print(event.timestamp, event.summary)
```

## Extensibility

### Custom RepoManager

Implement the `RepoManager` protocol for custom storage backends:

```python
from pathlib import Path
from fastrr import Fastrr, RepoHistoryEntry
from fastrr.services.repo_manager import RepoManager

class MyRepoManager(RepoManager):
    def get_workspace_path(self) -> Path: ...
    def ensure_workspace(self) -> str: ...
    def sync(self, message: str = "sync") -> None: ...
    def forget(self) -> None: ...
    def get_history(self, limit: int) -> list[RepoHistoryEntry]: ...

memory = Fastrr(
    storage_path="./data/repo",
    repo_manager=MyRepoManager(...),
)
```

### Custom SearchStrategy

Plug in semantic or vector search:

```python
from pathlib import Path
from fastrr import Fastrr, SearchStrategy

class VectorSearch(SearchStrategy):
    def search(self, root: Path, query: str) -> list[str]:
        # Your vector/semantic search logic
        return ["snippet1", "snippet2"]

memory = Fastrr(
    storage_path="./data/repo",
    search_strategy=VectorSearch(),
)
```

### Custom Model

Use a different Agno model:

```python
from agno.models.anthropic import Claude
from fastrr import Fastrr

memory = Fastrr(
    storage_path="./data/repo",
    model=Claude(id="claude-3-5-sonnet-20241022"),
)
```

## Public API

| Export | Description |
|--------|-------------|
| `Fastrr` | Main client class |
| `RepoManager` | Abstract protocol for storage backends |
| `GitRepoManager` | Default single-repo Git implementation |
| `SearchStrategy` | Abstract search interface |
| `RegexSearch` | Default regex-based search |

```python
from fastrr import Fastrr, RepoManager, GitRepoManager, SearchStrategy, RegexSearch
```
