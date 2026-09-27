"""Install Open ALO packages from local or remote Git repositories."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .build import build_package
from .errors import PackagingError
from .manifest import load_manifest, validate_manifest


def install_from_git(
    repo_url_or_local_path: str | Path,
    dest_dir: str | Path,
    *,
    ref: str = "HEAD",
    subdir: str | None = None,
) -> Path:
    """Clone a Git repository, validate its package, and copy it to ``dest_dir``."""

    with tempfile.TemporaryDirectory(prefix="alo-package-") as temporary:
        clone_dir = Path(temporary) / "repository"
        command = ["git", "clone", "--depth", "1"]
        if ref != "HEAD":
            command.extend(["--branch", ref])
        command.extend([str(repo_url_or_local_path), str(clone_dir)])
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as error:
            raise PackagingError(f"could not run git clone: {error}") from error
        if result.returncode:
            message = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
            raise PackagingError(f"git clone failed: {message}")

        package_source = clone_dir if subdir is None else _subdirectory(clone_dir, subdir)
        manifest_path = package_source / "alo-package.json"
        if not manifest_path.is_file():
            raise PackagingError(f"manifest file not found in cloned package: {manifest_path}")
        manifest = load_manifest(manifest_path)
        errors = validate_manifest(manifest)
        if errors:
            raise PackagingError("invalid package manifest: " + "; ".join(errors))
        try:
            return build_package(package_source, dest_dir)
        except PackagingError:
            raise


def _subdirectory(clone_dir: Path, subdir: str) -> Path:
    candidate = (clone_dir / subdir).resolve()
    root = clone_dir.resolve()
    if candidate != root and root not in candidate.parents:
        raise PackagingError("subdir must stay within the cloned repository")
    if not candidate.is_dir():
        raise PackagingError(f"package subdir not found in cloned repository: {subdir}")
    return candidate
