"""Unit tests for deterministic history summaries."""

from fastrr.history_summary import summarize_memory_change


def test_summary_repository_update_when_no_files() -> None:
    summary = summarize_memory_change(
        message="sync",
        changed_files=[],
        diff_text="",
    )
    assert summary == "repository update"


def test_summary_added_memory_single_file() -> None:
    summary = summarize_memory_change(
        message="remember",
        changed_files=["preferences.md"],
        diff_text="@@\n+prefers concise replies\n",
    )
    assert summary == "added memory to preferences.md"


def test_summary_removed_memory_single_file() -> None:
    summary = summarize_memory_change(
        message="forget obsolete detail",
        changed_files=["preferences.md"],
        diff_text="@@\n-old value\n",
    )
    assert summary == "removed memory from preferences.md"


def test_summary_updated_memory_single_file() -> None:
    summary = summarize_memory_change(
        message="update preference",
        changed_files=["preferences.md"],
        diff_text="@@\n-old\n+new\n",
    )
    assert summary == "updated memory in preferences.md"


def test_summary_multi_file_update() -> None:
    summary = summarize_memory_change(
        message="bulk update",
        changed_files=["a.md", "b.md"],
        diff_text="",
    )
    assert summary == "updated 2 memory files"
