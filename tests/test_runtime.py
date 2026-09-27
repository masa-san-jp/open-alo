import copy
import unittest

from packages.core import ValidationError, load_document
from packages.providers import MockDecisionProvider
from packages.runtime import run

from test_compiler import MINIMAL_ALO


EXAMPLE_DOCUMENT = load_document("examples/minimal/alo.yaml")


class RuntimeTests(unittest.TestCase):
    def test_emergency_input_escalates_and_stops(self):
        provider = MockDecisionProvider(
            {
                "is_emergency": {"p_true": 0.97, "p_false": 0.03},
                "category": {"technical": 1.0},
            }
        )
        record = run(
            EXAMPLE_DOCUMENT,
            {"message": "prod is down"},
            provider,
            run_id="run-1",
            timestamp="2026-01-01T00:00:00+00:00",
        )

        self.assertEqual(record["status"], "terminal_state")
        self.assertEqual(record["state_after"]["status"], "routed")
        self.assertEqual(record["output"]["action"], "escalate")
        self.assertEqual(record["run_id"], "run-1")
        matched_ids = [entry["id"] for entry in record["rule_trace"] if entry["matched"]]
        self.assertEqual(matched_ids, ["emergency"])

    def test_run_captures_provider_metadata(self):
        provider = MockDecisionProvider(
            {"is_emergency": {"p_true": 0.97}, "category": {"technical": 1.0}}
        )
        provider.config = {"temperature": 0}
        record = run(EXAMPLE_DOCUMENT, {"message": "prod is down"}, provider)

        self.assertEqual(record["provider"], "mock")
        self.assertEqual(record["provider_model"], "deterministic")
        self.assertEqual(record["provider_config"], {"temperature": 0})

    def test_uncertain_input_requires_human_review(self):
        provider = MockDecisionProvider(
            {
                "is_emergency": {"p_true": 0.1, "p_false": 0.9},
                "category": {"technical": 0.4, "billing": 0.3, "other": 0.3},
            }
        )
        record = run(EXAMPLE_DOCUMENT, {"message": "hello"}, provider)

        self.assertEqual(record["status"], "human_review_required")
        self.assertEqual(record["state_after"]["status"], "review")
        self.assertEqual(record["output"]["action"], "human_review")
        matched_ids = [entry["id"] for entry in record["rule_trace"] if entry["matched"]]
        self.assertEqual(matched_ids, ["uncertain"])

    def test_billing_category_routes_without_touching_other_fields(self):
        provider = MockDecisionProvider(
            {
                "is_emergency": {"p_true": 0.0, "p_false": 1.0},
                "category": {"billing": 0.9, "technical": 0.05, "other": 0.05},
            }
        )
        record = run(EXAMPLE_DOCUMENT, {"message": "invoice question"}, provider)

        self.assertEqual(record["output"]["action"], "route_billing")
        self.assertEqual(record["state_before"]["status"], "new")
        self.assertEqual(record["state_after"]["status"], "routed")

    def test_missing_required_input_reports_input_error(self):
        provider = MockDecisionProvider({})
        record = run(EXAMPLE_DOCUMENT, {}, provider)

        self.assertEqual(record["status"], "input_error")
        self.assertIn("message", record["error"])
        self.assertIsNone(record["state_after"])

    def test_unknown_input_field_reports_input_error(self):
        provider = MockDecisionProvider({})
        record = run(EXAMPLE_DOCUMENT, {"message": "hi", "extra": 1}, provider)

        self.assertEqual(record["status"], "input_error")
        self.assertIn("extra", record["error"])

    def test_decision_reads_are_limited_to_declared_references(self):
        provider = MockDecisionProvider(
            {"is_emergency": True, "category": {"technical": 1.0}}
        )
        record = run(EXAMPLE_DOCUMENT, {"message": "urgent outage"}, provider)

        for request in record["decision_requests"]:
            self.assertEqual(list(request["reads"]), ["input.message"])
            self.assertEqual(request["reads"]["input.message"], "urgent outage")

    def test_run_is_deterministic_for_same_input_and_provider_config(self):
        provider_a = MockDecisionProvider(
            {"is_emergency": {"p_true": 0.2}, "category": {"other": 0.9}}
        )
        provider_b = MockDecisionProvider(
            {"is_emergency": {"p_true": 0.2}, "category": {"other": 0.9}}
        )
        record_a = run(
            EXAMPLE_DOCUMENT,
            {"message": "misc question"},
            provider_a,
            run_id="fixed",
            timestamp="2026-01-01T00:00:00+00:00",
        )
        record_b = run(
            EXAMPLE_DOCUMENT,
            {"message": "misc question"},
            provider_b,
            run_id="fixed",
            timestamp="2026-01-01T00:00:00+00:00",
        )
        self.assertEqual(record_a, record_b)

    def test_derived_values_are_evaluated_before_rules(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["derived_values"] = {
            "message_length": {
                "type": "integer",
                "expression": "0",
            }
        }
        provider = MockDecisionProvider(
            {"is_emergency": {"p_true": 0.99}, "category": {"technical": 1.0}}
        )
        record = run(document, {"message": "hi"}, provider)
        self.assertEqual(record["status"], "terminal_state")

    def test_invalid_document_raises_execution_error(self):
        document = copy.deepcopy(MINIMAL_ALO)
        del document["alo"]["purpose"]
        provider = MockDecisionProvider({})
        with self.assertRaises(ValidationError):
            run(document, {"message": "hi"}, provider)


if __name__ == "__main__":
    unittest.main()
