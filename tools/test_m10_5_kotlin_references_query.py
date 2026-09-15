from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_snapshot import create_compiler_snapshot
from tools.compiler_snapshot_editing import find_snapshot_usages

ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"

class KotlinReferencesQueryParityTest(unittest.TestCase):
    def _project(self, root: Path) -> dict[str, Path]:
        mapping = {"references-consumer": "documentation-consumer.source", "resolution-provider-a": "resolution-provider-a.source", "resolution-provider-b": "resolution-provider-b.source"}
        paths = {}
        for source_id, fixture in mapping.items():
            path = root / f"{source_id}.aidl"
            path.write_text((PARITY / fixture).read_text(encoding="utf-8"), encoding="utf-8")
            paths[source_id] = path
        return paths

    def _render(self, label: str, result) -> str:
        target = result.target
        usages = ",".join(f"{u.source_path.stem}:{u.location.line}:{u.location.column}:{u.location.offset}:{u.length}" for u in result.usages)
        return "|".join((label, result.status, target.fully_qualified_name if target else "", usages))

    def test_python_authority_matches_pinned_references_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); paths = self._project(root); consumer_path = paths["references-consumer"]
            consumer = consumer_path.read_text(encoding="utf-8"); snapshot = create_compiler_snapshot([root])
            local = consumer.index("Local\n", consumer.index("local:")) + 1
            imported = consumer.index("Public\n", consumer.index("imported:")) + 1
            qualified = consumer.index("demo.shared.Public", consumer.index("qualified:")) + len("demo.shared.") + 1
            ambiguous = consumer.index("Duplicate") + 1
            shifted = "\n" + consumer; shifted_snapshot = create_compiler_snapshot([root], {consumer_path: shifted})
            invalid_text = consumer + "§"; invalid_snapshot = create_compiler_snapshot([root], {consumer_path: invalid_text})
            actual = "\n".join((
                self._render("saved-local", find_snapshot_usages(snapshot, consumer_path, local)),
                self._render("saved-imported", find_snapshot_usages(snapshot, consumer_path, imported)),
                self._render("saved-qualified", find_snapshot_usages(snapshot, consumer_path, qualified)),
                self._render("saved-ambiguous", find_snapshot_usages(snapshot, consumer_path, ambiguous)),
                self._render("memory-shifted-imported", find_snapshot_usages(shifted_snapshot, consumer_path, shifted.index("Public\n", shifted.index("imported:")) + 1)),
                self._render("memory-lexical-failure", find_snapshot_usages(invalid_snapshot, consumer_path, invalid_text.index("Local\n", invalid_text.index("local:")) + 1)),
            ))
            self.assertEqual((PARITY / "references-query.signature").read_text(encoding="utf-8").rstrip(), actual)

    def test_isolated_roots_do_not_leak(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name, module in (("root-a", "a"), ("root-b", "b")):
                root = base / name; root.mkdir(); path = root / "main.aidl"
                text = f"module {module}\nentity A {{ ref: A }}\n"; path.write_text(text, encoding="utf-8")
                result = find_snapshot_usages(create_compiler_snapshot([root]), path, text.rindex("A"))
                self.assertEqual("resolved", result.status); self.assertEqual(f"{module}.A", result.target.fully_qualified_name)
                self.assertEqual(("main",), tuple(item.source_path.stem for item in result.usages))

if __name__ == "__main__": unittest.main()
