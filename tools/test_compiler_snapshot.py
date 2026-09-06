from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_snapshot import create_compiler_snapshot


class CompilerSnapshotTest(unittest.TestCase):
    def _write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_override_is_authoritative_for_diagnostics_without_mutating_disk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Shared {\n}\n")
            saved = source.read_text(encoding="utf-8")
            unsaved = saved + "entity Shared {\n}\n"

            snapshot = create_compiler_snapshot([root], {source: unsaved})
            self.assertEqual(unsaved, snapshot.text(source))
            self.assertTrue(any(item.code.value == "AIDL-R002" for item in snapshot.diagnostics(source)))
            self.assertEqual(saved, source.read_text(encoding="utf-8"))

    def test_no_override_preserves_saved_file_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nentity Shared {\n}\nentity Shared {\n}\n",
            )
            saved = load_compiler_analysis([root])
            snapshot = create_compiler_snapshot([root])
            self.assertEqual(
                [item.to_json() for item in saved.diagnostics],
                [item.to_json() for item in snapshot.analysis.diagnostics],
            )
            self.assertEqual(source.read_text(encoding="utf-8"), snapshot.text(source))

    def test_snapshots_are_isolated_and_fall_back_to_disk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Shared {\n}\n")
            changed = source.read_text(encoding="utf-8") + "entity Shared {\n}\n"

            changed_snapshot = create_compiler_snapshot([root], {source: changed})
            saved_snapshot = create_compiler_snapshot([root])

            self.assertTrue(any(item.code.value == "AIDL-R002" for item in changed_snapshot.diagnostics()))
            self.assertFalse(any(item.code.value == "AIDL-R002" for item in saved_snapshot.diagnostics()))
            self.assertNotIn(source.resolve(), saved_snapshot.overridden_paths)
            self.assertIn(source.resolve(), changed_snapshot.overridden_paths)

    def test_resolution_completion_and_documentation_share_unsaved_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nimport lib.Old\nimport lib.New\nentity Uses {\n  value: Old\n}\n",
            )
            target = self._write(
                root,
                "lib.aidl",
                "module lib\nexport entity Old {\n}\nexport entity New {\n}\n",
            )
            unsaved = source.read_text(encoding="utf-8").replace("value: Old", "value: New")
            snapshot = create_compiler_snapshot([root], {source: unsaved})
            offset = unsaved.index("New", unsaved.index("value:"))

            resolution = snapshot.resolve(source, offset)
            self.assertEqual("resolved", resolution.status)
            assert resolution.target is not None
            self.assertEqual("lib.New", resolution.target.fully_qualified_name)
            self.assertEqual(target.resolve(), resolution.target.source_path.resolve())

            completion = snapshot.complete(source, offset + 1)
            self.assertEqual("resolved", completion.status)
            self.assertTrue(any(item.fully_qualified_name == "lib.New" for item in completion.candidates))

            documentation = snapshot.document(source, offset)
            self.assertEqual("resolved", documentation.status)
            assert documentation.declaration is not None
            self.assertEqual("lib.New", documentation.declaration.fully_qualified_name)

    def test_override_cannot_add_or_escape_project_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            root = Path(directory)
            self._write(root, "app.aidl", "module app\nentity Shared {}\n")
            foreign = Path(other) / "foreign.aidl"
            with self.assertRaisesRegex(ValueError, "outside discovered project files"):
                create_compiler_snapshot([root], {foreign: "module foreign\nentity Hidden {}\n"})


if __name__ == "__main__":
    unittest.main()
