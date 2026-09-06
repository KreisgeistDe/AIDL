from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class PublicReasonDiagnosticsTest(unittest.TestCase):
    def test_public_query_and_public_mutation_with_reason_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "operations.aidl"
            source.write_text(
                "module example.publicapi\n"
                "@publicReason(\"Public read contract.\")\n"
                "export query getPublic() -> string {\n"
                "  auth: public\n"
                "  read: PublicData.get()\n"
                "  consistency: strong\n"
                "  errors: [InternalFailure]\n"
                "}\n"
                "@publicReason(\"Public write contract.\")\n"
                "export mutation recordPublic() -> string {\n"
                "  auth: public\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: PublicStore.append()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_public_query_and_mutation_require_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "operations.aidl"
            source.write_text(
                "module example.publicapi\n"
                "query getPublic() -> string {\n"
                "  auth: public\n"
                "  read: PublicData.get()\n"
                "}\n"
                "mutation recordPublic() -> string {\n"
                "  auth: public\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: PublicStore.append()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 2)
            self.assertEqual(
                [diagnostic.code.value for diagnostic in analysis.diagnostics],
                ["AIDL-DIST406", "AIDL-DIST406"],
            )
            self.assertEqual(
                [diagnostic.message for diagnostic in analysis.diagnostics],
                [
                    "public query 'example.publicapi.getPublic' must declare exactly one @publicReason annotation; found 0",
                    "public mutation 'example.publicapi.recordPublic' must declare exactly one @publicReason annotation; found 0",
                ],
            )
            self.assertEqual(
                [
                    (diagnostic.location.line, diagnostic.location.column)
                    for diagnostic in analysis.diagnostics
                ],
                [(3, 3), (7, 3)],
            )
            for diagnostic in analysis.diagnostics:
                self.assertEqual(diagnostic.phase, "policy")
                self.assertEqual(
                    diagnostic.severity,
                    compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
                )
                self.assertEqual(diagnostic.source_path, source)

    def test_public_reason_is_rejected_on_non_public_query_and_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "operations.aidl"
            source.write_text(
                "module example.publicapi\n"
                "@publicReason(\"Not public.\")\n"
                "query getPrivate() -> string {\n"
                "  auth: authenticated\n"
                "  read: PrivateData.get()\n"
                "}\n"
                "@publicReason(\"Still not public.\")\n"
                "mutation recordPrivate() -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: PrivateStore.append()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 2)
            self.assertEqual(
                [diagnostic.message for diagnostic in analysis.diagnostics],
                [
                    "@publicReason on query 'example.publicapi.getPrivate' requires 'auth: public'",
                    "@publicReason on mutation 'example.publicapi.recordPrivate' requires 'auth: public'",
                ],
            )
            self.assertEqual(
                [
                    (diagnostic.location.line, diagnostic.location.column)
                    for diagnostic in analysis.diagnostics
                ],
                [(2, 1), (7, 1)],
            )

    def test_empty_and_duplicate_public_reasons_are_rejected_at_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "operations.aidl"
            source.write_text(
                "module example.publicapi\n"
                "@publicReason(\"\")\n"
                "query emptyReason() -> string {\n"
                "  auth: public\n"
                "  read: PublicData.get()\n"
                "}\n"
                "@publicReason(\"First reason.\")\n"
                "@publicReason(\"Second reason.\")\n"
                "query duplicateReason() -> string {\n"
                "  auth: public\n"
                "  read: PublicData.get()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 2)
            self.assertEqual(
                [diagnostic.message for diagnostic in analysis.diagnostics],
                [
                    "@publicReason on public query 'example.publicapi.emptyReason' must contain exactly one non-empty string reason",
                    "public query 'example.publicapi.duplicateReason' must declare exactly one @publicReason annotation; found 2",
                ],
            )
            self.assertEqual(
                [
                    (diagnostic.location.line, diagnostic.location.column)
                    for diagnostic in analysis.diagnostics
                ],
                [(2, 1), (8, 1)],
            )

    def test_public_reason_order_and_json_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-public.aidl"
            second = root / "b-private.aidl"
            first.write_text(
                "module example.publicapi\n"
                "query publicRead() -> string {\n"
                "  auth: public\n"
                "  read: PublicData.get()\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.publicapi\n"
                "@publicReason(\"Not public.\")\n"
                "query privateRead() -> string {\n"
                "  auth: authenticated\n"
                "  read: PrivateData.get()\n"
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
                    "AIDL-DIST406",
                    "public query 'example.publicapi.publicRead' must declare exactly one @publicReason annotation; found 0",
                    "a-public.aidl",
                    3,
                    3,
                ),
                (
                    "AIDL-DIST406",
                    "@publicReason on query 'example.publicapi.privateRead' requires 'auth: public'",
                    "b-private.aidl",
                    2,
                    1,
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
                ["AIDL-DIST406", "AIDL-DIST406"],
            )


if __name__ == "__main__":
    unittest.main()
