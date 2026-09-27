"""Optional local/offline registry-discovery index helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import PackagingError


def load_registry(path: str | Path) -> dict[str, Any]:
    """Load a JSON registry index from local disk."""

    registry_path = Path(path)
    try:
        value = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagingError(f"could not load registry {registry_path}: {error}") from error
    if not isinstance(value, dict):
        raise PackagingError(f"registry root must be an object: {registry_path}")
    return value


def search_registry(registry: dict[str, Any], query: str) -> list[dict[str, Any]]:
    """Find entries whose name or description contains ``query`` case-insensitively."""

    needle = query.casefold()
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        return []
    matches: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "")
        description = entry.get("description", "")
        if needle in str(name).casefold() or needle in str(description).casefold():
            matches.append(entry)
    return matches
