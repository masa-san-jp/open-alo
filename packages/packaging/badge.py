"""Generate compatibility badge Markdown without network access."""

from __future__ import annotations

from urllib.parse import quote


def badge_markdown(spec_version: str) -> str:
    """Return a shields.io-style Open ALO compatibility badge snippet."""

    encoded_version = quote(str(spec_version), safe="")
    return (
        f"[![Open ALO](https://img.shields.io/badge/Open%20ALO-{encoded_version}-blue)]"
        "(https://github.com/masa-san-jp/open-alo)"
    )
