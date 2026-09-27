import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from packages.cli import main


class CliTests(unittest.TestCase):
    def _run(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main(argv)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_validate_accepts_valid_document(self):
        status, out, _ = self._run(["validate", "examples/minimal/alo.yaml"])
        self.assertEqual(status, 0)
        self.assertIn("valid", out)

    def test_validate_rejects_missing_file(self):
        status, _, err = self._run(["validate", "examples/minimal/missing.yaml"])
        self.assertEqual(status, 1)
        self.assertIn("file not found", err)

    def test_graph_renders_mermaid_flowchart(self):
        status, out, _ = self._run(["graph", "examples/minimal/alo.yaml"])
        self.assertEqual(status, 0)
        self.assertTrue(out.startswith("flowchart TD"))

    def test_graph_writes_to_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "graph.mmd"
            status, out, _ = self._run(
                ["graph", "examples/minimal/alo.yaml", "--out", str(out_path)]
            )
            self.assertEqual(status, 0)
            self.assertEqual(out, "")
            self.assertTrue(out_path.read_text(encoding="utf-8").startswith("flowchart TD"))

    def test_run_produces_run_record_json(self):
        status, out, _ = self._run(
            ["run", "examples/minimal/alo.yaml", "--input", "examples/minimal/input.json"]
        )
        self.assertEqual(status, 0)
        record = json.loads(out)
        self.assertEqual(record["alo_id"], "support-triage")
        self.assertIn("status", record)

    def test_run_with_responses_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            responses_path = Path(tmp) / "responses.json"
            responses_path.write_text(
                json.dumps({"is_emergency": {"p_true": 0.97}, "category": {"technical": 1.0}}),
                encoding="utf-8",
            )
            status, out, _ = self._run(
                [
                    "run",
                    "examples/minimal/alo.yaml",
                    "--input",
                    "examples/minimal/input.json",
                    "--responses",
                    str(responses_path),
                ]
            )
            self.assertEqual(status, 0)
            record = json.loads(out)
            self.assertEqual(record["status"], "terminal_state")
            self.assertEqual(record["output"]["action"], "escalate")

    def test_run_reports_input_error_with_nonzero_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            input_path.write_text("{}", encoding="utf-8")
            status, out, _ = self._run(
                ["run", "examples/minimal/alo.yaml", "--input", str(input_path)]
            )
            self.assertEqual(status, 1)
            record = json.loads(out)
            self.assertEqual(record["status"], "input_error")

    def test_test_command_runs_declared_cases(self):
        status, out, _ = self._run(["test", "examples/minimal"])
        self.assertEqual(status, 0)
        self.assertIn("5/5 passed", out)

    def test_no_command_prints_help(self):
        status, out, _ = self._run([])
        self.assertEqual(status, 1)
        self.assertIn("usage", out.lower())

    def test_package_build_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, out, err = self._run(
                ["package", "build", "examples/minimal", "--out", tmp]
            )
            self.assertEqual(status, 0, err)
            package_path = Path(out.strip())
            self.assertTrue(package_path.is_dir())
            self.assertEqual(package_path.name, "support-triage-0.1.0")

    def test_package_install_command_uses_local_git_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"
            root.mkdir()
            for name in ("alo.yaml", "alo-package.json"):
                shutil.copy(Path("examples/minimal") / name, root / name)
            subprocess.run(["git", "init", str(root)], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "-c",
                    "user.name=Open ALO Tests",
                    "-c",
                    "user.email=tests@example.invalid",
                    "commit",
                    "-m",
                    "package",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            destination = Path(tmp) / "installed"
            status, out, err = self._run(
                ["package", "install", str(root), "--dest", str(destination)]
            )
            self.assertEqual(status, 0, err)
            self.assertEqual(Path(out.strip()).name, "support-triage-0.1.0")

    def test_package_search_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "name": "support-triage",
                                "description": "Route support",
                                "source": "./support",
                                "latest_version": "0.1.0",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            status, out, err = self._run(
                ["package", "search", str(registry_path), "SUPPORT"]
            )
            self.assertEqual(status, 0, err)
            self.assertEqual(json.loads(out)[0]["name"], "support-triage")

    def test_package_badge_command_accepts_manifest(self):
        status, out, err = self._run(
            ["package", "badge", "examples/minimal/alo-package.json"]
        )
        self.assertEqual(status, 0, err)
        self.assertIn("Open%20ALO-0.1-blue", out)


if __name__ == "__main__":
    unittest.main()
