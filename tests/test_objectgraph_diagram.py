import unittest

from packages.compiler import compile_object_graph, render_mermaid, render_svg
from packages.core import load_document


CANONICAL_MINIMAL = load_document("examples/canonical-minimal/alo.yaml")


class ObjectGraphDiagramTests(unittest.TestCase):
    def test_mermaid_shows_all_object_model_node_types_distinctly(self):
        graph = compile_object_graph(CANONICAL_MINIMAL)
        diagram = render_mermaid(graph)

        self.assertIn("MAIN_OBJECT", diagram)
        self.assertIn("SUB_OBJECT", diagram)
        self.assertIn("STATE", diagram)
        self.assertIn("MANAGER", diagram)
        self.assertIn("INPUT", diagram)
        self.assertIn("OUTPUT", diagram)
        self.assertIn("JEV_NOUL", diagram)
        self.assertIn("class n_main_learning_coach mainobj", diagram)
        self.assertIn("class n_manager_learning_coach_manager manager", diagram)
        self.assertIn(
            "class n_sub_comprehension_analyzer subobj", diagram
        )
        self.assertIn("classDef mainobj", diagram)
        self.assertIn("classDef manager", diagram)
        self.assertIn("classDef jev", diagram)

    def test_svg_renders_the_object_graph(self):
        graph = compile_object_graph(CANONICAL_MINIMAL)
        diagram = render_svg(graph)

        self.assertTrue(diagram.startswith('<svg xmlns="http://www.w3.org/2000/svg"'))
        self.assertIn("MAIN_OBJECT", diagram)
        self.assertIn("MANAGER", diagram)


if __name__ == "__main__":
    unittest.main()
