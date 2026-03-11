# Usage

## Basic Usage

### remember

Store a memory for a user. The writer agent decides how to organise it (e.g. `preferences.md`, `history.jsonl`).

```python
from fastrr import Fastrr

memory = Fastrr(storage_path="./data/repo", worktree_root="./data/users")

memory.remember("alice", "Prefers concise bullet-point answers.")
memory.remember("alice", "Works in the healthcare industry.")
memory.remember("bob", "Likes dark mode and minimal UIs.")
```

### recall

Retrieve memory. With a `query`, returns content relevant to that query. Without a query, summarises all memory.

```python
# Query-specific recall
context = memory.recall("alice", query="communication style")
# → "Prefers concise bullet-point answers."

# Full summary
summary = memory.recall("alice")
# → Synthesised summary of all stored memory for alice
```

### forget

Remove all memory for a user.

```python
memory.forget("bob")
```

### list_users

List users with active workspaces.

```python
users = memory.list_users()  # ["alice", "bob", ...]
```

### history

Inspect memory changes for a user over time.

```python
events = memory.history("alice", limit=20)
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
    def get_worktree_path(self, user_id: str) -> Path: ...
    def ensure_user_worktree(self, user_id: str) -> str: ...
    def sync_user(self, user_id: str, message: str = "sync") -> None: ...
    def remove_user(self, user_id: str, *, wipe_remote: bool = False) -> None: ...
    def list_users(self) -> list[str]: ...
    def get_user_history(self, user_id: str, limit: int) -> list[RepoHistoryEntry]: ...

memory = Fastrr(
    storage_path="./data/repo",
    worktree_root="./data/users",
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
    worktree_root="./data/users",
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
    worktree_root="./data/users",
    model=Claude(id="claude-3-5-sonnet-20241022"),
)
```

## Public API

| Export | Description |
|--------|-------------|
| `Fastrr` | Main client class |
| `RepoManager` | Abstract protocol for storage backends |
| `GitRepoManager` | Default Git worktree implementation |
| `SearchStrategy` | Abstract search interface |
| `RegexSearch` | Default regex-based search |

```python
from fastrr import Fastrr, RepoManager, GitRepoManager, SearchStrategy, RegexSearch
```
