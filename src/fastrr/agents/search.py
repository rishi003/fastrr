"""Search strategies for reading memory workspaces.

Provides an abstract SearchStrategy and a RegexSearch default so callers can
plug in semantic/vector search later without changing the agent interface.
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path


class SearchStrategy(ABC):
    """
    Abstract strategy for searching a user's memory workspace.

    Implementations receive the workspace root directory and a query string,
    and return a list of relevant text snippets for the ReaderAgent to summarise.
    """

    @abstractmethod
    def search(self, root: Path, query: str) -> list[str]:
        """
        Search for content relevant to `query` under `root`.

        Args:
            root: The user's workspace root directory.
            query: Free-text or regex query string.

        Returns:
            List of matching text snippets (file content fragments).
        """
        ...


class RegexSearch(SearchStrategy):
    """
    Default search: scan all text files under root, return lines matching query as a regex.

    Falls back to a literal substring match if the query is not a valid regex.
    Returns at most `max_results` matching lines across all files.
    """

    def __init__(self, max_results: int = 50):
        self.max_results = max_results

    def search(self, root: Path, query: str) -> list[str]:
        if not root.exists():
            return []

        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        results: list[str] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            rel = path.relative_to(root)
            for line in text.splitlines():
                if pattern.search(line):
                    results.append(f"[{rel}] {line.strip()}")
                    if len(results) >= self.max_results:
                        return results

        return results
