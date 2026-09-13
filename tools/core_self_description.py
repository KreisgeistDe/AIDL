from __future__ import annotations

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
)


class CoreSelfDescriptionError(ValueError):
    """Raised when the P2 direct Core contract is structurally invalid."""


@dataclass(frozen=True)
class Cardinality:
    minimum: int
    maximum: int | None


@dataclass(frozen=True)
class ModifierUse:
    name: str
    cardinality: Cardinality


@dataclass(frozen=True)
class BodyContract:
    body_type: str
    name_policy: str
    cardinality: Cardinality
    type_position: bool
    expected_type: str | None
    modifiers: tuple[ModifierUse, ...]


@dataclass(frozen=True)
class DeclarationKindContract:
    name: str
    arguments: Cardinality
    produces: tuple[str, ...]
    body: tuple[BodyContract, ...]


@dataclass(frozen=True)
class SelfDescribedCore:
    contracts: dict[str, DeclarationKindContract]
    type_carriers: frozenset[str]
    declarations: tuple[Declaration, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "contracts": {
                name: {
                    "arguments": {
                        "min": contract.arguments.minimum,
                        "max": contract.arguments.maximum,
                    },
                    "produces": list(contract.produces),
                    "body": [
                        {
                            "bodyType": slot.body_type,
                            "namePolicy": slot.name_policy,
                            "cardinality": {
                                "min": slot.cardinality.minimum,
                                "max": slot.cardinality.maximum,
                            },
                            "typePosition": slot.type_position,
                            "expectedType": slot.expected_type,
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
            "typeCarriers": sorted(self.type_carriers),
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
        named = term.arguments[0]
        aliases = {
            "optional": Cardinality(0, 1),
            "required": Cardinality(1, 1),
            "many": Cardinality(0, None),
        }
        if named in aliases:
            return aliases[named]
    if len(term.arguments) != 2:
        raise CoreSelfDescriptionError(
            f"{subject} cardinality must be cardinal(min, max|many)"
        )
    minimum, maximum = term.arguments
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
        raise CoreSelfDescriptionError(f"{subject} cardinal minimum must be >= 0")
    if maximum == "many" or maximum is None:
        return Cardinality(minimum, None)
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < minimum:
        raise CoreSelfDescriptionError(
            f"{subject} cardinal maximum must be >= minimum or many"
        )
    return Cardinality(minimum, maximum)


def _name_policy(term: KernelTerm, subject: str) -> str:
    if term.name != "name" or len(term.arguments) != 1:
        raise CoreSelfDescriptionError(f"{subject} must use name(required|optional|forbidden)")
    policy = term.arguments[0]
    if policy not in {"required", "optional", "forbidden"}:
        raise CoreSelfDescriptionError(f"{subject} has unsupported name policy {policy!r}")
    return str(policy)


def _modifier(term: KernelTerm, subject: str) -> ModifierUse:
    if term.name != "modifier" or not term.arguments or not isinstance(term.arguments[0], str):
        raise CoreSelfDescriptionError(f"{subject} must use modifier(name[, cardinal(...)])")
    cardinality = Cardinality(0, 1)
    if len(term.arguments) > 2:
        raise CoreSelfDescriptionError(f"{subject} modifier has too many arguments")
    if len(term.arguments) == 2:
        nested = term.arguments[1]
        if not isinstance(nested, KernelTerm):
            raise CoreSelfDescriptionError(f"{subject} modifier cardinality must be structural")
        cardinality = _cardinality(nested, subject)
    return ModifierUse(term.arguments[0], cardinality)


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
    type_position = False
    expected_type: str | None = None
    modifiers: list[ModifierUse] = []
    for item in term.arguments:
        if isinstance(item, KernelTerm):
            if item.name == "name":
                if name_policy is not None:
                    raise CoreSelfDescriptionError(f"{owner}.{entry.name}: duplicate name(...)")
                name_policy = _name_policy(item, f"{owner}.{entry.name}")
            elif item.name == "cardinal":
                if cardinality is not None:
                    raise CoreSelfDescriptionError(f"{owner}.{entry.name}: duplicate cardinal(...)")
                cardinality = _cardinality(item, f"{owner}.{entry.name}")
            elif item.name == "modifier":
                modifiers.append(_modifier(item, f"{owner}.{entry.name}"))
            elif item.name == "type-position":
                if type_position:
                    raise CoreSelfDescriptionError(f"{owner}.{entry.name}: duplicate type-position")
                type_position = True
            else:
                raise CoreSelfDescriptionError(
                    f"{owner}.{entry.name}: unsupported nested combinator {item.name!r}"
                )
        elif isinstance(item, str):
            if expected_type is not None:
                raise CoreSelfDescriptionError(
                    f"{owner}.{entry.name}: multiple direct value types are ambiguous"
                )
            expected_type = item
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
        type_position,
        expected_type,
        tuple(modifiers),
    )


def _kind_contract(declaration: Declaration) -> DeclarationKindContract:
    if declaration.name is None:
        raise CoreSelfDescriptionError("declaration-kind contract requires a name")
    argument_cardinality = Cardinality(0, 0)
    produces: list[str] = []
    seen_header_terms: set[str] = set()
    for header_name, value in declaration.arguments:
        term = _term(value, f"{declaration.name}.{header_name}")
        if term.name in seen_header_terms:
            raise CoreSelfDescriptionError(
                f"{declaration.name}: duplicate structural header term {term.name!r}"
            )
        seen_header_terms.add(term.name)
        if term.name == "args":
            if len(term.arguments) != 1 or not isinstance(term.arguments[0], KernelTerm):
                raise CoreSelfDescriptionError(
                    f"{declaration.name}: args(...) must contain one cardinal(...)"
                )
            argument_cardinality = _cardinality(
                term.arguments[0], f"{declaration.name}.args"
            )
        elif term.name == "produces":
            if not term.arguments or not all(isinstance(item, str) for item in term.arguments):
                raise CoreSelfDescriptionError(
                    f"{declaration.name}: produces(...) requires carrier-space names"
                )
            produces.extend(str(item) for item in term.arguments)
        else:
            raise CoreSelfDescriptionError(
                f"{declaration.name}: unsupported declaration header combinator {term.name!r}"
            )
    return DeclarationKindContract(
        declaration.name,
        argument_cardinality,
        tuple(produces),
        tuple(_body_contract(entry, declaration.name) for entry in declaration.body),
    )


def _within(count: int, cardinality: Cardinality) -> bool:
    return count >= cardinality.minimum and (
        cardinality.maximum is None or count <= cardinality.maximum
    )


def _validate_type_ref(type_ref: TypeRef, carriers: frozenset[str], subject: str) -> None:
    if type_ref.name not in carriers:
        raise CoreSelfDescriptionError(
            f"{subject}: unresolved type carrier {type_ref.name!r}"
        )
    for index, argument in enumerate(type_ref.arguments):
        _validate_type_ref(argument, carriers, f"{subject}.argument[{index}]")


def _validate_instance(
    declaration: Declaration,
    contract: DeclarationKindContract,
    carriers: frozenset[str],
) -> None:
    subject = declaration.name or declaration.kind
    if not _within(len(declaration.arguments), contract.arguments):
        raise CoreSelfDescriptionError(
            f"{subject}: declaration argument count violates {contract.name} contract"
        )

    by_type = {slot.body_type: slot for slot in contract.body}
    unknown = sorted({entry.body_type for entry in declaration.body} - set(by_type))
    if unknown:
        raise CoreSelfDescriptionError(
            f"{subject}: undeclared body type(s): {', '.join(unknown)}"
        )

    for body_type, slot in by_type.items():
        entries = [entry for entry in declaration.body if entry.body_type == body_type]
        if not _within(len(entries), slot.cardinality):
            raise CoreSelfDescriptionError(
                f"{subject}.{body_type}: body-entry count violates cardinality"
            )
        seen_names: set[str] = set()
        modifier_contracts = {item.name: item for item in slot.modifiers}
        for entry in entries:
            if slot.name_policy == "required" and entry.name is None:
                raise CoreSelfDescriptionError(f"{subject}.{body_type}: name is required")
            if slot.name_policy == "forbidden" and entry.name is not None:
                raise CoreSelfDescriptionError(f"{subject}.{body_type}: name is forbidden")
            if entry.name is not None:
                if entry.name in seen_names:
                    raise CoreSelfDescriptionError(
                        f"{subject}.{body_type}: duplicate name {entry.name!r}"
                    )
                seen_names.add(entry.name)

            if slot.type_position:
                if entry.value is None or entry.value.kind != "typeRef":
                    raise CoreSelfDescriptionError(
                        f"{subject}.{body_type}: value must be a resolved type position"
                    )
                _validate_type_ref(
                    entry.value.value,
                    carriers,
                    f"{subject}.{body_type}.{entry.name or '<unnamed>'}",
                )
            elif slot.expected_type is not None:
                if (
                    entry.value is None
                    or entry.value.kind != "typeRef"
                    or entry.value.value.name != slot.expected_type
                ):
                    raise CoreSelfDescriptionError(
                        f"{subject}.{body_type}: expected structural value {slot.expected_type!r}"
                    )

            counts: dict[str, int] = {}
            for modifier in entry.modifiers:
                counts[modifier.name] = counts.get(modifier.name, 0) + 1
                if modifier.name not in modifier_contracts:
                    raise CoreSelfDescriptionError(
                        f"{subject}.{body_type}: modifier {modifier.name!r} is not declared"
                    )
            for name, modifier_contract in modifier_contracts.items():
                if not _within(counts.get(name, 0), modifier_contract.cardinality):
                    raise CoreSelfDescriptionError(
                        f"{subject}.{body_type}: modifier {name!r} violates cardinality"
                    )


def compile_self_described_core(source: str) -> SelfDescribedCore:
    """Compile the P2 direct Core using only the finite P1 structural vocabulary."""

    program = parse_bootstrap_source(source)
    contract_declarations = [
        declaration
        for declaration in program.declarations
        if declaration.kind == "declaration"
    ]
    contracts = {
        declaration.name: _kind_contract(declaration)
        for declaration in contract_declarations
        if declaration.name is not None
    }
    if "declaration" not in contracts:
        raise CoreSelfDescriptionError(
            "self-described Core must define the declaration declaration-kind"
        )

    unknown_kinds = sorted(
        {
            declaration.kind
            for declaration in program.declarations
            if declaration.kind not in contracts
        }
    )
    if unknown_kinds:
        raise CoreSelfDescriptionError(
            "declarations use undefined declaration-kind(s): " + ", ".join(unknown_kinds)
        )

    carriers = frozenset(
        declaration.name
        for declaration in program.declarations
        if declaration.name is not None
        and "type" in contracts[declaration.kind].produces
    )

    for declaration in program.declarations:
        _validate_instance(declaration, contracts[declaration.kind], carriers)

    return SelfDescribedCore(contracts, carriers, program.declarations)


def load_self_described_core(path: Path | None = None) -> SelfDescribedCore:
    root = Path(__file__).resolve().parents[1]
    source_path = path or root / "spec" / "core-self-description-v1.aidl"
    return compile_self_described_core(source_path.read_text(encoding="utf-8"))


__all__ = [
    "BodyContract",
    "Cardinality",
    "CoreSelfDescriptionError",
    "DeclarationKindContract",
    "ModifierUse",
    "SelfDescribedCore",
    "compile_self_described_core",
    "load_self_described_core",
]
