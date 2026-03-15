# Writer Agent Multi-File Routing Implementation Plan

> **Status:** Implemented 2026-03-15.
> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the writer agent prompt so it routes each piece of input to zero, one, or multiple memory files based on each file's description, and always distils content rather than copying it verbatim.

**Architecture:** Two files change — the prompt string in `writer.py` and the description fields in `default_template.json`. No new files, no new tools, no schema changes. Existing tests for prompt structure need updating to match the revised wording.

**Tech Stack:** Python, pytest

---

### Task 1: Update writer prompt in `writer.py`

**Files:**
- Modify: `src/fastrr/agents/writer.py:12-48`

**Step 1: Write the failing tests**

In `tests/test_agents.py`, update `TestWriterAgentPrompt` to reflect the new prompt shape. The old `test_prompt_contains_decide_actions` checks for `"UPDATE"`, `"WRITE NEW"`, `"SKIP"` — these change to lowercase inline options. Add a new test for the PLAN phase content.

Replace the two existing `TestWriterAgentPrompt` tests that will break:

```python
class TestWriterAgentPrompt:
    def test_prompt_contains_all_five_phases(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        for phase in ["PHASE 1", "PHASE 2", "PHASE 3", "PHASE 4", "PHASE 5"]:
            assert phase in instructions, f"Missing {phase} in writer instructions"

    def test_prompt_plan_phase_contains_per_file_routing(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "PLAN" in instructions
        for action in ["append", "update", "skip"]:
            assert action in instructions

    def test_prompt_requires_distilled_content(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "verbatim" in instructions.lower()

    def test_prompt_allows_multiple_file_writes(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "multiple" in instructions.lower() or "zero, one" in instructions.lower()

    def test_prompt_contains_commit_prefix(self, fake_toolset, mock_model):
        with patch("fastrr.agents.writer.Agent") as MockAgent:
            WriterAgent(fake_toolset, mock_model, memory_files="pref.md")
        instructions = MockAgent.call_args.kwargs["instructions"]
        assert "COMMIT: " in instructions
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_agents.py::TestWriterAgentPrompt -v
```

Expected: `test_prompt_contains_decide_actions` FAILS (checking for removed strings), new tests FAIL (prompt not updated yet).

**Step 3: Update `_WRITER_INSTRUCTIONS_TEMPLATE` in `writer.py`**

Replace the `_WRITER_INSTRUCTIONS_TEMPLATE` string (lines 12–48) with:

```python
_WRITER_INSTRUCTIONS_TEMPLATE = """
You are a memory writer agent. Your job is to persist memory to disk.

Memory Files:
{memory_files}

PHASE 1 — ASSESS
Review the pre-filtered snippets provided in the user message
(format: [filename] matching line).
Determine whether similar information is already stored.
If no snippets were provided, proceed directly to PHASE 3.

PHASE 2 — READ
If snippets indicate existing similar content, call read_file on the
relevant file(s) to see the full current state before planning.

PHASE 3 — PLAN
For each Memory File listed above, independently decide:
  - Does the input contain information that belongs in this file,
    based on its description?
If yes, determine:
  - action: append | update | skip (if already identical)
  - distilled content: a concise rephrasing in your own words.
    Never copy the raw input verbatim.

Only include files where the answer is yes. It is fine if no file
matches — do nothing.

PHASE 4 — EXECUTE
Execute every write in your plan. Files not in the plan are not touched.
A single input may touch zero, one, or multiple files.

PHASE 5 — COMMIT
End your response with exactly one line summarising what you stored, in
the imperative mood, under 72 characters. Prefix it with "COMMIT: ".
Example: COMMIT: update preferred communication style in preferences.md
""".strip()
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_agents.py::TestWriterAgentPrompt -v
```

Expected: all 5 tests PASS.

**Step 5: Run full test suite to confirm no regressions**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

**Step 6: Commit**

```bash
git add src/fastrr/agents/writer.py tests/test_agents.py
git commit -m "refactor: restructure writer prompt for per-file routing and concise distillation"
```

---

### Task 2: Update `default_template.json` descriptions

**Files:**
- Modify: `src/fastrr/templates/default_template.json`
- Test: `tests/test_template.py`

**Step 1: Read the existing template test**

```bash
cat tests/test_template.py
```

Understand what is currently asserted about descriptions so you know what to update.

**Step 2: Write a failing test for the new descriptions**

In `tests/test_template.py`, add or update a test that asserts the default template descriptions contain the new distinguishing language:

```python
def test_default_template_history_description_requires_concise_events():
    from fastrr.template import load_template
    template = load_template(None)  # loads default
    history = next(f for f in template if f.name == "history.jsonl")
    assert "verbatim" in history.description.lower() or "concise" in history.description.lower()

def test_default_template_facts_description_is_atemporal():
    from fastrr.template import load_template
    template = load_template(None)
    facts = next(f for f in template if f.name == "facts.md")
    assert "atemporal" in facts.description.lower() or "timestamp" in facts.description.lower()
```

**Step 3: Run tests to verify they fail**

```bash
pytest tests/test_template.py -v -k "atemporal or concise_events"
```

Expected: both new tests FAIL.

**Step 4: Update `default_template.json`**

Replace the file with:

```json
{
  "files": [
    {
      "name": "preferences.md",
      "description": "Preferences and settings"
    },
    {
      "name": "history.jsonl",
      "description": "Chronological memory entries in JSON Lines format. Each line is a JSON object with fields: timestamp (ISO-8601), type (string category), content (string detail). This file is to track events and not full conversations. Events must be concise past-tense summaries (≤20 words). Never copy raw input verbatim."
    },
    {
      "name": "facts.md",
      "description": "Atemporal facts about the person — things that are true regardless of when they happened (e.g. occupation, location, relationships). No timestamps."
    }
  ]
}
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_template.py -v
```

Expected: all template tests PASS.

**Step 6: Commit**

```bash
git add src/fastrr/templates/default_template.json tests/test_template.py
git commit -m "feat: sharpen default template descriptions for per-file routing"
```

---

### Task 3: Smoke-check with eval notebook (optional, no commit)

**Files:**
- Read: `evals/locomo/locomo_eval.ipynb`

If an eval is already set up and runnable locally, run a quick manual check to confirm the writer agent correctly routes a mixed-signal input (e.g. `"I went to a LGBTQ support group yesterday and it was so powerful"`) to `history.jsonl` only, with a concise summary entry, not raw text.

This is a manual verification step — no code changes, no commit.
