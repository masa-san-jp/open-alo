import copy
import unittest

from packages.compiler import PromptError, render_prompt
from packages.core import load_document


CANONICAL_MINIMAL = load_document("examples/canonical-minimal/alo.yaml")


class PromptTests(unittest.TestCase):
    def test_renders_all_four_components(self):
        prompt = render_prompt(CANONICAL_MINIMAL)

        self.assertTrue(prompt.startswith("# ALO\n"))
        self.assertIn("## mainObj", prompt)
        self.assertIn("- id: learning_coach", prompt)
        self.assertIn("## subObjList", prompt)
        self.assertIn("### comprehension_analyzer", prompt)
        self.assertIn("### explanation_engine", prompt)
        self.assertIn("## State", prompt)
        self.assertIn("- level: 1", prompt)
        self.assertIn("## managerObj", prompt)
        self.assertIn("1. ", prompt)
        self.assertIn("Jev Noul", prompt)
        self.assertIn("## Input", prompt)

    def test_reflects_declared_process_steps_not_generic_boilerplate(self):
        prompt = render_prompt(CANONICAL_MINIMAL)
        self.assertIn("comprehension_analyzerを使って理解状況を評価する", prompt)

    def test_is_deterministic(self):
        first = render_prompt(CANONICAL_MINIMAL)
        second = render_prompt(copy.deepcopy(CANONICAL_MINIMAL))
        self.assertEqual(first, second)

    def test_rejects_legacy_spec_version(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["spec_version"] = "0.1"
        with self.assertRaisesRegex(PromptError, "spec_version"):
            render_prompt(document)

    def test_rejects_missing_component(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        del document["alo"]["managerObj"]
        with self.assertRaisesRegex(PromptError, "alo.managerObj"):
            render_prompt(document)

    def test_handles_empty_sub_obj_list(self):
        document = copy.deepcopy(CANONICAL_MINIMAL)
        document["alo"]["subObjList"] = []
        prompt = render_prompt(document)
        self.assertIn("no sub-objects declared", prompt)


if __name__ == "__main__":
    unittest.main()
