"""Build plain-directory Open ALO packages."""

from __future__ import annotations

import shutil
from pathlib import Path

from .errors import PackagingError
from .manifest import load_manifest, validate_manifest

_EXCLUDED_NAMES = {".git", ".hg", ".svn", "__pycache__"}


def build_package(source_dir: str | Path, output_dir: str | Path) -> Path:
    """Validate and copy a package source tree into a versioned directory."""

    source = Path(source_dir)
    if not source.is_dir():
        raise PackagingError(f"package source directory not found: {source}")
    manifest = load_manifest(source / "alo-package.json")
    errors = validate_manifest(manifest)
    if errors:
        raise PackagingError("invalid package manifest: " + "; ".join(errors))

    target_root = Path(output_dir)
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / f"{manifest['name']}-{manifest['version']}"
    if target.exists():
        raise PackagingError(f"package output already exists: {target}")
    try:
        shutil.copytree(source, target, ignore=_ignore_source)
    except OSError as error:
        raise PackagingError(f"could not build package {target}: {error}") from error
    return target


def _ignore_source(directory: str, names: list[str]) -> set[str]:
    del directory
    return {
        name
        for name in names
        if name in _EXCLUDED_NAMES or name.startswith(".")
    }
