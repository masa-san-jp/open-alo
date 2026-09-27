import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from packages.packaging import PackagingError, install_from_git


class PackagingInstallTests(unittest.TestCase):
    def _create_git_repository(self, root: Path, *, nested: bool = False) -> Path:
        package = root / "packages" / "nested" if nested else root
        package.mkdir(parents=True, exist_ok=True)
        shutil.copy("examples/canonical-minimal/alo.yaml", package / "alo.yaml")
        (package / "alo-package.json").write_text(
            json.dumps(
                {
                    "name": "git-test",
                    "version": "0.2.0",
                    "spec_version": "0.1",
                    "entry": "alo.yaml",
                }
            ),
            encoding="utf-8",
        )
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
                "initial package",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return package

    def test_install_from_local_git_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"
            self._create_git_repository(root)
            installed = install_from_git(root, Path(tmp) / "installed")
            self.assertEqual(installed.name, "git-test-0.2.0")
            self.assertTrue((installed / "alo.yaml").is_file())

    def test_install_from_local_git_subdirectory_and_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"
            self._create_git_repository(root, nested=True)
            subprocess.run(["git", "-C", str(root), "branch", "-M", "package-branch"], check=True)
            installed = install_from_git(
                root,
                Path(tmp) / "installed",
                ref="package-branch",
                subdir="packages/nested",
            )
            self.assertEqual(installed.name, "git-test-0.2.0")

    def test_install_rejects_repository_without_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"
            root.mkdir()
            (root / "README.md").write_text("not a package", encoding="utf-8")
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
                    "empty package",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with self.assertRaisesRegex(PackagingError, "manifest file not found"):
                install_from_git(root, Path(tmp) / "installed")


if __name__ == "__main__":
    unittest.main()
