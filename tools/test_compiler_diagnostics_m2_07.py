from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class TransactionIsolationDiagnosticsTest(unittest.TestCase):
    def test_bound_mutation_with_supported_isolation_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [readCommitted, serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    write: OrderDb.update()\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_bound_consumer_with_supported_isolation_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [readCommitted]\n"
                "}\n"
                "consumer ApplyOrder {\n"
                "  idempotency: event.eventId retain 30d\n"
                "  transaction on OrderDb isolation readCommitted {\n"
                "    write: OrderDb.update()\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  runs [consumer ApplyOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_bound_transaction_requires_declared_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [readCommitted, serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb {\n"
                "    write: OrderDb.update()\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(
                diagnostic.code,
                compiler_diagnostics.CompilerDiagnosticCode.TRANSACTION_ISOLATION,
            )
            self.assertEqual(diagnostic.code, "AIDL-DIST407")
            self.assertEqual(diagnostic.phase, "policy")
            self.assertEqual(
                diagnostic.severity,
                compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
            )
            self.assertEqual(
                diagnostic.message,
                "transaction in 'example.orders.ChangeOrder' on resource 'example.orders.OrderDb' must declare isolation",
            )
            self.assertEqual(diagnostic.source_path, source)
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (10, 3),
            )

    def test_bound_transaction_rejects_unsupported_resource_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [readCommitted, serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation repeatableRead {\n"
                "    write: OrderDb.update()\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(diagnostic.code, "AIDL-DIST407")
            self.assertEqual(
                diagnostic.message,
                "transaction in 'example.orders.ChangeOrder' on resource 'example.orders.OrderDb' declares isolation 'repeatableRead' not supported by the resource",
            )
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (10, 3),
            )

    def test_unresolved_transaction_binding_adds_no_m2_07_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on MissingDb isolation serializable {\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [MissingDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_m2_03_outside_service_resource_boundary_remains_dist402_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "resource AuditDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on AuditDb {\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            self.assertEqual(analysis.diagnostics[0].code, "AIDL-DIST402")
            self.assertEqual(
                analysis.diagnostics[0].message,
                "transaction in 'example.orders.ChangeOrder' targets resource 'example.orders.AuditDb' outside service 'example.orders.OrdersService' resource boundary",
            )

    def test_isolation_order_and_json_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-missing.aidl"
            second = root / "b-unsupported.aidl"
            first.write_text(
                "module example.orders\n"
                "resource PrimaryDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation MissingIsolation {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on PrimaryDb {\n"
                "  }\n"
                "}\n"
                "service PrimaryService {\n"
                "  uses [PrimaryDb]\n"
                "  exposes [mutation MissingIsolation]\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.orders\n"
                "resource SecondaryDb sql {\n"
                "  transactions [readCommitted]\n"
                "}\n"
                "mutation UnsupportedIsolation {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on SecondaryDb isolation serializable {\n"
                "  }\n"
                "}\n"
                "service SecondaryService {\n"
                "  uses [SecondaryDb]\n"
                "  exposes [mutation UnsupportedIsolation]\n"
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
                    "AIDL-DIST407",
                    "transaction in 'example.orders.MissingIsolation' on resource 'example.orders.PrimaryDb' must declare isolation",
                    "a-missing.aidl",
                    10,
                    3,
                ),
                (
                    "AIDL-DIST407",
                    "transaction in 'example.orders.UnsupportedIsolation' on resource 'example.orders.SecondaryDb' declares isolation 'serializable' not supported by the resource",
                    "b-unsupported.aidl",
                    10,
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
                ["AIDL-DIST407", "AIDL-DIST407"],
            )


if __name__ == "__main__":
    unittest.main()
