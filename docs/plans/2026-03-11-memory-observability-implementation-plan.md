# Memory Observability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add full observability for user memory with richer history metadata, commit graph APIs, snapshots, and anomaly detection while preserving existing `remember`, `recall`, and `forget` behavior.

**Architecture:** Extend history domain models, then add read-only graph/snapshot/anomaly repo contracts in `RepoManager` and implement them in `GitRepoManager`. Expose these capabilities through new `Fastrr` client methods and keep deterministic output and typed errors. Build incrementally via TDD with focused tests per capability.

**Tech Stack:** Python 3.12, GitPython, pytest.

---

### Task 1: Add Observation Domain Models

**Files:**
- Modify: `src/fastrr/history.py`
- Modify: `src/fastrr/__init__.py`
- Test: `tests/test_client.py`

**Step 1: Write failing test for new model exports**

```python
from fastrr import MemoryGraphNode, MemorySnapshot, MemoryAnomaly


def test_observation_models_importable() -> None:
    node = MemoryGraphNode(commit="abc", parents=["p1"], children=["c1"], depth=1)
    snap = MemorySnapshot(commit="abc", files={"preferences.md": "hello"})
    anomaly = MemoryAnomaly(
        type="write_burst",
        severity="warn",
        evidence={"commits_per_hour": 120},
        suggested_action="review recent writes",
    )
    assert node.commit == "abc"
    assert "preferences.md" in snap.files
    assert anomaly.severity == "warn"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_client.py::test_observation_models_importable -v`  
Expected: FAIL with import error for missing observation models.

**Step 3: Add minimal observation dataclasses**

```python
# src/fastrr/history.py
@dataclass(frozen=True)
class MemoryGraphNode:
    commit: str
    parents: list[str]
    children: list[str]
    depth: int


@dataclass(frozen=True)
class MemorySnapshot:
    commit: str
    files: dict[str, str]


@dataclass(frozen=True)
class MemoryAnomaly:
    type: str
    severity: str
    evidence: dict[str, int | float | str]
    suggested_action: str
```

**Step 4: Export new models**

```python
# src/fastrr/__init__.py
from fastrr.history import MemoryAnomaly, MemoryGraphNode, MemorySnapshot
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_client.py::test_observation_models_importable -v`  
Expected: PASS.

**Step 6: Commit**

```bash
git add src/fastrr/history.py src/fastrr/__init__.py tests/test_client.py
git commit -m "feat: add memory observability domain models"
```

### Task 2: Extend RepoManager Contract for Graph/Snapshot APIs

**Files:**
- Modify: `src/fastrr/services/repo_manager/base.py`
- Modify: `src/fastrr/services/repo_manager/__init__.py`
- Test: `tests/test_repo_manager.py`

**Step 1: Write failing contract smoke test via fake manager**

```python
def test_repo_manager_observation_contract(fake_repo_manager) -> None:
    assert hasattr(fake_repo_manager, "get_user_lineage")
    assert hasattr(fake_repo_manager, "get_user_children")
    assert hasattr(fake_repo_manager, "get_user_leaves")
    assert hasattr(fake_repo_manager, "diff_user_commits")
    assert hasattr(fake_repo_manager, "snapshot_user_commit")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_repo_manager.py::test_repo_manager_observation_contract -v`  
Expected: FAIL due to missing methods on fake/contract implementation.

**Step 3: Add abstract methods to RepoManager**

```python
# src/fastrr/services/repo_manager/base.py
@abstractmethod
def get_user_lineage(self, user_id: str, commit: str | None, limit: int) -> list[str]:
    ...

@abstractmethod
def get_user_children(self, user_id: str, commit: str) -> list[str]:
    ...

@abstractmethod
def get_user_leaves(self, user_id: str) -> list[str]:
    ...

@abstractmethod
def diff_user_commits(
    self, user_id: str, from_commit: str, to_commit: str, patch: bool
) -> str:
    ...

@abstractmethod
def snapshot_user_commit(
    self, user_id: str, commit: str | None, files: list[str] | None
) -> tuple[str, dict[str, str]]:
    ...
```

**Step 4: Add placeholder implementations in fake repo manager fixture**

```python
# tests/conftest.py fake repo manager
def get_user_lineage(self, user_id, commit=None, limit=100): return []
def get_user_children(self, user_id, commit): return []
def get_user_leaves(self, user_id): return []
def diff_user_commits(self, user_id, from_commit, to_commit, patch=False): return ""
def snapshot_user_commit(self, user_id, commit=None, files=None): return ("", {})
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_repo_manager.py::test_repo_manager_observation_contract -v`  
Expected: PASS.

**Step 6: Commit**

```bash
git add src/fastrr/services/repo_manager/base.py src/fastrr/services/repo_manager/__init__.py tests/conftest.py tests/test_repo_manager.py
git commit -m "feat: add repo observation contract methods"
```

### Task 3: Implement Git Lineage, Children, Leaves, and Diff

**Files:**
- Modify: `src/fastrr/services/repo_manager/git_repo_manager.py`
- Test: `tests/test_repo_manager.py`

**Step 1: Write failing graph tests**

```python
def test_get_user_lineage_returns_newest_to_oldest(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_user_worktree("alice")
    path = git_repo_manager.get_worktree_path("alice")
    (path / "a.md").write_text("1")
    git_repo_manager.sync_user("alice", "c1")
    (path / "a.md").write_text("2")
    git_repo_manager.sync_user("alice", "c2")
    lineage = git_repo_manager.get_user_lineage("alice", commit=None, limit=10)
    assert len(lineage) == 2


def test_get_user_children_empty_for_leaf(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_user_worktree("alice")
    path = git_repo_manager.get_worktree_path("alice")
    (path / "a.md").write_text("1")
    git_repo_manager.sync_user("alice", "c1")
    head = git_repo_manager.get_user_history("alice", 1)[0].commit
    assert git_repo_manager.get_user_children("alice", head) == []
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_repo_manager.py::test_get_user_lineage_returns_newest_to_oldest tests/test_repo_manager.py::test_get_user_children_empty_for_leaf -v`  
Expected: FAIL because methods are not implemented.

**Step 3: Implement methods in GitRepoManager**

```python
def get_user_lineage(self, user_id: str, commit: str | None, limit: int) -> list[str]:
    branch = self._user_branch(user_id)
    if branch not in (h.name for h in self.repo.heads):
        return []
    target = commit or branch
    commits = list(self.repo.iter_commits(target, max_count=min(limit, 200)))
    return [c.hexsha for c in commits]

def get_user_children(self, user_id: str, commit: str) -> list[str]:
    branch = self._user_branch(user_id)
    if branch not in (h.name for h in self.repo.heads):
        return []
    rev = f"{branch} --all"
    children = self.repo.git.rev_list("--all", "--children", "--max-count=500").splitlines()
    for row in children:
        parts = row.split()
        if parts and parts[0] == commit:
            return parts[1:]
    return []

def get_user_leaves(self, user_id: str) -> list[str]:
    branch = self._user_branch(user_id)
    if branch not in (h.name for h in self.repo.heads):
        return []
    return [self.repo.commit(branch).hexsha]

def diff_user_commits(self, user_id: str, from_commit: str, to_commit: str, patch: bool) -> str:
    _ = self._user_branch(user_id)  # keep signature user-scoped for future checks
    return self.repo.git.diff(from_commit, to_commit, "--patch" if patch else "--stat")
```

**Step 4: Add diff test**

```python
def test_diff_user_commits_returns_summary(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_user_worktree("alice")
    path = git_repo_manager.get_worktree_path("alice")
    (path / "a.md").write_text("one")
    git_repo_manager.sync_user("alice", "c1")
    (path / "a.md").write_text("two")
    git_repo_manager.sync_user("alice", "c2")
    events = git_repo_manager.get_user_history("alice", 2)
    diff = git_repo_manager.diff_user_commits("alice", events[1].commit, events[0].commit, patch=False)
    assert "a.md" in diff
```

**Step 5: Run focused tests**

Run: `pytest tests/test_repo_manager.py -k "lineage or children or diff_user_commits" -v`  
Expected: PASS.

**Step 6: Commit**

```bash
git add src/fastrr/services/repo_manager/git_repo_manager.py tests/test_repo_manager.py
git commit -m "feat: implement git graph and diff observation queries"
```

### Task 4: Implement Snapshot Retrieval with Safety Limits

**Files:**
- Modify: `src/fastrr/services/repo_manager/git_repo_manager.py`
- Test: `tests/test_repo_manager.py`

**Step 1: Write failing snapshot tests**

```python
def test_snapshot_user_commit_returns_file_content(git_repo_manager: GitRepoManager) -> None:
    git_repo_manager.ensure_user_worktree("alice")
    path = git_repo_manager.get_worktree_path("alice")
    (path / "profile.md").write_text("likes tea")
    git_repo_manager.sync_user("alice", "add profile")
    commit = git_repo_manager.get_user_history("alice", 1)[0].commit
    commit_hash, files = git_repo_manager.snapshot_user_commit("alice", commit=commit, files=None)
    assert commit_hash == commit
    assert files["profile.md"] == "likes tea"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_repo_manager.py::test_snapshot_user_commit_returns_file_content -v`  
Expected: FAIL because snapshot method is missing/incomplete.

**Step 3: Implement snapshot method with caps**

```python
def snapshot_user_commit(
    self, user_id: str, commit: str | None, files: list[str] | None
) -> tuple[str, dict[str, str]]:
    branch = self._user_branch(user_id)
    if branch not in (h.name for h in self.repo.heads):
        return ("", {})
    resolved = self.repo.commit(commit or branch)
    selected = set(files or [])
    out: dict[str, str] = {}
    for blob in resolved.tree.traverse():
        if blob.type != "blob":
            continue
        rel = blob.path
        if selected and rel not in selected:
            continue
        out[rel] = blob.data_stream.read().decode("utf-8", errors="ignore")
    return (resolved.hexsha, dict(sorted(out.items())))
```

**Step 4: Add file-filter test**

```python
def test_snapshot_user_commit_respects_file_filter(git_repo_manager: GitRepoManager) -> None:
    # setup with profile.md + notes.md
    # assert only requested file appears
    ...
```

**Step 5: Run focused tests**

Run: `pytest tests/test_repo_manager.py -k "snapshot_user_commit" -v`  
Expected: PASS.

**Step 6: Commit**

```bash
git add src/fastrr/services/repo_manager/git_repo_manager.py tests/test_repo_manager.py
git commit -m "feat: add git snapshot retrieval for user commits"
```

### Task 5: Add Client APIs for Graph, Diff, Snapshot

**Files:**
- Modify: `src/fastrr/client.py`
- Test: `tests/test_client.py`

**Step 1: Write failing client tests**

```python
def test_lineage_calls_repo_and_returns_hashes(memory: Fastrr, fake_repo_manager) -> None:
    fake_repo_manager.get_user_lineage = MagicMock(return_value=["c2", "c1"])
    assert memory.lineage("alice") == ["c2", "c1"]


def test_snapshot_maps_repo_output(memory: Fastrr, fake_repo_manager) -> None:
    fake_repo_manager.snapshot_user_commit = MagicMock(
        return_value=("abc", {"preferences.md": "hello"})
    )
    snap = memory.snapshot("alice")
    assert snap.commit == "abc"
    assert snap.files["preferences.md"] == "hello"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_client.py::test_lineage_calls_repo_and_returns_hashes tests/test_client.py::test_snapshot_maps_repo_output -v`  
Expected: FAIL because client methods do not exist.

**Step 3: Add client methods**

```python
def lineage(self, user_id: str, commit: str | None = None, limit: int = 100) -> list[str]:
    if limit <= 0:
        raise ValueError("limit must be > 0")
    return self._repo.get_user_lineage(user_id, commit=commit, limit=limit)

def children(self, user_id: str, commit: str) -> list[str]:
    return self._repo.get_user_children(user_id, commit)

def leaves(self, user_id: str) -> list[str]:
    return self._repo.get_user_leaves(user_id)

def diff(self, user_id: str, from_commit: str, to_commit: str, patch: bool = False) -> str:
    return self._repo.diff_user_commits(user_id, from_commit, to_commit, patch=patch)

def snapshot(
    self, user_id: str, commit: str | None = None, files: list[str] | None = None
) -> MemorySnapshot:
    resolved, out = self._repo.snapshot_user_commit(user_id, commit=commit, files=files)
    return MemorySnapshot(commit=resolved, files=out)
```

**Step 4: Run focused tests**

Run: `pytest tests/test_client.py -k "lineage or children or leaves or snapshot or diff" -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/fastrr/client.py tests/test_client.py
git commit -m "feat: expose graph diff and snapshot APIs on client"
```

### Task 6: Add Deterministic Anomaly Detection Utilities

**Files:**
- Create: `src/fastrr/anomalies.py`
- Modify: `src/fastrr/client.py`
- Test: `tests/test_history_summary.py`
- Test: `tests/test_client.py`

**Step 1: Write failing anomaly tests**

```python
from fastrr.anomalies import detect_anomalies


def test_detect_anomalies_flags_delete_heavy_change() -> None:
    events = [
        {"commit": "a", "insertions": 2, "deletions": 20, "changed_files": ["prefs.md"]}
    ]
    anomalies = detect_anomalies(events)
    assert any(a.type == "delete_heavy_change" for a in anomalies)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_history_summary.py::test_detect_anomalies_flags_delete_heavy_change -v`  
Expected: FAIL with module/function missing.

**Step 3: Implement minimal deterministic detectors**

```python
# src/fastrr/anomalies.py
def detect_anomalies(events: list[dict]) -> list[MemoryAnomaly]:
    out: list[MemoryAnomaly] = []
    for e in events:
        ins = int(e.get("insertions", 0))
        dels = int(e.get("deletions", 0))
        total = max(ins + dels, 1)
        if dels / total >= 0.8 and total >= 10:
            out.append(
                MemoryAnomaly(
                    type="delete_heavy_change",
                    severity="warn",
                    evidence={"insertions": ins, "deletions": dels},
                    suggested_action="review this commit diff",
                )
            )
    return out
```

**Step 4: Add client anomaly method**

```python
def anomalies(self, user_id: str, limit: int = 100) -> list[MemoryAnomaly]:
    events = self.history(user_id, limit=limit)
    raw = [{"commit": e.commit, "insertions": 0, "deletions": 0, "changed_files": e.changed_files} for e in events]
    return detect_anomalies(raw)
```

**Step 5: Run focused tests**

Run: `pytest tests/test_history_summary.py::test_detect_anomalies_flags_delete_heavy_change tests/test_client.py -k anomalies -v`  
Expected: PASS.

**Step 6: Commit**

```bash
git add src/fastrr/anomalies.py src/fastrr/client.py tests/test_history_summary.py tests/test_client.py
git commit -m "feat: add deterministic memory anomaly detection"
```

### Task 7: Harden Edge Cases and Typed Errors

**Files:**
- Create: `src/fastrr/errors.py`
- Modify: `src/fastrr/services/repo_manager/git_repo_manager.py`
- Modify: `src/fastrr/client.py`
- Test: `tests/test_repo_manager.py`
- Test: `tests/test_client.py`

**Step 1: Write failing error-contract tests**

```python
def test_snapshot_unknown_user_raises_user_not_found(memory: Fastrr) -> None:
    with pytest.raises(UserNotFoundError):
        memory.snapshot("missing")
```

**Step 2: Run test to verify failure**

Run: `pytest tests/test_client.py::test_snapshot_unknown_user_raises_user_not_found -v`  
Expected: FAIL because typed error not implemented.

**Step 3: Add typed errors and wire them**

```python
class UserNotFoundError(Exception): ...
class CommitNotFoundError(Exception): ...
class InvalidRangeError(Exception): ...
class SnapshotTooLargeError(Exception): ...
class ObservationUnavailableError(Exception): ...
```

**Step 4: Add size cap behavior to snapshot and tests**

Run: `pytest tests/test_repo_manager.py -k "snapshot and limit" -v`  
Expected: PASS for cap and exception cases.

**Step 5: Commit**

```bash
git add src/fastrr/errors.py src/fastrr/services/repo_manager/git_repo_manager.py src/fastrr/client.py tests/test_repo_manager.py tests/test_client.py
git commit -m "fix: add typed observability errors and safety caps"
```

### Task 8: Documentation and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/USAGE.md`
- Modify: `docs/ARCHITECTURE.md`
- Test: `tests/test_client.py`
- Test: `tests/test_repo_manager.py`
- Test: `tests_intg/test_client_e2e.py`

**Step 1: Document new observability APIs with examples**

```markdown
events = memory.history("alice", limit=20)
lineage = memory.lineage("alice")
snap = memory.snapshot("alice")
```

**Step 2: Add/adjust integration test for observability**

```python
def test_observability_smoke(memory: Fastrr) -> None:
    memory.remember("alice", "prefers concise output")
    assert memory.history("alice", limit=10)
```

**Step 3: Run focused tests first**

Run: `pytest tests/test_repo_manager.py -k "history or lineage or snapshot or diff" -v`  
Expected: PASS.

Run: `pytest tests/test_client.py -k "history or lineage or children or leaves or diff or snapshot or anomalies" -v`  
Expected: PASS.

**Step 4: Run full suite**

Run: `pytest -v`  
Expected: PASS with no regressions.

**Step 5: Commit**

```bash
git add README.md docs/USAGE.md docs/ARCHITECTURE.md tests/test_repo_manager.py tests/test_client.py tests_intg/test_client_e2e.py
git commit -m "docs: add memory observability API usage and coverage"
```
