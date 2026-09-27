import copy
import unittest

from packages.compiler import ObjectGraphError, compile_object_graph
from packages.core import load_document


CANONICAL_MINIMAL = load_document("examples/canonical-minimal/alo.yaml")


class ObjectGraphTests(unittest.TestCase):
    def test_contains_all_minimum_node_types(self):
        graph = compile_object_graph(CANONICAL_MINIMAL)
        node_types = {node["type"] for node in graph["nodes"]}
        self.assertEqual(
            {"MAIN_OBJECT", "SUB_OBJECT", "STATE", "MANAGER", "INPUT", "OUTPUT", "JEV_NOUL"},
            node_types,
        )

    def test_contains_all_minimum_relationships(self):
        graph = compile_object_graph(CANONICAL_MINIMAL)
        edge_types = {edge["type"] for edge in graph["edges"]}
        self.assertEqual(
            {
                "CONTAINS",
                "COORDINATES",
                "READS_STATE",
                "UPDATES_STATE",
                "RECEIVES",
                "EMITS",
                "CALCULATES",
            },
            edge_types,
        )

    def test_main_object_contains_and_manager_coordinates_each_sub_object(self):
        graph = compile_object_graph(CANONICAL_MINIMAL)
        edges = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
        for sub_id in ("sub.comprehension_analyzer", "sub.explanation_engine"):
            self.assertIn(("main.learning_coach", sub_id, "CONTAINS"), edges)
            self.assertIn(
                ("manager.learning_coach_manager", sub_id, "COORDINATES"), edges
            )

    def test_manager_reads_and_updates_a_single_state_node(self):
        graph = compile_object_graph(CANONICAL_MINIMAL)
        state_nodes = [node for node in graph["nodes"] if node["type"] == "STATE"]
        self.assertEqual(len(state_nodes), 1)
        edges = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
        self.assertIn(("state", "manager.learning_coach_manager", "READS_STATE"), edges)
        self.assertIn(("manager.learning_coach_manager", "state", "UPDATES_STATE"), edges)

    def test_jev_calculation_step_produces_an_overlay_node(self):
        graph = compile_object_graph(CANONICAL_MINIMAL)
        calc_nodes = [node for node in graph["nodes"] if node["id"] == "calc.analyze_comprehension"]
        self.assertEqual(len(calc_nodes), 1)
        self.assertEqual(calc_nodes[0]["type"], "JEV_NOUL")
        self.assertIn("question", calc_nodes[0]["data"])

    def test_output_is_deterministic(self):
        first = compile_object_graph(CANONICAL_MINIMAL)
        second = compile_object_graph(copy.deepcopy(CANONICAL_MINIMAL))
        self.assertEqual(first, second)

    def test_rejects_legacy_spec_version(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["spec_version"] = "0.1"
        with self.assertRaisesRegex(ObjectGraphError, "spec_version"):
            compile_object_graph(document)

    def test_rejects_unknown_jev_calculation_type(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["managerObj"]["process"][1]["calculation"]["jev"]["type"] = "Maybe"
        with self.assertRaisesRegex(ObjectGraphError, "jev.type must be one of"):
            compile_object_graph(document)

    def test_a_decision_only_document_cannot_satisfy_this_compiler(self):
        # The whole point of the correction: there is no way to produce a
        # conformant Object Graph IR without mainObj/subObjList/State/managerObj,
        # regardless of how thorough a decision workflow might be.
        document = {
            "alo": {
                "spec_version": "0.2",
                "id": "workflow-only",
                "version": "0.1.0",
            }
        }
        with self.assertRaises(ObjectGraphError):
            compile_object_graph(document)


if __name__ == "__main__":
    unittest.main()
