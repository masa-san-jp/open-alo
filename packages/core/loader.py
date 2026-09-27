"""Load JSON or YAML ALO documents without making the compiler parse files."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class LoadError(ValueError):
    """Raised when an ALO source file cannot be parsed."""


def load_document(path: str | Path) -> dict[str, Any]:
    """Load a JSON or YAML mapping.

    PyYAML is used when available. The development environment also supports a
    dependency-free Ruby Psych fallback, keeping the reference CLI usable
    before a package manager setup exists.
    """

    source_path = Path(path)
    if not source_path.is_file():
        raise LoadError(f"file not found: {source_path}")
    text = source_path.read_text(encoding="utf-8")
    suffix = source_path.suffix.lower()
    try:
        if suffix == ".json":
            document = json.loads(text)
        else:
            document = _load_yaml(text, source_path)
    except (json.JSONDecodeError, ValueError, OSError) as error:
        raise LoadError(f"could not parse {source_path}: {error}") from error
    if not isinstance(document, dict):
        raise LoadError(f"document root must be an object: {source_path}")
    return document


def _load_yaml(text: str, source_path: Path) -> Any:
    try:
        import yaml  # type: ignore[import-not-found]

        return yaml.safe_load(text)
    except ImportError:
        pass

    ruby = shutil.which("ruby")
    if not ruby:
        raise LoadError(
            "YAML support requires PyYAML or Ruby; use JSON or install PyYAML"
        )
    script = (
        "require 'yaml'; require 'json'; "
        "puts JSON.generate(YAML.safe_load(File.read(ARGV[0]), aliases: false))"
    )
    result = subprocess.run(
        [ruby, "-e", script, str(source_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = result.stderr.strip() or "Ruby YAML parser failed"
        raise LoadError(message)
    return json.loads(result.stdout)
