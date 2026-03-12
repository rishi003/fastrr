# Memory History API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Git-backed `history(user_id, limit=...)` API that returns commit metadata, changed files, and deterministic human-readable memory change summaries.

**Architecture:** Extend `RepoManager` with a history read contract, implement it in `GitRepoManager` using branch commit traversal + diff metadata, and expose a typed `Fastrr.history()` client method that maps repo events to public API models. Keep existing `remember`, `recall`, and `forget` behavior unchanged.

**Tech Stack:** Python 3.12, GitPython, pytest.

---

### Task 1: Add Public History Types and Repo Contract

**Files:**
- Create: `src/fastrr/history.py`
- Modify: `src/fastrr/services/repo_manager/base.py`
- Modify: `src/fastrr/services/repo_manager/__init__.py`
- Modify: `src/fastrr/__init__.py`
- Test: `tests/test_client.py`

**Step 1: Write failing test for public history type exposure**

```python
from fastrr import MemoryHistoryEvent


def test_memory_history_event_importable() -> None:
    event = MemoryHistoryEvent(
        commit="abc123",
        timestamp="2026-03-11T00:00:00Z",
        message="remember",
        changed_files=["preferences.md"],
        summary="added memory to preferences.md",
    )
    assert event.commit == "abc123"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_client.py::test_memory_history_event_importable -v`
Expected: FAIL with import error for `MemoryHistoryEvent`.

**Step 3: Add minimal history models and protocol contracts**

```python
# src/fastrr/history.py
from dataclasses import dataclass


@dataclass(frozen=True)
class RepoHistoryEntry:
    commit: str
    timestamp: str
    message: str
    changed_files: list[str]
    diff_text: str


@dataclass(frozen=True)
class MemoryHistoryEvent:
    commit: str
    timestamp: str
    message: str
    changed_files: list[str]
    summary: str
```

```python
# src/fastrr/services/repo_manager/base.py
@abstractmethod
def get_user_history(self, user_id: str, limit: int) -> list[RepoHistoryEntry]:
    """Return newest-first commit history for one user branch."""
    ...
```

**Step 4: Export the new type**

```python
# src/fastrr/__init__.py
from fastrr.history import MemoryHistoryEvent
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_client.py::test_memory_history_event_importable -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add src/fastrr/history.py src/fastrr/services/repo_manager/base.py src/fastrr/services/repo_manager/__init__.py src/fastrr/__init__.py tests/test_client.py
git commit -m "feat: add history domain models and repo contract"
```

### Task 2: Implement GitRepoManager History Retrieval

**Files:**
- Modify: `src/fastrr/services/repo_manager/git_repo_manager.py`
- Test: `tests/test_repo_manager.py`

**Step 1: Write failing repo-manager history tests**

```python
def test_get_user_history_newest_first(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_user_worktree("alice")
    path = git_repo_manager.get_worktree_path("alice")
    (path / "a.md").write_text("first")
    git_repo_manager.sync_user("alice", "first commit")
    (path / "a.md").write_text("second")
    git_repo_manager.sync_user("alice", "second commit")

    events = git_repo_manager.get_user_history("alice", limit=10)
    assert len(events) == 2
    assert events[0].message == "second commit"
    assert events[1].message == "first commit"
```

```python
def test_get_user_history_missing_branch_returns_empty(
    git_repo_manager: GitRepoManager,
) -> None:
    assert git_repo_manager.get_user_history("missing", limit=10) == []
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_repo_manager.py::test_get_user_history_newest_first tests/test_repo_manager.py::test_get_user_history_missing_branch_returns_empty -v`
Expected: FAIL because `get_user_history` is not implemented.

**Step 3: Implement minimal Git history retrieval**

```python
def get_user_history(self, user_id: str, limit: int) -> list[RepoHistoryEntry]:
    branch = self._user_branch(user_id)
    if not any(h.name == branch for h in self.repo.heads):
        return []

    commits = list(self.repo.iter_commits(branch, max_count=limit))
    entries: list[RepoHistoryEntry] = []
    for commit in commits:
        changed_files = list(commit.stats.files.keys())
        parent = commit.parents[0] if commit.parents else None
        diff_text = commit.diff(parent, create_patch=True) if parent else commit.diff(NULL_TREE, create_patch=True)
        entries.append(
            RepoHistoryEntry(
                commit=commit.hexsha,
                timestamp=commit.committed_datetime.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                message=commit.message.strip(),
                changed_files=changed_files,
                diff_text="\n".join(d.diff.decode("utf-8", errors="ignore") for d in diff_text),
            )
        )
    return entries
```

**Step 4: Add `limit` validation**

```python
if limit <= 0:
    raise ValueError("limit must be > 0")
limit = min(limit, 200)
```

**Step 5: Run focused tests**

Run: `pytest tests/test_repo_manager.py::test_get_user_history_newest_first tests/test_repo_manager.py::test_get_user_history_missing_branch_returns_empty -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add src/fastrr/services/repo_manager/git_repo_manager.py tests/test_repo_manager.py
git commit -m "feat: add git user history retrieval"
```

### Task 3: Add Deterministic Summary Utility and Client API

**Files:**
- Create: `src/fastrr/history_summary.py`
- Modify: `src/fastrr/client.py`
- Test: `tests/test_client.py`

**Step 1: Write failing tests for `Fastrr.history()`**

```python
def test_history_limit_validation(memory: Fastrr) -> None:
    with pytest.raises(ValueError, match="limit must be > 0"):
        memory.history("alice", limit=0)
```

```python
def test_history_maps_repo_entries(fake_repo_manager, mock_model, mock_agent_run) -> None:
    # fake repo manager should return one RepoHistoryEntry from get_user_history
    memory = Fastrr(
        storage_path=Path("/tmp/s"),
        worktree_root=Path("/tmp/w"),
        repo_manager=fake_repo_manager,
        model=mock_model,
    )
    events = memory.history("alice", limit=5)
    assert events[0].changed_files == ["preferences.md"]
    assert "updated" in events[0].summary.lower()
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_client.py::test_history_limit_validation tests/test_client.py::test_history_maps_repo_entries -v`
Expected: FAIL because `history()` does not exist.

**Step 3: Add deterministic summary function**

```python
def summarize_memory_change(message: str, changed_files: list[str], diff_text: str) -> str:
    if not changed_files:
        return "repository update"
    if len(changed_files) > 1:
        return f"updated {len(changed_files)} memory files"
    file_name = changed_files[0]
    if "\n+ " in diff_text and "\n- " not in diff_text:
        return f"added memory to {file_name}"
    if "\n- " in diff_text and "\n+ " not in diff_text:
        return f"removed memory from {file_name}"
    return f"updated memory in {file_name}"
```

**Step 4: Add `history()` method to client**

```python
def history(self, user_id: str, limit: int = 20) -> list[MemoryHistoryEvent]:
    if limit <= 0:
        raise ValueError("limit must be > 0")
    entries = self._repo.get_user_history(user_id, limit=limit)
    return [
        MemoryHistoryEvent(
            commit=e.commit,
            timestamp=e.timestamp,
            message=e.message,
            changed_files=e.changed_files,
            summary=summarize_memory_change(e.message, e.changed_files, e.diff_text),
        )
        for e in entries
    ]
```

**Step 5: Run focused tests**

Run: `pytest tests/test_client.py::test_history_limit_validation tests/test_client.py::test_history_maps_repo_entries -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add src/fastrr/history_summary.py src/fastrr/client.py tests/test_client.py tests/conftest.py
git commit -m "feat: expose memory history API with deterministic summaries"
```

### Task 4: Harden Tests and Update Docs

**Files:**
- Modify: `tests/test_repo_manager.py`
- Modify: `tests/test_client.py`
- Modify: `README.md`
- Modify: `docs/USAGE.md`

**Step 1: Add edge-case tests**

```python
def test_get_user_history_limit_hard_cap(git_repo_manager: GitRepoManager) -> None:
    # create >200 commits for one user, request 500, assert len <= 200
    ...
```

```python
def test_history_empty_for_unknown_user(memory: Fastrr) -> None:
    assert memory.history("missing", limit=10) == []
```

**Step 2: Run the new tests first**

Run: `pytest tests/test_repo_manager.py -k history -v`
Expected: PASS.

Run: `pytest tests/test_client.py -k history -v`
Expected: PASS.

**Step 3: Document the new API**

```markdown
### Inspect memory history

```python
events = memory.history("alice", limit=20)
for event in events:
    print(event.timestamp, event.summary)
```
```

**Step 4: Run full test suite**

Run: `pytest -v`
Expected: PASS with no regressions.

**Step 5: Commit**

```bash
git add tests/test_repo_manager.py tests/test_client.py README.md docs/USAGE.md
git commit -m "docs: add memory history usage and edge-case coverage"
```

### Task 5: Optional Follow-up Prep for Rollback

**Files:**
- Modify: `docs/ARCHITECTURE.md`

**Step 1: Add non-blocking design note**

```markdown
Future extension: `rollback(user_id, to=commit)` can reuse `get_user_history` and branch checkout/reset semantics with safe guards.
```

**Step 2: Run docs checks (if any)**

Run: `pytest -q`
Expected: PASS.

**Step 3: Commit**

```bash
git add docs/ARCHITECTURE.md
git commit -m "docs: note rollback extension on history foundation"
```
