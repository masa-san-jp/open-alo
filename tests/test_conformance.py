import copy
import json
import unittest
from pathlib import Path

from packages.compiler import compile_alo, graph_to_json
from packages.core import ensure_valid, load_document
from packages.providers import MockDecisionProvider
from packages.runtime import ReplayMismatch, replay, run


CASES_ROOT = Path(__file__).resolve().parent.parent / "conformance" / "cases"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _without_run_identifiers(record):
    result = copy.deepcopy(record)
    # run_id and timestamp are excluded because they are inherently non-deterministic per run.
    result.pop("run_id", None)
    result.pop("timestamp", None)
    return result


class ConformanceTests(unittest.TestCase):
    def test_every_case_matches_golden_graph_and_runs(self):
        case_dirs = sorted(path for path in CASES_ROOT.iterdir() if path.is_dir())
        self.assertGreaterEqual(len(case_dirs), 2)

        for case_dir in case_dirs:
            with self.subTest(case=case_dir.name):
                document = load_document(case_dir / "alo.yaml")
                ensure_valid(document)
                graph = compile_alo(document)
                self.assertEqual(
                    graph_to_json(graph),
                    (case_dir / "graph.json").read_text(encoding="utf-8"),
                )

                for run_dir in sorted((case_dir / "runs").iterdir()):
                    with self.subTest(run=run_dir.name):
                        record = run(
                            document,
                            _read_json(run_dir / "input.json"),
                            MockDecisionProvider(_read_json(run_dir / "responses.json")),
                        )
                        expected = _read_json(run_dir / "expected_run_record.json")
                        self.assertEqual(
                            _without_run_identifiers(record),
                            _without_run_identifiers(expected),
                        )

    def test_replay_reproduces_a_produced_run(self):
        case_dir = CASES_ROOT / "scalar-and-derived"
        document = load_document(case_dir / "alo.yaml")
        run_dir = case_dir / "runs" / "approved"
        produced = run(
            document,
            _read_json(run_dir / "input.json"),
            MockDecisionProvider(_read_json(run_dir / "responses.json")),
        )

        replayed = replay(document, produced)
        self.assertEqual(
            _without_run_identifiers(replayed), _without_run_identifiers(produced)
        )

    def test_replay_detects_a_mutated_state_after(self):
        case_dir = CASES_ROOT / "support-triage"
        document = load_document(case_dir / "alo.yaml")
        run_dir = case_dir / "runs" / "emergency"
        produced = run(
            document,
            _read_json(run_dir / "input.json"),
            MockDecisionProvider(_read_json(run_dir / "responses.json")),
        )
        mutated = copy.deepcopy(produced)
        mutated["state_after"] = {"status": "wrong"}

        with self.assertRaises(ReplayMismatch) as context:
            replay(document, mutated)
        self.assertIn("state_after", str(context.exception))


if __name__ == "__main__":
    unittest.main()
