"""Fastrr: a semantic memory layer for AI applications."""

from fastrr.agents.search import RegexSearch, SearchStrategy
from fastrr.client import Fastrr
from fastrr.services.repo_manager import GitRepoManager, RepoManager

__all__ = ["Fastrr", "RepoManager", "GitRepoManager", "SearchStrategy", "RegexSearch"]
