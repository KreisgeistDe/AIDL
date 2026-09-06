from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_workspace import create_compiler_workspace, discover_workspace_roots


class CompilerWorkspaceTest(unittest.TestCase):
    def _write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_root_order_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = base / "z-root"
            second = base / "a-root"
            first.mkdir()
            second.mkdir()
            self.assertEqual(
                discover_workspace_roots([first, second, first]),
                discover_workspace_roots([second, first]),
            )

    def test_independent_roots_do_not_leak_declarations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            left = base / "left"
            right = base / "right"
            left.mkdir()
            right.mkdir()
            left_source = self._write(
                left,
                "app.aidl",
                "module app\nimport shared.Target\nentity Uses {\n  value: Target\n}\n",
            )
            self._write(right, "shared.aidl", "module shared\nexport entity Target {}\n")

            workspace = create_compiler_workspace([right, left])
            left_snapshot = workspace.snapshot_for(left_source)
            self.assertIsNotNone(left_snapshot)
            assert left_snapshot is not None
            self.assertTrue(
                any(item.code.value == "AIDL-R001" for item in left_snapshot.diagnostics(left_source))
            )
            self.assertIsNone(
                next(
                    (
                        declaration
                        for declaration in left_snapshot.analysis.project.declaration_names
                        if declaration.fully_qualified_name == "shared.Target"
                    ),
                    None,
                )
            )

    def test_overlapping_roots_assign_files_to_most_specific_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            child = parent / "nested"
            child.mkdir()
            parent_source = self._write(parent, "parent.aidl", "module parent\nentity Parent {}\n")
            child_source = self._write(child, "child.aidl", "module child\nentity Child {}\n")

            workspace = create_compiler_workspace([parent, child])
            self.assertEqual(parent.resolve(), workspace.owner(parent_source))
            self.assertEqual(child.resolve(), workspace.owner(child_source))
            parent_snapshot = workspace.snapshot_for(parent_source)
            child_snapshot = workspace.snapshot_for(child_source)
            assert parent_snapshot is not None and child_snapshot is not None
            self.assertNotIn(child_source.resolve(), parent_snapshot.source_texts)
            self.assertNotIn(parent_source.resolve(), child_snapshot.source_texts)

    def test_unsaved_new_aidl_file_is_admitted_to_owning_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(root, "saved.aidl", "module app\nentity Saved {}\n")
            unsaved = root / "new.aidl"
            text = "module app\nentity New {}\n"

            workspace = create_compiler_workspace([root], {unsaved: text})
            self.assertEqual(root.resolve(), workspace.owner(unsaved))
            snapshot = workspace.snapshot_for(unsaved)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(text, snapshot.text(unsaved))
            self.assertFalse(unsaved.exists())

    def test_unknown_or_non_aidl_unsaved_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "outside configured roots"):
                create_compiler_workspace(
                    [root],
                    {Path(other) / "foreign.aidl": "module foreign\nentity Hidden {}\n"},
                )
            with self.assertRaisesRegex(ValueError, "must be an .aidl file"):
                create_compiler_workspace([root], {root / "note.txt": "not aidl"})

    def test_single_root_saved_analysis_matches_existing_compiler(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nentity Shared {}\nentity Shared {}\n",
            )
            saved = load_compiler_analysis([root])
            workspace = create_compiler_workspace([root])
            snapshot = workspace.snapshot_for(source)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(
                [item.to_json() for item in saved.diagnostics],
                [item.to_json() for item in snapshot.analysis.diagnostics],
            )


if __name__ == "__main__":
    unittest.main()
