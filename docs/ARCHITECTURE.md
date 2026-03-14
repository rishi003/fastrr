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
                    │  read_file,                    │
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

- **Store**: Receives content, runs `SearchStrategy.search()` to pre-filter
  existing related snippets, then calls the agent with those snippets injected
  into the prompt. The agent follows five named phases (ASSESS → READ → DECIDE
  → WRITE → COMMIT) to detect duplicates, update existing entries, or write new
  ones.
- **Remove**: Calls `forget` to clear memory files from the workspace.

### ReaderAgent

An Agno agent that:

- Uses a `SearchStrategy` to pre-filter relevant snippets from the workspace.
- Reads files via `read_file` and synthesises a concise response.
- With a `query`: returns memory relevant to that query.
- Without a `query`: summarises all memory.

### MemoryToolset

Plain Python callables that wrap `RepoManager` file operations. No AI framework dependency. These are registered as tools for the agents but can be used directly or adapted to other frameworks.

File discovery is **template-driven**: the list of workspace files is declared in the memory template and injected into agent instructions at construction time.

| Agent | Read tools | Write tools |
|-------|------------|-------------|
| ReaderAgent | `read_file` | — |
| WriterAgent | `read_file` | `write_file`, `append_file`, `delete_file`, `sync`, `forget` |

### MemoryTemplate

A JSON file that declares the workspace file structure. Loaded once at `Fastrr` construction and used to:

1. Initialise empty files in the workspace (if they do not yet exist) via `RepoManager.initialize_workspace`.
2. Format the `Memory Files:` block injected into `WriterAgent` and `ReaderAgent` system instructions.

The built-in default template (`src/fastrr/templates/default_template.json`) defines `preferences.md`, `history.jsonl`, and `facts.md`. A custom template path can be supplied via `FASTRR_MEMORY_TEMPLATE_PATH` or `FastrrConfig.memory_template_path`.

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
2. `SearchStrategy.search(workspace, content)` pre-filters related snippets.
3. Agent receives the content and snippets (if any) and runs five phases:
   ASSESS (review snippets) → READ (read file if needed) → DECIDE
   (UPDATE / WRITE NEW / SKIP) → WRITE → COMMIT.
4. Agent calls `append_file`, `write_file`, or nothing depending on DECIDE.
5. `GitRepoManager` commits to the current branch.

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
