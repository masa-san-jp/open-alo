"""Packaging, local Git installation, registry discovery, and badges."""

from .badge import badge_markdown
from .build import build_package
from .errors import PackagingError
from .install import install_from_git
from .manifest import load_manifest, validate_manifest
from .registry import load_registry, search_registry

__all__ = [
    "PackagingError",
    "badge_markdown",
    "build_package",
    "install_from_git",
    "load_manifest",
    "load_registry",
    "search_registry",
    "validate_manifest",
]
