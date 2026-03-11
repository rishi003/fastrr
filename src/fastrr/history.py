"""Public history models for memory history APIs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RepoHistoryEntry:
    """History record returned by RepoManager backends."""

    commit: str
    timestamp: str
    message: str
    changed_files: list[str]
    diff_text: str


@dataclass(frozen=True)
class MemoryHistoryEvent:
    """Public history record exposed by the client API."""

    commit: str
    timestamp: str
    message: str
    changed_files: list[str]
    summary: str
