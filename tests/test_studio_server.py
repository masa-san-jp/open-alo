import json
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from packages.studio import StudioServer


class StudioServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = StudioServer(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.source = Path("examples/canonical-minimal/alo.yaml").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _get(self, path):
        with urlopen(self.base_url + path, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def _post(self, path, payload):
        request = Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read().decode("utf-8"))

    def test_default_host_is_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertNotEqual(self.server.server_address[0], "0.0.0.0")

    def test_examples_lists_canonical_minimal(self):
        status, payload = self._get("/api/examples")
        self.assertEqual(status, 200)
        self.assertTrue(any(item["id"] == "canonical-minimal" for item in payload))

    def test_validate_accepts_valid_and_reports_invalid_source(self):
        status, valid = self._post("/api/validate", {"source": self.source})
        self.assertEqual(status, 200)
        self.assertTrue(valid["valid"])
        self.assertEqual(valid["errors"], [])

        status, invalid = self._post("/api/validate", {"source": "{}"})
        self.assertEqual(status, 200)
        self.assertFalse(invalid["valid"])
        self.assertTrue(invalid["errors"])

    def test_prompt_renders_all_four_components(self):
        status, payload = self._post("/api/prompt", {"source": self.source})
        self.assertEqual(status, 200)
        self.assertIn("## mainObj", payload["prompt"])
        self.assertIn("## managerObj", payload["prompt"])

    def test_graph_returns_object_graph_mermaid_and_svg(self):
        status, payload = self._post("/api/graph", {"source": self.source})
        self.assertEqual(status, 200)
        self.assertIn("MAIN_OBJECT", payload["mermaid"])
        self.assertIn("MANAGER", payload["mermaid"])
        self.assertTrue(payload["svg"].startswith("<svg"))

    def test_run_returns_manager_run_record(self):
        status, record = self._post(
            "/api/run",
            {
                "source": self.source,
                "input": {"user_message": "hello"},
                "responses": {"analyze_comprehension": {"p_true": 0.9}},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(record["status"], "ok")
        self.assertIn("State_after", record)
        self.assertIn("manager_trace", record)


if __name__ == "__main__":
    unittest.main()
