from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools import _core_semantics_runtime as _runtime
from tools.core_bootstrap import TypeRef, parse_source
from tools.core_self_description import CoreSelfDescriptionError, check_semantic_meta_ir


Cardinality = _runtime.Cardinality
ArgumentContract = _runtime.ArgumentContract
ModifierContract = _runtime.ModifierContract
BodySlotContract = _runtime.BodySlotContract
DeclarationContract = _runtime.DeclarationContract
MetaCombinator = _runtime.MetaCombinator
SemanticRegistry = _runtime.SemanticRegistry
SemanticDiagnostic = _runtime.SemanticDiagnostic
CoreContractError = _runtime.CoreContractError
registry_digest = _runtime.registry_digest
validate_source = _runtime.validate_source
infer_expression_type = _runtime.infer_expression_type


def _type_from_json(value: Any) -> TypeRef:
    if not isinstance(value, dict):
        raise CoreContractError(f"expected TypeRef object, found {value!r}")
    unknown = sorted(set(value) - {"name", "arguments", "optional"})
    if unknown:
        raise CoreContractError("TypeRef contains undeclared metadata: " + ", ".join(unknown))
    name = value.get("name")
    arguments = value.get("arguments", [])
    optional = value.get("optional", False)
    if not isinstance(name, str) or not name:
        raise CoreContractError("TypeRef.name must be a non-empty string")
    if not isinstance(arguments, list):
        raise CoreContractError("TypeRef.arguments must be a list")
    if not isinstance(optional, bool):
        raise CoreContractError("TypeRef.optional must be bool")
    return TypeRef(name, tuple(_type_from_json(item) for item in arguments), optional)


def _cardinality(value: Any, subject: str) -> Cardinality:
    if not isinstance(value, list) or len(value) != 2 or not isinstance(value[0], int) or isinstance(value[0], bool) or value[0] < 0:
        raise CoreContractError(f"{subject} must be [min, max|null]")
    maximum = value[1]
    if maximum is not None and (not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < value[0]):
        raise CoreContractError(f"{subject} maximum must be >= minimum or null")
    return Cardinality(value[0], maximum)


def _load_meta_ir(*, direct_source: str, meta_ir_text: str) -> dict[str, Any]:
    try:
        check_semantic_meta_ir(direct_source, meta_ir_text)
    except CoreSelfDescriptionError as exc:
        raise CoreContractError(str(exc)) from exc
    try:
        payload = json.loads(meta_ir_text)
    except json.JSONDecodeError as exc:
        raise CoreContractError(f"Core semantic meta-IR is not valid JSON: {exc}") from exc
    if payload.get("authorityInput") is not False:
        raise CoreContractError("Core semantic meta-IR must declare authorityInput=false")
    if payload.get("role") != "derived-non-authoritative-runtime-meta-ir":
        raise CoreContractError("unexpected Core semantic meta-IR role")
    return payload


def _registry_from_meta_ir(payload: dict[str, Any]) -> SemanticRegistry:
    raw_declarations = payload.get("declarations")
    raw_modifiers = payload.get("modifiers")
    raw_combinators = payload.get("combinators")
    raw_carriers = payload.get("typeCarriers")
    if not isinstance(raw_declarations, dict):
        raise CoreContractError("Core semantic meta-IR declarations must be an object")
    if not isinstance(raw_modifiers, dict):
        raise CoreContractError("Core semantic meta-IR modifiers must be an object")
    if not isinstance(raw_combinators, dict):
        raise CoreContractError("Core semantic meta-IR combinators must be an object")
    if not isinstance(raw_carriers, list) or not raw_carriers or not all(isinstance(item, str) and item for item in raw_carriers) or len(raw_carriers) != len(set(raw_carriers)):
        raise CoreContractError("Core semantic meta-IR typeCarriers must be unique non-empty strings")

    declarations: dict[str, DeclarationContract] = {}
    for kind, raw in raw_declarations.items():
        if not isinstance(raw, dict):
            raise CoreContractError(f"declaration contract {kind!r} must be an object")
        slots: list[BodySlotContract] = []
        for raw_slot in raw.get("slots", []):
            if not isinstance(raw_slot, dict):
                raise CoreContractError(f"{kind}: slot must be an object")
            raw_type = raw_slot.get("valueType")
            slots.append(BodySlotContract(
                body_type=str(raw_slot["bodyType"]),
                name_policy=str(raw_slot["namePolicy"]),
                value_type=None if raw_type is None else _type_from_json(raw_type),
                cardinality=_cardinality(raw_slot["cardinality"], f"{kind}.{raw_slot['bodyType']}"),
                ordered=bool(raw_slot.get("ordered", False)),
                unique_by_name=bool(raw_slot.get("uniqueByName", False)),
                modifiers=tuple(str(item) for item in raw_slot.get("modifiers", [])),
            ))
        declarations[str(kind)] = DeclarationContract(str(kind), str(raw["namePolicy"]), (), None, tuple(slots), tuple(str(item) for item in raw.get("modifiers", [])))

    modifiers: dict[str, ModifierContract] = {}
    for name, raw in raw_modifiers.items():
        if not isinstance(raw, dict):
            raise CoreContractError(f"modifier contract {name!r} must be an object")
        modifiers[str(name)] = ModifierContract(str(name), tuple(str(item) for item in raw.get("targets", [])), (), _cardinality(raw["cardinality"], f"modifier {name}"))

    combinators: dict[str, MetaCombinator] = {}
    for name, raw in raw_combinators.items():
        if not isinstance(raw, dict):
            raise CoreContractError(f"combinator {name!r} must be an object")
        behavior = raw.get("behavior")
        if not isinstance(behavior, str) or not behavior:
            raise CoreContractError(f"combinator {name!r} behavior must be a string")
        combinators[str(name)] = MetaCombinator(str(name), behavior, _cardinality(raw["arguments"], f"combinator {name}"))

    # The runtime engine remains generic. P3 replaces its historical host-owned
    # visible base-type set from direct AIDL-derived type-carrier evidence.
    _runtime.BUILTIN_TYPES.clear()
    _runtime.BUILTIN_TYPES.update(raw_carriers)
    return SemanticRegistry(declarations, modifiers, combinators)


def load_semantic_registry(
    *legacy_module_sources: str,
    direct_source: str | None = None,
    meta_ir_text: str | None = None,
    core_source: str | None = None,
    core_projection: str | None = None,
) -> SemanticRegistry:
    """Load runtime semantics from direct Core plus exact derived meta-IR.

    Declaration-bearing legacy Definition-object modules and the old Core
    source/projection pair are rejected as semantic authority inputs. Empty
    compatibility modules are tolerated while callers finish migration.
    """
    if core_source is not None or core_projection is not None:
        raise CoreContractError("legacy Definition-object Core source/projection are not semantic authority inputs in P3")
    for source in legacy_module_sources:
        program = parse_source(source)
        if program.declarations:
            raise CoreContractError("legacy Definition-object semantic modules are not authority inputs in P3")

    root = Path(__file__).resolve().parents[1]
    if direct_source is None:
        direct_source = (root / "spec" / "core-self-description-v1.aidl").read_text(encoding="utf-8")
    if meta_ir_text is None:
        meta_ir_text = (root / "spec" / "core-meta-ir-v1.json").read_text(encoding="utf-8")
    return _registry_from_meta_ir(_load_meta_ir(direct_source=direct_source, meta_ir_text=meta_ir_text))


__all__ = [
    "Cardinality",
    "ArgumentContract",
    "ModifierContract",
    "BodySlotContract",
    "DeclarationContract",
    "MetaCombinator",
    "SemanticRegistry",
    "SemanticDiagnostic",
    "CoreContractError",
    "load_semantic_registry",
    "registry_digest",
    "validate_source",
    "infer_expression_type",
]
