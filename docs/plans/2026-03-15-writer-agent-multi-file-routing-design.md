# Writer Agent: Multi-File Routing & Concise Event Storage

**Date:** 2026-03-15
**Status:** Implemented (2026-03-15)

## Problem

The writer agent prompt has two issues:

1. **Single-action constraint** — PHASE 3 says "choose exactly one action", preventing the agent from writing to multiple files in a single pass even when the input contains information that belongs in more than one file.
2. **No summarisation rule** — the agent may store raw input verbatim rather than distilling it, leading to bloated history entries instead of concise events.

## Taxonomy

Three files, each with a clear, non-overlapping responsibility:

| File | What goes here |
|---|---|
| `history.jsonl` | Time-bound events — things that *happened*. Timestamped, concise past-tense summaries. Never raw input. |
| `facts.md` | Atemporal truths — things that *are* true regardless of when (occupation, location, relationships). No timestamps. |
| `preferences.md` | How the user likes things done — communication style, formatting, tooling choices. |

**Example:** `"I went to a LGBTQ support group yesterday"` → history only (`"attended LGBTQ support group"`). Not facts (time-bound). Not preferences.

## Design

### Prompt Restructure

Replace the current 5-phase prompt with an updated version where PHASE 3 becomes a per-file planning step:

```
PHASE 1 — ASSESS
Review pre-filtered snippets (format: [filename] matching line).
Determine whether similar information is already stored.
If no snippets were provided, proceed directly to PHASE 3.

PHASE 2 — READ
If snippets indicate existing similar content, call read_file on
the relevant file(s) to see the full current state.

PHASE 3 — PLAN
For each Memory File, independently ask:
  "Does the input contain information that belongs in this file,
   based on its description?"
If yes, decide:
  - action: append | update | skip (already identical)
  - distilled content: a concise rephrasing in your own words.
    Never copy the raw input verbatim.

Only include files where the answer is yes. It is fine if no file
matches — output SKIP with no writes.

PHASE 4 — EXECUTE
Execute every write in your plan. Files not in the plan are not touched.
One input can touch zero, one, or multiple files.

PHASE 5 — COMMIT
End your response with exactly one COMMIT: line summarising all writes,
imperative mood, under 72 characters.
```

The routing logic lives entirely in the template file descriptions — not in the prompt. Changing the template changes the routing. The prompt is template-agnostic.

### Default Template Description Updates

`default_template.json` descriptions need enough signal to distinguish each file:

**`history.jsonl`** (addition to existing description):
> Events must be concise past-tense summaries (≤20 words). Never copy raw input verbatim.

**`facts.md`** (replace "Standalone facts"):
> Atemporal facts about the person — things that are true regardless of when they happened (e.g. occupation, location, relationships). No timestamps.

**`preferences.md`**: unchanged — already unambiguous.

## What Does Not Change

- The ASSESS → READ deduplication logic (phases 1–2) is unchanged.
- The COMMIT phase is unchanged.
- The toolset (`read_file`, `write_file`, `append_file`) is unchanged.
- The template schema is unchanged — only the `description` strings are updated.
- No hardcoded file names in the prompt.

## Out of Scope

- Cross-file deduplication (e.g. detecting that the same fact was written to both `facts.md` and `history.jsonl`) — the descriptions + planning step should prevent this in practice.
- Reader agent changes.
