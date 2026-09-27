import json
import tempfile
import unittest
from pathlib import Path

from packages.packaging import PackagingError, load_manifest, validate_manifest


class PackagingManifestTests(unittest.TestCase):
    def test_canonical_minimal_example_manifest_is_valid(self):
        manifest = load_manifest("examples/canonical-minimal/alo-package.json")
        self.assertEqual(validate_manifest(manifest), [])
        self.assertEqual(manifest["name"], "learning-coach")

    def test_missing_manifest_is_an_error(self):
        with self.assertRaises(PackagingError):
            load_manifest("examples/canonical-minimal/missing-package.json")

    def test_manifest_reports_missing_required_fields_and_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alo-package.json"
            path.write_text(json.dumps({"name": "bad"}), encoding="utf-8")
            errors = validate_manifest(load_manifest(path))
        self.assertIn("version is required", errors)
        self.assertIn("spec_version is required", errors)
        self.assertIn("entry is required", errors)

    def test_manifest_validates_referenced_alo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "alo.yaml").write_text("alo:\n  spec_version: '0.1'\n", encoding="utf-8")
            manifest_path = root / "alo-package.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "name": "invalid-alo",
                        "version": "0.1.0",
                        "spec_version": "0.1",
                        "entry": "alo.yaml",
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_manifest(load_manifest(manifest_path))
        self.assertTrue(any(error.startswith("entry ALO:") for error in errors))

    def test_entry_must_stay_relative_to_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "alo-package.json"
            path.write_text(
                json.dumps(
                    {
                        "name": "bad-entry",
                        "version": "0.1.0",
                        "spec_version": "0.1",
                        "entry": "../alo.yaml",
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_manifest(load_manifest(path))
        self.assertIn("entry must be a relative path within the package", errors)


if __name__ == "__main__":
    unittest.main()
