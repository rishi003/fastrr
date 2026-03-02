"""Ingest LoCoMo conversations into Fastrr memory.

Each of the 10 conversations becomes a separate user. Messages are stored
with session timestamps so recall can surface temporally relevant context.

Based on: https://github.com/getzep/zep-papers/tree/main/kg_architecture_agent_memory/locomo_eval
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from fastrr import Fastrr


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
    num_users: int = 10,
    max_sessions: int = 35,
    log: Callable[[str], None] | None = None,
) -> list[str]:
    """Ingest LoCoMo conversations into Fastrr.

    Args:
        memory: Fastrr instance
        data_path: Path to locomo10.json
        num_users: Number of conversations (default 10)
        max_sessions: Max sessions per conversation (default 35)
        log: Optional callback(msg) for progress, e.g. lambda m: print(m)

    Returns:
        List of user_ids created (e.g. locomo_0, locomo_1, ...)
    """
    path = Path(data_path)
    with open(path) as f:
        data = json.load(f)

    user_ids: list[str] = []
    for group_idx in range(min(num_users, len(data))):
        sample = data[group_idx]
        conversation = sample.get("conversation", {})
        user_id = f"locomo_{group_idx}"
        user_ids.append(user_id)

        for session_idx in range(max_sessions):
            session_key = f"session_{session_idx}"
            session = conversation.get(session_key)
            if session is None:
                continue

            date_key = f"session_{session_idx}_date_time"
            session_date = conversation.get(date_key, "unknown")

            for msg in session:
                content = _format_message(msg, session_date)
                memory.remember(user_id, content)

        if log:
            log(f"    Ingested {user_id}")

    return user_ids
