from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class QuerySideEffectDiagnosticsTest(unittest.TestCase):
    def test_read_only_query_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "query.aidl"
            source.write_text(
                "module example.catalog\n"
                "query getItem(id: uuid) -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  read: Item.byId(id)\n"
                "  consistency: strong\n"
                "  errors: [InvalidInput]\n"
                "  timeout: 1s\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_query_rejects_existing_explicit_side_effect_constructs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "query.aidl"
            source.write_text(
                "module example.catalog\n"
                "query unsafeQuery() -> string {\n"
                "  write: Store.update()\n"
                "  emit: Changed() to Events\n"
                "  call: Billing.charge()\n"
                "  start: workflow RebuildCatalog()\n"
                "  transaction on CatalogDb isolation serializable {\n"
                "    write: CatalogDb.update()\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 5)
            expected_effects = ["write", "emit", "call", "start", "transaction"]
            for index, (diagnostic, effect) in enumerate(
                zip(analysis.diagnostics, expected_effects), start=3
            ):
                self.assertEqual(
                    diagnostic.code,
                    compiler_diagnostics.CompilerDiagnosticCode.QUERY_SIDE_EFFECT,
                )
                self.assertEqual(diagnostic.code, "AIDL-DIST403")
                self.assertEqual(diagnostic.phase, "policy")
                self.assertEqual(
                    diagnostic.severity,
                    compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
                )
                self.assertEqual(
                    diagnostic.message,
                    "query 'example.catalog.unsafeQuery' must be side-effect-free; "
                    f"found '{effect}' effect",
                )
                self.assertEqual(diagnostic.source_path, source)
                self.assertEqual(
                    (diagnostic.location.line, diagnostic.location.column),
                    (index, 3),
                )

    def test_query_side_effect_order_and_json_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-query.aidl"
            second = root / "b-query.aidl"
            first.write_text(
                "module example.catalog\n"
                "query firstQuery() -> string {\n"
                "  call: Search.refresh()\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.catalog\n"
                "query secondQuery() -> string {\n"
                "  transaction on CatalogDb isolation readCommitted {\n"
                "    write: CatalogDb.update()\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis(
                [second, first]
            )

            def snapshot(analysis: compiler_diagnostics.CompilerAnalysis):
                return [
                    (
                        diagnostic.code.value,
                        diagnostic.message,
                        diagnostic.source_path.name,
                        diagnostic.location.line,
                        diagnostic.location.column,
                    )
                    for diagnostic in analysis.diagnostics
                ]

            expected = [
                (
                    "AIDL-DIST403",
                    "query 'example.catalog.firstQuery' must be side-effect-free; found 'call' effect",
                    "a-query.aidl",
                    3,
                    3,
                ),
                (
                    "AIDL-DIST403",
                    "query 'example.catalog.secondQuery' must be side-effect-free; found 'transaction' effect",
                    "b-query.aidl",
                    3,
                    3,
                ),
            ]
            self.assertEqual(snapshot(first_analysis), expected)
            self.assertEqual(snapshot(second_analysis), expected)

            first_json = compiler_diagnostics.compiler_diagnostics_to_json(
                first_analysis.diagnostics
            )
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(
                second_analysis.diagnostics
            )
            self.assertEqual(first_json, second_json)
            self.assertEqual(
                [item["code"] for item in json.loads(first_json)],
                ["AIDL-DIST403", "AIDL-DIST403"],
            )


if __name__ == "__main__":
    unittest.main()
