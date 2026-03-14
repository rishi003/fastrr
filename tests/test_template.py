"""Unit tests for template loading and formatting utilities."""

import json
from pathlib import Path

import pytest

from fastrr.template import TemplateFile, format_template, load_template


def test_load_template_default() -> None:
    files = load_template()
    names = [f.name for f in files]
    assert "preferences.md" in names
    assert "history.jsonl" in names
    assert "facts.md" in names


def test_load_template_all_entries_have_name_and_description() -> None:
    for f in load_template():
        assert f.name
        assert f.description


def test_load_template_custom(tmp_path: Path) -> None:
    custom = tmp_path / "custom.json"
    custom.write_text(
        json.dumps(
            {
                "files": [
                    {"name": "notes.md", "description": "General notes"},
                    {"name": "log.jsonl", "description": "Event log"},
                ]
            }
        )
    )
    files = load_template(custom)
    assert len(files) == 2
    assert files[0] == TemplateFile(name="notes.md", description="General notes")
    assert files[1] == TemplateFile(name="log.jsonl", description="Event log")


def test_format_template() -> None:
    files = [
        TemplateFile(name="a.md", description="Alpha file"),
        TemplateFile(name="b.jsonl", description="Beta file"),
    ]
    result = format_template(files)
    assert result == "- a.md: Alpha file\n- b.jsonl: Beta file"


def test_load_template_none_uses_default() -> None:
    assert load_template(None) == load_template()
