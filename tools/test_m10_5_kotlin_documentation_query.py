from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_documentation import document_project_source
from tools.compiler_snapshot import create_compiler_snapshot


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
SOURCE_IDS = (
    "documentation-consumer",
    "resolution-provider-a",
    "resolution-provider-b",
)


class KotlinDocumentationQueryParityTest(unittest.TestCase):
    def _project(self, root: Path) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for source_id in SOURCE_IDS:
            path = root / f"{source_id}.aidl"
            path.write_text(
                (PARITY / f"{source_id}.source").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            paths[source_id] = path
        return paths

    def _render(self, label: str, result) -> str:
        declaration = result.declaration
        return "|".join(
            (
                label,
                result.status,
                declaration.fully_qualified_name if declaration else "",
                declaration.kind if declaration else "",
                declaration.source_path.stem if declaration else "",
                str(declaration.line) if declaration else "",
                str(declaration.column) if declaration else "",
                str(declaration.offset) if declaration else "",
                declaration.representation if declaration else "",
            )
        )

    def test_python_authority_matches_pinned_documentation_query_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._project(root)
            analysis = load_compiler_analysis([root])
            consumer_path = paths["documentation-consumer"]
            consumer = consumer_path.read_text(encoding="utf-8")
            local = consumer.index("Local\n", consumer.index("local:"))
            imported = consumer.index("Public\n", consumer.index("imported:"))
            qualified = consumer.index("demo.shared.Public", consumer.index("qualified:"))
            ambiguous = consumer.index("Duplicate\n")
            missing = consumer.index("Missing\n")

            saved = [
                self._render("saved-local", document_project_source(analysis, consumer_path, local + 1)),
                self._render("saved-imported", document_project_source(analysis, consumer_path, imported + 1)),
                self._render(
                    "saved-qualified",
                    document_project_source(
                        analysis,
                        consumer_path,
                        qualified + len("demo.shared.") + 1,
                    ),
                ),
                self._render("saved-ambiguous", document_project_source(analysis, consumer_path, ambiguous + 1)),
                self._render("saved-unresolved", document_project_source(analysis, consumer_path, missing + 1)),
                self._render("saved-invalid", document_project_source(analysis, consumer_path, len(consumer))),
            ]

            shifted = "\n" + consumer
            shifted_snapshot = create_compiler_snapshot([root], {consumer_path: shifted})
            memory = [
                self._render(
                    "memory-shifted-local",
                    shifted_snapshot.document(
                        consumer_path,
                        shifted.index("Local\n", shifted.index("local:")) + 1,
                    ),
                )
            ]

            invalid = consumer + "§"
            invalid_snapshot = create_compiler_snapshot([root], {consumer_path: invalid})
            memory.append(
                self._render(
                    "memory-lexical-failure",
                    invalid_snapshot.document(consumer_path, 0),
                )
            )

            actual = "\n".join(saved + memory)
            expected = (PARITY / "documentation-query.signature").read_text(encoding="utf-8").rstrip()
            self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
