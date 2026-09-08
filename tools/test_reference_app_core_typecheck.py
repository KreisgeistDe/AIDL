from __future__ import annotations

import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis


ROOT = Path(__file__).resolve().parents[1]
TYPE_CODES = {"AIDL-T001", "AIDL-T002", "AIDL-T003", "AIDL-T004", "AIDL-T005"}
REFERENCE_APPLICATIONS = (
    "examples/petstore",
    "examples/calendar-offline",
    "examples/videohub",
)
EXPECTED_TYPE_DIAGNOSTICS = {
    "examples/petstore": [],
    "examples/calendar-offline": [
        ("AIDL-T005", "domain/calendar.aidl", 8, 3),
        ("AIDL-T005", "domain/calendar.aidl", 11, 3),
        ("AIDL-T005", "domain/calendar.aidl", 12, 3),
        ("AIDL-T005", "domain/calendar.aidl", 14, 3),
        ("AIDL-T005", "domain/calendar.aidl", 63, 3),
        ("AIDL-T005", "domain/calendar.aidl", 65, 3),
    ],
    "examples/videohub": [],
}


class ReferenceApplicationCoreTypecheckTest(unittest.TestCase):
    def _core_type_diagnostics(self, inputs: list[Path]):
        return tuple(
            diagnostic
            for diagnostic in load_compiler_analysis(inputs).diagnostics
            if diagnostic.code.value in TYPE_CODES
        )

    @staticmethod
    def _anchors(root: Path, diagnostics) -> list[tuple[str, str, int, int]]:
        return [
            (
                diagnostic.code.value,
                diagnostic.source_path.relative_to(root).as_posix(),
                diagnostic.location.line,
                diagnostic.location.column,
            )
            for diagnostic in diagnostics
        ]

    def test_full_reference_applications_have_deterministic_core_type_outcomes(self) -> None:
        for relative in REFERENCE_APPLICATIONS:
            with self.subTest(relative=relative):
                root = ROOT / relative
                sources = sorted(root.rglob("*.aidl"))
                self.assertGreater(len(sources), 5, f"expected full reference application at {relative}")

                directory_result = self._core_type_diagnostics([root])
                reversed_result = self._core_type_diagnostics(list(reversed(sources)))

                self.assertEqual(
                    [diagnostic.to_json() for diagnostic in directory_result],
                    [diagnostic.to_json() for diagnostic in reversed_result],
                )
                self.assertEqual(
                    EXPECTED_TYPE_DIAGNOSTICS[relative],
                    self._anchors(root, directory_result),
                )
                if relative == "examples/calendar-offline":
                    self.assertTrue(
                        all(diagnostic.code.value == "AIDL-T005" for diagnostic in directory_result)
                    )
                    self.assertTrue(
                        all(diagnostic.subject is not None and diagnostic.subject.kind == "value" for diagnostic in directory_result)
                    )


if __name__ == "__main__":
    unittest.main()
