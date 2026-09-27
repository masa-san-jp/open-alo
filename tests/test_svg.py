import copy
import unittest

from packages.compiler import SvgError, compile_object_graph, render_svg
from packages.core import load_document


CANONICAL_MINIMAL = load_document("examples/canonical-minimal/alo.yaml")


class SvgTests(unittest.TestCase):
    def test_renders_compiled_graph(self):
        diagram = render_svg(compile_object_graph(CANONICAL_MINIMAL))

        self.assertTrue(diagram.startswith('<svg xmlns="http://www.w3.org/2000/svg"'))
        self.assertIn('<rect x="', diagram)
        self.assertIn("MAIN_OBJECT", diagram)
        self.assertIn("INPUT", diagram)
        self.assertIn('marker-end="url(#arrowhead)"', diagram)
        self.assertIn('class="edge-label"', diagram)

    def test_output_is_deterministic_when_graph_order_changes(self):
        graph = compile_object_graph(CANONICAL_MINIMAL)
        reordered = copy.deepcopy(graph)
        reordered["nodes"] = list(reversed(reordered["nodes"]))
        reordered["edges"] = list(reversed(reordered["edges"]))

        self.assertEqual(render_svg(graph), render_svg(reordered))

    def test_escapes_dangerous_label_text(self):
        graph = {
            "nodes": [
                {
                    "id": "input.message",
                    "type": "INPUT",
                    "data": {"name": '<danger> & "quoted"'},
                }
            ],
            "edges": [],
        }
        diagram = render_svg(graph)

        self.assertIn("&lt;danger&gt; &amp; &quot;quoted&quot;", diagram)
        self.assertNotIn("<danger>", diagram)

    def test_rejects_edge_to_unknown_node(self):
        graph = {
            "nodes": [{"id": "input.message", "type": "INPUT"}],
            "edges": [
                {"from": "input.message", "to": "decision.missing", "type": "READS"}
            ],
        }
        with self.assertRaisesRegex(SvgError, "unknown node"):
            render_svg(graph)


if __name__ == "__main__":
    unittest.main()
