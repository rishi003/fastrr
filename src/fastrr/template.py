"""Memory template loading and formatting utilities."""

import json
from pathlib import Path
from typing import NamedTuple

_DEFAULT_TEMPLATE_PATH = Path(__file__).parent / "templates" / "default_template.json"


class TemplateFile(NamedTuple):
    """A single file entry in a memory template."""

    name: str
    description: str


def load_template(path: Path | None = None) -> list[TemplateFile]:
    """
    Load a memory template from a JSON file.

    If *path* is None the built-in default template is used
    (preferences.md, history.jsonl, facts.md).
    """
    template_path = path or _DEFAULT_TEMPLATE_PATH
    data = json.loads(template_path.read_text(encoding="utf-8"))
    return [TemplateFile(name=f["name"], description=f["description"]) for f in data["files"]]


def format_template(files: list[TemplateFile]) -> str:
    """Return the formatted Memory Files block injected into agent instructions."""
    return "\n".join(f"- {f.name}: {f.description}" for f in files)
