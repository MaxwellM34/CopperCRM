#!/usr/bin/env python3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EDITOR_RULES_FILE = BASE_DIR / "prompts" / "editor_rules.txt"

def get_editor_version() -> str:
    """
    Read the first line of prompts/editor_rules.txt to get a version tag.
    Expected format of first line: '# VERSION: v001'
    If missing, returns 'unknown'.
    """
    try:
        text = EDITOR_RULES_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "unknown"

    lines = text.splitlines()
    if not lines:
        return "unknown"

    first = lines[0].strip()
    if first.startswith("# VERSION:"):
        return first.split(":", 1)[1].strip()
    return "unknown"


def edit_email(text: str) -> str:
    """
    Simple editor for now:
    - Replace every occurrence of 'Copper' with 'Copper McInnis'.
    """
    return text.replace("Copper", "Copper McInnis")
