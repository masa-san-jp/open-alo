import json
import tempfile
import unittest
from pathlib import Path

from packages.packaging import load_registry, search_registry


class PackagingRegistryTests(unittest.TestCase):
    def test_load_and_search_registry_case_insensitively(self):
        registry = {
            "entries": [
                {
                    "name": "support-triage",
                    "description": "Routes support requests",
                    "source": "./support",
                    "latest_version": "0.1.0",
                },
                {
                    "name": "invoice-review",
                    "description": "Checks invoices",
                    "source": "./invoice",
                    "latest_version": "1.0.0",
                },
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            loaded = load_registry(path)
        self.assertEqual(search_registry(loaded, "SUPPORT"), [registry["entries"][0]])
        self.assertEqual(search_registry(loaded, "invoice"), [registry["entries"][1]])
        self.assertEqual(search_registry(loaded, "unknown"), [])

    def test_empty_query_matches_all_entries(self):
        registry = {"entries": [{"name": "one", "description": "first"}]}
        self.assertEqual(search_registry(registry, ""), registry["entries"])


if __name__ == "__main__":
    unittest.main()
