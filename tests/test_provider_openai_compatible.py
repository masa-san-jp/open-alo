import json
import unittest

from packages.providers import (
    OpenAICompatibleProvider,
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


def chat_response(content):
    return {"choices": [{"message": {"content": json.dumps(content)}}]}


class ScriptedTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0
        self.payloads = []

    def __call__(self, payload):
        self.calls += 1
        self.payloads.append(payload)
        response = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if isinstance(response, BaseException):
            raise response
        return response


class OpenAICompatibleProviderTests(unittest.TestCase):
    def test_binary_fixtures_return_normalized_results(self):
        for index, fixture in enumerate(BINARY_FIXTURES):
            transport = ScriptedTransport(chat_response({"p_true": 0.2 + index * 0.3}))
            provider = OpenAICompatibleProvider("test-model", transport=transport)

            result = provider.binary(
                fixture["decision_id"], fixture["state"], fixture["question"]
            )

            assert_conforms_binary(result)
            self.assertEqual(transport.calls, 1)
            self.assertEqual(transport.payloads[0]["model"], "test-model")

    def test_categorical_fixtures_return_normalized_results(self):
        for index, fixture in enumerate(CATEGORICAL_FIXTURES):
            probabilities = {
                option: float(index + option_index + 1)
                for option_index, option in enumerate(fixture["options"])
            }
            transport = ScriptedTransport(chat_response(probabilities))
            provider = OpenAICompatibleProvider("test-model", transport=transport)

            result = provider.categorical(
                fixture["decision_id"],
                fixture["state"],
                fixture["question"],
                fixture["options"],
            )

            assert_conforms_categorical(result, fixture["options"])
            self.assertIn(json.dumps(fixture["options"]), transport.payloads[0]["messages"][0]["content"])
            self.assertIn("options", transport.payloads[0]["messages"][1]["content"])

    def test_scalar_fixtures_return_normalized_results(self):
        for fixture in SCALAR_FIXTURES:
            minimum = float(fixture["scale"]["min"])
            maximum = float(fixture["scale"]["max"])
            response = {
                "score": minimum + (maximum - minimum) * 0.25,
                "confidence": 0.8,
            }
            transport = ScriptedTransport(chat_response(response))
            provider = OpenAICompatibleProvider("test-model", transport=transport)

            result = provider.scalar(
                fixture["decision_id"],
                fixture["state"],
                fixture["question"],
                fixture["scale"],
            )

            assert_conforms_scalar(result, fixture["scale"])
            self.assertIn("scale", transport.payloads[0]["messages"][1]["content"])

    def test_timeout_is_retried_then_succeeds(self):
        transport = ScriptedTransport(
            ProviderTimeoutError("temporary timeout"),
            ProviderTimeoutError("temporary timeout"),
            chat_response({"p_true": 0.75}),
        )
        provider = OpenAICompatibleProvider("test-model", transport=transport)

        result = provider.binary("decision", {}, "Is it true?")

        assert_conforms_binary(result)
        self.assertEqual(transport.calls, 3)

    def test_rate_limit_is_retried_and_eventually_raised(self):
        transport = ScriptedTransport(ProviderRateLimitError("rate limited"))
        provider = OpenAICompatibleProvider("test-model", transport=transport)

        with self.assertRaises(ProviderRateLimitError):
            provider.binary("decision", {}, "Is it true?")

        self.assertEqual(transport.calls, 3)

    def test_non_json_content_raises_provider_response_error(self):
        transport = ScriptedTransport(
            {"choices": [{"message": {"content": "not JSON"}}]}
        )
        provider = OpenAICompatibleProvider("test-model", transport=transport)

        with self.assertRaises(ProviderResponseError):
            provider.binary("decision", {}, "Is it true?")

    def test_missing_expected_keys_raise_provider_response_error(self):
        transport = ScriptedTransport(chat_response({"other": 0.5}))
        provider = OpenAICompatibleProvider("test-model", transport=transport)

        with self.assertRaises(ProviderResponseError):
            provider.binary("decision", {}, "Is it true?")

    def test_normalizer_value_errors_propagate(self):
        cases = (
            (
                "binary",
                ScriptedTransport(chat_response({"p_true": -0.1})),
                lambda provider: provider.binary("decision", {}, "Is it true?"),
            ),
            (
                "categorical",
                ScriptedTransport(chat_response({"yes": -1.0, "no": 1.0})),
                lambda provider: provider.categorical(
                    "decision", {}, "Which?", ["yes", "no"]
                ),
            ),
            (
                "scalar",
                ScriptedTransport(
                    chat_response({"score": 11.0, "confidence": 0.9})
                ),
                lambda provider: provider.scalar(
                    "decision", {}, "How high?", {"min": 0.0, "max": 10.0}
                ),
            ),
        )
        for name, transport, call in cases:
            with self.subTest(name=name):
                provider = OpenAICompatibleProvider("test-model", transport=transport)
                with self.assertRaises(ValueError):
                    call(provider)


if __name__ == "__main__":
    unittest.main()
