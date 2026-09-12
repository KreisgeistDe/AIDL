"""Executable M10.1-09 complete language-surface coverage audit.

The frozen contract remains the only normative semantic inventory.  This module
walks that contract generically, correlates its leaves with the already-integrated
compatibility/Production Normalization evidence, and exposes deterministic audit
JSON.  It deliberately does not define another declaration, body-slot, modifier,
or type grammar.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterator

try:
    from .compiler_declaration_family_parity import declaration_family_dispositions
    from .compiler_language_surface import LanguageSurfaceBridge
    from .compiler_language_surface_body_parity import ContractBodyParityBridge
    from .compiler_operation_execution_parity import operation_execution_dispositions
    from .compiler_operation_policy_parity import operation_policy_dispositions
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from compiler_declaration_family_parity import declaration_family_dispositions
    from compiler_language_surface import LanguageSurfaceBridge
    from compiler_language_surface_body_parity import ContractBodyParityBridge
    from compiler_operation_execution_parity import operation_execution_dispositions
    from compiler_operation_policy_parity import operation_policy_dispositions


LANGUAGE_SURFACE_COVERAGE_VERSION = "aidl.m10.1-language-surface-coverage/v1"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _semantic_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Return normative/compatibility contract facts, excluding illustrative examples."""

    return {key: value for key, value in contract.items() if key != "examples"}


def _list_item_label(item: Any, index: int) -> str:
    if isinstance(item, dict):
        for key in ("kind", "name", "id"):
            value = item.get(key)
            if isinstance(value, str) and value:
                return value
    return str(index)


def _contract_leaves(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[str, Any]]:
    """Yield every leaf from the contract without maintaining a parallel fact list."""

    if isinstance(value, dict):
        for key in sorted(value):
            yield from _contract_leaves(value[key], path + (str(key),))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _contract_leaves(item, path + (_list_item_label(item, index),))
        return
    yield "/" + "/".join(path), value


def _declaration_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = data.get("declarations")
    if not isinstance(items, list):
        raise ValueError("declaration-family audit must contain declarations")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("declaration_kind"), str):
            raise ValueError("declaration-family audit item is malformed")
        result[item["declaration_kind"]] = item
    return result


def _validate_contract_links(
    contract: dict[str, Any], declaration_map: dict[str, dict[str, Any]]
) -> None:
    modifiers = {
        item["name"]: item
        for item in contract.get("modifiers", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if len(modifiers) != len(contract.get("modifiers", [])):
        raise ValueError("frozen contract modifiers must have unique string names")

    declaration_kinds = set(declaration_map)
    for modifier_name, modifier in modifiers.items():
        for target in modifier.get("targets", []):
            root = str(target).split(".", 1)[0]
            if root not in declaration_kinds:
                raise ValueError(
                    f"modifier {modifier_name!r} targets unknown declaration family {root!r}"
                )

    for declaration in contract.get("declaration_kinds", []):
        kind = declaration["kind"]
        for header in declaration.get("header_args", []):
            parameter = header.get("parameter") if isinstance(header, dict) else None
            if not isinstance(parameter, dict):
                continue
            target = f"{kind}.parameter"
            for modifier_name in parameter.get("modifiers", []):
                modifier = modifiers.get(str(modifier_name))
                if modifier is None:
                    raise ValueError(
                        f"{target} references undeclared modifier {modifier_name!r}"
                    )
                if target not in modifier.get("targets", []):
                    raise ValueError(
                        f"{target} references modifier {modifier_name!r} without matching target evidence"
                    )


def _modifier_dispositions(
    contract: dict[str, Any], declaration_map: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for modifier in contract.get("modifiers", []):
        targets: list[dict[str, Any]] = []
        for target in modifier.get("targets", []):
            root = str(target).split(".", 1)[0]
            family = declaration_map[root]
            targets.append(
                {
                    "target": target,
                    "declaration_kind": root,
                    "production_disposition": family["disposition"],
                    "production_admission": family["production_admission"],
                }
            )
        result.append(
            {
                "name": modifier["name"],
                "arity": modifier["arity"],
                "argument_mode": modifier["argument_mode"],
                "targets": targets,
                "compatibility_disposition": "contract_driven",
            }
        )
    return result


def _bridge_semantic_shapes() -> dict[str, Any]:
    """Derive TypeRef/reference-projection shapes from the executable bridge itself."""

    bridge = LanguageSurfaceBridge()
    projection_bridge = LanguageSurfaceBridge(
        reference_projections={"Pet.id": ("Pet", "id", "uuid")}
    )
    return {
        "type_ref_optional": bridge.type_ref("string?").semantic(),
        "type_ref_range": bridge.type_ref("string(1 .. 80)").semantic(),
        "reference_projection": projection_bridge.type_ref("Pet.id").semantic(),
    }


def _fact_disposition(
    path: str, declaration_map: dict[str, dict[str, Any]]
) -> tuple[str, str]:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "declaration_kinds":
        family = declaration_map[parts[1]]
        return "contract_driven", str(family["production_admission"])
    if parts and parts[0] == "modifiers":
        return "contract_driven", "target_dependent"
    return "contract_metadata", "not_applicable"


def _build_coverage(
    contract: dict[str, Any],
    compiler_contract: dict[str, Any],
    body_contract: dict[str, Any],
    declaration_data: dict[str, Any],
    policy_data: dict[str, Any],
    execution_data: dict[str, Any],
) -> dict[str, Any]:
    """Build complete coverage while failing closed on contract/evidence drift."""

    if contract.get("authority") != "M10.1" or contract.get("status") != "frozen":
        raise ValueError("language-surface coverage requires the frozen M10.1 contract")
    if contract != compiler_contract or contract != body_contract:
        raise ValueError("compatibility bridge contract drift detected")

    revision = int(contract["contract_revision"])
    for name, data in (
        ("declaration-family", declaration_data),
        ("operation-policy", policy_data),
        ("operation-execution", execution_data),
    ):
        if int(data.get("contract_revision", -1)) != revision:
            raise ValueError(f"{name} audit contract revision drift detected")

    declaration_map = _declaration_map(declaration_data)
    contract_kinds = [item["kind"] for item in contract.get("declaration_kinds", [])]
    if contract_kinds != list(declaration_map):
        raise ValueError("declaration-family audit no longer matches frozen contract order")
    _validate_contract_links(contract, declaration_map)

    semantic_contract = _semantic_contract(contract)
    leaves = list(_contract_leaves(semantic_contract))
    facts: list[dict[str, Any]] = []
    for path, value in leaves:
        compatibility, production = _fact_disposition(path, declaration_map)
        facts.append(
            {
                "path": path,
                "value": value,
                "compatibility_disposition": compatibility,
                "production_disposition": production,
            }
        )

    return {
        "schema_version": LANGUAGE_SURFACE_COVERAGE_VERSION,
        "contract_revision": revision,
        "contract_sha256": "sha256:"
        + hashlib.sha256(_stable_json(semantic_contract).encode("utf-8")).hexdigest(),
        "contract_leaf_count": len(facts),
        "contract_facts": facts,
        "declaration_dispositions": declaration_data["declarations"],
        "modifier_dispositions": _modifier_dispositions(contract, declaration_map),
        "bridge_semantic_shapes": _bridge_semantic_shapes(),
        "operation_policy_dispositions": policy_data["declarations"],
        "operation_execution_dispositions": execution_data["declarations"],
    }


def language_surface_coverage() -> dict[str, Any]:
    """Return deterministic complete frozen-v1 coverage/disposition evidence."""

    surface = LanguageSurfaceBridge()
    body = ContractBodyParityBridge()
    return _build_coverage(
        surface.contract,
        surface.contract,
        body.contract,
        declaration_family_dispositions(),
        operation_policy_dispositions(),
        operation_execution_dispositions(),
    )


def language_surface_coverage_json() -> str:
    return _stable_json(language_surface_coverage())
