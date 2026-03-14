# Agent Prompt Improvements Design

**Date:** 2026-03-14
**Status:** Approved

## Problem

The `WriterAgent` has two gaps that cause unnecessary memory duplication:

1. It has no `read_file` tool — it cannot inspect existing content before writing.
2. It has no pre-filtering step — it receives no signal about whether similar
   information is already stored, so it defaults to appending blindly.

The `ReaderAgent` already has a pre-filtering pipeline (`SearchStrategy` →
snippets → agent), but its prompt lacks two things that lead to unreliable
behaviour:

- No explanation of the snippet format (`[filename] matching line`), so the
  agent cannot reliably map snippets back to files.
- The instruction "Read any additional files if needed" is too vague — the
  agent either over-calls `read_file` (wasteful) or under-calls it (incomplete
  answers).

## Design

### Approach

Approach B: inject `SearchStrategy` into `WriterAgent` (mirroring the
`ReaderAgent` pattern) and restructure both prompts into named phases that
give the LLM an unambiguous execution order.

### Architecture changes

Only `WriterAgent` requires structural code changes. `ReaderAgent` changes are
prompt-only.

#### `WriterAgent.__init__`

- Add `search_strategy: Optional[SearchStrategy] = None` parameter (defaults
  to `RegexSearch()`).
- Give the underlying Agno agent `toolset.read_tools + toolset.write_tools`
  instead of `toolset.write_tools` alone.

#### `WriterAgent.store()`

Before building the prompt:

1. Call `self._search.search(workspace, content)` with the raw incoming content
   as the query.
2. If snippets are returned, inject them into the prompt so the agent can
   assess existing similar content in PHASE 1.
3. If no snippets are returned, omit the snippets block and let the agent
   proceed directly to DECIDE.

### Prompt design — WriterAgent

Replace the current flat 7-line instruction block with five named phases:

```
PHASE 1 — ASSESS
Review the pre-filtered snippets (format: [filename] matching line).
Determine whether similar information is already stored.
If no snippets were provided, proceed directly to PHASE 3.

PHASE 2 — READ
If snippets indicate existing similar content, call read_file on the
relevant file(s) to see the full current state.

PHASE 3 — DECIDE
Choose exactly one action:
  - UPDATE: existing content covers the same fact/preference — read the
    file, merge new details, and rewrite the whole file with write_file.
  - WRITE NEW: no sufficiently similar content exists — use append_file
    or write_file as appropriate for the content type.
  - SKIP: the incoming content is identical to what is already stored.

PHASE 4 — WRITE
Execute the chosen action. Use the Memory Files list to pick the right
target file. Prefer markdown for prose notes, JSONL for structured
entries, plain text for simple facts. Never make up data. Only store
what you are explicitly given.

PHASE 5 — COMMIT
End your response with exactly one line summarising what you stored, in
the imperative mood, under 72 characters. Prefix it with "COMMIT: ".
Example: COMMIT: update preferred communication style in preferences.md
```

### Prompt design — ReaderAgent

Replace the current three numbered steps with three named phases, adding the
two missing pieces:

```
PHASE 1 — REVIEW
Examine the pre-filtered snippets (format: [filename] matching line).
The filename tells you which file to call read_file on for more context.
Note which files contain potentially relevant content.
If no snippets were provided, proceed to PHASE 2 and read files directly.

PHASE 2 — EXPAND (optional)
Call read_file when:
  (a) snippets for a file are sparse (fewer than 3 lines) and the query
      needs fuller context, or
  (b) the query asks for a complete summary of a topic.
Do not call read_file if the snippets already fully answer the query.

PHASE 3 — SYNTHESISE
Return only content relevant to the query in plain text.
Be concise. Do not invent information not found in the files.
If no relevant memory is found, say so plainly.
```

### Data flow

#### `remember(content)` — updated

```
store(content)
  │
  ├─ search_strategy.search(workspace, content)  ← NEW
  │     └─ returns snippets (or [])
  │
  ├─ build prompt with snippets injected          ← NEW
  │
  └─ agent.run(prompt)
        │
        ├─ ASSESS: reviews snippets
        ├─ READ (optional): calls read_file if snippets found
        ├─ DECIDE: UPDATE / WRITE NEW / SKIP
        ├─ WRITE: write_file / append_file / (no-op)
        └─ COMMIT: emits "COMMIT: ..." line
              └─ _extract_commit_message → toolset.sync()
```

#### `recall(query)` — structurally unchanged, prompt improved

```
search(query)
  │
  ├─ search_strategy.search(workspace, query)
  │     └─ returns snippets (or [])
  │
  ├─ build prompt with snippets injected
  │
  └─ agent.run(prompt)
        │
        ├─ REVIEW: notes source files from snippets
        ├─ EXPAND (optional): calls read_file if snippets sparse
        └─ SYNTHESISE: returns concise relevant answer
```

### Error handling / edge cases

| Scenario | Behaviour |
|---|---|
| `search_strategy.search()` returns `[]` | Snippets block omitted from prompt; writer goes straight to DECIDE (WRITE NEW). Reader falls back to "read files directly". No change from current behaviour. |
| Agent chooses SKIP | `_extract_commit_message` falls back to `"remember"` (existing). `toolset.sync()` is called; no-op in Git if no files changed. |
| `read_file` returns `{"error": "File not found"}` | Already handled in `MemoryToolset.read_file`. Agent receives JSON error and falls through to WRITE NEW. No new handling needed. |

### Files changed

| File | Change type |
|---|---|
| `src/fastrr/agents/writer.py` | Structural + prompt |
| `src/fastrr/agents/reader.py` | Prompt only |
| `src/fastrr/agents/toolset.py` | None |
| All other files | None |
