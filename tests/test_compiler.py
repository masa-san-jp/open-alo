import copy
import json
import unittest

from packages.compiler import CompileError, compile_alo, graph_to_json


MINIMAL_ALO = {
    "alo": {
        "spec_version": "0.1",
        "id": "support-triage",
        "version": "0.1.0",
        "purpose": "Route support requests.",
        "inputs": {
            "message": {"type": "string", "required": True},
        },
        "state_schema": {
            "status": {
                "type": "enum",
                "values": ["new", "routed", "review"],
                "initial": "new",
                "updated_by": "rule_engine",
            },
        },
        "decisions": [
            {
                "id": "is_emergency",
                "type": "binary",
                "reads": ["input.message"],
                "question": "Is this an emergency?",
            },
            {
                "id": "category",
                "type": "categorical",
                "reads": ["input.message"],
                "question": "What is the category?",
                "options": {
                    "technical": "Technical",
                    "billing": "Billing",
                    "other": "Other",
                },
            },
        ],
        "thresholds": {
            "emergency_accept": 0.9,
            "category_accept": 0.7,
        },
        "transition_rules": [
            {
                "id": "emergency",
                "priority": 10,
                "when": "decision.is_emergency.p_true >= threshold.emergency_accept",
                "set": {"status": "routed", "action": "escalate"},
                "stop_condition": "terminal_state",
            },
            {
                "id": "uncertain",
                "priority": 100,
                "when": "no_previous_rule_matched",
                "set": {"status": "review", "action": "human_review"},
                "stop_condition": "human_review_required",
            },
        ],
        "outputs": {
            "action": {"type": "string"},
            "state": {"type": "object"},
        },
        "stop_conditions": ["terminal_state", "human_review_required"],
    }
}


class CompilerTests(unittest.TestCase):
    def test_compiles_minimal_workflow(self):
        graph = compile_alo(MINIMAL_ALO)

        self.assertEqual(graph["graph_ir_version"], "0.1")
        self.assertEqual(
            graph["source"],
            {
                "spec_version": "0.1",
                "alo_id": "support-triage",
                "alo_version": "0.1.0",
            },
        )
        nodes = {node["id"]: node for node in graph["nodes"]}
        self.assertEqual(nodes["decision.is_emergency"]["type"], "DECISION_BINARY")
        self.assertEqual(nodes["decision.category"]["type"], "DECISION_CATEGORICAL")
        self.assertEqual(nodes["rule.emergency"]["type"], "RULE")
        self.assertEqual(nodes["stop.terminal_state"]["type"], "STOP")

        edges = {
            (edge["from"], edge["to"], edge["type"])
            for edge in graph["edges"]
        }
        self.assertIn(("input.message", "decision.category", "READS"), edges)
        self.assertIn(("decision.is_emergency", "rule.emergency", "GATES"), edges)
        self.assertIn(("rule.emergency", "state.status", "UPDATES"), edges)
        self.assertIn(("rule.emergency", "output.action", "EMITS"), edges)
        self.assertIn(("rule.emergency", "stop.terminal_state", "STOPS"), edges)
        self.assertIn(("rule.uncertain", "stop.human_review_required", "STOPS"), edges)

    def test_rejects_undeclared_stop_condition(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["transition_rules"][0]["stop_condition"] = "unknown_condition"
        with self.assertRaisesRegex(CompileError, "not declared in alo.stop_conditions"):
            compile_alo(document)

    def test_output_is_deterministic(self):
        first = graph_to_json(compile_alo(MINIMAL_ALO))
        changed_order = copy.deepcopy(MINIMAL_ALO)
        changed_order["alo"]["inputs"] = {"message": changed_order["alo"]["inputs"]["message"]}
        changed_order["alo"]["outputs"] = {
            "state": changed_order["alo"]["outputs"]["state"],
            "action": changed_order["alo"]["outputs"]["action"],
        }
        second = graph_to_json(compile_alo(changed_order))
        self.assertEqual(json.loads(first), json.loads(second))

    def test_rejects_unknown_rule_target(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["transition_rules"][0]["set"]["missing"] = True
        with self.assertRaisesRegex(CompileError, "does not name a state or output"):
            compile_alo(document)

    def test_shared_state_and_output_target_gets_both_edges(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["state_schema"]["action"] = {
            "type": "string",
            "initial": "none",
            "updated_by": "rule_engine",
        }
        graph = compile_alo(document)
        edges = {
            (edge["from"], edge["to"], edge["type"])
            for edge in graph["edges"]
        }
        self.assertIn(("rule.emergency", "state.action", "UPDATES"), edges)
        self.assertIn(("rule.emergency", "output.action", "EMITS"), edges)

    def test_rejects_unknown_reference(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["decisions"][0]["reads"] = ["input.unknown"]
        with self.assertRaisesRegex(CompileError, "unknown reference"):
            compile_alo(document)

    def test_rejects_duplicate_priorities(self):
        document = copy.deepcopy(MINIMAL_ALO)
        document["alo"]["transition_rules"][1]["priority"] = 10
        with self.assertRaisesRegex(CompileError, "priorities must be unique"):
            compile_alo(document)


if __name__ == "__main__":
    unittest.main()
