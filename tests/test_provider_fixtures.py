import unittest

from packages.providers import MockDecisionProvider
from packages.providers.fixtures import (
    BINARY_FIXTURES,
    CATEGORICAL_FIXTURES,
    SCALAR_FIXTURES,
    assert_conforms_binary,
    assert_conforms_categorical,
    assert_conforms_scalar,
)


class ProviderFixtureTests(unittest.TestCase):
    def setUp(self):
        self.provider = MockDecisionProvider()

    def test_mock_binary_results_conform(self):
        for fixture in BINARY_FIXTURES:
            with self.subTest(decision_id=fixture["decision_id"]):
                result = self.provider.binary(
                    fixture["decision_id"], fixture["state"], fixture["question"]
                )
                assert_conforms_binary(result)

    def test_mock_categorical_results_conform(self):
        for fixture in CATEGORICAL_FIXTURES:
            with self.subTest(decision_id=fixture["decision_id"]):
                result = self.provider.categorical(
                    fixture["decision_id"],
                    fixture["state"],
                    fixture["question"],
                    fixture["options"],
                )
                assert_conforms_categorical(result, fixture["options"])

    def test_mock_scalar_results_conform(self):
        for fixture in SCALAR_FIXTURES:
            with self.subTest(decision_id=fixture["decision_id"]):
                result = self.provider.scalar(
                    fixture["decision_id"],
                    fixture["state"],
                    fixture["question"],
                    fixture["scale"],
                )
                assert_conforms_scalar(result, fixture["scale"])


if __name__ == "__main__":
    unittest.main()
