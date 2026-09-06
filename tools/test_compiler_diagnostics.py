from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import aidl_parser  # noqa: E402
import compiler_diagnostics  # noqa: E402


class CompilerDiagnosticsTest(unittest.TestCase):
    def test_parser_diagnostic_preserves_source_location_and_stable_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "broken.aidl"
            source.write_text(
                "module example.bad\n"
                "value Pet {\n"
                "  $\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(
                diagnostic.code,
                compiler_diagnostics.CompilerDiagnosticCode.PARSE_FAILURE,
            )
            self.assertEqual(diagnostic.code, "AIDL-P001")
            self.assertEqual(diagnostic.phase, "parse")
            self.assertEqual(
                diagnostic.severity,
                compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
            )
            self.assertEqual(diagnostic.severity, "error")
            self.assertEqual(diagnostic.message, "unexpected character '$'")
            self.assertEqual(diagnostic.source_path, source)
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (3, 3),
            )

    def test_resolution_diagnostics_use_stable_codes_severity_and_existing_locations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.aidl"
            second = root / "b.aidl"
            first.write_text(
                "module example.catalog\n"
                "import missing.module.Type\n"
                "value Pet {\n}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.catalog\n"
                "error Pet {\n}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(
                [
                    (
                        diagnostic.code.value,
                        diagnostic.phase,
                        diagnostic.severity.value,
                        diagnostic.message,
                        diagnostic.source_path.name,
                        diagnostic.location.line,
                        diagnostic.location.column,
                    )
                    for diagnostic in analysis.diagnostics
                ],
                [
                    (
                        "AIDL-R001",
                        "resolve",
                        "error",
                        "unresolved import 'missing.module.Type'",
                        "a.aidl",
                        2,
                        1,
                    ),
                    (
                        "AIDL-R002",
                        "resolve",
                        "error",
                        "duplicate declaration 'example.catalog.Pet'",
                        "b.aidl",
                        2,
                        1,
                    ),
                ],
            )
            self.assertEqual(
                len(
                    analysis.project.symbol_table.lookup_declarations(
                        "example.catalog.Pet"
                    )
                ),
                2,
            )
            self.assertEqual(len(analysis.project.import_resolutions), 1)
            self.assertEqual(analysis.project.import_resolutions[0].declarations, ())

    def test_diagnostic_codes_are_structural_not_message_path_or_order_dependent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.aidl"
            second = root / "b.aidl"
            third = root / "c.aidl"
            first.write_text(
                "module example.one\n"
                "import missing.first.Type\n"
                "value Shared {\n}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.one\n"
                "error Shared {\n}\n",
                encoding="utf-8",
            )
            third.write_text(
                "module example.two\n"
                "import missing.second.Other\n"
                "  @\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis(
                [third, second, first]
            )

            def structural_snapshot(
                analysis: compiler_diagnostics.CompilerAnalysis,
            ) -> list[tuple[str, str, str]]:
                return [
                    (
                        diagnostic.code.value,
                        diagnostic.phase,
                        diagnostic.severity.value,
                    )
                    for diagnostic in analysis.diagnostics
                ]

            expected = [
                ("AIDL-R001", "resolve", "error"),
                ("AIDL-R002", "resolve", "error"),
                ("AIDL-R001", "resolve", "error"),
                ("AIDL-P001", "parse", "error"),
            ]
            self.assertEqual(structural_snapshot(first_analysis), expected)
            self.assertEqual(structural_snapshot(second_analysis), expected)

            unresolved_codes = {
                diagnostic.code
                for diagnostic in first_analysis.diagnostics
                if diagnostic.message.startswith("unresolved import")
            }
            self.assertEqual(
                unresolved_codes,
                {compiler_diagnostics.CompilerDiagnosticCode.UNRESOLVED_IMPORT},
            )

    def test_parser_severity_maps_to_explicit_compiler_severity_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "valid.aidl"
            source.write_text(
                "module example.valid\nvalue Pet {\n}\n",
                encoding="utf-8",
            )
            analysis = compiler_diagnostics.load_compiler_analysis([root])
            document = analysis.project.documents[0]

            diagnostics = compiler_diagnostics.collect_compiler_diagnostics(
                analysis.project,
                {
                    document.source_path: (
                        aidl_parser.Diagnostic(
                            message="warning text is not an identity",
                            start=aidl_parser.Span(line=1, column=1, offset=0),
                            severity="warning",
                        ),
                        aidl_parser.Diagnostic(
                            message="info text is not an identity",
                            start=aidl_parser.Span(line=1, column=1, offset=0),
                            severity="info",
                        ),
                    )
                },
            )

            self.assertEqual(
                [diagnostic.code for diagnostic in diagnostics],
                [
                    compiler_diagnostics.CompilerDiagnosticCode.PARSE_FAILURE,
                    compiler_diagnostics.CompilerDiagnosticCode.PARSE_FAILURE,
                ],
            )
            self.assertEqual(
                [diagnostic.severity for diagnostic in diagnostics],
                [
                    compiler_diagnostics.CompilerDiagnosticSeverity.WARNING,
                    compiler_diagnostics.CompilerDiagnosticSeverity.INFO,
                ],
            )

    def test_diagnostic_order_is_stable_by_project_source_and_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.aidl"
            second = root / "b.aidl"
            first.write_text(
                "module example.catalog\n"
                "import missing.one.Type\n"
                "  $\n"
                "import missing.two.Type\n"
                "value Pet {\n}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.catalog\n"
                "error Pet {\n}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])

            def snapshot(analysis: compiler_diagnostics.CompilerAnalysis):
                return [
                    (
                        diagnostic.code.value,
                        diagnostic.phase,
                        diagnostic.severity.value,
                        diagnostic.message,
                        diagnostic.source_path.name,
                        diagnostic.location.line,
                        diagnostic.location.column,
                    )
                    for diagnostic in analysis.diagnostics
                ]

            expected = [
                (
                    "AIDL-R001",
                    "resolve",
                    "error",
                    "unresolved import 'missing.one.Type'",
                    "a.aidl",
                    2,
                    1,
                ),
                (
                    "AIDL-P001",
                    "parse",
                    "error",
                    "unexpected character '$'",
                    "a.aidl",
                    3,
                    3,
                ),
                (
                    "AIDL-R001",
                    "resolve",
                    "error",
                    "unresolved import 'missing.two.Type'",
                    "a.aidl",
                    4,
                    1,
                ),
                (
                    "AIDL-R002",
                    "resolve",
                    "error",
                    "duplicate declaration 'example.catalog.Pet'",
                    "b.aidl",
                    2,
                    1,
                ),
            ]
            self.assertEqual(snapshot(first_analysis), expected)
            self.assertEqual(snapshot(second_analysis), expected)

    def test_diagnostic_json_schema_preserves_existing_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "broken.aidl"
            source.write_text(
                "module example.bad\n"
                "value Pet {\n"
                "  $\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = analysis.diagnostics[0]

            self.assertEqual(
                diagnostic.to_json(),
                {
                    "code": "AIDL-P001",
                    "phase": "parse",
                    "severity": "error",
                    "message": "unexpected character '$'",
                    "location": {
                        "file": str(source),
                        "line": 3,
                        "column": 3,
                        "offset": diagnostic.location.offset,
                    },
                },
            )

    def test_diagnostic_json_output_is_deterministic_and_preserves_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a.aidl"
            second = root / "b.aidl"
            first.write_text(
                "module example.catalog\n"
                "import missing.one.Type\n"
                "value Pet {\n}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.catalog\n"
                "import missing.two.Type\n"
                "error Pet {\n}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])

            first_output = compiler_diagnostics.compiler_diagnostics_to_json(
                first_analysis.diagnostics
            )
            second_output = compiler_diagnostics.compiler_diagnostics_to_json(
                second_analysis.diagnostics
            )

            self.assertEqual(first_output, second_output)
            decoded = json.loads(first_output)
            self.assertEqual(
                [diagnostic["code"] for diagnostic in decoded],
                ["AIDL-R001", "AIDL-R001", "AIDL-R002"],
            )
            self.assertEqual(
                [diagnostic["location"]["file"] for diagnostic in decoded],
                [str(first), str(second), str(second)],
            )
            self.assertEqual(
                [diagnostic["severity"] for diagnostic in decoded],
                ["error", "error", "error"],
            )

    def test_persisted_entity_with_exactly_one_owner_service_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entity = root / "a-domain.aidl"
            service = root / "b-service.aidl"
            entity.write_text(
                "module example.domain\n"
                "export entity Pet {\n}\n",
                encoding="utf-8",
            )
            service.write_text(
                "module example.system\n"
                "import example.domain.*\n"
                "service PetService {\n"
                "  owns [Pet]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_persisted_entity_without_owner_service_has_stable_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entity = root / "entity.aidl"
            entity.write_text(
                "module example.domain\n"
                "entity Pet {\n}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(
                diagnostic.code,
                compiler_diagnostics.CompilerDiagnosticCode.ENTITY_OWNER_CARDINALITY,
            )
            self.assertEqual(diagnostic.code, "AIDL-DIST400")
            self.assertEqual(diagnostic.phase, "policy")
            self.assertEqual(
                diagnostic.severity,
                compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
            )
            self.assertEqual(
                diagnostic.message,
                "persisted entity 'example.domain.Pet' must have exactly one owner service; found none",
            )
            self.assertEqual(diagnostic.source_path, entity)
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (2, 1),
            )

    def test_multiple_owner_services_are_deterministic_across_input_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entity = root / "a-domain.aidl"
            first_service = root / "b-first.aidl"
            second_service = root / "c-second.aidl"
            entity.write_text(
                "module example.domain\n"
                "export entity Pet {\n}\n",
                encoding="utf-8",
            )
            first_service.write_text(
                "module example.first\n"
                "import example.domain.Pet\n"
                "service FirstService {\n"
                "  owns [Pet]\n"
                "}\n",
                encoding="utf-8",
            )
            second_service.write_text(
                "module example.second\n"
                "import example.domain.*\n"
                "service SecondService {\n"
                "  owns [Pet]\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis(
                [second_service, first_service, entity]
            )

            def snapshot(analysis: compiler_diagnostics.CompilerAnalysis):
                return [
                    (
                        diagnostic.code.value,
                        diagnostic.phase,
                        diagnostic.severity.value,
                        diagnostic.message,
                        diagnostic.source_path.name,
                        diagnostic.location.line,
                        diagnostic.location.column,
                    )
                    for diagnostic in analysis.diagnostics
                ]

            expected = [
                (
                    "AIDL-DIST400",
                    "policy",
                    "error",
                    "persisted entity 'example.domain.Pet' must have exactly one owner service; found 2: example.first.FirstService, example.second.SecondService",
                    "a-domain.aidl",
                    2,
                    8,
                )
            ]
            self.assertEqual(snapshot(first_analysis), expected)
            self.assertEqual(snapshot(second_analysis), expected)
            self.assertEqual(
                compiler_diagnostics.compiler_diagnostics_to_json(
                    first_analysis.diagnostics
                ),
                compiler_diagnostics.compiler_diagnostics_to_json(
                    second_analysis.diagnostics
                ),
            )

    def test_valid_project_has_no_compiler_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "consumer.aidl").write_text(
                "module example.consumer\n"
                "import example.provider.Visible\n"
                "value Consumer {\n}\n",
                encoding="utf-8",
            )
            (root / "provider.aidl").write_text(
                "module example.provider\n"
                "export value Visible {\n}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())
            self.assertEqual(len(analysis.project.import_resolutions), 1)
            self.assertEqual(
                [
                    declaration.fully_qualified_name
                    for declaration in analysis.project.import_resolutions[0].declarations
                ],
                ["example.provider.Visible"],
            )


if __name__ == "__main__":
    unittest.main()
