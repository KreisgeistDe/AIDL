from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from tools import _core_semantics_runtime as _runtime
from tools.core_bootstrap import TypeRef, Value, parse_source
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
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not isinstance(value[0], int)
        or isinstance(value[0], bool)
        or value[0] < 0
    ):
        raise CoreContractError(f"{subject} must be [min, max|null]")
    maximum = value[1]
    if maximum is not None and (
        not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or maximum < value[0]
    ):
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
    if payload.get("schemaVersion") != 2:
        raise CoreContractError("Core semantic meta-IR schemaVersion must be 2")
    return payload


def _argument_from_json(raw: Any, subject: str) -> ArgumentContract:
    if not isinstance(raw, dict):
        raise CoreContractError(f"{subject} argument contract must be an object")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise CoreContractError(f"{subject} argument name must be non-empty")
    return ArgumentContract(
        name,
        _type_from_json(raw["type"]),
        _cardinality(raw["cardinality"], f"{subject}.{name}"),
    )


def _registry_from_meta_ir(payload: dict[str, Any]) -> SemanticRegistry:
    raw_declarations = payload.get("declarations")
    raw_modifiers = payload.get("modifiers")
    raw_combinators = payload.get("combinators")
    raw_symbols = payload.get("predeclaredTypeSymbols")
    if not isinstance(raw_declarations, dict):
        raise CoreContractError("Core semantic meta-IR declarations must be an object")
    if not isinstance(raw_modifiers, dict):
        raise CoreContractError("Core semantic meta-IR modifiers must be an object")
    if not isinstance(raw_combinators, dict):
        raise CoreContractError("Core semantic meta-IR combinators must be an object")
    if (
        not isinstance(raw_symbols, list)
        or not raw_symbols
        or not all(isinstance(item, str) and item for item in raw_symbols)
        or len(raw_symbols) != len(set(raw_symbols))
    ):
        raise CoreContractError(
            "Core semantic meta-IR predeclaredTypeSymbols must be unique non-empty strings"
        )

    declarations: dict[str, DeclarationContract] = {}
    for kind, raw in raw_declarations.items():
        if not isinstance(raw, dict):
            raise CoreContractError(f"declaration contract {kind!r} must be an object")
        slots: list[BodySlotContract] = []
        for raw_slot in raw.get("slots", []):
            if not isinstance(raw_slot, dict):
                raise CoreContractError(f"{kind}: slot must be an object")
            raw_type = raw_slot.get("valueType")
            slots.append(
                BodySlotContract(
                    body_type=str(raw_slot["bodyType"]),
                    name_policy=str(raw_slot["namePolicy"]),
                    value_type=None if raw_type is None else _type_from_json(raw_type),
                    cardinality=_cardinality(
                        raw_slot["cardinality"], f"{kind}.{raw_slot['bodyType']}"
                    ),
                    ordered=bool(raw_slot.get("ordered", False)),
                    unique_by_name=bool(raw_slot.get("uniqueByName", False)),
                    modifiers=tuple(str(item) for item in raw_slot.get("modifiers", [])),
                )
            )
        raw_result = raw.get("result")
        declarations[str(kind)] = DeclarationContract(
            str(kind),
            str(raw["namePolicy"]),
            tuple(
                _argument_from_json(item, str(kind))
                for item in raw.get("arguments", [])
            ),
            None if raw_result is None else _type_from_json(raw_result),
            tuple(slots),
            tuple(str(item) for item in raw.get("modifiers", [])),
        )

    modifiers: dict[str, ModifierContract] = {}
    for name, raw in raw_modifiers.items():
        if not isinstance(raw, dict):
            raise CoreContractError(f"modifier contract {name!r} must be an object")
        modifiers[str(name)] = ModifierContract(
            str(name),
            tuple(str(item) for item in raw.get("targets", [])),
            tuple(
                _argument_from_json(item, f"modifier {name}")
                for item in raw.get("arguments", [])
            ),
            _cardinality(raw["cardinality"], f"modifier {name}"),
        )

    combinators: dict[str, MetaCombinator] = {}
    for name, raw in raw_combinators.items():
        if not isinstance(raw, dict):
            raise CoreContractError(f"combinator {name!r} must be an object")
        behavior = raw.get("behavior")
        if not isinstance(behavior, str) or not behavior:
            raise CoreContractError(f"combinator {name!r} behavior must be a string")
        combinators[str(name)] = MetaCombinator(
            str(name),
            behavior,
            _cardinality(raw["arguments"], f"combinator {name}"),
        )

    # Direct-Core-declared symbol identities, not a host-owned kind/capability catalog.
    _runtime.BUILTIN_TYPES.clear()
    _runtime.BUILTIN_TYPES.update(raw_symbols)
    return SemanticRegistry(declarations, modifiers, combinators)


def _expanded_registry_for_source(
    source: str, registry: SemanticRegistry
) -> tuple[SemanticRegistry, tuple[SemanticDiagnostic, ...]]:
    program = parse_source(source)
    spans = _runtime._SourceSpans(source)
    by_kind: dict[str, list] = {}
    for declaration in program.declarations:
        by_kind.setdefault(declaration.kind, []).append(declaration)

    diagnostics: list[SemanticDiagnostic] = []
    declarations = dict(registry.declarations)
    for kind, contract in registry.declarations.items():
        wildcard = (
            contract.arguments[0]
            if len(contract.arguments) == 1 and contract.arguments[0].name == "*"
            else None
        )
        if wildcard is None:
            if contract.arguments:
                continue
            cursor = 0
            for declaration in by_kind.get(kind, []):
                line, column = spans.declaration(declaration, cursor)
                cursor = line
                if declaration.arguments_present:
                    diagnostics.append(
                        SemanticDiagnostic(
                            "CORE-S035",
                            line,
                            column,
                            f"declaration {kind} has Args=void and forbids an argument list",
                            "Args=void",
                        )
                    )
            continue

        names: set[str] = set()
        cursor = 0
        for declaration in by_kind.get(kind, []):
            line, column = spans.declaration(declaration, cursor)
            cursor = line
            count = len(declaration.arguments)
            if not wildcard.cardinality.accepts(count):
                diagnostics.append(
                    SemanticDiagnostic(
                        "CORE-S004",
                        line,
                        column,
                        f"argument slot occurs {count} time(s) on declaration {kind}",
                        wildcard.cardinality.describe(),
                    )
                )
            names.update(name for name, _ in declaration.arguments)
        expanded = tuple(
            ArgumentContract(name, wildcard.type_ref, Cardinality(0, 1))
            for name in sorted(names)
        )
        declarations[kind] = replace(contract, arguments=expanded)

    return SemanticRegistry(declarations, registry.modifiers, registry.combinators), tuple(diagnostics)


def validate_source(source: str, registry: SemanticRegistry) -> tuple[SemanticDiagnostic, ...]:
    expanded, prefix = _expanded_registry_for_source(source, registry)
    diagnostics = list(prefix)
    diagnostics.extend(_runtime.validate_source(source, expanded))

    program = parse_source(source)
    spans = _runtime._SourceSpans(source)
    symbols = {item.name: item for item in program.declarations if item.name is not None}
    cursor = 0
    for declaration in program.declarations:
        line, column = spans.declaration(declaration, cursor)
        cursor = line
        contract = registry.declarations.get(declaration.kind)
        if contract is None or declaration.result is None or contract.result is None:
            continue
        trial: list[SemanticDiagnostic] = []
        _runtime._validate_value(
            trial,
            Value("typeRef", declaration.result, _runtime._fmt_type(declaration.result)),
            contract.result,
            registry,
            symbols,
            {},
            line,
            column,
            f"result of declaration {declaration.kind}",
        )
        diagnostics.extend(trial)

    unique = {
        (item.code, item.line, item.column, item.message, item.expected): item
        for item in diagnostics
    }
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (item.line, item.column, item.code, item.message),
        )
    )


def load_semantic_registry(
    *legacy_module_sources: str,
    direct_source: str | None = None,
    meta_ir_text: str | None = None,
    core_source: str | None = None,
    core_projection: str | None = None,
) -> SemanticRegistry:
    """Load runtime semantics from direct Core plus exact derived meta-IR."""
    if core_source is not None or core_projection is not None:
        raise CoreContractError(
            "legacy Definition-object Core source/projection are not semantic authority inputs"
        )
    for source in legacy_module_sources:
        program = parse_source(source)
        if program.declarations:
            raise CoreContractError(
                "legacy Definition-object semantic modules are not authority inputs"
            )

    root = Path(__file__).resolve().parents[1]
    if direct_source is None:
        direct_source = (
            root / "spec" / "core-self-description-v1.aidl"
        ).read_text(encoding="utf-8")
    if meta_ir_text is None:
        meta_ir_text = (root / "spec" / "core-meta-ir-v1.json").read_text(
            encoding="utf-8"
        )
    return _registry_from_meta_ir(
        _load_meta_ir(direct_source=direct_source, meta_ir_text=meta_ir_text)
    )


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
