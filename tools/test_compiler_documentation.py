from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_documentation import document_project_source


class CompilerDocumentationTest(unittest.TestCase):
    def _write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_documents_local_imported_and_qualified_declarations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\n"
                "import lib.Shared\n"
                "entity LocalThing {\n}\n"
                "entity Uses {\n"
                "  local: LocalThing\n"
                "  imported: Shared\n"
                "  qualified: lib.Shared\n"
                "}\n",
            )
            lib = self._write(root, "lib.aidl", "module lib\nexport entity Shared {\n}\n")
            analysis = load_compiler_analysis([root])
            text = source.read_text(encoding="utf-8")

            cases = [
                (text.index("LocalThing", text.index("local:")), "app.LocalThing", "entity", source),
                (text.index("Shared", text.index("imported:")), "lib.Shared", "entity", lib),
                (text.index("Shared", text.index("qualified:")), "lib.Shared", "entity", lib),
            ]
            for offset, fqn, kind, target_file in cases:
                with self.subTest(fqn=fqn, offset=offset):
                    result = document_project_source(analysis, source, offset)
                    self.assertEqual("resolved", result.status)
                    self.assertIsNotNone(result.declaration)
                    assert result.declaration is not None
                    self.assertEqual(fqn, result.declaration.fully_qualified_name)
                    self.assertEqual(kind, result.declaration.kind)
                    self.assertEqual(target_file.resolve(), result.declaration.source_path.resolve())
                    self.assertIn("entity", result.declaration.representation)
                    self.assertIn(fqn.rsplit(".", 1)[-1], result.declaration.representation)

    def test_documents_declaration_name_using_compiler_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nexport entity Shared {\n}\n")
            analysis = load_compiler_analysis([root])
            text = source.read_text(encoding="utf-8")
            result = document_project_source(analysis, source, text.index("Shared") + 1)

            self.assertEqual("resolved", result.status)
            self.assertIsNotNone(result.declaration)
            assert result.declaration is not None
            self.assertEqual("app.Shared", result.declaration.fully_qualified_name)
            self.assertEqual("entity", result.declaration.kind)
            self.assertEqual("entity Shared", result.declaration.representation)
            self.assertGreaterEqual(result.declaration.line, 1)
            self.assertGreaterEqual(result.declaration.column, 1)

    def test_diagnostic_documentation_preserves_compiler_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nentity Shared {\n}\nentity Shared {\n}\n",
            )
            analysis = load_compiler_analysis([root])
            duplicate = next(item for item in analysis.diagnostics if item.code.value == "AIDL-R002")

            result = document_project_source(analysis, source, duplicate.location.offset)

            self.assertEqual("resolved", result.status)
            self.assertGreaterEqual(len(result.diagnostics), 1)
            payload = next(item.to_json() for item in result.diagnostics if item.code.value == "AIDL-R002")
            self.assertEqual("AIDL-R002", payload["code"])
            self.assertIn("phase", payload)
            self.assertIn("severity", payload)
            self.assertIn("message", payload)
            self.assertIn("location", payload)
            if "subject" in payload:
                self.assertIn("kind", payload["subject"])
                self.assertIn("name", payload["subject"])
            if "expected" in payload:
                self.assertIsInstance(payload["expected"], str)
            if "docs" in payload:
                self.assertIsInstance(payload["docs"], str)

    def test_unresolved_ambiguous_invalid_and_foreign_positions_do_not_guess(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\n"
                "import one.*\n"
                "import two.*\n"
                "entity Uses {\n"
                "  ambiguous: Shared\n"
                "  missing: Missing\n"
                "}\n",
            )
            self._write(root, "one.aidl", "module one\nexport entity Shared {\n}\n")
            self._write(root, "two.aidl", "module two\nexport entity Shared {\n}\n")
            analysis = load_compiler_analysis([root])
            text = source.read_text(encoding="utf-8")

            ambiguous = document_project_source(analysis, source, text.index("Shared"))
            unresolved = document_project_source(analysis, source, text.index("Missing"))
            invalid = document_project_source(analysis, source, len(text))
            foreign = document_project_source(analysis, root / "missing.aidl", 0)

            self.assertEqual("ambiguous", ambiguous.status)
            self.assertIsNone(ambiguous.declaration)
            self.assertEqual((), ambiguous.diagnostics)
            self.assertEqual("unresolved", unresolved.status)
            self.assertIsNone(unresolved.declaration)
            self.assertEqual((), unresolved.diagnostics)
            self.assertEqual("invalid", invalid.status)
            self.assertEqual("invalid", foreign.status)


if __name__ == "__main__":
    unittest.main()
