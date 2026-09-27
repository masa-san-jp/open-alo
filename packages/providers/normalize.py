"""Provider-independent normalization and validation helpers."""

from __future__ import annotations

from collections.abc import Mapping


def normalize_binary(p_true: float, p_false: float) -> dict[str, float]:
    """Normalize binary probabilities to a positive-total distribution."""

    return _normalize_probabilities({"p_true": p_true, "p_false": p_false})


def normalize_categorical(probabilities: Mapping[str, float]) -> dict[str, float]:
    """Normalize categorical probabilities to a positive-total distribution."""

    return _normalize_probabilities(dict(probabilities))


def normalize_scalar(
    score: float, confidence: float, scale: Mapping[str, float]
) -> dict[str, float]:
    """Validate and return a scalar score and its confidence."""

    score = float(score)
    confidence = float(confidence)
    minimum = float(scale.get("min", 0))
    maximum = float(scale.get("max", 1))
    if score < minimum or score > maximum:
        raise ValueError("scalar score outside scale")
    if not 0 <= confidence <= 1:
        raise ValueError("scalar confidence must be between 0 and 1")
    return {"score": score, "confidence": confidence}


def _normalize_probabilities(values: Mapping[str, float]) -> dict[str, float]:
    if any(value < 0 for value in values.values()):
        raise ValueError("probabilities cannot be negative")
    total = sum(values.values())
    if total <= 0:
        raise ValueError("probabilities must have a positive total")
    return {key: value / total for key, value in values.items()}
