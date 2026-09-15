from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_resolution import resolve_project_reference
from tools.compiler_snapshot import create_compiler_snapshot


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
SOURCE_IDS = (
    "resolution-consumer",
    "resolution-provider-a",
    "resolution-provider-b",
)


class KotlinDefinitionQueryParityTest(unittest.TestCase):
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
        target = result.target
        fields = [
            label,
            result.status,
            result.reference or "",
            target.fully_qualified_name if target is not None else "",
            target.kind if target is not None else "",
            target.source_path.stem if target is not None else "",
            str(target.location.line) if target is not None else "",
            str(target.location.column) if target is not None else "",
            str(target.location.offset) if target is not None else "",
        ]
        return "|".join(fields)

    def test_python_authority_matches_pinned_definition_query_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._project(root)
            analysis = load_compiler_analysis([root])
            consumer = paths["resolution-consumer"].read_text(encoding="utf-8")
            provider_a = paths["resolution-provider-a"].read_text(encoding="utf-8")
            provider_b = paths["resolution-provider-b"].read_text(encoding="utf-8")

            saved = [
                self._render(
                    "saved-local",
                    resolve_project_reference(
                        analysis.project,
                        paths["resolution-consumer"],
                        consumer.index("Local"),
                    ),
                ),
                self._render(
                    "saved-exact-import",
                    resolve_project_reference(
                        analysis.project,
                        paths["resolution-consumer"],
                        consumer.index("Public"),
                    ),
                ),
                self._render(
                    "saved-module-missing",
                    resolve_project_reference(
                        analysis.project,
                        paths["resolution-consumer"],
                        consumer.index("demo.consumer"),
                    ),
                ),
                self._render(
                    "saved-hidden-local",
                    resolve_project_reference(
                        analysis.project,
                        paths["resolution-provider-a"],
                        provider_a.index("Hidden"),
                    ),
                ),
                self._render(
                    "saved-duplicate",
                    resolve_project_reference(
                        analysis.project,
                        paths["resolution-provider-a"],
                        provider_a.index("Duplicate"),
                    ),
                ),
                self._render(
                    "saved-other",
                    resolve_project_reference(
                        analysis.project,
                        paths["resolution-provider-b"],
                        provider_b.index("Other"),
                    ),
                ),
                self._render(
                    "saved-out-of-range",
                    resolve_project_reference(
                        analysis.project,
                        paths["resolution-consumer"],
                        len(consumer),
                    ),
                ),
            ]

            override = (
                consumer
                + "entity Uses {\n"
                + "  hidden: Hidden\n"
                + "  missing: Missing\n"
                + "  duplicate: Duplicate\n"
                + "  imported: Public\n"
                + "}\n"
            )
            snapshot = create_compiler_snapshot(
                [root],
                {paths["resolution-consumer"]: override},
            )
            memory = [
                self._render(
                    "memory-hidden",
                    snapshot.resolve(
                        paths["resolution-consumer"],
                        override.index("Hidden", len(consumer)),
                    ),
                ),
                self._render(
                    "memory-missing",
                    snapshot.resolve(
                        paths["resolution-consumer"],
                        override.index("Missing", len(consumer)),
                    ),
                ),
                self._render(
                    "memory-duplicate",
                    snapshot.resolve(
                        paths["resolution-consumer"],
                        override.index("Duplicate", len(consumer)),
                    ),
                ),
                self._render(
                    "memory-public",
                    snapshot.resolve(
                        paths["resolution-consumer"],
                        override.index("Public", len(consumer)),
                    ),
                ),
            ]
            invalid_override = consumer + "§"
            invalid_snapshot = create_compiler_snapshot(
                [root],
                {paths["resolution-consumer"]: invalid_override},
            )
            memory.append(
                self._render(
                    "memory-lexical-failure",
                    invalid_snapshot.resolve(paths["resolution-consumer"], 0),
                )
            )

            actual = "\n".join(saved + memory)
            expected = (PARITY / "definition-query.signature").read_text(
                encoding="utf-8"
            ).rstrip()
            self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
