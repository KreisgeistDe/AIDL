from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class TransactionBoundaryDiagnosticsTest(unittest.TestCase):
    def test_transaction_within_service_and_resource_boundary_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "entity Order {\n}\n"
                "resource OrderDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    order = Order.require(input.orderId)\n"
                "    write: order.update()\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  owns [Order]\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_transaction_rejects_entity_owned_by_another_service(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orders = root / "a-orders.aidl"
            customers = root / "b-customers.aidl"
            orders.write_text(
                "module example.orders\n"
                "import example.customers.Customer\n"
                "resource OrderDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    customer = Customer.require(input.customerId)\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )
            customers.write_text(
                "module example.customers\n"
                "export entity Customer {\n}\n"
                "service CustomersService {\n"
                "  owns [Customer]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(
                diagnostic.code,
                compiler_diagnostics.CompilerDiagnosticCode.TRANSACTION_BOUNDARY,
            )
            self.assertEqual(diagnostic.code, "AIDL-DIST402")
            self.assertEqual(diagnostic.phase, "policy")
            self.assertEqual(
                diagnostic.severity,
                compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
            )
            self.assertEqual(
                diagnostic.message,
                "transaction in 'example.orders.ChangeOrder' for service 'example.orders.OrdersService' accesses entity 'example.customers.Customer' owned by 'example.customers.CustomersService'",
            )
            self.assertEqual(diagnostic.source_path, orders)
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (12, 5),
            )

    def test_transaction_rejects_resource_outside_service_resource_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "orders.aidl"
            source.write_text(
                "module example.orders\n"
                "entity Order {\n}\n"
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
                "  transaction on AuditDb isolation serializable {\n"
                "    order = Order.require(input.orderId)\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  owns [Order]\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(diagnostic.code, "AIDL-DIST402")
            self.assertEqual(
                diagnostic.message,
                "transaction in 'example.orders.ChangeOrder' targets resource 'example.orders.AuditDb' outside service 'example.orders.OrdersService' resource boundary",
            )
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (15, 3),
            )

    def test_transaction_rejects_second_resource_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            operation = root / "a-operation.aidl"
            topology = root / "b-topology.aidl"
            operation.write_text(
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
                "  transaction on OrderDb isolation serializable {\n"
                "    first = AuditDb.append(input.orderId)\n"
                "    second = AuditDb.append(input.orderId)\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            topology.write_text(
                "module example.orders\n"
                "service OrdersService {\n"
                "  uses [OrderDb, AuditDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis(
                [topology, operation]
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
                    "AIDL-DIST402",
                    "policy",
                    "error",
                    "transaction in 'example.orders.ChangeOrder' on 'example.orders.OrderDb' accesses second resource 'example.orders.AuditDb'",
                    "a-operation.aidl",
                    14,
                    5,
                ),
                (
                    "AIDL-DIST402",
                    "policy",
                    "error",
                    "transaction in 'example.orders.ChangeOrder' on 'example.orders.OrderDb' accesses second resource 'example.orders.AuditDb'",
                    "a-operation.aidl",
                    15,
                    5,
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
                ["AIDL-DIST402", "AIDL-DIST402"],
            )


if __name__ == "__main__":
    unittest.main()
