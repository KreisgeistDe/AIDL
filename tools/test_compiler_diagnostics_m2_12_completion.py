from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


_EXPECTED = {
    "AIDL-DIST401": "source and target entities owned by same service",
    "AIDL-DIST402": "transaction confined to bound service and single target resource",
    "AIDL-DIST406": (
        "public operations have exactly one non-empty @publicReason; "
        "non-public operations have none"
    ),
    "AIDL-DIST407": "declared isolation supported by target resource",
    "AIDL-DIST408": "transactional emits use via outbox",
    "AIDL-DIST412": "valid API transport, version, compatibility, and operation mappings",
}


class DiagnosticActionabilityCompletionTest(unittest.TestCase):
    def _diagnostics(
        self, root: Path, code: str, paths: list[Path] | None = None
    ) -> tuple[compiler_diagnostics.CompilerDiagnostic, ...]:
        analysis = compiler_diagnostics.load_compiler_analysis(paths or [root])
        return tuple(item for item in analysis.diagnostics if item.code == code)

    def _assert_metadata(
        self,
        diagnostic: compiler_diagnostics.CompilerDiagnostic,
        *,
        code: str,
        kind: str,
        name: str,
    ) -> None:
        payload = diagnostic.to_json()
        self.assertEqual(payload["subject"], {"kind": kind, "name": name})
        self.assertEqual(payload["expected"], _EXPECTED[code])
        self.assertEqual(payload["docs"], f"aidl://diagnostics/{code}")
        self.assertNotIn("allowedFixes", payload)

    def _assert_json_deterministic(self, root: Path, code: str) -> None:
        first = self._diagnostics(root, code)
        second = self._diagnostics(
            root,
            code,
            sorted(root.glob("*.aidl"), reverse=True),
        )
        self.assertEqual(
            compiler_diagnostics.compiler_diagnostics_to_json(first),
            compiler_diagnostics.compiler_diagnostics_to_json(second),
        )

    def test_dist401_metadata_preserves_field_anchors_and_local_source_entity(self) -> None:
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
                "module example.customers\nexport entity Customer {\n}\n",
                encoding="utf-8",
            )
            warehouse.write_text(
                "module example.warehouse\nexport entity Warehouse {\n}\n",
                encoding="utf-8",
            )
            order_service.write_text(
                "module example.orders\nservice OrderService {\n  owns [Order]\n}\n",
                encoding="utf-8",
            )
            customer_service.write_text(
                "module example.customers\nservice CustomerService {\n  owns [Customer]\n}\n",
                encoding="utf-8",
            )
            warehouse_service.write_text(
                "module example.warehouse\nservice WarehouseService {\n  owns [Warehouse]\n}\n",
                encoding="utf-8",
            )

            diagnostics = self._diagnostics(root, "AIDL-DIST401")
            self.assertEqual(
                [(item.location.line, item.location.column) for item in diagnostics],
                [(5, 3), (6, 3)],
            )
            for diagnostic in diagnostics:
                self._assert_metadata(
                    diagnostic,
                    code="AIDL-DIST401",
                    kind="entity",
                    name="Order",
                )
            self._assert_json_deterministic(root, "AIDL-DIST401")

    def test_dist402_all_boundary_variants_have_operation_metadata_and_existing_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orders = root / "a-orders.aidl"
            customers = root / "b-customers.aidl"
            orders.write_text(
                "module example.orders\n"
                "import example.customers.Customer\n"
                "entity Order {\n}\n"
                "resource OrderDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "resource AuditDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation OutsideTarget {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "  transaction on AuditDb isolation serializable {\n"
                "  }\n"
                "}\n"
                "mutation SecondResource {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    audit = AuditDb.append(input.id)\n"
                "  }\n"
                "}\n"
                "mutation ForeignEntity {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    customer = Customer.require(input.customerId)\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  owns [Order]\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation OutsideTarget, mutation SecondResource, mutation ForeignEntity]\n"
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

            diagnostics = self._diagnostics(root, "AIDL-DIST402")
            self.assertEqual(
                [(item.location.line, item.location.column) for item in diagnostics],
                [(16, 3), (25, 5), (34, 5)],
            )
            self.assertEqual(
                [item.to_json()["subject"] for item in diagnostics],
                [
                    {"kind": "mutation", "name": "OutsideTarget"},
                    {"kind": "mutation", "name": "SecondResource"},
                    {"kind": "mutation", "name": "ForeignEntity"},
                ],
            )
            for diagnostic in diagnostics:
                payload = diagnostic.to_json()
                self.assertEqual(payload["expected"], _EXPECTED["AIDL-DIST402"])
                self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST402")
                self.assertNotIn("allowedFixes", payload)
            self._assert_json_deterministic(root, "AIDL-DIST402")

    def test_dist406_all_public_reason_variants_have_local_operation_metadata_and_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "operations.aidl"
            source.write_text(
                "module example.publicapi\n"
                "@publicReason(\"Not public.\")\n"
                "query PrivateRead() -> string {\n"
                "  auth: authenticated\n"
                "  read: PrivateData.get()\n"
                "}\n"
                "query MissingReason() -> string {\n"
                "  auth: public\n"
                "  read: PublicData.get()\n"
                "}\n"
                "@publicReason(\"First reason.\")\n"
                "@publicReason(\"Second reason.\")\n"
                "query DuplicateReason() -> string {\n"
                "  auth: public\n"
                "  read: PublicData.get()\n"
                "}\n"
                "@publicReason(\"\")\n"
                "mutation EmptyReason() -> string {\n"
                "  auth: public\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: PublicStore.append()\n"
                "}\n",
                encoding="utf-8",
            )

            diagnostics = self._diagnostics(root, "AIDL-DIST406")
            self.assertEqual(
                [(item.location.line, item.location.column) for item in diagnostics],
                [(2, 1), (8, 3), (12, 1), (17, 1)],
            )
            expected_subjects = [
                ("query", "PrivateRead"),
                ("query", "MissingReason"),
                ("query", "DuplicateReason"),
                ("mutation", "EmptyReason"),
            ]
            for diagnostic, (kind, name) in zip(diagnostics, expected_subjects):
                self._assert_metadata(
                    diagnostic,
                    code="AIDL-DIST406",
                    kind=kind,
                    name=name,
                )
            self._assert_json_deterministic(root, "AIDL-DIST406")

    def test_dist407_missing_and_unsupported_isolation_have_operation_metadata_and_transaction_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "isolation.aidl"
            source.write_text(
                "module example.orders\n"
                "resource PrimaryDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "resource SecondaryDb sql {\n"
                "  transactions [readCommitted]\n"
                "}\n"
                "mutation MissingIsolation {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "  transaction on PrimaryDb {\n"
                "  }\n"
                "}\n"
                "consumer UnsupportedIsolation {\n"
                "  idempotency: event.eventId retain 30d\n"
                "  transaction on SecondaryDb isolation serializable {\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [PrimaryDb, SecondaryDb]\n"
                "  exposes [mutation MissingIsolation]\n"
                "  runs [consumer UnsupportedIsolation]\n"
                "}\n",
                encoding="utf-8",
            )

            diagnostics = self._diagnostics(root, "AIDL-DIST407")
            self.assertEqual(
                [(item.location.line, item.location.column) for item in diagnostics],
                [(13, 3), (18, 3)],
            )
            for diagnostic, kind, name in [
                (diagnostics[0], "mutation", "MissingIsolation"),
                (diagnostics[1], "consumer", "UnsupportedIsolation"),
            ]:
                self._assert_metadata(
                    diagnostic,
                    code="AIDL-DIST407",
                    kind=kind,
                    name=name,
                )
            self._assert_json_deterministic(root, "AIDL-DIST407")

    def test_dist408_direct_and_nested_emits_have_operation_metadata_and_emit_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "outbox.aidl"
            source.write_text(
                "module example.orders\n"
                "resource OrderDb sql {\n"
                "  transactions [serializable]\n"
                "}\n"
                "mutation ChangeOrder {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    emit: OrderChanged() to OrderEvents\n"
                "  }\n"
                "}\n"
                "consumer ApplyOrder {\n"
                "  idempotency: event.eventId retain 30d\n"
                "  transaction on OrderDb isolation serializable {\n"
                "    when true {\n"
                "      emit: OrderApplied() to OrderEvents\n"
                "    }\n"
                "  }\n"
                "}\n"
                "service OrdersService {\n"
                "  uses [OrderDb]\n"
                "  exposes [mutation ChangeOrder]\n"
                "  runs [consumer ApplyOrder]\n"
                "}\n",
                encoding="utf-8",
            )

            diagnostics = self._diagnostics(root, "AIDL-DIST408")
            self.assertEqual(
                [(item.location.line, item.location.column) for item in diagnostics],
                [(11, 5), (18, 7)],
            )
            for diagnostic, kind, name in [
                (diagnostics[0], "mutation", "ChangeOrder"),
                (diagnostics[1], "consumer", "ApplyOrder"),
            ]:
                self._assert_metadata(
                    diagnostic,
                    code="AIDL-DIST408",
                    kind=kind,
                    name=name,
                )
            self._assert_json_deterministic(root, "AIDL-DIST408")

    def test_dist412_all_api_emission_variants_have_api_metadata_no_fix_and_existing_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            api = root / "c-api.aidl"
            first.write_text(
                "module example.first\nexport query Shared {\n}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\nexport query Shared {\n}\n",
                encoding="utf-8",
            )
            api.write_text(
                "module example.api\n"
                "import example.first.*\n"
                "import example.second.*\n"
                "query ListPets {\n}\n"
                "mutation UpdatePet {\n"
                "  auth: private\n"
                "  allow: true\n"
                "  errors: []\n"
                "  idempotency: request.id\n"
                "  call: applyUpdate()\n"
                "}\n"
                "api EmptyApi {\n"
                "}\n"
                "api ValueApi {\n"
                "  transport websocket\n"
                "  version 0\n"
                "  operations [query Missing]\n"
                "  compatibility rolling\n"
                "}\n"
                "api ExplicitKindApi {\n"
                "  transport rest\n"
                "  version 1\n"
                "  operations [ListPets]\n"
                "  compatibility backward\n"
                "}\n"
                "api MismatchApi {\n"
                "  transport rest\n"
                "  version 1\n"
                "  operations [query UpdatePet]\n"
                "  compatibility backward\n"
                "}\n"
                "api DuplicateApi {\n"
                "  transport rest\n"
                "  version 1\n"
                "  operations [query ListPets, query example.api.ListPets]\n"
                "  compatibility backward\n"
                "}\n"
                "api AmbiguousApi {\n"
                "  transport rest\n"
                "  version 1\n"
                "  operations [query Shared]\n"
                "  compatibility backward\n"
                "}\n"
                "api MalformedListApi {\n"
                "  transport rest\n"
                "  version 1\n"
                "  operations query ListPets\n"
                "  compatibility backward\n"
                "}\n",
                encoding="utf-8",
            )

            diagnostics = self._diagnostics(root, "AIDL-DIST412")
            self.assertEqual(len(diagnostics), 13)
            self.assertEqual(
                [item.to_json()["subject"]["name"] for item in diagnostics],
                [
                    "EmptyApi",
                    "EmptyApi",
                    "EmptyApi",
                    "EmptyApi",
                    "ValueApi",
                    "ValueApi",
                    "ValueApi",
                    "ValueApi",
                    "ExplicitKindApi",
                    "MismatchApi",
                    "DuplicateApi",
                    "AmbiguousApi",
                    "MalformedListApi",
                ],
            )
            self.assertEqual(
                [(item.location.line, item.location.column) for item in diagnostics[:4]],
                [(13, 1), (13, 1), (13, 1), (13, 1)],
            )
            for diagnostic in diagnostics:
                self._assert_metadata(
                    diagnostic,
                    code="AIDL-DIST412",
                    kind="api",
                    name=diagnostic.to_json()["subject"]["name"],
                )
            self._assert_json_deterministic(root, "AIDL-DIST412")


if __name__ == "__main__":
    unittest.main()
