import json
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from packages.studio import StudioServer


class StudioServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = StudioServer(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.source = Path("examples/minimal/alo.yaml").read_text(encoding="utf-8")
        cls.input_data = json.loads(
            Path("examples/minimal/input.json").read_text(encoding="utf-8")
        )

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
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_default_host_is_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertNotEqual(self.server.server_address[0], "0.0.0.0")

    def test_examples_lists_minimal(self):
        status, payload = self._get("/api/examples")
        self.assertEqual(status, 200)
        self.assertTrue(any(item["id"] == "minimal" for item in payload))

    def test_validate_accepts_valid_and_reports_invalid_source(self):
        status, valid = self._post("/api/validate", {"source": self.source})
        self.assertEqual(status, 200)
        self.assertTrue(valid["valid"])
        self.assertEqual(valid["errors"], [])

        status, invalid = self._post("/api/validate", {"source": "{}"})
        self.assertEqual(status, 200)
        self.assertFalse(invalid["valid"])
        self.assertTrue(invalid["errors"])

    def test_graph_returns_mermaid_and_svg(self):
        status, payload = self._post("/api/graph", {"source": self.source})
        self.assertEqual(status, 200)
        self.assertIn("mermaid", payload)
        self.assertIn("svg", payload)
        self.assertTrue(payload["svg"].startswith("<svg"))

    def test_run_returns_mock_run_record(self):
        status, record = self._post(
            "/api/run",
            {
                "source": self.source,
                "input": self.input_data,
                "responses": {
                    "is_emergency": {"p_true": 0.97},
                    "category": {"technical": 1.0},
                },
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(record["status"], "terminal_state")
        self.assertEqual(record["provider"], "mock")


if __name__ == "__main__":
    unittest.main()
