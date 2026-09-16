from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_refactoring import rename_project_symbol
from tools.compiler_snapshot import create_compiler_snapshot
from tools.compiler_snapshot_editing import plan_snapshot_rename

ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"


class KotlinRenamePlanningParityTest(unittest.TestCase):
    def _project(self, root: Path) -> dict[str, Path]:
        mapping = {
            "references-consumer": "documentation-consumer.source",
            "resolution-provider-a": "resolution-provider-a.source",
            "resolution-provider-b": "resolution-provider-b.source",
        }
        paths: dict[str, Path] = {}
        for source_id, fixture in mapping.items():
            path = root / f"{source_id}.aidl"
            path.write_text((PARITY / fixture).read_text(encoding="utf-8"), encoding="utf-8")
            paths[source_id] = path
        return paths

    def _render(self, label: str, result) -> str:
        target = result.target
        edits = ",".join(
            f"{edit.source_path.stem}:{edit.offset}:{edit.length}:{edit.replacement}"
            for edit in result.edits
        )
        return "|".join(
            (
                label,
                result.status,
                target.fully_qualified_name if target else "",
                result.new_fully_qualified_name or "",
                edits,
            )
        )

    def test_python_snapshot_oracle_matches_pinned_rename_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._project(root)
            consumer_path = paths["references-consumer"]
            consumer = consumer_path.read_text(encoding="utf-8")
            snapshot = create_compiler_snapshot([root])
            local = consumer.index("Local\n", consumer.index("local:")) + 1
            imported = consumer.index("Public\n", consumer.index("imported:")) + 1
            ambiguous = consumer.index("Duplicate") + 1
            shifted = "\n" + consumer
            shifted_snapshot = create_compiler_snapshot([root], {consumer_path: shifted})
            invalid = consumer + "§"
            invalid_snapshot = create_compiler_snapshot([root], {consumer_path: invalid})
            actual = "\n".join(
                (
                    self._render("saved-local", plan_snapshot_rename(snapshot, consumer_path, local, "Renamed")),
                    self._render("saved-imported", plan_snapshot_rename(snapshot, consumer_path, imported, "Renamed")),
                    self._render("saved-ambiguous", plan_snapshot_rename(snapshot, consumer_path, ambiguous, "Renamed")),
                    self._render("saved-collision", plan_snapshot_rename(snapshot, consumer_path, imported, "Other")),
                    self._render("saved-invalid-name", plan_snapshot_rename(snapshot, consumer_path, imported, "entity")),
                    self._render(
                        "memory-shifted-imported",
                        plan_snapshot_rename(
                            shifted_snapshot,
                            consumer_path,
                            shifted.index("Public\n", shifted.index("imported:")) + 1,
                            "Renamed",
                        ),
                    ),
                    self._render(
                        "memory-lexical-failure",
                        plan_snapshot_rename(
                            invalid_snapshot,
                            consumer_path,
                            invalid.index("Local\n", invalid.index("local:")) + 1,
                            "Renamed",
                        ),
                    ),
                )
            )
            self.assertEqual((PARITY / "rename-planning.signature").read_text(encoding="utf-8").rstrip(), actual)

    def test_saved_snapshot_plan_matches_non_applying_refactoring_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._project(root)
            consumer_path = paths["references-consumer"]
            consumer = consumer_path.read_text(encoding="utf-8")
            offset = consumer.index("Public\n", consumer.index("imported:")) + 1
            snapshot = plan_snapshot_rename(create_compiler_snapshot([root]), consumer_path, offset, "Renamed")
            saved = rename_project_symbol([root], consumer_path, offset, "Renamed", apply=False)
            self.assertEqual(snapshot.status, saved.status)
            self.assertEqual(snapshot.new_fully_qualified_name, saved.new_fully_qualified_name)
            self.assertEqual(
                tuple((item.source_path, item.offset, item.length, item.replacement) for item in snapshot.edits),
                tuple((item.source_path, item.location.offset, item.length, item.replacement) for item in saved.edits),
            )

    def test_isolated_roots_and_repeated_snapshots_remain_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name, module in (("root-a", "a"), ("root-b", "b")):
                root = base / name
                root.mkdir()
                path = root / "main.aidl"
                text = f"module {module}\nentity A {{ ref: A }}\n"
                path.write_text(text, encoding="utf-8")
                first = plan_snapshot_rename(create_compiler_snapshot([root]), path, text.rindex("A"), "Renamed")
                second = plan_snapshot_rename(create_compiler_snapshot([root]), path, text.rindex("A"), "Renamed")
                self.assertEqual(first, second)
                self.assertEqual("ready", first.status)
                self.assertEqual(f"{module}.Renamed", first.new_fully_qualified_name)
                self.assertTrue(all(edit.source_path == path for edit in first.edits))


if __name__ == "__main__":
    unittest.main()
