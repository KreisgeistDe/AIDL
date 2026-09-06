import unittest

from tools.spec_lint import UNRESOLVED_PLACEHOLDER


class UnresolvedPlaceholderTests(unittest.TestCase):
    def test_todo_markers_but_not_todo_markdown_filename(self) -> None:
        self.assertIsNone(UNRESOLVED_PLACEHOLDER.search("Follow TODO.md milestone order"))
        for text in ("TODO: implement this", "TBD", "FIXME later"):
            with self.subTest(text=text):
                self.assertIsNotNone(UNRESOLVED_PLACEHOLDER.search(text))


if __name__ == "__main__":
    unittest.main()
