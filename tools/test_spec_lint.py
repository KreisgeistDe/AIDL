import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.spec_lint import Report, UNRESOLVED_PLACEHOLDER, app_profile_versions, check_project


class UnresolvedPlaceholderTests(unittest.TestCase):
    def test_todo_markers_but_not_todo_markdown_filename(self) -> None:
        self.assertIsNone(UNRESOLVED_PLACEHOLDER.search("Follow TODO.md milestone order"))
        for text in ("TODO: implement this", "TBD", "FIXME later"):
            with self.subTest(text=text):
                self.assertIsNotNone(UNRESOLVED_PLACEHOLDER.search(text))


class FrozenCanonicalSourceLintTests(unittest.TestCase):
    def test_app_profiles_accept_legacy_and_frozen_block_forms(self) -> None:
        legacy = "profile core version 1\nprofile web version 2\n"
        canonical = "profile core {\n  version 1\n}\nprofile web { version 2 }\n"
        self.assertEqual({"core": 1, "web": 2}, app_profile_versions(legacy))
        self.assertEqual({"core": 1, "web": 2}, app_profile_versions(canonical))

    def test_canonical_profile_and_entity_field_slots_pass_project_lint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "examples" / "demo"
            docs = root / "docs"
            project.mkdir(parents=True)
            docs.mkdir()
            grammar = docs / "06-grammar.md"
            grammar.write_text("canonical grammar", encoding="utf-8")
            source = project / "app.aidl"
            source.write_text(
                """module demo
app Demo {
  profile core {
    version 1
  }
}
entity Record {
  field id: uuid primary immutable
  field revision: revision generated concurrencyToken
  field name: string mutable
}
service DemoService {
  owns [Record]
  uses []
  exposes []
  runs []
}
system DemoSystem {
  services [DemoService]
  resources []
}
""",
                encoding="utf-8",
            )
            lock = {
                "profiles": {"core": 1},
                "standardLibrary": "aidl.std",
                "grammar": "sha256:" + hashlib.sha256(grammar.read_bytes()).hexdigest(),
            }
            (project / "aidl.lock").write_text(json.dumps(lock), encoding="utf-8")

            report = Report()
            check_project(project, report)

            self.assertEqual([], report.errors)

    def test_invalid_canonical_profile_still_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "examples" / "demo"
            docs = root / "docs"
            project.mkdir(parents=True)
            docs.mkdir()
            grammar = docs / "06-grammar.md"
            grammar.write_text("canonical grammar", encoding="utf-8")
            (project / "app.aidl").write_text(
                """module demo
app Demo {
  profile core {
    version nope
  }
}
""",
                encoding="utf-8",
            )
            lock = {
                "profiles": {"core": 1},
                "standardLibrary": "aidl.std",
                "grammar": "sha256:" + hashlib.sha256(grammar.read_bytes()).hexdigest(),
            }
            (project / "aidl.lock").write_text(json.dumps(lock), encoding="utf-8")

            report = Report()
            check_project(project, report)

            self.assertTrue(any("locked profiles do not match" in error for error in report.errors))
            self.assertTrue(any("does not activate core profile version 1" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
