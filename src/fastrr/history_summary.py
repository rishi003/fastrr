"""Deterministic summaries for memory history entries."""


def summarize_memory_change(
    message: str,
    changed_files: list[str],
    diff_text: str,
) -> str:
    if not changed_files:
        return "repository update"

    if len(changed_files) > 1:
        return f"updated {len(changed_files)} memory files"

    file_name = changed_files[0]
    has_additions = False
    has_removals = False
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            has_additions = True
        elif line.startswith("-"):
            has_removals = True

    if has_additions and not has_removals:
        return f"added memory to {file_name}"
    if has_removals and not has_additions:
        return f"removed memory from {file_name}"
    return f"updated memory in {file_name}"
