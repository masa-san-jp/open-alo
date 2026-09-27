import copy
import unittest

from packages.core import ValidationError, ensure_valid, validate_alo

from test_compiler import MINIMAL_ALO


class ValidatorTests(unittest.TestCase):
    def test_accepts_minimal_document(self):
        self.assertEqual(validate_alo(MINIMAL_ALO), [])
        ensure_valid(MINIMAL_ALO)  # must not raise

    def test_accepts_threshold_version(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["threshold_version"] = "2026-01-01"
        self.assertEqual(validate_alo(document), [])

    def test_rejects_empty_threshold_version(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["threshold_version"] = ""
        self.assertIn(
            "alo.threshold_version must be a non-empty string",
            validate_alo(document),
        )

    def test_rejects_missing_required_field(self):
        document = copy.deepcopy(MINIMAL_ALO)
        del document["alo"]["purpose"]
        errors = validate_alo(document)
        self.assertIn("alo.purpose is required", errors)

    def test_rejects_wrong_spec_version(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["spec_version"] = "0.2"
        errors = validate_alo(document)
        self.assertIn("alo.spec_version must be '0.1'", errors)

    def test_rejects_invalid_identifier(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["id"] = "not an id"
        errors = validate_alo(document)
        self.assertTrue(any("alo.id" in error for error in errors))

    def test_rejects_duplicate_decision_id(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["decisions"].append(copy.deepcopy(document["alo"]["decisions"][0]))
        errors = validate_alo(document)
        self.assertIn("duplicate decision id: is_emergency", errors)

    def test_rejects_categorical_decision_without_options(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["decisions"][1]["options"] = {}
        errors = validate_alo(document)
        self.assertTrue(
            any("options must contain at least one option" in error for error in errors)
        )

    def test_rejects_duplicate_rule_priority(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["transition_rules"][1]["priority"] = 10
        errors = validate_alo(document)
        self.assertIn("duplicate transition rule priority: 10", errors)

    def test_rejects_rule_target_not_in_state_or_output(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["transition_rules"][0]["set"]["missing_field"] = "x"
        errors = validate_alo(document)
        self.assertTrue(
            any("is not a state or output field" in error for error in errors)
        )

    def test_rejects_undeclared_stop_condition(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["transition_rules"][0]["stop_condition"] = "not_declared"
        errors = validate_alo(document)
        self.assertTrue(
            any("must be declared in alo.stop_conditions" in error for error in errors)
        )

    def test_accepts_declared_stop_condition(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["stop_conditions"] = ["terminal_state", "human_review_required"]
        self.assertEqual(validate_alo(document), [])

    def test_ensure_valid_raises_with_errors(self):
        document = copy.deepcopy(MINIMAL_ALO)
        del document["alo"]["purpose"]
        with self.assertRaises(ValidationError) as context:
            ensure_valid(document)
        self.assertIn("alo.purpose is required", context.exception.errors)


if __name__ == "__main__":
    unittest.main()
