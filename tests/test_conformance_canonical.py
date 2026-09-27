import copy
import json
import unittest
from pathlib import Path

from packages.compiler import compile_object_graph, graph_to_json, render_prompt
from packages.core import ensure_valid, load_document
from packages.providers import MockDecisionProvider
from packages.runtime import run_manager


CASES_ROOT = Path(__file__).resolve().parent.parent / "conformance" / "canonical-cases"

_REQUIRED_NODE_TYPES = {
    "MAIN_OBJECT",
    "SUB_OBJECT",
    "STATE",
    "MANAGER",
    "INPUT",
    "OUTPUT",
}


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _without_run_identifiers(record):
    result = copy.deepcopy(record)
    # run_id and timestamp are excluded because they are inherently
    # non-deterministic per run; alo.canonical_hash is deterministic and
    # remains part of the pinned comparison.
    result.pop("run_id", None)
    result.pop("timestamp", None)
    return result


class CanonicalConformanceTests(unittest.TestCase):
    def test_every_case_matches_golden_graph_prompt_and_runs(self):
        case_dirs = sorted(path for path in CASES_ROOT.iterdir() if path.is_dir())
        self.assertGreaterEqual(len(case_dirs), 1)

        for case_dir in case_dirs:
            with self.subTest(case=case_dir.name):
                document = load_document(case_dir / "alo.yaml")
                ensure_valid(document)

                graph = compile_object_graph(document)
                self.assertEqual(
                    graph_to_json(graph),
                    (case_dir / "object_graph.json").read_text(encoding="utf-8"),
                )

                prompt = render_prompt(document)
                self.assertEqual(prompt, (case_dir / "prompt.md").read_text(encoding="utf-8"))

                for run_dir in sorted((case_dir / "runs").iterdir()):
                    with self.subTest(run=run_dir.name):
                        record = run_manager(
                            document,
                            _read_json(run_dir / "input.json"),
                            MockDecisionProvider(_read_json(run_dir / "responses.json")),
                        )
                        expected = _read_json(run_dir / "expected_run_record.json")
                        self.assertEqual(
                            _without_run_identifiers(record),
                            _without_run_identifiers(expected),
                        )

    def test_every_golden_object_graph_has_all_four_core_components(self):
        # The whole point of the correction (issue #9): a conformant
        # implementation must be unable to lose mainObj/subObjList/State/
        # managerObj. Assert it directly against the pinned fixtures, not
        # only against a hand-written document in test_objectgraph.py.
        case_dirs = sorted(path for path in CASES_ROOT.iterdir() if path.is_dir())
        for case_dir in case_dirs:
            with self.subTest(case=case_dir.name):
                graph = json.loads((case_dir / "object_graph.json").read_text(encoding="utf-8"))
                node_types = {node["type"] for node in graph["nodes"]}
                missing = _REQUIRED_NODE_TYPES - node_types
                self.assertEqual(
                    missing,
                    set(),
                    f"{case_dir.name}/object_graph.json is missing required node types: {missing}",
                )

    def test_every_golden_prompt_shows_all_four_components(self):
        case_dirs = sorted(path for path in CASES_ROOT.iterdir() if path.is_dir())
        for case_dir in case_dirs:
            with self.subTest(case=case_dir.name):
                prompt = (case_dir / "prompt.md").read_text(encoding="utf-8")
                for heading in ("## mainObj", "## subObjList", "## State", "## managerObj"):
                    self.assertIn(heading, prompt)


if __name__ == "__main__":
    unittest.main()
