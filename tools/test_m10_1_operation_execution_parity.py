from __future__ import annotations

import json
import unittest

try:
    from .aidl_parser import Node
    from .compiler_language_surface import LanguageSurfaceBridge, _format_parameter_list
    from .compiler_language_surface_body_parity import ContractBodyParityBridge
    from .compiler_operation_execution_parity import (
        EXECUTION_PARITY_VERSION,
        operation_execution_dispositions,
        operation_execution_dispositions_json,
    )
except ImportError:  # pragma: no cover
    from aidl_parser import Node
    from compiler_language_surface import LanguageSurfaceBridge, _format_parameter_list
    from compiler_language_surface_body_parity import ContractBodyParityBridge
    from compiler_operation_execution_parity import (
        EXECUTION_PARITY_VERSION,
        operation_execution_dispositions,
        operation_execution_dispositions_json,
    )


def _operation(kind: str, parameters: str = "", returns: str = "int", children=None) -> Node:
    return Node(
        kind=kind,
        name="execute",
        attrs={"parameters": parameters, "returns": returns},
        children=list(children or []),
    )


def _by_key():
    data = operation_execution_dispositions()
    return data, {
        (item["operation_kind"], item["concept"]): item
        for item in data["declarations"]
    }


class OperationExecutionParityTest(unittest.TestCase):
    def test_package_dispositions_are_contract_derived_and_complete(self) -> None:
        data, items = _by_key()
        self.assertEqual(data["schema_version"], EXECUTION_PARITY_VERSION)
        self.assertEqual(data["contract_revision"], 4)

        for kind in ("query", "mutation"):
            self.assertEqual(items[(kind, "type_ref_range")]["disposition"], "production_parity")
            self.assertEqual(items[(kind, "parameter_default")]["disposition"], "production_parity")
            self.assertEqual(items[(kind, "generic_type_arguments")]["disposition"], "excluded")
            self.assertEqual(items[(kind, "non_range_constraints")]["disposition"], "excluded")
            self.assertEqual(items[(kind, "operation_generics")]["disposition"], "excluded")

        for concept in ("idempotency", "transaction"):
            item = items[("mutation", concept)]
            self.assertEqual(item["disposition"], "excluded")
            self.assertEqual(item["diagnostic_boundary"], "AIDL-N010 -> AIDL-N013")

    def test_audit_json_is_byte_stable(self) -> None:
        first = operation_execution_dispositions_json()
        second = operation_execution_dispositions_json()
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first)["contract_revision"], 4)
        self.assertNotIn(": ", first)
        self.assertNotIn(", ", first)

    def test_range_and_default_are_losslessly_preserved_for_query_and_mutation(self) -> None:
        bridge = LanguageSurfaceBridge()
        for kind in ("query", "mutation"):
            with self.subTest(kind=kind):
                declaration, diagnostics = bridge.normalize_declaration(
                    _operation(kind, "(limit: int(1..10) default 5)", "int(0..20)?")
                )
                self.assertEqual(diagnostics, [])
                header = next(item for item in declaration.header_args if item.name == "parameters")
                parameter = header.value[0]
                self.assertEqual(parameter.type_ref.range, (1, 10))
                self.assertEqual(parameter.modifiers[0].name, "default")
                self.assertEqual(parameter.modifiers[0].args, ("5",))
                self.assertIsNotNone(declaration.result_type)
                self.assertEqual(declaration.result_type.range, (0, 20))
                self.assertEqual(_format_parameter_list(header.value), "limit: int(1..10) default 5")

    def test_unsupported_typeref_shapes_keep_aidl_n015_fail_closed_evidence(self) -> None:
        bridge = LanguageSurfaceBridge()
        for raw in ("int(1)", "Result<string>"):
            with self.subTest(raw=raw):
                diagnostics = []
                bridge.type_ref(raw, diagnostics)
                self.assertEqual([item.code for item in diagnostics], ["AIDL-N015"])

    def test_mutation_idempotency_and_transaction_remain_legacy_fail_closed_clauses(self) -> None:
        bridge = ContractBodyParityBridge()
        node = _operation(
            "mutation",
            children=[
                Node(kind="clause", name="idempotency: request.id", attrs={}, children=[]),
                Node(kind="clause", name="transaction: required", attrs={}, children=[]),
            ],
        )
        declaration, diagnostics = bridge.normalize_declaration(node)
        self.assertEqual(declaration.body_slots, ())
        self.assertEqual([item.code for item in diagnostics], ["AIDL-N010", "AIDL-N010"])
        self.assertTrue(all(item.severity == "warning" for item in diagnostics))


if __name__ == "__main__":
    unittest.main()
