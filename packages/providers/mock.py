"""Deterministic provider for local runs and tests."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from .capabilities import ProviderCapabilities
from .normalize import normalize_binary, normalize_categorical, normalize_scalar


class MockDecisionProvider:
    """Return configured responses, with neutral deterministic fallbacks.

    Responses are keyed by decision ID. A binary response can be a boolean or
    ``{"p_true": 0.9, "p_false": 0.1}``; categorical responses are mappings
    of option to probability; scalar responses use ``score`` and optionally
    ``confidence``.
    """

    name = "mock"
    model = "deterministic"
    capabilities = ProviderCapabilities(
        decision_types=frozenset({"binary", "categorical", "scalar"})
    )

    def __init__(self, responses: Mapping[str, Any] | None = None):
        self.responses = copy.deepcopy(dict(responses or {}))

    def binary(
        self, decision_id: str, state: dict[str, Any], question: str
    ) -> dict[str, float]:
        response = self.responses.get(decision_id, {})
        if isinstance(response, bool):
            return {"p_true": 1.0 if response else 0.0, "p_false": 0.0 if response else 1.0}
        if not isinstance(response, Mapping):
            response = {}
        p_true = float(response.get("p_true", 0.5))
        p_false = float(response.get("p_false", 1.0 - p_true))
        return normalize_binary(p_true, p_false)

    def categorical(
        self,
        decision_id: str,
        state: dict[str, Any],
        question: str,
        options: list[str],
    ) -> dict[str, float]:
        response = self.responses.get(decision_id, {})
        if not isinstance(response, Mapping):
            response = {}
        probabilities = {option: float(response.get(option, 0.0)) for option in options}
        if sum(probabilities.values()) <= 0:
            probabilities = {option: 1.0 for option in options}
        return normalize_categorical(probabilities)

    def scalar(
        self,
        decision_id: str,
        state: dict[str, Any],
        question: str,
        scale: dict[str, Any],
    ) -> dict[str, float]:
        response = self.responses.get(decision_id, {})
        if not isinstance(response, Mapping):
            response = {}
        minimum = float(scale.get("min", 0))
        maximum = float(scale.get("max", 1))
        score = float(response.get("score", (minimum + maximum) / 2))
        confidence = float(response.get("confidence", 1.0))
        try:
            return normalize_scalar(score, confidence, scale)
        except ValueError as error:
            if score < minimum or score > maximum:
                raise ValueError(f"mock scalar score outside scale for {decision_id}") from error
            raise ValueError(
                f"mock scalar confidence must be between 0 and 1 for {decision_id}"
            ) from error
