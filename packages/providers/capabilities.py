"""Capabilities advertised by a decision provider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapabilities:
    """Describe the decision primitives and transport features a provider supports."""

    decision_types: frozenset[str]
    supports_batching: bool = False
    supports_streaming: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        allowed = frozenset({"binary", "categorical", "scalar"})
        decision_types = frozenset(self.decision_types)
        if not decision_types <= allowed:
            raise ValueError("decision_types must be a subset of the supported decision types")
        object.__setattr__(self, "decision_types", decision_types)
