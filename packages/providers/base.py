"""Provider-neutral decision interface."""

from __future__ import annotations

from typing import Any, Protocol


class DecisionProvider(Protocol):
    """Return typed probabilistic decisions without mutating runtime state."""

    name: str
    model: str | None

    def binary(
        self, decision_id: str, state: dict[str, Any], question: str
    ) -> dict[str, float]: ...

    def categorical(
        self,
        decision_id: str,
        state: dict[str, Any],
        question: str,
        options: list[str],
    ) -> dict[str, float]: ...

    def scalar(
        self,
        decision_id: str,
        state: dict[str, Any],
        question: str,
        scale: dict[str, Any],
    ) -> dict[str, float]: ...
