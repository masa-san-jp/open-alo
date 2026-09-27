import unittest

from packages.runtime import ExpressionError, evaluate


class ExpressionsTests(unittest.TestCase):
    def test_evaluates_dotted_references_and_comparisons(self):
        context = {
            "decision": {"is_emergency": {"p_true": 0.95}},
            "threshold": {"emergency_accept": 0.9},
        }
        self.assertTrue(
            evaluate("decision.is_emergency.p_true >= threshold.emergency_accept", context)
        )

    def test_evaluates_bare_identifier(self):
        self.assertTrue(evaluate("no_previous_rule_matched", {"no_previous_rule_matched": True}))
        self.assertFalse(evaluate("no_previous_rule_matched", {"no_previous_rule_matched": False}))

    def test_supports_boolean_and_arithmetic_operators(self):
        context = {"state": {"count": 3}, "input": {"limit": 10}}
        self.assertTrue(evaluate("state.count > 0 and state.count < input.limit", context))
        self.assertEqual(evaluate("state.count * 2 + 1", context), 7)

    def test_supports_membership_and_not(self):
        context = {"decision": {"category": "billing"}}
        self.assertTrue(evaluate("decision.category in ['billing', 'technical']", context))
        self.assertTrue(evaluate("not (decision.category == 'other')", context))

    def test_rejects_unknown_identifier(self):
        with self.assertRaisesRegex(ExpressionError, "unknown identifier"):
            evaluate("missing_name", {})

    def test_rejects_unknown_attribute(self):
        with self.assertRaisesRegex(ExpressionError, "unknown attribute"):
            evaluate("state.missing", {"state": {}})

    def test_rejects_disallowed_syntax(self):
        with self.assertRaises(ExpressionError):
            evaluate("__import__('os')", {})
        with self.assertRaises(ExpressionError):
            evaluate("[x for x in state.values]", {"state": {"values": [1, 2]}})

    def test_rejects_syntax_errors(self):
        with self.assertRaisesRegex(ExpressionError, "invalid expression"):
            evaluate("state. ==", {})


if __name__ == "__main__":
    unittest.main()
