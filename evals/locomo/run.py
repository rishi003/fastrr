#!/usr/bin/env python3
"""Run LoCoMo evaluation for Fastrr.

Pipeline (based on zep-papers locomo_eval):
1. Ingest: Load conversations into Fastrr memory (remember)
2. Recall + Generate: For each QA, recall context and generate answer via LLM
3. Grade: Compare generated vs gold answer using LLM grader

Uses the same LLM as Fastrr (Ollama by default). Configure via:
  FASTRR_PROVIDER=ollama  FASTRR_MODEL=llama3.2  OLLAMA_HOST=http://localhost:11434

Usage:
    python -m evals.locomo.run [--dataset PATH] [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

# Reduce overlapping requests: disable Agno telemetry before importing Agno
os.environ.setdefault("AGNO_TELEMETRY", "false")

from agno.agent import Agent

from fastrr import Fastrr
from fastrr.agents.toolset import MemoryToolset
from fastrr.core.config import FastrrConfig

from evals.locomo.ingest import ingest_locomo, ingest_locomo_direct

logger = logging.getLogger(__name__)


def _elapsed(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s" if m else f"{s}s"


def _build_eval_model():
    """Build LLM for answer generation and grading (same config as Fastrr)."""
    cfg = FastrrConfig()
    if cfg.provider == "openrouter":
        from agno.models.openrouter import OpenRouter
        return OpenRouter(id=cfg.model, api_key=cfg.openrouter_api_key)
    from agno.models.ollama import Ollama
    return Ollama(id=cfg.model, host=cfg.ollama_host)

SCRIPT_DIR = Path(__file__).resolve().parent
EVALS_DIR = SCRIPT_DIR.parent
DATASETS_DIR = EVALS_DIR / "datasets"
DEFAULT_DATASET = DATASETS_DIR / "locomo10.json"

# Category labels from LoCoMo (category 5 = abstention, skipped)
CATEGORY_NAMES = {
    1: "single_hop",
    2: "temporal",
    3: "multi_hop",
    4: "open_domain",
    5: "abstention",
}

ANSWER_PROMPT = """You are a helpful expert assistant answering questions based on the provided context.

# CONTEXT:
You have access to facts and memories from a conversation.

# INSTRUCTIONS:
1. Carefully analyze all provided memories
2. Pay special attention to timestamps to determine the answer
3. If the question asks about a specific event or fact, look for direct evidence in the memories
4. If memories contain contradictory information, prioritize the most recent memory
5. Always convert relative time references to specific dates, months, or years when possible
6. Be as specific as possible when talking about people, places, and events
7. Timestamps in memories represent when the event occurred, not when it was mentioned.

# APPROACH:
1. Examine all memories related to the question
2. Look for explicit mentions of dates, times, locations, or events
3. Formulate a precise, concise answer based solely on the evidence
4. Ensure your answer directly addresses the question

Context:
{context}

Question: {question}
Answer:"""

GRADE_PROMPT = """You are an expert grader that determines if answers match a gold standard.

Your task: Label an answer as CORRECT or WRONG.

You will be given:
(1) A question (about something one user should know about another from prior conversations)
(2) A gold (ground truth) answer
(3) A generated answer to score

Be generous:
- If the generated answer touches on the same topic as the gold, count CORRECT
- For time questions: "May 7th" vs "7 May" = CORRECT. Relative refs ("last Tuesday") = CORRECT if same date
- Do NOT include both CORRECT and WRONG. Return exactly one label.

Question: {question}
Gold answer: {gold}
Generated answer: {response}

Return exactly CORRECT or WRONG as your final answer."""


def _generate_answer(agent: Agent, context: str, question: str) -> str:
    """Generate answer using LLM given recalled context."""
    prompt = ANSWER_PROMPT.format(context=context, question=question)
    result = agent.run(prompt)
    return (result.content or "").strip() if hasattr(result, "content") else str(result).strip()


def _grade_answer(agent: Agent, question: str, gold: str, response: str) -> bool:
    """Grade generated answer against gold using LLM."""
    prompt = GRADE_PROMPT.format(question=question, gold=str(gold), response=response)
    result = agent.run(prompt)
    text = (result.content or "").strip().upper() if hasattr(result, "content") else str(result).strip().upper()
    # Parse CORRECT/WRONG from response (Ollama may not return strict JSON)
    return "CORRECT" in text and "WRONG" not in text and "INCORRECT" not in text


def run_eval(
    dataset_path: Path,
    output_dir: Path,
    *,
    use_fake_repo: bool = False,
    verbose: bool = False,
    direct_ingest: bool = False,
) -> dict:
    """Run full LoCoMo eval: ingest, recall, generate, grade."""
    start_total = time.monotonic()
    cfg = FastrrConfig()
    logger.info("Config: provider=%s model=%s", cfg.provider, cfg.model)
    logger.info("Dataset: %s", dataset_path)
    logger.info("")

    with open(dataset_path) as f:
        data = json.load(f)

    num_conversations = min(10, len(data))

    # Create eval model and agent (uses FASTRR_* env vars, Ollama by default)
    eval_model = _build_eval_model()
    answer_agent = Agent(
        model=eval_model,
        instructions="Answer concisely based only on the context provided.",
    )
    grade_agent = Agent(
        model=eval_model,
        instructions="Return exactly CORRECT or WRONG as your final answer.",
    )

    # Create repo and paths first (same for direct or agent-based ingest)
    storage_path = Path(tempfile.mkdtemp(prefix="fastrr_locomo_repo_"))
    if use_fake_repo:
        from evals.fake_repo import FakeRepoManager
        root = Path(tempfile.mkdtemp(prefix="fastrr_locomo_"))
        repo = FakeRepoManager(root)
        storage_path = root / "repo"
        storage_path.mkdir(parents=True, exist_ok=True)
        logger.info("Storage: FakeRepoManager (no Git)")
    else:
        from fastrr.services.repo_manager import GitRepoManager
        repo = GitRepoManager(storage_path)
        logger.info("Storage: Git repository")

    # 1. Ingest
    step_start = time.monotonic()
    if direct_ingest:
        logger.info("Step 1/3: Ingesting conversations (direct write, no LLM)...")
        toolset = MemoryToolset(repo)
        ingest_locomo_direct(toolset, dataset_path, num_users=num_conversations, log=logger.info)
        memory = Fastrr(storage_path=storage_path, repo_manager=repo)
    else:
        memory = Fastrr(storage_path=storage_path, repo_manager=repo)
        logger.info("Step 1/3: Ingesting conversations into memory...")
        ingest_locomo(
            memory,
            dataset_path,
            num_conversations=num_conversations,
            log=logger.info,
        )
    logger.info(
        "  Done. Ingested %d conversations in %s.",
        num_conversations,
        _elapsed(time.monotonic() - step_start),
    )
    logger.info("")

    # 2. Recall + Generate + Grade
    step_start = time.monotonic()
    logger.info("Step 2/3: Running QA (recall → generate → grade)...")
    results: dict[str, list] = defaultdict(list)
    scores_by_category: dict[str, list[bool]] = defaultdict(list)
    total_qa = sum(
        len([q for q in data[i].get("qa", []) if q.get("category") != 5])
        for i in range(num_conversations)
    )
    done = 0

    def _progress(done: int, total: int, group: int, n_group: int, q_in_group: int, n_in_group: int) -> None:
        elapsed = _elapsed(time.monotonic() - step_start)
        line = f"  Group {group + 1}/{num_conversations} | Question {q_in_group}/{n_in_group} | {done}/{total} total | {elapsed}"
        sys.stderr.write(f"\r{line}    ")
        sys.stderr.flush()

    for group_idx in range(num_conversations):
        qa_set = data[group_idx].get("qa", [])
        qa_filtered = [qa for qa in qa_set if qa.get("category") != 5]
        n_qa = len(qa_filtered)
        logger.info("  Group %d/%d: %d questions", group_idx + 1, num_conversations, n_qa)

        for q_idx, qa in enumerate(qa_filtered):
            question = qa.get("question", "")
            gold = qa.get("answer")
            if gold is None:
                continue
            # Sequential: one Ollama round-trip at a time (recall → generate → grade)
            context = memory.recall(query=question)
            answer = _generate_answer(answer_agent, context, question)
            grade = _grade_answer(grade_agent, question, gold, answer)

            done += 1
            if verbose:
                mark = "✓" if grade else "✗"
                sys.stderr.write("\n")  # newline before verbose so progress line doesn't overwrite
                logger.debug("[%s] %d/%d Q: %s...", mark, done, total_qa, question[:60])
            else:
                _progress(done, total_qa, group_idx, num_conversations, q_idx + 1, n_qa)

            cat = qa.get("category", 0)
            cat_name = CATEGORY_NAMES.get(cat, "unknown")
            scores_by_category[cat_name].append(grade)
            group_key = f"group_{group_idx}"
            results[group_key].append(
                {
                    "question": question,
                    "answer": answer,
                    "golden_answer": gold,
                    "grade": grade,
                    "category": cat_name,
                }
            )
        if not verbose:
            sys.stderr.write("\n")
            sys.stderr.flush()

    # 3. Aggregate scores
    logger.info("")
    logger.info("Step 3/3: Aggregating results...")
    total = sum(len(v) for v in results.values())
    correct = sum(1 for items in results.values() for it in items if it["grade"])
    overall = correct / total if total else 0

    by_cat = {
        name: sum(scores) / len(scores) if scores else 0
        for name, scores in scores_by_category.items()
        if name != "abstention"
    }

    logger.info("  QA step complete in %s.", _elapsed(time.monotonic() - step_start))
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "locomo_results.json"
    with open(out_file, "w") as f:
        json.dump(
            {
                "overall_accuracy": overall,
                "total_questions": total,
                "correct": correct,
                "by_category": by_cat,
                "results": dict(results),
            },
            f,
            indent=2,
        )

    logger.info("  Total time: %s.", _elapsed(time.monotonic() - start_total))
    return {
        "overall_accuracy": overall,
        "total": total,
        "correct": correct,
        "by_category": by_cat,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LoCoMo eval for Fastrr")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Path to locomo10.json (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for results (default: evals/output or $TMPDIR/fastrr_locomo_output if cwd not writable)",
    )
    parser.add_argument(
        "--fake-repo",
        action="store_true",
        help="Use FakeRepoManager (no Git, faster for quick tests)",
    )
    parser.add_argument(
        "--direct-ingest",
        action="store_true",
        help="Write conversation data directly to repo (no LLM during ingest); one Ollama call at a time during QA only",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="DEBUG level: log each conversation and QA result",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="WARNING level: only errors and final results",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        logger.error("Dataset not found: %s", args.dataset)
        logger.error("Run: python -m evals.download locomo10")
        return 1

    # Default output dir: use writable location when cwd may be read-only (e.g. /workspace in containers)
    if args.output_dir is None:
        default_output = Path("evals/output")
        try:
            default_output.mkdir(parents=True, exist_ok=True)
            args.output_dir = default_output
        except OSError:
            args.output_dir = Path(tempfile.gettempdir()) / "fastrr_locomo_output"
            args.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Output dir (cwd not writable): %s", args.output_dir)

    level = logging.DEBUG if args.verbose else (logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )

    result = run_eval(
        args.dataset,
        args.output_dir,
        use_fake_repo=args.fake_repo,
        verbose=args.verbose,
        direct_ingest=args.direct_ingest,
    )

    # Always show results (even in --quiet)
    out = sys.stderr
    out.write("\n=== LoCoMo Eval Results ===\n")
    out.write(f"Overall: {result['overall_accuracy']:.2%} ({result['correct']}/{result['total']})\n")
    for cat, acc in result["by_category"].items():
        out.write(f"  {cat}: {acc:.2%}\n")
    out.write(f"\nResults saved to {args.output_dir / 'locomo_results.json'}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
