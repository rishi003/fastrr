"""Unit tests for RegexSearch."""

from pathlib import Path

import pytest

from fastrr.agents.search import RegexSearch


def test_search_nonexistent_root_returns_empty(tmp_path: Path) -> None:
    root = tmp_path / "missing"
    search = RegexSearch()
    assert search.search(root, "anything") == []


def test_search_valid_regex_returns_matching_lines(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("foo here\nno match\nbar there")
    (tmp_path / "b.txt").write_text("baz only")
    search = RegexSearch()
    results = search.search(tmp_path, "foo|bar")
    assert len(results) == 2
    assert any("[a.txt] foo here" in r for r in results)
    assert any("[a.txt] bar there" in r for r in results)
    assert not any("b.txt" in r for r in results)


def test_search_invalid_regex_falls_back_to_literal(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("literal a(b paren")
    search = RegexSearch()
    results = search.search(tmp_path, "a(b")
    assert len(results) == 1
    assert "[f.txt] literal a(b paren" in results[0]


def test_search_case_insensitive(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("Foo BAR")
    search = RegexSearch()
    results = search.search(tmp_path, "foo")
    assert len(results) == 1
    assert "Foo" in results[0]
    results = search.search(tmp_path, "bar")
    assert len(results) == 1
    assert "BAR" in results[0]


def test_search_max_results_cap(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("match\nmatch\nmatch\nmatch")
    search = RegexSearch(max_results=2)
    results = search.search(tmp_path, "match")
    assert len(results) == 2


def test_search_skips_directories(tmp_path: Path) -> None:
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir" / "f.txt").write_text("match")
    search = RegexSearch()
    results = search.search(tmp_path, "match")
    assert len(results) == 1
    assert "dir/f.txt" in results[0] or "dir\\f.txt" in results[0]


def test_search_read_errors_ignored(tmp_path: Path) -> None:
    (tmp_path / "good.txt").write_text("match")
    # Non-UTF-8 / binary is read with errors="ignore"; should not crash
    (tmp_path / "binary.bin").write_bytes(b"\xff\xfe\x00")
    search = RegexSearch()
    results = search.search(tmp_path, "match")
    assert len(results) == 1
    assert "good.txt" in results[0]
