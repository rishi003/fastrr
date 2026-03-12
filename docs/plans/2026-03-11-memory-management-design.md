# Memory History API Design

Date: 2026-03-11
Status: Approved for planning

## Goal

Improve memory management ergonomics for this Git-based memory library by exposing user-visible memory history. The storage already keeps history in Git branches, but the product lacks an API to access it.

## Scope

First release adds:

- `history(user_id, limit=...)` on `Fastrr`
- Git-backed history retrieval from `user/{user_id}` branch
- Deterministic, human-readable change summaries

Out of scope for this release:

- Rollback API
- LLM-generated summaries
- New retention/decay policies

## API Design

Add public method:

- `Fastrr.history(user_id: str, limit: int = 20) -> list[MemoryHistoryEvent]`

Add response model:

- `MemoryHistoryEvent`
  - `commit: str`
  - `timestamp: str` (ISO-8601 UTC)
  - `message: str`
  - `changed_files: list[str]`
  - `summary: str`

Behavior:

- Newest-first history
- Bounded by `limit`
- Read-only (no behavior changes to `remember`, `recall`, `forget`)

## Architecture

### 1) Repo layer

Extend `RepoManager` with:

- `get_user_history(user_id: str, limit: int) -> list[...]`

`GitRepoManager` implementation responsibilities:

- Read commits from `user/{user_id}` branch
- Collect commit hash, author time, message
- Collect changed files per commit
- Collect compact diff context for summary heuristics

### 2) Client layer

`Fastrr.history()`:

- Validates `limit`
- Calls repo manager history method
- Maps repo records to public `MemoryHistoryEvent`

### 3) Summary generation

Add deterministic summary utility (no LLM dependency):

- Append-like change: "added memory to `<file>`"
- Replacement-like change: "updated memory in `<file>`"
- Delete-like change: "removed memory file `<file>`"
- Multi-file change: "updated N memory files"
- Fallback: "memory update in `<file1>, <file2>`"

## Error Handling

- Missing user/branch: return `[]`
- `limit <= 0`: raise `ValueError("limit must be > 0")`
- Large limits: enforce internal safe cap (e.g. 200)
- Unsupported or binary diff: fallback to generic summary
- Non-memory commits: include with generic summary

## Testing Strategy

### Unit tests: repo history

- Newest-first ordering
- `limit` behavior
- Metadata and changed-files extraction
- Missing branch returns empty

### Unit tests: summary utility

- Added/updated/removed detection
- Multi-file aggregation
- Fallback behavior

### Client tests

- Input validation
- Mapping to `MemoryHistoryEvent`
- Fake repo manager compatibility

### Integration test

- Two `remember()` writes for one user
- `history()` returns corresponding events and summaries

## Chosen Approach and Trade-offs

Selected: Git-first history + deterministic summary layer.

Why:

- Works with existing architecture
- Deterministic and test-friendly
- No model dependency, cost, or latency risk

Trade-off:

- Summary text is less expressive than LLM-generated narratives, but predictable and robust.

## Future Extensions

- Add `rollback(user_id, to=...)`
- Optional LLM summary enhancement with deterministic fallback
- Structured memory event journal for richer domain analytics
