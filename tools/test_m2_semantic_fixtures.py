from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
FIXTURE_ROOT = TOOLS_DIR / "m2_semantic_fixtures"
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class M2SemanticFixtureCorpusTest(unittest.TestCase):
    def _manifest(self) -> list[dict[str, object]]:
        payload = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
        cases = payload["cases"]
        self.assertEqual(
            [case["rule"] for case in cases],
            [f"M2-{index:02d}" for index in range(1, 12)],
        )
        self.assertEqual(
            {item["code"] for case in cases for item in case["expected"]},
            {
                "AIDL-DIST400",
                "AIDL-DIST401",
                "AIDL-DIST402",
                "AIDL-DIST403",
                "AIDL-DIST404",
                "AIDL-DIST405",
                "AIDL-DIST406",
                "AIDL-DIST407",
                "AIDL-DIST408",
                "AIDL-DIST411",
                "AIDL-DIST412",
                "AIDL-DIST413",
            },
        )
        return cases

    def _snapshot(
        self, case_dir: Path, diagnostics: tuple[compiler_diagnostics.CompilerDiagnostic, ...]
    ) -> list[dict[str, object]]:
        return [
            {
                "code": diagnostic.code.value,
                "file": diagnostic.source_path.relative_to(case_dir).as_posix(),
                "line": diagnostic.location.line,
                "column": diagnostic.location.column,
            }
            for diagnostic in diagnostics
        ]

    def test_negative_fixture_corpus_covers_every_m2_semantic_rule(self) -> None:
        for case in self._manifest():
            case_dir = FIXTURE_ROOT / str(case["id"])
            with self.subTest(rule=case["rule"], case=case["id"]):
                first = compiler_diagnostics.load_compiler_analysis([case_dir])
                reversed_sources = sorted(case_dir.glob("*.aidl"), reverse=True)
                second = compiler_diagnostics.load_compiler_analysis(reversed_sources)

                self.assertEqual(self._snapshot(case_dir, first.diagnostics), case["expected"])
                self.assertEqual(self._snapshot(case_dir, second.diagnostics), case["expected"])
                self.assertEqual(
                    compiler_diagnostics.compiler_diagnostics_to_json(first.diagnostics),
                    compiler_diagnostics.compiler_diagnostics_to_json(second.diagnostics),
                )


if __name__ == "__main__":
    unittest.main()
