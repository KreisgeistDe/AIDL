from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_completion import complete_project_reference
from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_snapshot import create_compiler_snapshot


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
SOURCE_IDS = (
    "completion-consumer",
    "resolution-provider-a",
    "resolution-provider-b",
)


class KotlinCompletionQueryParityTest(unittest.TestCase):
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
        candidates = ";".join(
            "~".join(
                (
                    candidate.insert_text,
                    candidate.display_text,
                    candidate.fully_qualified_name,
                    candidate.kind,
                    candidate.origin,
                    candidate.source_path.stem,
                    str(candidate.source_offset),
                )
            )
            for candidate in result.candidates
        )
        return "|".join(
            (
                label,
                result.status,
                result.prefix or "",
                result.qualifier or "",
                candidates,
            )
        )

    def test_python_authority_matches_pinned_completion_query_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._project(root)
            analysis = load_compiler_analysis([root])
            consumer_path = paths["completion-consumer"]
            consumer = consumer_path.read_text(encoding="utf-8")
            qualified = consumer.index("demo.shared.Pub", 80)
            local = consumer.index("Loc\n")
            exact = consumer.index("Pub\n")
            ambiguous = consumer.index("Dup\n")

            saved = [
                self._render(
                    "saved-local",
                    complete_project_reference(
                        analysis.project, consumer_path, local + len("Loc")
                    ),
                ),
                self._render(
                    "saved-exact",
                    complete_project_reference(
                        analysis.project, consumer_path, exact + len("Pub")
                    ),
                ),
                self._render(
                    "saved-qualified",
                    complete_project_reference(
                        analysis.project,
                        consumer_path,
                        qualified + len("demo.shared.Pub"),
                    ),
                ),
                self._render(
                    "saved-dot",
                    complete_project_reference(
                        analysis.project,
                        consumer_path,
                        qualified + len("demo.shared."),
                    ),
                ),
                self._render(
                    "saved-ambiguous",
                    complete_project_reference(
                        analysis.project, consumer_path, ambiguous + len("Dup")
                    ),
                ),
                self._render(
                    "saved-invalid-key",
                    complete_project_reference(
                        analysis.project,
                        consumer_path,
                        consumer.index("local:") + 3,
                    ),
                ),
                self._render(
                    "saved-invalid-module",
                    complete_project_reference(
                        analysis.project,
                        consumer_path,
                        consumer.index("demo.consumer") + 4,
                    ),
                ),
                self._render(
                    "saved-out-of-range",
                    complete_project_reference(
                        analysis.project, consumer_path, len(consumer) + 1
                    ),
                ),
            ]

            shifted = "\n" + consumer
            shifted_snapshot = create_compiler_snapshot(
                [root],
                {consumer_path: shifted},
            )
            memory = [
                self._render(
                    "memory-shifted-local",
                    shifted_snapshot.complete(
                        consumer_path, shifted.index("Loc\n") + len("Loc")
                    ),
                )
            ]

            invalid = consumer + "§"
            invalid_snapshot = create_compiler_snapshot(
                [root],
                {consumer_path: invalid},
            )
            memory.append(
                self._render(
                    "memory-lexical-failure",
                    invalid_snapshot.complete(consumer_path, 0),
                )
            )

            actual = "\n".join(saved + memory)
            expected = (PARITY / "completion-query.signature").read_text(
                encoding="utf-8"
            ).rstrip()
            self.assertEqual(expected, actual)

    def test_python_authority_rejects_non_reference_clause_value_tokens(self) -> None:
        source = (
            "module demo\n"
            "entity Local {}\n"
            "entity Uses {\n"
            '  stringValue: "Local"\n'
            "  numberValue: 123\n"
            "  annotationValue: @Local\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "non-reference.aidl"
            source_path.write_text(source, encoding="utf-8")
            analysis = load_compiler_analysis([root])
            offsets = (
                source.index('"Local"') + 3,
                source.index("123") + 2,
                source.index("@Local") + 3,
            )

            for offset in offsets:
                with self.subTest(offset=offset):
                    result = complete_project_reference(
                        analysis.project,
                        source_path,
                        offset,
                    )
                    self.assertEqual("invalid", result.status)
                    self.assertIsNone(result.prefix)
                    self.assertIsNone(result.qualifier)
                    self.assertEqual((), result.candidates)


if __name__ == "__main__":
    unittest.main()
