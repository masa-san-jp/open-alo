"""Provisional Jev adapter boundary.

This module assumes the injected ``JevClient`` returns these raw shapes:

* ``noul(question, context)`` returns ``{"p_true": <float>}``, optionally
  with ``"p_false": <float>``.
* ``choice(question, context, options)`` returns a mapping from each option
  name to a probability float, for example ``{"yes": 0.8, "no": 0.2}``.
* ``score(question, context, scale)`` returns
  ``{"score": <float>, "confidence": <float>}``.

These shapes and the ``JevClient`` protocol are provisional interfaces pending
real Jev API documentation. This is not a verified integration with the real
Jev service; a real Jev SDK or client can be injected later without changing
``DecisionProvider`` callers.
"""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any, Protocol

from .capabilities import ProviderCapabilities
from .errors import ProviderResponseError
from .normalize import normalize_binary, normalize_categorical, normalize_scalar
from .retry import call_with_retry


class JevClient(Protocol):
    """Minimal injectable client boundary for Jev's published primitives."""

    def noul(self, question: str, context: dict) -> dict: ...

    def choice(
        self, question: str, context: dict, options: list[str]
    ) -> dict: ...

    def score(self, question: str, context: dict, scale: dict) -> dict: ...


class JevProvider:
    """DecisionProvider adapter backed by an injected provisional Jev client."""

    name = "jev"
    capabilities = ProviderCapabilities(
        decision_types=frozenset({"binary", "categorical", "scalar"})
    )

    def __init__(
        self,
        client: JevClient,
        *,
        model: str = "jev",
        config: dict[str, Any] | None = None,
    ) -> None:
        self._client = client
        self.model = model
        self.config = config

    def binary(
        self, decision_id: str, state: dict[str, Any], question: str
    ) -> dict[str, float]:
        response = call_with_retry(lambda: self._client.noul(question, state))
        result = self._require_mapping(response, "binary")
        if "p_true" not in result:
            raise ProviderResponseError(
                "Jev Noul response is missing required key 'p_true'"
            )
        p_true = self._require_number(result["p_true"], "Jev Noul 'p_true'")
        if "p_false" in result:
            p_false = self._require_number(result["p_false"], "Jev Noul 'p_false'")
        else:
            p_false = 1.0 - p_true
        return normalize_binary(p_true, p_false)

    def categorical(
        self,
        decision_id: str,
        state: dict[str, Any],
        question: str,
        options: list[str],
    ) -> dict[str, float]:
        response = call_with_retry(
            lambda: self._client.choice(question, state, options)
        )
        result = self._require_mapping(response, "categorical")
        probabilities = {}
        for option in options:
            value = result.get(option, 0.0)
            probabilities[option] = self._require_number(
                value, f"Jev Choice probability for option {option!r}"
            )
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
        response = call_with_retry(lambda: self._client.score(question, state, scale))
        result = self._require_mapping(response, "scalar")
        missing = [key for key in ("score", "confidence") if key not in result]
        if missing:
            raise ProviderResponseError(
                f"Jev Score response is missing required keys {missing}"
            )
        score = self._require_number(result["score"], "Jev Score 'score'")
        confidence = self._require_number(
            result["confidence"], "Jev Score 'confidence'"
        )
        return normalize_scalar(score, confidence, scale)

    @staticmethod
    def _require_mapping(response: Any, decision_type: str) -> Mapping[str, Any]:
        if not isinstance(response, Mapping):
            raise ProviderResponseError(
                f"Jev {decision_type} response must be a mapping"
            )
        return response

    @staticmethod
    def _require_number(value: Any, field: str) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ProviderResponseError(f"{field} must be a number")
        return float(value)
