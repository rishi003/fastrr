# Evals

Evaluation setup for Fastrr memory systems. Datasets are **gitignored** (they can be large, e.g. ~3MB for LoCoMo). Use the download script to fetch them.

## Prerequisites

Install the project first (from repo root):

```bash
uv sync
# or: pip install -e .
```

## Quick Start

```bash
# List available datasets
python -m evals.download --list

# Download a dataset
python -m evals.download locomo10

# Download multiple
python -m evals.download locomo10 longmemeval_oracle

# Download all
python -m evals.download --all
```

Datasets are stored in `evals/datasets/`. Any `.json` file in that directory can be used for evaluation.

## LoCoMo Evaluation

[LoCoMo](https://github.com/snap-research/locomo) evaluates very long-term conversational memory. The pipeline (based on [zep-papers locomo_eval](https://github.com/getzep/zep-papers/tree/main/kg_architecture_agent_memory/locomo_eval)):

1. **Ingest**: Load 10 conversations into Fastrr (`remember` each message with session timestamps)
2. **Recall + Generate**: For each QA, `recall` context and generate answer via LLM (gpt-4o-mini)
3. **Grade**: Compare generated vs gold answer using LLM grader

### Run LoCoMo Eval

Uses the same LLM as Fastrr (Ollama by default). Ensure [Ollama](https://ollama.ai) is running with a model (e.g. `ollama pull llama3.2`).

```bash
# Install project first (from repo root)
uv sync

# Download dataset
python -m evals.download locomo10

# Run eval (uses FASTRR_PROVIDER, FASTRR_MODEL, OLLAMA_HOST from env)
python -m evals.locomo.run

# Options
python -m evals.locomo.run --dataset evals/datasets/locomo10.json --output-dir evals/output
python -m evals.locomo.run --fake-repo   # Use FakeRepoManager (no Git, faster)
python -m evals.locomo.run --direct-ingest   # No LLM during ingest; Ollama only for QA, one call at a time
python -m evals.locomo.run -v            # Verbose: DEBUG level, log each QA
python -m evals.locomo.run -q            # Quiet: WARNING only, minimal output
```

Results are saved to `evals/output/locomo_results.json` with overall accuracy and per-category scores (single_hop, temporal, multi_hop, open_domain).

**Notebook (step by step):** [evals/locomo/locomo_eval.ipynb](locomo/locomo_eval.ipynb) — run each step in a separate cell (setup → load data → ingest → one QA → full QA → results).

## Registered Datasets

| Name | Source | Description |
|------|--------|-------------|
| `locomo10` | [snap-research/locomo](https://github.com/snap-research/locomo) | LoCoMo: 10 very long-term conversations with QA annotations (ACL 2024) |
| `longmemeval_oracle` | [LongMemEval](https://github.com/xiaowu0162/LongMemEval) | 500 questions, evidence sessions only (~115k tokens) |
| `longmemeval_s` | LongMemEval | ~40 history sessions per question |
| `longmemeval_m` | LongMemEval | ~500 sessions per question |

## Adding a New Dataset

1. Add an entry to `evals/registry.json`:

```json
{
  "my_dataset": {
    "source": "https://github.com/org/repo",
    "url": "https://example.com/data.json",
    "filename": "my_dataset.json",
    "description": "Short description"
  }
}
```

2. Download: `python -m evals.download my_dataset`

3. Run eval: `python -m evals.locomo.run --dataset evals/datasets/my_dataset.json` (LoCoMo format).

## Dataset Formats

- **LoCoMo**: Array of samples; each has `conversation`, `qa` (list of `{question, answer, evidence, category}`), etc.
- **LongMemEval**: Array of instances; each has `question_id`, `question`, `answer`, `haystack_sessions`, `answer_session_ids`, etc.

Eval scripts should detect format (e.g. by checking for `qa` vs `haystack_sessions`) and run the appropriate evaluation.
