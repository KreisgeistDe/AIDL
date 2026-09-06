from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_refactoring import find_project_usages, rename_project_symbol
from tools.test_aidl_ir import _MINIMAL_PROJECT


class CompilerRefactoringTest(unittest.TestCase):
    def _write_project(self, root: Path, text: str = _MINIMAL_PROJECT) -> Path:
        path = root / "app.aidl"
        path.write_text(text, encoding="utf-8")
        return path

    def test_find_usages_returns_only_references_to_unique_compiler_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write_project(root)
            text = source.read_text(encoding="utf-8")
            declaration_offset = text.index("Species")
            analysis = load_compiler_analysis([root])

            result = find_project_usages(analysis, source, declaration_offset)

            self.assertEqual("resolved", result.status)
            self.assertIsNotNone(result.target)
            self.assertEqual("demo.Species", result.target.fully_qualified_name)
            self.assertEqual(1, len(result.usages))
            usage = result.usages[0]
            self.assertEqual(source, usage.source_path)
            self.assertEqual(text.index("Species required"), usage.location.offset)
            self.assertEqual(len("Species"), usage.length)

    def test_find_usages_returns_no_guessed_results_for_ambiguous_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.aidl"
            source.write_text(
                "module app\nimport one.*\nimport two.*\nentity Uses { target: Shared }\n",
                encoding="utf-8",
            )
            (root / "one.aidl").write_text("module one\nexport enum Shared { one }\n", encoding="utf-8")
            (root / "two.aidl").write_text("module two\nexport enum Shared { two }\n", encoding="utf-8")
            analysis = load_compiler_analysis([root])

            result = find_project_usages(analysis, source, source.read_text(encoding="utf-8").index("Shared"))

            self.assertEqual("ambiguous", result.status)
            self.assertEqual((), result.usages)

    def test_safe_rename_plans_and_applies_all_compiler_owned_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write_project(root)
            declaration_offset = source.read_text(encoding="utf-8").index("Species")

            plan = rename_project_symbol([root], source, declaration_offset, "AnimalKind", apply=False)
            self.assertEqual("ready", plan.status)
            self.assertFalse(plan.applied)
            self.assertEqual("demo.AnimalKind", plan.new_fully_qualified_name)
            self.assertEqual(2, len(plan.edits))
            self.assertIn("Species", source.read_text(encoding="utf-8"))

            applied = rename_project_symbol([root], source, declaration_offset, "AnimalKind", apply=True)
            self.assertEqual("applied", applied.status)
            self.assertTrue(applied.applied)
            renamed = source.read_text(encoding="utf-8")
            self.assertNotIn("Species", renamed)
            self.assertEqual(2, renamed.count("AnimalKind"))
            analysis = load_compiler_analysis([root])
            self.assertFalse(any(diagnostic.severity.value == "error" for diagnostic in analysis.diagnostics))
            self.assertEqual(1, len(analysis.project.symbol_table.lookup_declarations("demo.AnimalKind")))

    def test_safe_rename_rejects_keyword_and_collision_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write_project(root)
            original = source.read_text(encoding="utf-8")
            declaration_offset = original.index("Species")

            keyword = rename_project_symbol([root], source, declaration_offset, "entity", apply=True)
            self.assertEqual("invalidName", keyword.status)
            self.assertEqual(original, source.read_text(encoding="utf-8"))

            collision_text = original.replace("export enum Species { dog, cat }", "export enum AnimalKind { bird }\n\nexport enum Species { dog, cat }")
            source.write_text(collision_text, encoding="utf-8")
            collision_offset = collision_text.index("Species")
            collision = rename_project_symbol([root], source, collision_offset, "AnimalKind", apply=True)
            self.assertEqual("collision", collision.status)
            self.assertEqual(collision_text, source.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
