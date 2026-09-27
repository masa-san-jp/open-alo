import json
import tempfile
import unittest
from pathlib import Path

from packages.packaging import PackagingError, build_package


class PackagingBuildTests(unittest.TestCase):
    def test_build_copies_package_and_excludes_private_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            (source / "alo.yaml").write_text(
                Path("examples/minimal/alo.yaml").read_text(encoding="utf-8"), encoding="utf-8"
            )
            (source / "alo-package.json").write_text(
                json.dumps(
                    {
                        "name": "copy-test",
                        "version": "1.2.3",
                        "spec_version": "0.1",
                        "entry": "alo.yaml",
                    }
                ),
                encoding="utf-8",
            )
            (source / "notes.txt").write_text("included", encoding="utf-8")
            (source / ".secret").write_text("excluded", encoding="utf-8")
            (source / ".git").mkdir()
            (source / "__pycache__").mkdir()

            target = build_package(source, output)

            self.assertEqual(target, output / "copy-test-1.2.3")
            self.assertTrue((target / "alo-package.json").is_file())
            self.assertTrue((target / "alo.yaml").is_file())
            self.assertTrue((target / "notes.txt").is_file())
            self.assertFalse((target / ".secret").exists())
            self.assertFalse((target / ".git").exists())
            self.assertFalse((target / "__pycache__").exists())

    def test_build_rejects_invalid_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "alo-package.json").write_text(
                json.dumps(
                    {
                        "name": "missing-entry",
                        "version": "0.1.0",
                        "spec_version": "0.1",
                        "entry": "alo.yaml",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(PackagingError, "invalid package manifest"):
                build_package(source, Path(tmp) / "output")


if __name__ == "__main__":
    unittest.main()
