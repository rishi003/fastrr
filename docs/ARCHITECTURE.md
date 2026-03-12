# Architecture

Fastrr is a semantic memory layer that uses LLM-powered agents to store and
retrieve memory on disk, backed by Git for versioning.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Fastrr Client                            │
│  remember(content) │ recall(query) │ forget() │ history(limit)   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            ┌───────────────┐               ┌───────────────┐
            │ WriterAgent   │               │ ReaderAgent   │
            │ (store/remove)│               │ (search)      │
            └───────┬───────┘               └───────┬───────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │      MemoryToolset             │
                    │  list_files, read_file,        │
                    │  write_file, append_file,      │
                    │  sync, forget                  │
                    └───────────────┬───────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │      RepoManager              │
                    │  (GitRepoManager default)     │
                    │  Single Git repository        │
                    └───────────────────────────────┘
```

## Components

### Fastrr (Client)

The main entry point. Exposes `remember`, `recall`, `forget`, and `history`.
Accepts optional overrides for `repo_manager`, `model`, `search_strategy`, and
`config`.

### WriterAgent

An [Agno](https://github.com/agno-agi/agno) agent that:

- **Store**: Receives content, inspects the workspace via `list_files`, decides where to put it (e.g. `preferences.md`, `history.jsonl`), and uses `write_file` or `append_file` + `sync`.
- **Remove**: Calls `forget` to clear memory files from the workspace.

### ReaderAgent

An Agno agent that:

- Uses a `SearchStrategy` to pre-filter relevant snippets from the workspace.
- Reads files via `read_file` and synthesises a concise response.
- With a `query`: returns memory relevant to that query.
- Without a `query`: summarises all memory.

### MemoryToolset

Plain Python callables that wrap `RepoManager` file operations. No AI framework dependency. These are registered as tools for the agents but can be used directly or adapted to other frameworks.

| Read tools | Write tools |
|------------|-------------|
| `list_files`, `read_file`, `file_exists` | `write_file`, `append_file`, `delete_file`, `sync`, `forget` |

### RepoManager

Abstract protocol for single-workspace storage. Implementations must provide:

- `ensure_workspace()` — create/return workspace path
- `sync(message)` — persist changes
- `forget()` — clear workspace memory files
- `get_history(limit)` — list commit history

**GitRepoManager** (default): Uses a single local Git repository and commits on
the current branch. Storage is local; no remote push by default.

### SearchStrategy

Abstract strategy for searching the memory workspace. Implementations receive
the workspace root and a query, and return a list of relevant text snippets for
the ReaderAgent to synthesise.

**RegexSearch** (default): Scans all text files, returns lines matching the query as a regex (or literal substring if regex invalid). Configurable `max_results` (default 50).

Future: semantic/vector search (e.g. via RedisVL) can be plugged in by implementing `SearchStrategy`.

## Data Flow

### remember(content)

1. Client calls `WriterAgent.store(content)`.
2. Agent runs with prompt: "Store the following memory: ..."
3. Agent calls `list_files` → sees existing files.
4. Agent decides target file (e.g. `preferences.md`) and calls `append_file` or `write_file`.
5. Agent calls `sync` to commit changes.
6. `GitRepoManager` commits to the current branch.

### recall(query=None)

1. Client calls `ReaderAgent.search(query)`.
2. If `query` given: `SearchStrategy.search(workspace, query)` returns pre-filtered snippets.
3. Agent receives snippets (or "read files directly" if none) and runs with appropriate prompt.
4. Agent may call `read_file` for additional context.
5. Agent returns synthesised text.

### forget()

1. Client calls `WriterAgent.remove()`.
2. A dedicated remove-agent runs with `forget` tool only.
3. `RepoManager.forget` clears stored memory files.

## Extensibility

| Extension point | How |
|----------------|-----|
| Custom storage | Implement `RepoManager` and pass `repo_manager=MyRepoManager(...)` to `Fastrr`. |
| Custom search | Implement `SearchStrategy` and pass `search_strategy=MySearch(...)` to `Fastrr`. |
| Custom LLM | Pass `model=MyAgnoModel(...)` to `Fastrr` (overrides env config). |
| Custom config | Pass `config=FastrrConfig(...)` or subclass and pass to `Fastrr`. |
