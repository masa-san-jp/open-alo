"""Load and validate Draft 0.1 Open ALO package manifests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from packages.core import LoadError, load_document, validate_alo

from .errors import PackagingError

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_REQUIRED_FIELDS = ("name", "version", "spec_version", "entry")
_ALLOWED_FIELDS = set(_REQUIRED_FIELDS) | {"description", "homepage"}


class Manifest(dict[str, Any]):
    """A dict-compatible manifest that remembers where it was loaded from."""

    def __init__(self, values: dict[str, Any], path: Path):
        super().__init__(values)
        self.path = path


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load a JSON package manifest and retain its path for entry validation."""

    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise PackagingError(f"manifest file not found: {manifest_path}")
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagingError(f"could not parse manifest {manifest_path}: {error}") from error
    if not isinstance(value, dict):
        raise PackagingError(f"manifest root must be an object: {manifest_path}")
    return Manifest(value, manifest_path)


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Return manifest and referenced ALO validation errors."""

    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]

    for field in manifest:
        if field not in _ALLOWED_FIELDS:
            errors.append(f"unknown field: {field}")
    for field in _REQUIRED_FIELDS:
        if field not in manifest:
            errors.append(f"{field} is required")

    name = manifest.get("name")
    if not isinstance(name, str) or not name:
        errors.append("name must be a non-empty string")
    elif not _IDENTIFIER.fullmatch(name):
        errors.append("name must match ^[A-Za-z][A-Za-z0-9_-]*$")

    if not isinstance(manifest.get("version"), str) or not manifest.get("version"):
        errors.append("version must be a non-empty string")
    if manifest.get("spec_version") != "0.1":
        errors.append("spec_version must be '0.1'")

    entry = manifest.get("entry")
    entry_path: Path | None = None
    if not isinstance(entry, str) or not entry:
        errors.append("entry must be a non-empty relative path")
    else:
        entry_path = Path(entry)
        if entry_path.is_absolute() or ".." in entry_path.parts:
            errors.append("entry must be a relative path within the package")

    for field in ("description", "homepage"):
        if field in manifest and (
            not isinstance(manifest[field], str) or not manifest[field]
        ):
            errors.append(f"{field} must be a non-empty string when provided")

    if entry_path is None:
        return errors
    manifest_path = getattr(manifest, "path", None)
    if manifest_path is None:
        errors.append("entry cannot be checked because the manifest path is unavailable")
        return errors

    entry_file = manifest_path.parent / entry_path
    if not entry_file.is_file():
        errors.append(f"entry file not found: {entry}")
        return errors

    try:
        document = load_document(entry_file)
    except LoadError as error:
        errors.append(f"entry ALO could not be loaded: {error}")
        return errors
    errors.extend(f"entry ALO: {error}" for error in validate_alo(document))
    return errors
