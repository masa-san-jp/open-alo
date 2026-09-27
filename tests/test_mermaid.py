import copy
import unittest

from packages.compiler import MermaidError, compile_object_graph, render_mermaid
from packages.core import load_document


CANONICAL_MINIMAL = load_document("examples/canonical-minimal/alo.yaml")


class MermaidTests(unittest.TestCase):
    def test_renders_compiled_graph(self):
        diagram = render_mermaid(compile_object_graph(CANONICAL_MINIMAL))

        self.assertTrue(diagram.startswith("flowchart TD\n"))
        self.assertIn("MAIN_OBJECT", diagram)
        self.assertIn("MANAGER", diagram)
        self.assertIn("-->|RECEIVES|", diagram)
        self.assertIn("classDef mainobj", diagram)

    def test_output_is_deterministic_when_graph_order_changes(self):
        graph = compile_object_graph(CANONICAL_MINIMAL)
        reordered = copy.deepcopy(graph)
        reordered["nodes"] = list(reversed(reordered["nodes"]))
        reordered["edges"] = list(reversed(reordered["edges"]))

        self.assertEqual(render_mermaid(graph), render_mermaid(reordered))

    def test_escapes_labels_and_resolves_sanitized_id_collisions(self):
        graph = {
            "nodes": [
                {
                    "id": "input.a-b",
                    "type": "INPUT",
                    "data": {"name": '<danger> & "quoted"'},
                },
                {
                    "id": "input.a_b",
                    "type": "INPUT",
                    "data": {"name": "other"},
                },
            ],
            "edges": [],
        }
        diagram = render_mermaid(graph)

        self.assertIn("&lt;danger&gt; &amp; &quot;quoted&quot;", diagram)
        node_lines = [
            line
            for line in diagram.splitlines()
            if line.startswith("    n_input_a_b_")
        ]
        self.assertEqual(len(node_lines), 2)

    def test_rejects_edge_to_unknown_node(self):
        graph = {
            "nodes": [{"id": "input.message", "type": "INPUT"}],
            "edges": [
                {
                    "from": "input.message",
                    "to": "decision.missing",
                    "type": "READS",
                }
            ],
        }
        with self.assertRaisesRegex(MermaidError, "unknown node"):
            render_mermaid(graph)


if __name__ == "__main__":
    unittest.main()
