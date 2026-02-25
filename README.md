# Fastrr

A **memory layer** for AI applications: per-user, versioned workspaces on disk. Use it from your app to give each user (or session) a persistent directory, read/write files there, and sync with a single call.

- **Per-user isolation**: One workspace per `user_id`; no cross-user access.
- **Versioned**: Backed by Git (one branch per user), so you get history and rollback.
- **Library-first**: Install and call from any Python app; no server required.

## Install

```bash
uv add fastrr
# or
pip install fastrr
```

## Use as a library

```python
from fastrr import Fastrr

# Point to a folder on disk (created if missing)
memory = Fastrr(
    storage_path="./data/repo",
    worktree_root="./data/users",
)

# Get (or create) this user's workspace; returns a path
path = memory.get_user_path("alice")

# Your app reads/writes any files under that path
(path / "context.json").write_text('{"last_topic": "greetings"}')
(path / "notes.md").write_text("# Session notes\n...")

# Persist changes
memory.sync("alice")

# Optional: list users, remove a user
memory.list_users()   # ["alice", ...]
memory.remove_user("bob")
```

## API

| Method | Description |
|--------|-------------|
| `get_user_path(user_id)` | Returns the path to the user's workspace (creates it if needed). |
| `sync(user_id, message="sync")` | Commits and persists changes in that workspace. |
| `list_users()` | List user IDs that have a workspace. |
| `remove_user(user_id)` | Remove the user's workspace and branch. |

Storage is local only (no remote). You can plug in a custom backend by implementing the `RepoManager` protocol and passing it to `Fastrr(repo_manager=...)`.
