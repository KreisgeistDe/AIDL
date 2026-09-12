from __future__ import annotations

import json

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


def test_package_dispositions_are_contract_derived_and_complete() -> None:
    data, items = _by_key()
    assert data["schema_version"] == EXECUTION_PARITY_VERSION
    assert data["contract_revision"] == 4

    for kind in ("query", "mutation"):
        assert items[(kind, "type_ref_range")]["disposition"] == "production_parity"
        assert items[(kind, "parameter_default")]["disposition"] == "production_parity"
        assert items[(kind, "generic_type_arguments")]["disposition"] == "excluded"
        assert items[(kind, "non_range_constraints")]["disposition"] == "excluded"
        assert items[(kind, "operation_generics")]["disposition"] == "excluded"

    for concept in ("idempotency", "transaction"):
        item = items[("mutation", concept)]
        assert item["disposition"] == "excluded"
        assert item["diagnostic_boundary"] == "AIDL-N010 -> AIDL-N013"


def test_audit_json_is_byte_stable() -> None:
    first = operation_execution_dispositions_json()
    second = operation_execution_dispositions_json()
    assert first == second
    assert json.loads(first)["contract_revision"] == 4
    assert ": " not in first
    assert ", " not in first


def test_range_and_default_are_losslessly_preserved_for_query_and_mutation() -> None:
    bridge = LanguageSurfaceBridge()
    for kind in ("query", "mutation"):
        declaration, diagnostics = bridge.normalize_declaration(
            _operation(kind, "(limit: int(1..10) default 5)", "int(0..20)?")
        )
        assert diagnostics == []
        header = next(item for item in declaration.header_args if item.name == "parameters")
        parameter = header.value[0]
        assert parameter.type_ref.range == (1, 10)
        assert parameter.modifiers[0].name == "default"
        assert parameter.modifiers[0].arguments == ("5",)
        assert declaration.result_type is not None
        assert declaration.result_type.range == (0, 20)
        assert _format_parameter_list(header.value) == "limit: int(1..10) default 5"


def test_unsupported_typeref_shapes_keep_aidl_n015_fail_closed_evidence() -> None:
    bridge = LanguageSurfaceBridge()
    for raw in ("int(1)", "Result<string>"):
        diagnostics = []
        bridge.type_ref(raw, diagnostics)
        assert [item.code for item in diagnostics] == ["AIDL-N015"]


def test_mutation_idempotency_and_transaction_remain_legacy_fail_closed_clauses() -> None:
    bridge = ContractBodyParityBridge()
    node = _operation(
        "mutation",
        children=[
            Node(kind="clause", name="idempotency: request.id", attrs={}, children=[]),
            Node(kind="clause", name="transaction: required", attrs={}, children=[]),
        ],
    )
    declaration, diagnostics = bridge.normalize_declaration(node)
    assert declaration.body_slots == ()
    assert [item.code for item in diagnostics] == ["AIDL-N010", "AIDL-N010"]
    assert all(item.severity == "warning" for item in diagnostics)
