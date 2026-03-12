"""Ingest LoCoMo conversations into Fastrr memory.

Messages are stored with session timestamps so recall can surface temporally
relevant context.

Based on: https://github.com/getzep/zep-papers/tree/main/kg_architecture_agent_memory/locomo_eval
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from fastrr import Fastrr
from fastrr.agents.toolset import MemoryToolset


def _format_message(msg: dict, session_date: str) -> str:
    """Format a single message for remember()."""
    speaker = msg.get("speaker", "Unknown")
    text = msg.get("text", "")
    blip = msg.get("blip_caption")
    img_desc = f" (image: {blip})" if blip else ""
    return f"[{session_date}] {speaker}: {text}{img_desc}"


def ingest_locomo(
    memory: Fastrr,
    data_path: str | Path,
    *,
    num_conversations: int = 10,
    max_sessions: int = 35,
    log: Callable[[str], None] | None = None,
) -> int:
    """Ingest LoCoMo conversations into Fastrr.

    Args:
        memory: Fastrr instance
        data_path: Path to locomo10.json
        num_conversations: Number of conversations (default 10)
        max_sessions: Max sessions per conversation (default 35)
        log: Optional callback(msg) for progress, e.g. lambda m: print(m)

    Returns:
        Number of conversations ingested.
    """
    path = Path(data_path)
    with open(path) as f:
        data = json.load(f)

    ingested = 0
    for group_idx in range(min(num_conversations, len(data))):
        sample = data[group_idx]
        conversation = sample.get("conversation", {})

        for session_idx in range(max_sessions):
            session_key = f"session_{session_idx}"
            session = conversation.get(session_key)
            if session is None:
                continue

            date_key = f"session_{session_idx}_date_time"
            session_date = conversation.get(date_key, "unknown")

            for msg in session:
                content = _format_message(msg, session_date)
                memory.remember(content)

        ingested += 1
        if log:
            log(f"    Ingested conversation {group_idx}")

    return ingested


def ingest_locomo_direct(
    toolset: MemoryToolset,
    data_path: str | Path,
    *,
    num_users: int = 10,
    max_sessions: int = 35,
    log: Callable[[str], None] | None = None,
) -> int:
    """Ingest LoCoMo conversations by writing files directly, without LLM calls."""
    path = Path(data_path)
    with open(path) as f:
        data = json.load(f)

    output_file = "locomo_history.md"
    toolset.write_file(output_file, "")
    ingested = 0

    for group_idx in range(min(num_users, len(data))):
        sample = data[group_idx]
        conversation = sample.get("conversation", {})

        for session_idx in range(max_sessions):
            session_key = f"session_{session_idx}"
            session = conversation.get(session_key)
            if session is None:
                continue

            date_key = f"session_{session_idx}_date_time"
            session_date = conversation.get(date_key, "unknown")

            for msg in session:
                content = _format_message(msg, session_date)
                toolset.append_file(output_file, content + "\n")

        ingested += 1
        if log:
            log(f"    Ingested conversation {group_idx}")

    toolset.sync(message="ingest locomo conversations")
    return ingested
