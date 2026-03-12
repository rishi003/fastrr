# Memory Observability Design (Graph + Risk + Snapshot)

Date: 2026-03-11
Status: Approved for planning

## Goal

Provide full memory observability for each user by extending history into commit graph introspection, deterministic state snapshots, and anomaly detection. This enables auditability, debugging, and safer multi-agent memory workflows without changing write behavior.

## Scope

This design adds:

- Richer commit history metadata and optional risk annotations.
- Graph APIs for lineage, children, leaves, and cross-commit diff.
- Deterministic snapshot reconstruction at a commit.
- Anomaly detection based on commit and file-change patterns.

Out of scope for this release:

- Automatic rollback execution.
- LLM-generated anomaly explanations.
- Cross-user/global graph analytics.

## API Surface

The existing `Fastrr` write and read calls remain unchanged. Observability expands through enhanced history and new graph-style methods.

- `history(user_id, limit=20, include_diff_stats=True, include_risk=True)`
- `lineage(user_id, commit=None, limit=100)`
- `children(user_id, commit)`
- `leaves(user_id)`
- `diff(user_id, from_commit, to_commit, format="summary" | "patch")`
- `snapshot(user_id, commit=None, files=None)`
- `anomalies(user_id, window="7d", limit=100)`

Design intent:

- Default outputs are deterministic and JSON-serializable.
- All methods are read-only and cannot mutate user memory.
- `history(...)` remains the primary entry point; graph and risk APIs are opt-in.

## Architecture

### MemoryGraphService

Add a dedicated introspection service over existing repository storage:

- Reads commit graph and commit metadata for `user/{user_id}`.
- Produces normalized models for timeline, graph, and risk views.
- Computes snapshots by resolving file trees at a commit.
- Applies anomaly detectors in a post-processing step.

No write path is introduced in this service.

### Observation Models

- `MemoryCommitEvent`
  - `commit`, `timestamp`, `author`, `message`
  - `changed_files`, `insertions`, `deletions`
  - optional `risk_flags`
- `MemoryGraphNode`
  - `commit`, `parents`, `children`, `depth`
- `MemorySnapshot`
  - `commit`, `files` (path -> content or metadata)
- `MemoryAnomaly`
  - `type`, `severity`, `evidence`, `suggested_action`

## Data Flow

### History and Graph Reads

1. API call validates user, arguments, and limits.
2. Service resolves user branch/worktree.
3. Service gathers commit metadata and edges.
4. Service normalizes to stable, typed output.
5. Optional anomaly and risk augmentation runs.
6. Response returns deterministic ordering.

### Snapshot Reads

1. Resolve target commit (`HEAD` if omitted).
2. Materialize tree entries for that commit.
3. Apply optional file filtering and size caps.
4. Return deterministic map ordered by path.

## Error Handling Contract

- `UserNotFoundError`: no branch/worktree for user.
- `CommitNotFoundError`: unknown commit in user scope.
- `InvalidRangeError`: invalid commit range semantics.
- `SnapshotTooLargeError`: file/byte cap exceeded.
- `ObservationUnavailableError`: repository metadata inaccessible.

Errors should return structured fields:

- `code`
- `message`
- `user_id`
- optional `commit`
- optional `details`

## Anomaly Model

Initial detectors:

- Write burst: unusual commit rate in a short window.
- Churn spike: sudden jump in files or line changes.
- Delete-heavy change: high deletion ratio.
- Oscillation: repeated back-and-forth edits to same files.
- Large file outlier: unexpected size/type additions.
- Divergence warning: multiple leaves when linear history is expected.

Severity levels:

- `info`: notable but expected variation.
- `warn`: behavior worth review.
- `critical`: potential corruption or misuse.

Each anomaly must include explicit evidence (commit hashes, metrics, threshold crossed).

## Compatibility Guarantees

- Backward compatibility: existing APIs and default behavior remain unchanged.
- Incremental adoption: callers can opt into graph/risk methods independently.
- Deterministic outputs: ordering and schema remain stable across runs.
- No storage migration required for initial release.
- Unknown or unsupported git edge cases degrade gracefully with typed errors.

## Rollout Plan

### Phase 1: Foundation

- Add shared observation domain models.
- Implement commit metadata extraction and deterministic ordering.
- Enhance `history(...)` with diff stats and optional risk placeholders.

Exit criteria:

- Existing `history(...)` consumers remain compatible.
- New metadata fields are documented and tested.

### Phase 2: Graph Queries

- Add `lineage`, `children`, `leaves`, and `diff`.
- Add user-scope validation to all graph traversals.

Exit criteria:

- Deterministic graph traversal tests pass for linear and branched histories.

### Phase 3: Snapshot

- Add `snapshot(...)` with filtering and safety caps.
- Add typed errors for oversized snapshots.

Exit criteria:

- State-at-commit reconstruction is deterministic and bounded.

### Phase 4: Anomaly Detection

- Implement initial detector set and severity model.
- Expose `anomalies(...)` and `risk_flags` integration in `history(...)`.

Exit criteria:

- Detector behavior is reproducible in fixture repos.
- False-positive-prone rules default to `info` until calibrated.

## Testing Strategy

- Unit tests:
  - normalization models
  - limit and validation behavior
  - anomaly threshold logic
- Repository fixture tests:
  - linear graph
  - branched graph
  - merge-like scenarios
  - delete-heavy and oscillation patterns
- Contract tests:
  - API shape stability
  - deterministic ordering
  - typed error guarantees
- Integration tests:
  - end-to-end with real user branches and snapshot/diff flows

## Risks and Mitigations

- Git edge-case complexity: mitigate with fixture coverage and strict user-scoped validation.
- Snapshot payload growth: mitigate with default caps and selective file filters.
- Anomaly noise: mitigate with conservative defaults and severity staging.
- Performance regressions on large histories: mitigate with pagination, caps, and cached commit metadata where needed.

## Success Criteria

- Developers can explain memory evolution from commits without manual git commands.
- `history(...)` remains simple while advanced graph and risk signals are available on demand.
- Snapshot and anomaly APIs improve debugging time for memory issues and regressions.
