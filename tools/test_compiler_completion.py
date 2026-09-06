from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_completion import complete_project_reference
from tools.compiler_diagnostics import load_compiler_analysis


class CompilerCompletionTest(unittest.TestCase):
    def _write(self, root: Path, relative: str, text: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_completes_module_local_exact_import_and_qualified_visibility(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\n"
                "import lib.Shared\n"
                "entity Uses {\n"
                "  local: LocalThing\n"
                "  imported: Shared\n"
                "  qualified: lib.Shared\n"
                "}\n",
            )
            self._write(root, "local.aidl", "module app\nentity LocalThing {\n}\n")
            self._write(root, "lib.aidl", "module lib\nexport entity Shared {\n}\n")
            analysis = load_compiler_analysis([root])
            text = source.read_text(encoding="utf-8")

            local_offset = text.index("LocalThing") + len("Loc")
            local = complete_project_reference(analysis.project, source, local_offset)
            self.assertEqual("resolved", local.status)
            self.assertEqual("Loc", local.prefix)
            self.assertEqual(["app.LocalThing"], [item.fully_qualified_name for item in local.candidates])
            self.assertEqual("local:app", local.candidates[0].origin)

            imported_offset = text.index("Shared\n", text.index("imported:")) + len("Sha")
            imported = complete_project_reference(analysis.project, source, imported_offset)
            self.assertEqual(["lib.Shared"], [item.fully_qualified_name for item in imported.candidates])
            self.assertEqual("exactImport:lib.Shared", imported.candidates[0].origin)

            qualified_start = text.index("lib.Shared\n", text.index("qualified:"))
            qualified = complete_project_reference(
                analysis.project,
                source,
                qualified_start + len("lib.Sha"),
            )
            self.assertEqual("lib", qualified.qualifier)
            self.assertEqual("Sha", qualified.prefix)
            self.assertEqual(["lib.Shared"], [item.fully_qualified_name for item in qualified.candidates])
            self.assertEqual("qualified:lib", qualified.candidates[0].origin)

    def test_omits_ambiguous_simple_names_instead_of_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\n"
                "import one.*\n"
                "import two.*\n"
                "entity Uses { target: Shared }\n",
            )
            self._write(root, "one.aidl", "module one\nexport entity Shared {\n}\n")
            self._write(root, "two.aidl", "module two\nexport entity Shared {\n}\n")
            analysis = load_compiler_analysis([root])
            text = source.read_text(encoding="utf-8")

            result = complete_project_reference(
                analysis.project,
                source,
                text.index("Shared") + len("Sha"),
            )

            self.assertEqual("resolved", result.status)
            self.assertEqual((), result.candidates)

    def test_supports_completion_immediately_after_qualified_dot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nentity Uses { target: lib.Shared }\n",
            )
            self._write(root, "lib.aidl", "module lib\nexport entity Shared {\n}\n")
            analysis = load_compiler_analysis([root])
            text = source.read_text(encoding="utf-8")
            dot_end = text.index("lib.Shared") + len("lib.")

            result = complete_project_reference(analysis.project, source, dot_end)

            self.assertEqual("resolved", result.status)
            self.assertEqual("lib", result.qualifier)
            self.assertEqual("", result.prefix)
            self.assertEqual(["Shared"], [item.insert_text for item in result.candidates])

    def test_rejects_declaration_module_import_and_clause_key_positions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\n"
                "import lib.Shared\n"
                "entity Shared {\n"
                "  Shared: Shared\n"
                "}\n",
            )
            self._write(root, "lib.aidl", "module lib\nexport entity Shared {\n}\n")
            analysis = load_compiler_analysis([root])
            text = source.read_text(encoding="utf-8")

            declaration_name = text.index("Shared", text.index("entity")) + len("Sha")
            module_name = text.index("app") + 1
            import_name = text.index("lib.Shared") + len("lib.Sha")
            clause_key = text.index("Shared", text.index("  Shared:")) + len("Sha")
            clause_value = text.index("Shared", text.index("  Shared:") + len("  Shared:")) + len("Sha")

            for label, offset in {
                "declaration": declaration_name,
                "module": module_name,
                "import": import_name,
                "clause-key": clause_key,
            }.items():
                with self.subTest(label=label):
                    result = complete_project_reference(analysis.project, source, offset)
                    self.assertEqual("invalid", result.status)
                    self.assertEqual((), result.candidates)

            valid = complete_project_reference(analysis.project, source, clause_value)
            self.assertEqual("resolved", valid.status)

    def test_rejects_other_parser_non_reference_positions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\n"
                "entity Shared {\n}\n"
                "enum Choice { Shared }\n",
            )
            analysis = load_compiler_analysis([root])
            text = source.read_text(encoding="utf-8")

            enum_case = text.index("Shared", text.index("enum Choice")) + len("Sha")
            result = complete_project_reference(analysis.project, source, enum_case)

            self.assertEqual("invalid", result.status)
            self.assertEqual((), result.candidates)

    def test_invalid_source_or_lexical_context_returns_no_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Uses { target: @ }\n")
            analysis = load_compiler_analysis([root])

            invalid = complete_project_reference(analysis.project, source, source.read_text().index("@"))
            foreign = complete_project_reference(analysis.project, root / "missing.aidl", 0)

            self.assertEqual("invalid", invalid.status)
            self.assertEqual((), invalid.candidates)
            self.assertEqual("invalid", foreign.status)
            self.assertEqual((), foreign.candidates)


if __name__ == "__main__":
    unittest.main()
