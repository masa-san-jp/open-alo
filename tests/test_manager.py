import copy
import unittest

from packages.core import load_document
from packages.providers import JevProvider, MockDecisionProvider
from packages.runtime import ManagerError, run_manager


CANONICAL_MINIMAL = load_document("examples/canonical-minimal/alo.yaml")


class FakeJevClient:
    def __init__(self, p_true=0.9):
        self.p_true = p_true

    def noul(self, question, context):
        return {"p_true": self.p_true}

    def choice(self, question, context, options):
        raise NotImplementedError

    def score(self, question, context, scale):
        raise NotImplementedError


class ManagerRuntimeTests(unittest.TestCase):
    def test_runs_the_jev_calculation_step_with_a_mock_provider(self):
        provider = MockDecisionProvider({"analyze_comprehension": {"p_true": 0.9}})
        record = run_manager(
            CANONICAL_MINIMAL, {"user_message": "hello"}, provider
        )

        self.assertEqual(record["status"], "ok")
        self.assertEqual(len(record["jev_calls"]), 1)
        self.assertEqual(record["jev_calls"][0]["primitive"], "Noul")
        self.assertAlmostEqual(record["jev_calls"][0]["result"]["p_true"], 0.9)
        self.assertEqual(record["jev_calls"][0]["provider"], "mock")

    def test_runs_with_jev_provider_and_no_alo_specific_code(self):
        provider = JevProvider(FakeJevClient(p_true=0.95))
        record = run_manager(CANONICAL_MINIMAL, {"user_message": "hello"}, provider)

        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["jev_calls"][0]["provider"], "jev")
        self.assertAlmostEqual(record["jev_calls"][0]["result"]["p_true"], 0.95)

    def test_runs_without_any_provider_since_jev_is_optional(self):
        record = run_manager(CANONICAL_MINIMAL, {"user_message": "hello"})

        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["jev_calls"], [])
        calculation_step = record["manager_trace"][1]
        self.assertIn("skipped", calculation_step["calculation"])

    def test_non_optional_calculation_without_a_provider_errors(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        step = document["alo"]["managerObj"]["process"][1]
        del step["calculation"]["provider"]
        record = run_manager(document, {"user_message": "hello"})

        self.assertEqual(record["status"], "error")
        self.assertIn("requires a Decision Provider", record["error"])

    def test_language_defined_steps_are_recorded_but_not_fabricated(self):
        record = run_manager(CANONICAL_MINIMAL, {"user_message": "hello"})
        kinds = [entry.get("kind") for entry in record["manager_trace"]]
        self.assertEqual(kinds.count("language_defined"), 3)

    def test_missing_required_input_reports_input_error(self):
        record = run_manager(CANONICAL_MINIMAL, {})
        self.assertEqual(record["status"], "input_error")
        self.assertIn("user_message", record["error"])

    def test_output_maps_state_field_and_state_alias(self):
        record = run_manager(CANONICAL_MINIMAL, {"user_message": "hello"})
        self.assertEqual(record["output"]["State"], record["State_after"])
        self.assertIsNone(record["output"]["response"])

    def test_state_update_with_when_condition_gates_on_jev_result(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"][1]["state_updates"] = [
            {
                "key": "progress",
                "value": 0.1,
                "when": "jev.analyze_comprehension.p_true >= 0.85",
            }
        ]
        provider = MockDecisionProvider({"analyze_comprehension": {"p_true": 0.9}})
        record = run_manager(document, {"user_message": "hello"}, provider)

        self.assertEqual(record["State_after"]["progress"], 0.1)
        self.assertEqual(len(record["state_updates"]), 1)

    def test_state_update_when_condition_false_does_not_apply(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"][1]["state_updates"] = [
            {
                "key": "progress",
                "value": 0.1,
                "when": "jev.analyze_comprehension.p_true >= 0.85",
            }
        ]
        provider = MockDecisionProvider({"analyze_comprehension": {"p_true": 0.2}})
        record = run_manager(document, {"user_message": "hello"}, provider)

        self.assertEqual(record["State_after"]["progress"], 0.0)
        self.assertEqual(record["state_updates"], [])

    def test_choice_calculation_step(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"].append(
            {
                "id": "classify_topic",
                "action": "classify the topic",
                "calculation": {
                    "jev": {
                        "type": "Choice",
                        "question": "which topic?",
                        "options": {"math": "Math", "cs": "CS"},
                    }
                },
            }
        )
        provider = MockDecisionProvider(
            {
                "classify_topic": {"math": 0.8, "cs": 0.2},
                "analyze_comprehension": {"p_true": 0.9},
            }
        )
        record = run_manager(document, {"user_message": "hi"}, provider)

        self.assertEqual(record["status"], "ok")
        classify_call = next(
            call for call in record["jev_calls"] if call["step"] == "classify_topic"
        )
        self.assertEqual(classify_call["primitive"], "Choice")
        self.assertAlmostEqual(classify_call["result"]["math"], 0.8)
        self.assertAlmostEqual(classify_call["result"]["cs"], 0.2)

    def test_score_calculation_step(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"].append(
            {
                "id": "rate_difficulty",
                "action": "rate the difficulty",
                "calculation": {
                    "jev": {
                        "type": "Score",
                        "question": "how difficult?",
                        "scale": {"min": 0, "max": 10},
                    }
                },
            }
        )
        provider = MockDecisionProvider(
            {
                "rate_difficulty": {"score": 7, "confidence": 0.8},
                "analyze_comprehension": {"p_true": 0.9},
            }
        )
        record = run_manager(document, {"user_message": "hi"}, provider)

        self.assertEqual(record["status"], "ok")
        rate_call = next(
            call for call in record["jev_calls"] if call["step"] == "rate_difficulty"
        )
        self.assertEqual(rate_call["primitive"], "Score")
        self.assertEqual(rate_call["result"], {"score": 7.0, "confidence": 0.8})

    def test_records_which_sub_object_a_process_step_uses(self):
        # Conformance question 8 ("how does managerObj coordinate sub-objects?"):
        # a process step MAY declare `uses: <subObj id>`, and the runtime
        # records it in the trace as `subObj_used` -- this is the only part
        # of sub-object coordination the reference runtime tracks mechanically;
        # the rest is language-defined (section 23.5).
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"][1]["uses"] = "comprehension_analyzer"
        record = run_manager(document, {"user_message": "hello"}, MockDecisionProvider({}))
        self.assertEqual(
            record["manager_trace"][1]["subObj_used"], "comprehension_analyzer"
        )

    def test_dynamic_sub_obj_creation_is_recorded_explicitly(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"][0]["creates_sub_obj"] = {
            "id": "motivation_tracker",
            "parent": "learning_coach",
            "purpose": "Track learner motivation over time.",
            "reason": "Learner showed signs of frustration.",
        }
        record = run_manager(document, {"user_message": "hi"}, MockDecisionProvider({}))

        self.assertEqual(record["status"], "ok")
        self.assertEqual(len(record["dynamic_sub_obj_creations"]), 1)
        creation = record["dynamic_sub_obj_creations"][0]
        self.assertEqual(creation["id"], "motivation_tracker")
        self.assertEqual(creation["parent"], "learning_coach")
        self.assertEqual(creation["reason"], "Learner showed signs of frustration.")
        self.assertEqual(creation["run_id"], record["run_id"])
        self.assertEqual(record["manager_trace"][0]["creates_sub_obj"], "motivation_tracker")

    def test_dynamic_sub_obj_creation_rejects_duplicate_id(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"][0]["creates_sub_obj"] = {
            "id": "comprehension_analyzer",
            "parent": "learning_coach",
            "reason": "duplicate on purpose",
        }
        record = run_manager(document, {"user_message": "hi"}, MockDecisionProvider({}))

        self.assertEqual(record["status"], "error")
        self.assertIn("already exists", record["error"])

    def test_declared_object_versions_are_recorded(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["mainObj"]["version"] = "1.2.0"
        document["alo"]["subObjList"][0]["version"] = "0.3.0"
        record = run_manager(document, {"user_message": "hi"}, MockDecisionProvider({}))

        self.assertEqual(
            record["alo"]["object_versions"],
            {
                "main.learning_coach": "1.2.0",
                "sub.comprehension_analyzer": "0.3.0",
            },
        )

    def test_object_versions_is_empty_when_not_declared(self):
        record = run_manager(CANONICAL_MINIMAL, {"user_message": "hi"}, MockDecisionProvider({}))
        self.assertEqual(record["alo"]["object_versions"], {})

    def test_canonical_hash_is_deterministic(self):
        record_a = run_manager(CANONICAL_MINIMAL, {"user_message": "hello"})
        record_b = run_manager(copy.deepcopy(CANONICAL_MINIMAL), {"user_message": "hello"})
        self.assertEqual(
            record_a["alo"]["canonical_hash"], record_b["alo"]["canonical_hash"]
        )

    def test_rejects_legacy_spec_version(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["spec_version"] = "0.1"
        with self.assertRaisesRegex(ManagerError, "spec_version"):
            run_manager(document, {"user_message": "hello"})


if __name__ == "__main__":
    unittest.main()
