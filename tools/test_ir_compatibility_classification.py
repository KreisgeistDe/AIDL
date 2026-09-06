from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.ir_compatibility import (
    IrCompatibilityClassificationError,
    classify_ir_diff,
    ir_compatibility_to_json,
)
from tools.ir_diff import IrDiffChange, diff_canonical_ir, semantic_ir_diff_to_json
from tools.test_aidl_ir import _MINIMAL_PROJECT


class IrCompatibilityClassificationTest(unittest.TestCase):
    def _ir(self, root: Path, name: str, text: str) -> dict:
        project = root / name
        project.mkdir()
        source = project / "app.aidl"
        source.write_text(text, encoding="utf-8")
        analysis = load_compiler_analysis([source])
        self.assertEqual((), analysis.diagnostics)
        return build_canonical_ir(analysis)

    def _classified(self, old: dict, new: dict):
        changes = diff_canonical_ir(old, new)
        return changes, classify_ir_diff(changes, old, new)

    def test_all_four_runtime_classes_are_represented_by_conservative_rules(self) -> None:
        safe_text = _MINIMAL_PROJECT.replace(
            "export enum Species { dog, cat }\n\n",
            "export enum Color { red, blue }\n\nexport enum Species { dog, cat }\n\n",
            1,
        )
        migration_text = _MINIMAL_PROJECT.replace(
            "  species: Species required immutable\n",
            "  species: Species required immutable\n  age: int required mutable\n",
            1,
        )
        conditional_text = _MINIMAL_PROJECT.replace("  timeout: 2s\n", "  timeout: 3s\n", 1)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = self._ir(root, "base", _MINIMAL_PROJECT)
            safe = self._ir(root, "safe", safe_text)
            migration = self._ir(root, "migration", migration_text)
            conditional = self._ir(root, "conditional", conditional_text)

        _, safe_classes = self._classified(base, safe)
        _, breaking_classes = self._classified(safe, base)
        _, migration_classes = self._classified(base, migration)
        _, conditional_classes = self._classified(base, conditional)

        self.assertIn("safe", {item.classification for item in safe_classes})
        self.assertIn("breaking", {item.classification for item in breaking_classes})
        self.assertIn("migration-required", {item.classification for item in migration_classes})
        self.assertIn("conditional", {item.classification for item in conditional_classes})
        self.assertTrue(any(item.rule == "declaration.standalone-added" for item in safe_classes))
        self.assertTrue(any(item.rule == "declaration.removed" for item in breaking_classes))
        self.assertTrue(any(item.rule == "entity.required-field-added" for item in migration_classes))
        self.assertTrue(any(item.rule == "operation.timeout-changed" for item in conditional_classes))

    def test_unknown_semantic_paths_are_conditional_never_safe(self) -> None:
        unknown_text = _MINIMAL_PROJECT.replace(
            "  scopes [pets.read]\n",
            "  scopes [pets.read, pets.write]\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self._ir(root, "old", _MINIMAL_PROJECT)
            new = self._ir(root, "new", unknown_text)

        changes, classifications = self._classified(old, new)
        self.assertTrue(changes)
        fallback = [item for item in classifications if item.rule == "unmodelled.review-required"]
        self.assertTrue(fallback)
        self.assertEqual({"conditional"}, {item.classification for item in fallback})
        self.assertNotIn("safe", {item.classification for item in fallback})

    def test_no_diff_is_empty_and_output_is_stable_in_fact_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = self._ir(root, "project", _MINIMAL_PROJECT)

        changes = diff_canonical_ir(document, document)
        first = classify_ir_diff(changes, document, document)
        second = classify_ir_diff(changes, document, document)
        self.assertEqual([], changes)
        self.assertEqual([], first)
        self.assertEqual(first, second)
        self.assertEqual([], ir_compatibility_to_json(first))

    def test_raw_m7_01_facts_remain_unchanged_and_reasons_are_deterministic(self) -> None:
        changed_text = _MINIMAL_PROJECT.replace("  timeout: 2s\n", "  timeout: 3s\n", 1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self._ir(root, "old", _MINIMAL_PROJECT)
            new = self._ir(root, "new", changed_text)

        changes = diff_canonical_ir(old, new)
        raw_before = semantic_ir_diff_to_json(changes)
        first = ir_compatibility_to_json(classify_ir_diff(changes, old, new))
        second = ir_compatibility_to_json(classify_ir_diff(changes, old, new))
        self.assertEqual(raw_before, semantic_ir_diff_to_json(changes))
        self.assertEqual(first, second)
        self.assertEqual([item.path for item in changes], [item["path"] for item in first])
        self.assertTrue(all(item["reason"] and item["rule"] for item in first))

    def test_classifier_rejects_facts_not_owned_by_supplied_ir_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = self._ir(root, "project", _MINIMAL_PROJECT)
        with self.assertRaisesRegex(IrCompatibilityClassificationError, "authoritative M7-01"):
            classify_ir_diff(
                [IrDiffChange("changed", "/app/fake", 1, 2)],
                document,
                document,
            )


if __name__ == "__main__":
    unittest.main()
