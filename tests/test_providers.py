import unittest

from packages.providers import MockDecisionProvider


class MockDecisionProviderTests(unittest.TestCase):
    def test_binary_defaults_to_neutral_probability(self):
        provider = MockDecisionProvider()
        result = provider.binary("is_emergency", {}, "Is this urgent?")
        self.assertEqual(result, {"p_true": 0.5, "p_false": 0.5})

    def test_binary_accepts_plain_boolean_response(self):
        provider = MockDecisionProvider({"is_emergency": True})
        result = provider.binary("is_emergency", {}, "Is this urgent?")
        self.assertEqual(result, {"p_true": 1.0, "p_false": 0.0})

    def test_binary_normalizes_configured_probabilities(self):
        provider = MockDecisionProvider({"is_emergency": {"p_true": 3, "p_false": 1}})
        result = provider.binary("is_emergency", {}, "Is this urgent?")
        self.assertEqual(result, {"p_true": 0.75, "p_false": 0.25})

    def test_categorical_defaults_to_uniform_distribution(self):
        provider = MockDecisionProvider()
        result = provider.categorical(
            "category", {}, "What category?", ["technical", "billing", "other"]
        )
        self.assertAlmostEqual(sum(result.values()), 1.0)
        self.assertEqual(len(result), 3)

    def test_categorical_normalizes_configured_probabilities(self):
        provider = MockDecisionProvider({"category": {"technical": 3, "billing": 1}})
        result = provider.categorical("category", {}, "What category?", ["technical", "billing"])
        self.assertEqual(result, {"technical": 0.75, "billing": 0.25})

    def test_scalar_defaults_to_scale_midpoint(self):
        provider = MockDecisionProvider()
        result = provider.scalar("confidence", {}, "How confident?", {"min": 0, "max": 10})
        self.assertEqual(result, {"score": 5.0, "confidence": 1.0})

    def test_scalar_rejects_score_outside_scale(self):
        provider = MockDecisionProvider({"confidence": {"score": 20}})
        with self.assertRaisesRegex(ValueError, "outside scale"):
            provider.scalar("confidence", {}, "How confident?", {"min": 0, "max": 10})

    def test_scalar_rejects_invalid_confidence(self):
        provider = MockDecisionProvider({"confidence": {"score": 5, "confidence": 1.5}})
        with self.assertRaisesRegex(ValueError, "confidence must be between"):
            provider.scalar("confidence", {}, "How confident?", {"min": 0, "max": 10})

    def test_categorical_rejects_negative_probability(self):
        provider = MockDecisionProvider({"category": {"technical": -1, "billing": 3}})
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            provider.categorical("category", {}, "What category?", ["technical", "billing"])


if __name__ == "__main__":
    unittest.main()
