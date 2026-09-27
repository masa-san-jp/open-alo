import unittest

from packages.packaging import badge_markdown


class PackagingBadgeTests(unittest.TestCase):
    def test_badge_markdown_uses_spec_version(self):
        self.assertEqual(
            badge_markdown("0.1"),
            "[![Open ALO](https://img.shields.io/badge/Open%20ALO-0.1-blue)]"
            "(https://github.com/masa-san-jp/open-alo)",
        )

    def test_badge_markdown_url_encodes_version(self):
        self.assertIn("0.1%20beta%2F2", badge_markdown("0.1 beta/2"))


if __name__ == "__main__":
    unittest.main()
