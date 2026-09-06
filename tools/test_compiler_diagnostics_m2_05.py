from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class MutationContractDiagnosticsTest(unittest.TestCase):
    def test_valid_mutation_with_direct_call_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.catalog\n"
                "mutation updateItem(id: uuid) -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: {\n"
                "    key input.id\n"
                "    scope principal\n"
                "    ttl 1h\n"
                "  }\n"
                "  call: Catalog.update(id)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_existing_transaction_and_workflow_start_are_each_valid_root_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.catalog\n"
                "mutation transactional() -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on CatalogDb isolation serializable {\n"
                "    write: Catalog.update()\n"
                "  }\n"
                "}\n"
                "mutation workflowBacked() -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  start: workflow RebuildCatalog()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_missing_required_clauses_and_root_effect_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.catalog\n"
                "mutation incomplete() -> string {\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 5)
            self.assertEqual(
                [diagnostic.code.value for diagnostic in analysis.diagnostics],
                ["AIDL-DIST404"] * 4 + ["AIDL-DIST405"],
            )
            for diagnostic in analysis.diagnostics:
                self.assertEqual(diagnostic.phase, "policy")
                self.assertEqual(
                    diagnostic.severity,
                    compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
                )
                self.assertEqual(diagnostic.source_path, source)
                self.assertEqual(
                    (diagnostic.location.line, diagnostic.location.column),
                    (2, 1),
                )
            messages = [diagnostic.message for diagnostic in analysis.diagnostics]
            self.assertEqual(
                messages,
                [
                    "mutation 'example.catalog.incomplete' must declare exactly one 'allow' clause; found 0",
                    "mutation 'example.catalog.incomplete' must declare exactly one 'auth' clause; found 0",
                    "mutation 'example.catalog.incomplete' must declare exactly one 'errors' clause; found 0",
                    "mutation 'example.catalog.incomplete' must declare exactly one 'idempotency' clause; found 0",
                    "mutation 'example.catalog.incomplete' must have exactly one root effect; found 0",
                ],
            )

    def test_duplicate_required_clause_is_anchored_to_second_occurrence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.catalog\n"
                "mutation duplicateAuth() -> string {\n"
                "  auth: authenticated\n"
                "  auth: service\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: Catalog.update()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(diagnostic.code.value, "AIDL-DIST404")
            self.assertEqual(
                diagnostic.message,
                "mutation 'example.catalog.duplicateAuth' must declare exactly one 'auth' clause; found 2",
            )
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (4, 3),
            )

    def test_multiple_root_effects_are_anchored_to_second_effect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.catalog\n"
                "mutation tooManyEffects() -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: Catalog.update()\n"
                "  start: saga ReconcileCatalog()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(diagnostic.code.value, "AIDL-DIST405")
            self.assertEqual(diagnostic.phase, "policy")
            self.assertEqual(
                diagnostic.message,
                "mutation 'example.catalog.tooManyEffects' must have exactly one root effect; found 2",
            )
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (8, 3),
            )

    def test_diagnostic_order_and_json_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-mutation.aidl"
            second = root / "b-mutation.aidl"
            first.write_text(
                "module example.catalog\n"
                "mutation first() -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.catalog\n"
                "mutation second() -> string {\n"
                "  auth: authenticated\n"
                "  auth: service\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: Catalog.update()\n"
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
                    "AIDL-DIST405",
                    "mutation 'example.catalog.first' must have exactly one root effect; found 0",
                    "a-mutation.aidl",
                    2,
                    1,
                ),
                (
                    "AIDL-DIST404",
                    "mutation 'example.catalog.second' must declare exactly one 'auth' clause; found 2",
                    "b-mutation.aidl",
                    4,
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
                ["AIDL-DIST405", "AIDL-DIST404"],
            )


if __name__ == "__main__":
    unittest.main()
