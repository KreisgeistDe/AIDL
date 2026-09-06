from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class CrossServiceRefDiagnosticsTest(unittest.TestCase):
    def test_ref_within_same_owner_service_boundary_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "a-order.aidl"
            target = root / "b-customer.aidl"
            service = root / "c-service.aidl"
            source.write_text(
                "module example.orders\n"
                "import example.customers.Customer\n"
                "export entity Order {\n"
                "  customer: ref Customer required\n"
                "}\n",
                encoding="utf-8",
            )
            target.write_text(
                "module example.customers\n"
                "export entity Customer {\n}\n",
                encoding="utf-8",
            )
            service.write_text(
                "module example.sales\n"
                "import example.orders.Order\n"
                "import example.customers.*\n"
                "service SalesService {\n"
                "  owns [Order, Customer]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(analysis.diagnostics, ())

    def test_cross_service_ref_has_stable_policy_diagnostic_at_field_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "a-order.aidl"
            target = root / "b-customer.aidl"
            source_service = root / "c-order-service.aidl"
            target_service = root / "d-customer-service.aidl"
            source.write_text(
                "module example.orders\n"
                "import example.customers.Customer\n"
                "export entity Order {\n"
                "  customer: ref Customer required\n"
                "}\n",
                encoding="utf-8",
            )
            target.write_text(
                "module example.customers\n"
                "export entity Customer {\n}\n",
                encoding="utf-8",
            )
            source_service.write_text(
                "module example.orders\n"
                "service OrderService {\n"
                "  owns [Order]\n"
                "}\n",
                encoding="utf-8",
            )
            target_service.write_text(
                "module example.customers\n"
                "service CustomerService {\n"
                "  owns [Customer]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])

            self.assertEqual(len(analysis.diagnostics), 1)
            diagnostic = analysis.diagnostics[0]
            self.assertEqual(
                diagnostic.code,
                compiler_diagnostics.CompilerDiagnosticCode.CROSS_SERVICE_REF,
            )
            self.assertEqual(diagnostic.code, "AIDL-DIST401")
            self.assertEqual(diagnostic.phase, "policy")
            self.assertEqual(
                diagnostic.severity,
                compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
            )
            self.assertEqual(
                diagnostic.message,
                "ref from entity 'example.orders.Order' to 'example.customers.Customer' crosses owner service boundary: 'example.orders.OrderService' -> 'example.customers.CustomerService'",
            )
            self.assertEqual(diagnostic.source_path, source)
            self.assertEqual(
                (diagnostic.location.line, diagnostic.location.column),
                (4, 3),
            )

    def test_cross_service_ref_order_and_json_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            order = root / "a-order.aidl"
            customer = root / "b-customer.aidl"
            warehouse = root / "c-warehouse.aidl"
            order_service = root / "d-order-service.aidl"
            customer_service = root / "e-customer-service.aidl"
            warehouse_service = root / "f-warehouse-service.aidl"
            order.write_text(
                "module example.orders\n"
                "import example.customers.Customer\n"
                "import example.warehouse.*\n"
                "export entity Order {\n"
                "  customer: ref Customer required\n"
                "  warehouse: ref Warehouse required\n"
                "}\n",
                encoding="utf-8",
            )
            customer.write_text(
                "module example.customers\n"
                "export entity Customer {\n}\n",
                encoding="utf-8",
            )
            warehouse.write_text(
                "module example.warehouse\n"
                "export entity Warehouse {\n}\n",
                encoding="utf-8",
            )
            order_service.write_text(
                "module example.orders\n"
                "service OrderService {\n"
                "  owns [Order]\n"
                "}\n",
                encoding="utf-8",
            )
            customer_service.write_text(
                "module example.customers\n"
                "service CustomerService {\n"
                "  owns [Customer]\n"
                "}\n",
                encoding="utf-8",
            )
            warehouse_service.write_text(
                "module example.warehouse\n"
                "service WarehouseService {\n"
                "  owns [Warehouse]\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis(
                [
                    warehouse_service,
                    order_service,
                    customer,
                    order,
                    customer_service,
                    warehouse,
                ]
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
                    "AIDL-DIST401",
                    "ref from entity 'example.orders.Order' to 'example.customers.Customer' crosses owner service boundary: 'example.orders.OrderService' -> 'example.customers.CustomerService'",
                    "a-order.aidl",
                    5,
                    3,
                ),
                (
                    "AIDL-DIST401",
                    "ref from entity 'example.orders.Order' to 'example.warehouse.Warehouse' crosses owner service boundary: 'example.orders.OrderService' -> 'example.warehouse.WarehouseService'",
                    "a-order.aidl",
                    6,
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
                ["AIDL-DIST401", "AIDL-DIST401"],
            )


if __name__ == "__main__":
    unittest.main()
