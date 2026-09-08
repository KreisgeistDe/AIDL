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


class ReferenceApplicationCoreTypecheckTest(unittest.TestCase):
    def _core_type_diagnostics(self, inputs: list[Path]) -> list[dict[str, object]]:
        return [
            diagnostic.to_json()
            for diagnostic in load_compiler_analysis(inputs).diagnostics
            if diagnostic.code.value in TYPE_CODES
        ]

    def test_full_reference_applications_pass_core_typechecking_deterministically(self) -> None:
        for relative in REFERENCE_APPLICATIONS:
            with self.subTest(relative=relative):
                root = ROOT / relative
                sources = sorted(root.rglob("*.aidl"))
                self.assertGreater(len(sources), 5, f"expected full reference application at {relative}")

                directory_result = self._core_type_diagnostics([root])
                reversed_result = self._core_type_diagnostics(list(reversed(sources)))

                self.assertEqual(directory_result, reversed_result)
                self.assertEqual([], directory_result)


if __name__ == "__main__":
    unittest.main()