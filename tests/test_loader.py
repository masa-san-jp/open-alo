import json
import tempfile
import unittest
from pathlib import Path

from packages.core import LoadError, load_document


class LoaderTests(unittest.TestCase):
    def test_loads_json_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alo.json"
            path.write_text(json.dumps({"alo": {"id": "x"}}), encoding="utf-8")
            document = load_document(path)
            self.assertEqual(document, {"alo": {"id": "x"}})

    def test_loads_yaml_document(self):
        document = load_document("examples/minimal/alo.yaml")
        self.assertEqual(document["alo"]["id"], "support-triage")

    def test_rejects_missing_file(self):
        with self.assertRaisesRegex(LoadError, "file not found"):
            load_document("examples/minimal/does-not-exist.yaml")

    def test_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alo.json"
            path.write_text("{not valid json", encoding="utf-8")
            with self.assertRaisesRegex(LoadError, "could not parse"):
                load_document(path)

    def test_rejects_non_object_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alo.json"
            path.write_text("[1, 2, 3]", encoding="utf-8")
            with self.assertRaisesRegex(LoadError, "document root must be an object"):
                load_document(path)


if __name__ == "__main__":
    unittest.main()
