"""Tests for the provisional Jev provider boundary."""

from __future__ import annotations

import unittest
from typing import Any

from packages.providers.errors import (
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from packages.providers.fixtures import (
    BINARY_FIXTURES,
    CATEGORICAL_FIXTURES,
    SCALAR_FIXTURES,
    assert_conforms_binary,
    assert_conforms_categorical,
    assert_conforms_scalar,
)
from packages.providers.jev import JevProvider


class FakeJevClient:
    """Deterministic in-memory client implementing the provisional protocol."""

    def __init__(self) -> None:
        self.binary_response: dict[str, Any] = {"p_true": 0.75}
        self.categorical_response: dict[str, Any] = {
            "technical": 0.6,
            "billing": 0.3,
            "other": 0.1,
        }
        self.scalar_response: dict[str, Any] | None = None

    def noul(self, question: str, context: dict) -> dict:
        return dict(self.binary_response)

    def choice(self, question: str, context: dict, options: list[str]) -> dict:
        return dict(self.categorical_response)

    def score(self, question: str, context: dict, scale: dict) -> dict:
        if self.scalar_response is not None:
            return dict(self.scalar_response)
        return {
            "score": (float(scale.get("min", 0)) + float(scale.get("max", 1))) / 2,
            "confidence": 0.8,
        }


class RetryingFakeJevClient(FakeJevClient):
    def __init__(self, method: str, error: Exception, failures: int = 2) -> None:
        super().__init__()
        self.method = method
        self.error = error
        self.failures = failures

    def _maybe_fail(self, method: str) -> None:
        if self.method == method and self.failures:
            self.failures -= 1
            raise self.error

    def noul(self, question: str, context: dict) -> dict:
        self._maybe_fail("noul")
        return super().noul(question, context)

    def choice(self, question: str, context: dict, options: list[str]) -> dict:
        self._maybe_fail("choice")
        return super().choice(question, context, options)

    def score(self, question: str, context: dict, scale: dict) -> dict:
        self._maybe_fail("score")
        return super().score(question, context, scale)


class JevProviderTests(unittest.TestCase):
    def test_binary_fixtures_produce_normalized_results(self) -> None:
        provider = JevProvider(FakeJevClient())
        for fixture in BINARY_FIXTURES:
            with self.subTest(decision_id=fixture["decision_id"]):
                result = provider.binary(**fixture)
                assert_conforms_binary(result)

    def test_categorical_fixtures_produce_normalized_results(self) -> None:
        provider = JevProvider(FakeJevClient())
        for fixture in CATEGORICAL_FIXTURES:
            with self.subTest(decision_id=fixture["decision_id"]):
                result = provider.categorical(**fixture)
                assert_conforms_categorical(result, fixture["options"])

    def test_scalar_fixtures_produce_normalized_results(self) -> None:
        provider = JevProvider(FakeJevClient())
        for fixture in SCALAR_FIXTURES:
            with self.subTest(decision_id=fixture["decision_id"]):
                result = provider.scalar(**fixture)
                assert_conforms_scalar(result, fixture["scale"])

    def test_timeout_twice_then_success_retries_each_primitive(self) -> None:
        for method, invoke in (
            (
                "noul",
                lambda provider: provider.binary(
                    "decision", {}, "question"
                ),
            ),
            (
                "choice",
                lambda provider: provider.categorical(
                    "decision", {}, "question", ["technical", "billing", "other"]
                ),
            ),
            (
                "score",
                lambda provider: provider.scalar(
                    "decision", {}, "question", {"min": 0.0, "max": 1.0}
                ),
            ),
        ):
            with self.subTest(method=method):
                provider = JevProvider(
                    RetryingFakeJevClient(method, ProviderTimeoutError("try again"))
                )
                result = invoke(provider)
                if method == "noul":
                    assert_conforms_binary(result)
                elif method == "choice":
                    assert_conforms_categorical(
                        result, ["technical", "billing", "other"]
                    )
                else:
                    assert_conforms_scalar(result, {"min": 0.0, "max": 1.0})

    def test_rate_limit_is_re_raised_after_retry_exhaustion(self) -> None:
        client = RetryingFakeJevClient(
            "noul", ProviderRateLimitError("slow down"), failures=3
        )
        with self.assertRaises(ProviderRateLimitError):
            JevProvider(client).binary("decision", {}, "question")

    def test_missing_binary_key_raises_provider_response_error(self) -> None:
        client = FakeJevClient()
        client.binary_response = {"p_false": 1.0}
        with self.assertRaisesRegex(ProviderResponseError, "p_true"):
            JevProvider(client).binary("decision", {}, "question")

    def test_out_of_bounds_scalar_score_propagates_value_error(self) -> None:
        client = FakeJevClient()
        client.scalar_response = {"score": 2.0, "confidence": 0.8}
        with self.assertRaises(ValueError):
            JevProvider(client).scalar(
                "decision", {}, "question", {"min": 0.0, "max": 1.0}
            )


if __name__ == "__main__":
    unittest.main()
