from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class ApiExposureDiagnosticsTest(unittest.TestCase):
    def test_valid_local_api_allows_unmapped_internal_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "api.aidl"
            source.write_text(
                "module example.api\n"
                "query ListPets {\n"
                "}\n"
                "query InternalHealth {\n"
                "}\n"
                "mutation UpdatePet {\n"
                "  auth: private\n"
                "  allow: true\n"
                "  errors: []\n"
                "  idempotency: request.id\n"
                "  call: applyUpdate()\n"
                "}\n"
                "api PublicApi {\n"
                "  transport rest\n"
                "  version 1\n"
                "  operations [query ListPets, mutation UpdatePet]\n"
                "  compatibility backward\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_imported_and_fqn_operations_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operations = root / "operations.aidl"
            api = root / "api.aidl"
            operations.write_text(
                "module example.operations\n"
                "export query ListPets {\n"
                "}\n"
                "export mutation UpdatePet {\n"
                "  auth: private\n"
                "  allow: true\n"
                "  errors: []\n"
                "  idempotency: request.id\n"
                "  call: applyUpdate()\n"
                "}\n",
                encoding="utf-8",
            )
            api.write_text(
                "module example.api\n"
                "import example.operations.ListPets\n"
                "api PublicApi {\n"
                "  transport rpc\n"
                "  version 2\n"
                "  operations [query ListPets, mutation example.operations.UpdatePet]\n"
                "  compatibility full\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_required_clause_cardinality_and_values_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "api.aidl"
            source.write_text(
                "module example.api\n"
                "query ListPets {\n"
                "}\n"
                "api BrokenApi {\n"
                "  transport http\n"
                "  transport rest\n"
                "  version 0\n"
                "  operations []\n"
                "  compatibility rolling\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostics = [
                diagnostic
                for diagnostic in analysis.diagnostics
                if diagnostic.code == "AIDL-DIST412"
            ]

            self.assertEqual(len(diagnostics), 4)
            self.assertEqual(
                [(diagnostic.location.line, diagnostic.location.column) for diagnostic in diagnostics],
                [(6, 3), (7, 3), (8, 3), (9, 3)],
            )
            self.assertEqual(
                [diagnostic.message for diagnostic in diagnostics],
                [
                    "api 'example.api.BrokenApi' must declare exactly one 'transport' clause; found 2",
                    "api 'example.api.BrokenApi' version must be a positive major integer; found '0'",
                    "api 'example.api.BrokenApi' must declare exactly one non-empty 'operations' list",
                    "api 'example.api.BrokenApi' compatibility must be one of none, backward, forward, full; found 'rolling'",
                ],
            )

    def test_missing_required_clauses_are_anchored_to_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "api.aidl"
            source.write_text(
                "module example.api\n"
                "api EmptyApi {\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostics = [
                diagnostic
                for diagnostic in analysis.diagnostics
                if diagnostic.code == "AIDL-DIST412"
            ]

            self.assertEqual(len(diagnostics), 4)
            self.assertTrue(
                all(
                    (diagnostic.location.line, diagnostic.location.column) == (2, 1)
                    for diagnostic in diagnostics
                )
            )
            self.assertEqual(
                sorted(diagnostic.message for diagnostic in diagnostics),
                sorted(
                    [
                        "api 'example.api.EmptyApi' must declare exactly one 'transport' clause; found 0",
                        "api 'example.api.EmptyApi' must declare exactly one 'version' clause; found 0",
                        "api 'example.api.EmptyApi' must declare exactly one non-empty 'operations' list",
                        "api 'example.api.EmptyApi' must declare exactly one 'compatibility' clause; found 0",
                    ]
                ),
            )

    def test_invalid_transport_and_version_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "api.aidl"
            source.write_text(
                "module example.api\n"
                "query ListPets {\n"
                "}\n"
                "api BrokenApi {\n"
                "  transport websocket\n"
                "  version 1.5\n"
                "  operations [query ListPets]\n"
                "  compatibility none\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostics = [d for d in analysis.diagnostics if d.code == "AIDL-DIST412"]

            self.assertEqual(
                [diagnostic.message for diagnostic in diagnostics],
                [
                    "api 'example.api.BrokenApi' transport must be one of rest, rpc, graphql; found 'websocket'",
                    "api 'example.api.BrokenApi' version must be a positive major integer; found '1.5'",
                ],
            )

    def test_operation_item_requires_explicit_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "api.aidl"
            source.write_text(
                "module example.api\n"
                "query ListPets {\n"
                "}\n"
                "api BrokenApi {\n"
                "  transport rest\n"
                "  version 1\n"
                "  operations [ListPets]\n"
                "  compatibility backward\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(d for d in analysis.diagnostics if d.code == "AIDL-DIST412")

            self.assertEqual(
                diagnostic.message,
                "api 'example.api.BrokenApi' operation item 'ListPets' must be explicit 'query NAME' or 'mutation NAME'",
            )
            self.assertEqual((diagnostic.location.line, diagnostic.location.column), (7, 3))

    def test_operation_kind_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "api.aidl"
            source.write_text(
                "module example.api\n"
                "mutation UpdatePet {\n"
                "  auth: private\n"
                "  allow: true\n"
                "  errors: []\n"
                "  idempotency: request.id\n"
                "  call: applyUpdate()\n"
                "}\n"
                "api BrokenApi {\n"
                "  transport graphql\n"
                "  version 1\n"
                "  operations [query UpdatePet]\n"
                "  compatibility forward\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(d for d in analysis.diagnostics if d.code == "AIDL-DIST412")

            self.assertEqual(
                diagnostic.message,
                "api 'example.api.BrokenApi' maps query 'UpdatePet' to declaration kind 'mutation'",
            )
            self.assertEqual((diagnostic.location.line, diagnostic.location.column), (12, 3))

    def test_unresolved_and_ambiguous_operation_mappings_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.aidl"
            second = root / "second.aidl"
            api = root / "api.aidl"
            first.write_text(
                "module example.first\n"
                "export query Shared {\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "export query Shared {\n"
                "}\n",
                encoding="utf-8",
            )
            api.write_text(
                "module example.api\n"
                "import example.first.*\n"
                "import example.second.*\n"
                "api BrokenApi {\n"
                "  transport rest\n"
                "  version 1\n"
                "  operations [query Shared, mutation Missing]\n"
                "  compatibility backward\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            messages = [
                diagnostic.message
                for diagnostic in analysis.diagnostics
                if diagnostic.code == "AIDL-DIST412"
            ]

            self.assertEqual(
                messages,
                [
                    "api 'example.api.BrokenApi' operation mutation 'Missing' must resolve uniquely; found 0 matching mutation declarations",
                    "api 'example.api.BrokenApi' operation query 'Shared' must resolve uniquely; found 2 matching query declarations",
                ],
            )

    def test_duplicate_mapping_to_same_declaration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "api.aidl"
            source.write_text(
                "module example.api\n"
                "query ListPets {\n"
                "}\n"
                "api BrokenApi {\n"
                "  transport rest\n"
                "  version 1\n"
                "  operations [query ListPets, query example.api.ListPets]\n"
                "  compatibility backward\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(d for d in analysis.diagnostics if d.code == "AIDL-DIST412")

            self.assertEqual(
                diagnostic.message,
                "api 'example.api.BrokenApi' maps operation 'example.api.ListPets' more than once",
            )
            self.assertEqual((diagnostic.location.line, diagnostic.location.column), (7, 3))

    def test_api_diagnostic_order_and_json_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "api FirstApi {\n"
                "  transport rest\n"
                "  version 0\n"
                "  operations []\n"
                "  compatibility backward\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "api SecondApi {\n"
                "  transport http\n"
                "  version 1\n"
                "  operations [query Missing]\n"
                "  compatibility none\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])

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
                    if diagnostic.code == "AIDL-DIST412"
                ]

            self.assertEqual(snapshot(first_analysis), snapshot(second_analysis))
            first_json = compiler_diagnostics.compiler_diagnostics_to_json(
                tuple(d for d in first_analysis.diagnostics if d.code == "AIDL-DIST412")
            )
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(
                tuple(d for d in second_analysis.diagnostics if d.code == "AIDL-DIST412")
            )
            self.assertEqual(first_json, second_json)
            self.assertEqual(
                [item["code"] for item in json.loads(first_json)],
                ["AIDL-DIST412"] * 4,
            )


if __name__ == "__main__":
    unittest.main()
