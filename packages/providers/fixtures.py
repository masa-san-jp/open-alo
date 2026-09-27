"""Provider-independent shape and invariant fixtures."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


BINARY_FIXTURES = [
    {
        "decision_id": "is_urgent",
        "state": {"priority": "unknown"},
        "question": "Is this request urgent?",
    },
    {
        "decision_id": "needs_review",
        "state": {"risk_score": 0.4},
        "question": "Does this request need human review?",
    },
]

CATEGORICAL_FIXTURES = [
    {
        "decision_id": "request_category",
        "state": {"summary": "A technical issue"},
        "question": "Which category best fits this request?",
        "options": ["technical", "billing", "other"],
    },
    {
        "decision_id": "sentiment",
        "state": {"message": "The customer is waiting"},
        "question": "What is the message sentiment?",
        "options": ["positive", "neutral", "negative"],
    },
]

SCALAR_FIXTURES = [
    {
        "decision_id": "confidence",
        "state": {"evidence": "partial"},
        "question": "How confident are you in this assessment?",
        "scale": {"min": 0.0, "max": 1.0},
    },
    {
        "decision_id": "priority",
        "state": {"impact": "moderate"},
        "question": "How high is the priority?",
        "scale": {"min": 1.0, "max": 5.0},
    },
]


def assert_conforms_binary(result: Mapping[str, Any]) -> None:
    """Assert that a binary result has the required normalized shape."""

    assert set(result) == {"p_true", "p_false"}
    assert all(isinstance(result[key], float) for key in ("p_true", "p_false"))
    assert math.isclose(result["p_true"] + result["p_false"], 1.0, abs_tol=1e-9)


def assert_conforms_categorical(
    result: Mapping[str, Any], options: list[str]
) -> None:
    """Assert that a categorical result covers exactly its declared options."""

    assert set(result) == set(options)
    assert all(isinstance(value, float) for value in result.values())
    assert math.isclose(sum(result.values()), 1.0, abs_tol=1e-9)


def assert_conforms_scalar(result: Mapping[str, Any], scale: Mapping[str, float]) -> None:
    """Assert that a scalar result is within its declared bounds."""

    assert set(result) == {"score", "confidence"}
    score = result["score"]
    confidence = result["confidence"]
    assert isinstance(score, float)
    assert isinstance(confidence, float)
    assert float(scale["min"]) <= score <= float(scale["max"])
    assert 0.0 <= confidence <= 1.0
