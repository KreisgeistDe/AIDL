from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.core_bootstrap import (
    BodyEntry,
    BootstrapSyntaxError,
    Declaration,
    KernelTerm,
    TypeRef,
    Value,
    parse_bootstrap_source,
    parse_meta_combinator,
    parse_type_ref,
)


class CoreSelfDescriptionError(ValueError):
    """Raised when the direct Core contract is structurally invalid."""


@dataclass(frozen=True)
class Cardinality:
    minimum: int
    maximum: int | None


@dataclass(frozen=True)
class ArgumentSetContract:
    mode: str
    value_type: TypeRef | None
    cardinality: Cardinality


@dataclass(frozen=True)
class ModifierUse:
    name: str
    cardinality: Cardinality


@dataclass(frozen=True)
class BodyContract:
    body_type: str
    name_policy: str
    cardinality: Cardinality
    expected_type: TypeRef | None
    modifiers: tuple[ModifierUse, ...]


@dataclass(frozen=True)
class DeclarationKindContract:
    name: str
    name_policy: str
    arguments: ArgumentSetContract
    result: TypeRef | None
    body: tuple[BodyContract, ...]


@dataclass(frozen=True)
class SelfDescribedCore:
    contracts: dict[str, DeclarationKindContract]
    aliases: dict[str, str]
    symbols: frozenset[str]
    declarations: tuple[Declaration, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "contracts": {
                name: {
                    "namePolicy": contract.name_policy,
                    "arguments": {
                        "mode": contract.arguments.mode,
                        "valueType": (
                            None
                            if contract.arguments.value_type is None
                            else contract.arguments.value_type.to_json()
                        ),
                        "cardinality": {
                            "min": contract.arguments.cardinality.minimum,
                            "max": contract.arguments.cardinality.maximum,
                        },
                    },
                    "result": None if contract.result is None else contract.result.to_json(),
                    "body": [
                        {
                            "bodyType": slot.body_type,
                            "namePolicy": slot.name_policy,
                            "cardinality": {
                                "min": slot.cardinality.minimum,
                                "max": slot.cardinality.maximum,
                            },
                            "expectedType": (
                                None if slot.expected_type is None else slot.expected_type.to_json()
                            ),
                            "modifiers": [
                                {
                                    "name": modifier.name,
                                    "cardinality": {
                                        "min": modifier.cardinality.minimum,
                                        "max": modifier.cardinality.maximum,
                                    },
                                }
                                for modifier in slot.modifiers
                            ],
                        }
                        for slot in contract.body
                    ],
                }
                for name, contract in sorted(self.contracts.items())
            },
            "aliases": dict(sorted(self.aliases.items())),
            "symbols": sorted(self.symbols),
        }


def _term(value: Value | None, subject: str) -> KernelTerm:
    if value is None or value.kind != "raw":
        raise CoreSelfDescriptionError(
            f"{subject} must be a Bootstrap meta-combinator expression"
        )
    try:
        return parse_meta_combinator(value.raw)
    except BootstrapSyntaxError as exc:
        raise CoreSelfDescriptionError(f"{subject}: {exc}") from exc


def _cardinality(term: KernelTerm, subject: str) -> Cardinality:
    if term.name != "cardinal":
        raise CoreSelfDescriptionError(f"{subject} must use cardinal(...)")
    if len(term.arguments) == 1 and isinstance(term.arguments[0], str):
        aliases = {
            "optional": Cardinality(0, 1),
            "required": Cardinality(1, 1),
            "many": Cardinality(0, None),
        }
        if term.arguments[0] in aliases:
            return aliases[term.arguments[0]]
    if len(term.arguments) != 2:
        raise CoreSelfDescriptionError(
            f"{subject} cardinality must be cardinal(min, max|many)"
        )
    minimum, maximum = term.arguments
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
        raise CoreSelfDescriptionError(f"{subject} cardinal minimum must be >= 0")
    if maximum == "many" or maximum is None:
        return Cardinality(minimum, None)
    if (
        not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or maximum < minimum
    ):
        raise CoreSelfDescriptionError(
            f"{subject} cardinal maximum must be >= minimum or many"
        )
    return Cardinality(minimum, maximum)


def _name_policy(term: KernelTerm, subject: str) -> str:
    if term.name != "name" or len(term.arguments) != 1:
        raise CoreSelfDescriptionError(
            f"{subject} must use name(required|optional|forbidden)"
        )
    policy = term.arguments[0]
    if policy not in {"required", "optional", "forbidden"}:
        raise CoreSelfDescriptionError(
            f"{subject} has unsupported name policy {policy!r}"
        )
    return str(policy)


def _modifier(term: KernelTerm, subject: str) -> ModifierUse:
    if (
        term.name != "modifier"
        or not term.arguments
        or not isinstance(term.arguments[0], str)
    ):
        raise CoreSelfDescriptionError(
            f"{subject} must use modifier(name[, cardinal(...)])"
        )
    cardinality = Cardinality(0, 1)
    if len(term.arguments) > 2:
        raise CoreSelfDescriptionError(f"{subject} modifier has too many arguments")
    if len(term.arguments) == 2:
        nested = term.arguments[1]
        if not isinstance(nested, KernelTerm):
            raise CoreSelfDescriptionError(
                f"{subject} modifier cardinality must be structural"
            )
        cardinality = _cardinality(nested, subject)
    return ModifierUse(term.arguments[0], cardinality)


def _as_type_ref(value: object, subject: str) -> TypeRef:
    if not isinstance(value, str) or not value:
        raise CoreSelfDescriptionError(f"{subject} requires a direct type contract")
    try:
        return parse_type_ref(value)
    except BootstrapSyntaxError as exc:
        raise CoreSelfDescriptionError(
            f"{subject}: invalid direct type contract {value!r}: {exc}"
        ) from exc


def _argument_contract(term: KernelTerm, subject: str) -> ArgumentSetContract:
    if term.name != "args" or len(term.arguments) != 2:
        raise CoreSelfDescriptionError(
            f"{subject} must use args(<value-type>, cardinal(...))"
        )
    value_type_raw, cardinal_raw = term.arguments
    if not isinstance(cardinal_raw, KernelTerm):
        raise CoreSelfDescriptionError(
            f"{subject} argument cardinality must be structural"
        )
    return ArgumentSetContract(
        "open",
        _as_type_ref(value_type_raw, subject),
        _cardinality(cardinal_raw, subject),
    )


def _body_contract(entry: BodyEntry, owner: str) -> BodyContract:
    if entry.body_type != "body" or entry.name is None:
        raise CoreSelfDescriptionError(
            f"{owner}: declaration-kind contracts must use named body entries"
        )
    term = _term(entry.value, f"{owner}.{entry.name}")
    if term.name != "body":
        raise CoreSelfDescriptionError(f"{owner}.{entry.name} must use body(...)")
    name_policy: str | None = None
    cardinality: Cardinality | None = None
    expected_type: TypeRef | None = None
    modifiers: list[ModifierUse] = []
    for item in term.arguments:
        if isinstance(item, KernelTerm):
            if item.name == "name":
                if name_policy is not None:
                    raise CoreSelfDescriptionError(
                        f"{owner}.{entry.name}: duplicate name(...)"
                    )
                name_policy = _name_policy(item, f"{owner}.{entry.name}")
            elif item.name == "cardinal":
                if cardinality is not None:
                    raise CoreSelfDescriptionError(
                        f"{owner}.{entry.name}: duplicate cardinal(...)"
                    )
                cardinality = _cardinality(item, f"{owner}.{entry.name}")
            elif item.name == "modifier":
                modifiers.append(_modifier(item, f"{owner}.{entry.name}"))
            else:
                raise CoreSelfDescriptionError(
                    f"{owner}.{entry.name}: unsupported nested combinator {item.name!r}"
                )
        elif isinstance(item, str):
            if expected_type is not None:
                raise CoreSelfDescriptionError(
                    f"{owner}.{entry.name}: multiple direct value types are ambiguous"
                )
            expected_type = _as_type_ref(item, f"{owner}.{entry.name}")
        else:
            raise CoreSelfDescriptionError(
                f"{owner}.{entry.name}: non-structural body contract atom {item!r}"
            )
    if name_policy is None or cardinality is None:
        raise CoreSelfDescriptionError(
            f"{owner}.{entry.name}: body(...) requires explicit name(...) and cardinal(...)"
        )
    modifier_names = [modifier.name for modifier in modifiers]
    if len(modifier_names) != len(set(modifier_names)):
        raise CoreSelfDescriptionError(
            f"{owner}.{entry.name}: duplicate modifier contract"
        )
    return BodyContract(
        entry.name,
        name_policy,
        cardinality,
        expected_type,
        tuple(modifiers),
    )


def _kind_contract(declaration: Declaration) -> DeclarationKindContract:
    if declaration.name is None:
        raise CoreSelfDescriptionError("declaration-kind contract requires a name")
    name_policy = "optional"
    argument_contract = ArgumentSetContract("closed", None, Cardinality(0, 0))
    seen_header_terms: set[str] = set()
    for header_name, value in declaration.arguments:
        term = _term(value, f"{declaration.name}.{header_name}")
        if term.name in seen_header_terms:
            raise CoreSelfDescriptionError(
                f"{declaration.name}: duplicate structural header term {term.name!r}"
            )
        seen_header_terms.add(term.name)
        if term.name == "name":
            name_policy = _name_policy(term, f"{declaration.name}.name")
        elif term.name == "args":
            argument_contract = _argument_contract(
                term, f"{declaration.name}.args"
            )
        else:
            raise CoreSelfDescriptionError(
                f"{declaration.name}: unsupported declaration header combinator {term.name!r}"
            )
    return DeclarationKindContract(
        declaration.name,
        name_policy,
        argument_contract,
        declaration.result,
        tuple(
            _body_contract(entry, declaration.name)
            for entry in declaration.body
            if entry.body_type == "body"
        ),
    )


def _within(count: int, cardinality: Cardinality) -> bool:
    return count >= cardinality.minimum and (
        cardinality.maximum is None or count <= cardinality.maximum
    )


def _validate_type_ref(
    type_ref: TypeRef, symbols: frozenset[str], subject: str
) -> None:
    if type_ref.name in {"any", "type", "identifier"}:
        for index, argument in enumerate(type_ref.arguments):
            _validate_type_ref(argument, symbols, f"{subject}.argument[{index}]")
        return
    if type_ref.name not in symbols:
        raise CoreSelfDescriptionError(
            f"{subject}: unresolved type symbol {type_ref.name!r}"
        )
    for index, argument in enumerate(type_ref.arguments):
        _validate_type_ref(argument, symbols, f"{subject}.argument[{index}]")


def _validate_contract_value(
    value: Value | None,
    expected: TypeRef | None,
    symbols: frozenset[str],
    subject: str,
) -> None:
    if expected is None:
        if value is not None:
            raise CoreSelfDescriptionError(f"{subject}: value is not permitted")
        return
    if expected.name == "any":
        return
    if expected.name == "identifier":
        if value is not None:
            raise CoreSelfDescriptionError(
                f"{subject}: identifier slots carry identity in the entry name"
            )
        return
    if expected.name == "type":
        if value is None or value.kind != "typeRef":
            raise CoreSelfDescriptionError(f"{subject}: value must be a TypeRef")
        _validate_type_ref(value.value, symbols, subject)
        return
    if expected.name == "string":
        if value is None or value.kind != "string":
            raise CoreSelfDescriptionError(f"{subject}: value must be string")
        return
    if expected.name == "bool":
        if (
            value is None
            or value.kind != "literal"
            or not isinstance(value.value, bool)
        ):
            raise CoreSelfDescriptionError(f"{subject}: value must be bool")
        return
    if expected.name == "int":
        if (
            value is None
            or value.kind != "number"
            or not isinstance(value.value, int)
            or isinstance(value.value, bool)
        ):
            raise CoreSelfDescriptionError(f"{subject}: value must be int")
        return
    if value is None:
        raise CoreSelfDescriptionError(f"{subject}: value is required")


def _validate_instance(
    declaration: Declaration,
    contract: DeclarationKindContract,
    symbols: frozenset[str],
) -> None:
    subject = declaration.name or declaration.kind
    if contract.name_policy == "required" and declaration.name is None:
        raise CoreSelfDescriptionError(f"{subject}: declaration name is required")
    if contract.name_policy == "forbidden" and declaration.name is not None:
        raise CoreSelfDescriptionError(f"{subject}: declaration name is forbidden")

    actual_arguments = declaration.arguments
    if contract.arguments.mode == "closed":
        if actual_arguments:
            raise CoreSelfDescriptionError(
                f"{subject}: declaration kind {contract.name} has a closed zero-parameter signature"
            )
    else:
        if not _within(len(actual_arguments), contract.arguments.cardinality):
            raise CoreSelfDescriptionError(
                f"{subject}: declaration argument count violates {contract.name} contract"
            )
        assert contract.arguments.value_type is not None
        if contract.arguments.value_type.name != "any":
            for name, value in actual_arguments:
                _validate_contract_value(
                    value,
                    contract.arguments.value_type,
                    symbols,
                    f"{subject}.argument.{name}",
                )

    if contract.result is None:
        if declaration.result is not None:
            raise CoreSelfDescriptionError(
                f"{subject}: declaration kind {contract.name} does not permit a result"
            )
    elif contract.name != "declaration" and declaration.result is None:
        raise CoreSelfDescriptionError(
            f"{subject}: declaration kind {contract.name} requires a result TypeRef"
        )
    elif declaration.result is not None:
        if contract.result.name == "type":
            _validate_type_ref(declaration.result, symbols, f"{subject}.result")
        elif (
            contract.result.name != "any"
            and declaration.result.name != contract.result.name
        ):
            raise CoreSelfDescriptionError(
                f"{subject}: result {_fmt_type(declaration.result)!r} does not match "
                f"{_fmt_type(contract.result)!r}"
            )

    by_type = {slot.body_type: slot for slot in contract.body}
    unknown = sorted({entry.body_type for entry in declaration.body} - set(by_type))
    if unknown:
        raise CoreSelfDescriptionError(
            f"{subject}: undeclared body type(s): {', '.join(unknown)}"
        )
    for body_type, slot in by_type.items():
        entries = [
            entry for entry in declaration.body if entry.body_type == body_type
        ]
        if not _within(len(entries), slot.cardinality):
            raise CoreSelfDescriptionError(
                f"{subject}.{body_type}: body-entry count violates cardinality"
            )
        seen_names: set[str] = set()
        modifier_contracts = {item.name: item for item in slot.modifiers}
        for entry in entries:
            if slot.name_policy == "required" and entry.name is None:
                raise CoreSelfDescriptionError(
                    f"{subject}.{body_type}: name is required"
                )
            if slot.name_policy == "forbidden" and entry.name is not None:
                raise CoreSelfDescriptionError(
                    f"{subject}.{body_type}: name is forbidden"
                )
            if entry.name is not None:
                if entry.name in seen_names:
                    raise CoreSelfDescriptionError(
                        f"{subject}.{body_type}: duplicate name {entry.name!r}"
                    )
                seen_names.add(entry.name)
            _validate_contract_value(
                entry.value,
                slot.expected_type,
                symbols,
                f"{subject}.{body_type}.{entry.name or '<unnamed>'}",
            )
            counts: dict[str, int] = {}
            for modifier in entry.modifiers:
                counts[modifier.name] = counts.get(modifier.name, 0) + 1
                if modifier.name not in modifier_contracts:
                    raise CoreSelfDescriptionError(
                        f"{subject}.{body_type}: modifier {modifier.name!r} is not declared"
                    )
            for name, modifier_contract in modifier_contracts.items():
                if not _within(
                    counts.get(name, 0), modifier_contract.cardinality
                ):
                    raise CoreSelfDescriptionError(
                        f"{subject}.{body_type}: modifier {name!r} violates cardinality"
                    )


def _fmt_type(type_ref: TypeRef) -> str:
    suffix = "?" if type_ref.optional else ""
    if not type_ref.arguments:
        return type_ref.name + suffix
    return (
        f"{type_ref.name}<"
        + ", ".join(_fmt_type(item) for item in type_ref.arguments)
        + ">"
        + suffix
    )


def _semantic_metadata(declaration: Declaration) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for entry in declaration.body:
        if entry.body_type != "semantic" or entry.name is None:
            continue
        if entry.name in result:
            raise CoreSelfDescriptionError(
                f"{declaration.name}: duplicate semantic metadata {entry.name!r}"
            )
        result[entry.name] = None if entry.value is None else entry.value.to_json()
    return result


def _contract_shape(contract: DeclarationKindContract) -> tuple[Any, ...]:
    return (
        contract.name_policy,
        contract.arguments,
        contract.result,
        contract.body,
    )


def compile_self_described_core(source: str) -> SelfDescribedCore:
    """Compile the direct Core using only the finite Bootstrap Kernel vocabulary."""
    program = parse_bootstrap_source(source)
    contract_declarations = [
        declaration
        for declaration in program.declarations
        if declaration.kind == "declaration"
    ]
    raw_contracts = {
        declaration.name: _kind_contract(declaration)
        for declaration in contract_declarations
        if declaration.name is not None
    }
    if "declaration" not in raw_contracts:
        raise CoreSelfDescriptionError(
            "self-described Core must define the declaration declaration-kind"
        )

    aliases: dict[str, str] = {}
    for declaration in contract_declarations:
        if declaration.name is None:
            continue
        metadata = _semantic_metadata(declaration)
        alias = metadata.get("alias")
        if alias is None:
            continue
        if not isinstance(alias, str) or not alias:
            raise CoreSelfDescriptionError(
                f"{declaration.name}: semantic alias must be a non-empty string"
            )
        if alias == declaration.name:
            raise CoreSelfDescriptionError(
                f"{declaration.name}: semantic alias cannot target itself"
            )
        aliases[declaration.name] = alias

    for alias, target in aliases.items():
        if target not in raw_contracts:
            raise CoreSelfDescriptionError(
                f"{alias}: semantic alias target {target!r} is not a declaration contract"
            )
        if _contract_shape(raw_contracts[alias]) != _contract_shape(raw_contracts[target]):
            raise CoreSelfDescriptionError(
                f"{alias}: alias contract must exactly match canonical {target!r} contract"
            )
    if "declaration" in aliases:
        raise CoreSelfDescriptionError(
            "the central declaration meta-class cannot itself be an alias"
        )

    contracts = {
        name: contract
        for name, contract in raw_contracts.items()
        if name not in aliases
    }

    def canonical_kind(kind: str) -> str:
        seen: set[str] = set()
        current = kind
        while current in aliases:
            if current in seen:
                raise CoreSelfDescriptionError(
                    f"cyclic declaration-kind alias involving {kind!r}"
                )
            seen.add(current)
            current = aliases[current]
        return current

    unknown_kinds = sorted(
        {
            declaration.kind
            for declaration in program.declarations
            if canonical_kind(declaration.kind) not in contracts
        }
    )
    if unknown_kinds:
        raise CoreSelfDescriptionError(
            "declarations use undefined declaration-kind(s): "
            + ", ".join(unknown_kinds)
        )

    symbols = frozenset(
        declaration.name
        for declaration in program.declarations
        if declaration.name is not None
    )
    for declaration in program.declarations:
        _validate_instance(
            declaration,
            contracts[canonical_kind(declaration.kind)],
            symbols,
        )
    return SelfDescribedCore(contracts, aliases, symbols, program.declarations)


def _runtime_type(type_ref: TypeRef | None) -> dict[str, Any] | None:
    if type_ref is None or type_ref.name == "identifier":
        return None
    if type_ref.name == "type":
        return TypeRef("TypeRef").to_json()
    return type_ref.to_json()


def semantic_meta_ir(model: SelfDescribedCore, source_sha256: str) -> dict[str, Any]:
    """Derive the non-authoritative runtime meta-IR from direct Core authority."""
    modifiers: dict[str, dict[str, Any]] = {}
    declarations: dict[str, dict[str, Any]] = {}
    for kind, contract in sorted(model.contracts.items()):
        slots: list[dict[str, Any]] = []
        for slot in contract.body:
            slots.append(
                {
                    "bodyType": slot.body_type,
                    "namePolicy": slot.name_policy,
                    "valueType": _runtime_type(slot.expected_type),
                    "cardinality": [
                        slot.cardinality.minimum,
                        slot.cardinality.maximum,
                    ],
                    "ordered": True,
                    "uniqueByName": slot.name_policy != "forbidden",
                    "modifiers": [item.name for item in slot.modifiers],
                }
            )
            for item in slot.modifiers:
                current = modifiers.setdefault(
                    item.name,
                    {
                        "targets": [],
                        "arguments": [],
                        "cardinality": [
                            item.cardinality.minimum,
                            item.cardinality.maximum,
                        ],
                    },
                )
                if slot.body_type not in current["targets"]:
                    current["targets"].append(slot.body_type)
                if current["cardinality"] != [
                    item.cardinality.minimum,
                    item.cardinality.maximum,
                ]:
                    raise CoreSelfDescriptionError(
                        f"modifier {item.name!r} has incompatible cardinalities"
                    )
        arguments: list[dict[str, Any]] = []
        if contract.arguments.mode == "open":
            assert contract.arguments.value_type is not None
            arguments.append(
                {
                    "name": "*",
                    "type": _runtime_type(contract.arguments.value_type),
                    "cardinality": [
                        contract.arguments.cardinality.minimum,
                        contract.arguments.cardinality.maximum,
                    ],
                }
            )
        declarations[kind] = {
            "namePolicy": contract.name_policy,
            "arguments": arguments,
            "result": _runtime_type(contract.result),
            "resultRequired": contract.result is not None and kind != "declaration",
            "slots": slots,
            "modifiers": [],
        }

    combinators: dict[str, dict[str, Any]] = {}
    for declaration in model.declarations:
        if declaration.name is None:
            continue
        metadata = _semantic_metadata(declaration)
        behavior = metadata.get("behavior")
        if behavior is None:
            continue
        if not isinstance(behavior, str) or not behavior:
            raise CoreSelfDescriptionError(
                f"{declaration.name}: semantic behavior must be a non-empty string"
            )
        minimum = metadata.get("minArgs", 0)
        maximum = metadata.get("maxArgs")
        if (
            not isinstance(minimum, int)
            or isinstance(minimum, bool)
            or minimum < 0
        ):
            raise CoreSelfDescriptionError(
                f"{declaration.name}: semantic minArgs must be >= 0"
            )
        if maximum is not None and (
            not isinstance(maximum, int)
            or isinstance(maximum, bool)
            or maximum < minimum
        ):
            raise CoreSelfDescriptionError(
                f"{declaration.name}: semantic maxArgs must be >= minArgs or null"
            )
        combinators[declaration.name] = {
            "behavior": behavior,
            "arguments": [minimum, maximum],
        }

    return {
        "schemaVersion": 3,
        "role": "derived-non-authoritative-runtime-meta-ir",
        "source": "spec/core-self-description-v1.aidl",
        "sourceSha256": source_sha256,
        "authorityInput": False,
        "declarations": declarations,
        "kindAliases": dict(sorted(model.aliases.items())),
        "modifiers": modifiers,
        "combinators": combinators,
        "predeclaredTypeSymbols": sorted(model.symbols),
    }


def semantic_meta_ir_text(source: str) -> str:
    normalized = source.replace("\r\n", "\n")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return (
        json.dumps(
            semantic_meta_ir(compile_self_described_core(source), digest),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def check_semantic_meta_ir(source: str, meta_ir_text: str) -> None:
    if meta_ir_text != semantic_meta_ir_text(source):
        raise CoreSelfDescriptionError(
            "Core semantic meta-IR drift: regenerate spec/core-meta-ir-v1.json "
            "from spec/core-self-description-v1.aidl"
        )


def load_self_described_core(path: Path | None = None) -> SelfDescribedCore:
    root = Path(__file__).resolve().parents[1]
    source_path = path or root / "spec" / "core-self-description-v1.aidl"
    return compile_self_described_core(source_path.read_text(encoding="utf-8"))


__all__ = [
    "ArgumentSetContract",
    "BodyContract",
    "Cardinality",
    "CoreSelfDescriptionError",
    "DeclarationKindContract",
    "ModifierUse",
    "SelfDescribedCore",
    "check_semantic_meta_ir",
    "compile_self_described_core",
    "load_self_described_core",
    "semantic_meta_ir",
    "semantic_meta_ir_text",
]
