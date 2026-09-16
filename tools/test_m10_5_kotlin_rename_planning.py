from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_refactoring import rename_project_symbol
from tools.compiler_snapshot import create_compiler_snapshot
from tools.compiler_snapshot_editing import plan_snapshot_rename

ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
DOMAIN = (PARITY / "canonical-ir-domain.source").read_text(encoding="utf-8")
ENVELOPE = (PARITY / "canonical-ir-envelope.source").read_text(encoding="utf-8")


class KotlinRenamePlanningParityTest(unittest.TestCase):
    def _project(self, root: Path, domain_text: str = DOMAIN) -> Path:
        domain = root / "rename-domain.aidl"
        domain.write_text(domain_text, encoding="utf-8")
        (root / "context-envelope.aidl").write_text(ENVELOPE, encoding="utf-8")
        return domain

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
            domain_path = self._project(root)
            snapshot = create_compiler_snapshot([root])
            status = DOMAIN.index("Status") + 1
            shifted = "\n" + DOMAIN
            shifted_snapshot = create_compiler_snapshot([root], {domain_path: shifted})
            invalid = DOMAIN + "§"
            invalid_snapshot = create_compiler_snapshot([root], {domain_path: invalid})
            actual = "\n".join(
                (
                    self._render("saved-status", plan_snapshot_rename(snapshot, domain_path, status, "Renamed")),
                    self._render("saved-collision", plan_snapshot_rename(snapshot, domain_path, status, "Pet")),
                    self._render("saved-invalid-name", plan_snapshot_rename(snapshot, domain_path, status, "entity")),
                    self._render(
                        "memory-shifted-status",
                        plan_snapshot_rename(
                            shifted_snapshot,
                            domain_path,
                            shifted.index("Status") + 1,
                            "Renamed",
                        ),
                    ),
                    self._render(
                        "memory-lexical-failure",
                        plan_snapshot_rename(invalid_snapshot, domain_path, invalid.index("Status") + 1, "Renamed"),
                    ),
                )
            )
            self.assertEqual((PARITY / "rename-planning.signature").read_text(encoding="utf-8").rstrip(), actual)

    def test_saved_snapshot_plan_matches_non_applying_refactoring_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            domain_path = self._project(root)
            offset = DOMAIN.index("Status") + 1
            snapshot = plan_snapshot_rename(create_compiler_snapshot([root]), domain_path, offset, "Renamed")
            saved = rename_project_symbol([root], domain_path, offset, "Renamed", apply=False)
            self.assertEqual("ready", snapshot.status)
            self.assertEqual(snapshot.status, saved.status)
            self.assertEqual(snapshot.new_fully_qualified_name, saved.new_fully_qualified_name)
            self.assertEqual(
                tuple((item.source_path, item.offset, item.length, item.replacement) for item in snapshot.edits),
                tuple((item.source_path, item.location.offset, item.length, item.replacement) for item in saved.edits),
            )

    def test_isolated_roots_and_repeated_snapshots_remain_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            rendered = []
            for name in ("root-a", "root-b"):
                root = base / name
                root.mkdir()
                domain_path = self._project(root)
                offset = DOMAIN.index("Status") + 1
                first = plan_snapshot_rename(create_compiler_snapshot([root]), domain_path, offset, "Renamed")
                second = plan_snapshot_rename(create_compiler_snapshot([root]), domain_path, offset, "Renamed")
                self.assertEqual(first, second)
                self.assertEqual("ready", first.status)
                self.assertEqual("parity.ir.domain.Renamed", first.new_fully_qualified_name)
                self.assertTrue(all(edit.source_path == domain_path for edit in first.edits))
                rendered.append(self._render(name, first))
            self.assertEqual(rendered[0].replace("root-a", "root-b"), rendered[1])


if __name__ == "__main__":
    unittest.main()
