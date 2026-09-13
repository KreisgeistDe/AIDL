from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools import _core_semantics_runtime as _runtime
from tools.core_bootstrap import BodyEntry, Declaration, TypeRef, Value, parse_source, projection_text


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


@dataclass(frozen=True)
class _MetaField:
    name: str
    type_ref: TypeRef
    required: bool


@dataclass(frozen=True)
class _MetaDefinition:
    name: str
    fields: tuple[_MetaField, ...]


@dataclass(frozen=True)
class _CoreMetaModel:
    definitions: dict[str, _MetaDefinition]
    category_argument: str
    categories: dict[str, str]
    ignored_categories: frozenset[str]
    name_policy_values: frozenset[str]


def _argument_value(declaration: Declaration, name: str) -> Value | None:
    for argument_name, value in declaration.arguments:
        if argument_name == name:
            return value
    return None


def _body_value(declaration: Declaration, name: str) -> Value | None:
    for entry in declaration.body:
        if entry.name == name:
            return entry.value
    return None


def _plain(value: Value | None) -> Any:
    return None if value is None else value.value


def _required(entry: BodyEntry) -> bool:
    return any(modifier.name == "required" for modifier in entry.modifiers)


def _type_from_json(value: Any) -> TypeRef:
    if isinstance(value, TypeRef):
        return value
    if not isinstance(value, dict) or "$typeRef" not in value:
        raise CoreContractError(f"expected TypeRef value, found {value!r}")
    payload = value["$typeRef"]
    unknown = sorted(set(payload) - {"name", "arguments", "optional"})
    if unknown:
        raise CoreContractError("TypeRef contains undeclared metadata: " + ", ".join(unknown))
    if "name" not in payload:
        raise CoreContractError("TypeRef missing required metadata: name")
    return TypeRef(
        str(payload["name"]),
        tuple(_type_from_json({"$typeRef": child}) for child in payload.get("arguments", [])),
        bool(payload.get("optional", False)),
    )


def _cardinality(value: Any) -> Cardinality:
    if not isinstance(value, dict):
        raise CoreContractError(f"expected Cardinality object, found {value!r}")
    minimum = int(value["min"])
    maximum = None if value.get("max") is None else int(value["max"])
    if minimum < 0 or (maximum is not None and maximum < minimum):
        raise CoreContractError(f"invalid Cardinality {value!r}")
    return Cardinality(minimum, maximum)


def _core_meta_model(core_source: str, core_projection: str) -> _CoreMetaModel:
    if core_projection != projection_text(core_source):
        raise CoreContractError(
            "Core projection drift: spec/core-registry-v1.json does not match normative spec/core.aidl"
        )

    program = parse_source(core_source)
    by_name = {item.name: item for item in program.declarations if item.name is not None}
    definitions: dict[str, _MetaDefinition] = {}
    for declaration in program.declarations:
        if declaration.kind != "declaration" or declaration.name is None:
            raise CoreContractError(
                "normative Core may contain only named declaration meta-definitions"
            )
        if _plain(_argument_value(declaration, "kind")) != "meta":
            continue
        fields = tuple(
            _MetaField(entry.name, entry.value.value, _required(entry))
            for entry in declaration.body
            if entry.name is not None
            and entry.value is not None
            and entry.value.kind == "typeRef"
        )
        definitions[declaration.name] = _MetaDefinition(declaration.name, fields)

    required = {
        "NamePolicy",
        "Cardinality",
        "TypeRef",
        "ArgumentDefinition",
        "ModifierDefinition",
        "BodySlotDefinition",
        "DeclarationDefinition",
        "MetaCombinatorDefinition",
    }
    missing = sorted(required - set(definitions))
    if missing:
        raise CoreContractError(
            "normative Core missing semantic meta-definitions: " + ", ".join(missing)
        )

    name_policy = by_name.get("NamePolicy")
    values = _plain(_body_value(name_policy, "values")) if name_policy else None
    if not isinstance(values, list) or not values or not all(isinstance(item, str) for item in values):
        raise CoreContractError("NamePolicy must declare string values")

    root = by_name.get("SemanticMetaModel")
    if root is None:
        raise CoreContractError("normative Core missing SemanticMetaModel")
    category_argument = _plain(_body_value(root, "categoryArgument"))
    raw_categories = _plain(_body_value(root, "categories"))
    raw_ignored = _plain(_body_value(root, "ignoredCategories"))
    if not isinstance(category_argument, str) or not category_argument:
        raise CoreContractError("SemanticMetaModel.categoryArgument must be a non-empty string")
    if not isinstance(raw_categories, dict) or not raw_categories:
        raise CoreContractError("SemanticMetaModel.categories must be a non-empty object")
    if not isinstance(raw_ignored, list) or not all(isinstance(item, str) for item in raw_ignored):
        raise CoreContractError("SemanticMetaModel.ignoredCategories must be a string list")

    categories: dict[str, str] = {}
    for category, target in raw_categories.items():
        target_type = _type_from_json(target)
        if target_type.arguments or target_type.optional or target_type.name not in definitions:
            raise CoreContractError(
                f"SemanticMetaModel category {category!r} must reference one declared meta-definition"
            )
        categories[str(category)] = target_type.name
    overlap = sorted(set(categories) & set(raw_ignored))
    if overlap:
        raise CoreContractError(
            "SemanticMetaModel categories cannot be both interpreted and ignored: "
            + ", ".join(overlap)
        )
    return _CoreMetaModel(
        definitions,
        category_argument,
        categories,
        frozenset(raw_ignored),
        frozenset(values),
    )


def _validate_meta_value(
    value: Any,
    expected: TypeRef,
    meta: _CoreMetaModel,
    subject: str,
) -> None:
    if value is None:
        if expected.optional:
            return
        raise CoreContractError(f"{subject} must be {_runtime._fmt_type(expected)}, found null")
    if expected.name == "string":
        if not isinstance(value, str):
            raise CoreContractError(f"{subject} must be string")
        return
    if expected.name == "bool":
        if not isinstance(value, bool):
            raise CoreContractError(f"{subject} must be bool")
        return
    if expected.name == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            raise CoreContractError(f"{subject} must be int")
        return
    if expected.name == "float":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise CoreContractError(f"{subject} must be float")
        return
    if expected.name == "json":
        return
    if expected.name == "list" and expected.arguments:
        if not isinstance(value, list):
            raise CoreContractError(f"{subject} must be {_runtime._fmt_type(expected)}")
        for index, item in enumerate(value):
            _validate_meta_value(item, expected.arguments[0], meta, f"{subject}[{index}]")
        return
    if expected.name == "TypeRef":
        _type_from_json(value)
        return
    if expected.name == "Cardinality":
        _validate_meta_object(value, "Cardinality", meta, subject)
        _cardinality(value)
        return
    if expected.name == "NamePolicy":
        if value not in meta.name_policy_values:
            raise CoreContractError(
                f"{subject} must be one of {sorted(meta.name_policy_values)!r}"
            )
        return
    if expected.name == "ModifierDefinition" and isinstance(value, str):
        # Slots/declarations carry references to named modifier definitions.
        return
    if expected.name in meta.definitions:
        _validate_meta_object(value, expected.name, meta, subject)
        return
    raise CoreContractError(
        f"{subject} uses unsupported Core meta type {_runtime._fmt_type(expected)}"
    )


def _validate_meta_object(
    value: Any,
    definition_name: str,
    meta: _CoreMetaModel,
    subject: str,
) -> None:
    if not isinstance(value, dict):
        raise CoreContractError(
            f"expected {definition_name} object for {subject}, found {value!r}"
        )
    definition = meta.definitions[definition_name]
    by_name = {field.name: field for field in definition.fields}
    unknown = sorted(set(value) - set(by_name))
    if unknown:
        raise CoreContractError(
            f"{definition_name} contains undeclared metadata: " + ", ".join(unknown)
        )
    missing = sorted(
        field.name
        for field in definition.fields
        if field.required and field.name not in value
    )
    if missing:
        raise CoreContractError(
            f"{definition_name} missing required metadata: " + ", ".join(missing)
        )
    for name, item in value.items():
        _validate_meta_value(item, by_name[name].type_ref, meta, f"{subject}.{name}")


def _declaration_metadata(
    declaration: Declaration,
    definition_name: str,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for entry in declaration.body:
        if entry.body_type != "body" or entry.name is None:
            raise CoreContractError(
                f"{declaration.name}: meta-definition bodies must use named body entries"
            )
        if entry.name in metadata:
            raise CoreContractError(
                f"{declaration.name}: duplicate metadata {entry.name!r}"
            )
        metadata[entry.name] = None if entry.value is None else entry.value.to_json()
    if definition_name == "ModifierDefinition":
        metadata["name"] = declaration.name
    elif definition_name == "DeclarationDefinition":
        metadata["kind"] = declaration.name
    return metadata


def _argument_contract(value: Any, meta: _CoreMetaModel) -> ArgumentContract:
    _validate_meta_object(value, "ArgumentDefinition", meta, "ArgumentDefinition")
    return ArgumentContract(
        str(value["name"]),
        _type_from_json(value["type"]),
        _cardinality(value["cardinality"]),
    )


def _body_slot_contract(value: Any, meta: _CoreMetaModel) -> BodySlotContract:
    _validate_meta_object(value, "BodySlotDefinition", meta, "BodySlotDefinition")
    raw_type = value.get("valueType")
    return BodySlotContract(
        body_type=str(value["bodyType"]),
        name_policy=str(value["namePolicy"]),
        value_type=None if raw_type is None else _type_from_json(raw_type),
        cardinality=_cardinality(value["cardinality"]),
        ordered=bool(value.get("ordered", False)),
        unique_by_name=bool(value.get("uniqueByName", False)),
        modifiers=tuple(str(item) for item in value.get("modifiers", [])),
    )


def load_semantic_registry(
    *module_sources: str,
    core_source: str | None = None,
    core_projection: str | None = None,
) -> SemanticRegistry:
    root = Path(__file__).resolve().parents[1]
    if core_source is None:
        core_source = (root / "spec" / "core.aidl").read_text(encoding="utf-8")
    if core_projection is None:
        core_projection = (root / "spec" / "core-registry-v1.json").read_text(
            encoding="utf-8"
        )
    meta = _core_meta_model(core_source, core_projection)

    declarations: dict[str, DeclarationContract] = {}
    modifiers: dict[str, ModifierContract] = {}
    combinators: dict[str, MetaCombinator] = {}
    for source in module_sources:
        program = parse_source(source)
        for declaration in program.declarations:
            if declaration.kind != "declaration" or declaration.name is None:
                raise CoreContractError(
                    "semantic modules may contain only named declaration meta-definitions"
                )
            header_names = [name for name, _ in declaration.arguments]
            unknown_headers = sorted(set(header_names) - {meta.category_argument})
            if unknown_headers:
                raise CoreContractError(
                    f"{declaration.name}: undeclared meta header arguments: "
                    + ", ".join(unknown_headers)
                )
            meta_kind = _plain(_argument_value(declaration, meta.category_argument))
            if not isinstance(meta_kind, str):
                raise CoreContractError(
                    f"{declaration.name}: {meta.category_argument} metadata must be a string"
                )
            if meta_kind in meta.ignored_categories:
                continue
            definition_name = meta.categories.get(meta_kind)
            if definition_name is None:
                raise CoreContractError(
                    f"{declaration.name}: unsupported Core semantic category {meta_kind!r}"
                )
            metadata = _declaration_metadata(declaration, definition_name)
            _validate_meta_object(metadata, definition_name, meta, declaration.name)

            if definition_name == "MetaCombinatorDefinition":
                combinators[declaration.name] = MetaCombinator(
                    declaration.name,
                    str(metadata["behavior"]),
                    _cardinality(metadata["arguments"]),
                )
            elif definition_name == "ModifierDefinition":
                modifiers[declaration.name] = ModifierContract(
                    declaration.name,
                    tuple(str(item) for item in metadata["targets"]),
                    tuple(
                        _argument_contract(item, meta)
                        for item in metadata.get("arguments", [])
                    ),
                    _cardinality(metadata["cardinality"]),
                )
            elif definition_name == "DeclarationDefinition":
                raw_result = metadata.get("result")
                declarations[declaration.name] = DeclarationContract(
                    declaration.name,
                    str(metadata["namePolicy"]),
                    tuple(
                        _argument_contract(item, meta)
                        for item in metadata.get("arguments", [])
                    ),
                    None if raw_result is None else _type_from_json(raw_result),
                    tuple(
                        _body_slot_contract(item, meta)
                        for item in metadata.get("slots", [])
                    ),
                    tuple(str(item) for item in metadata.get("modifiers", [])),
                )
            else:
                raise CoreContractError(
                    f"{declaration.name}: Core category maps to uninterpretable definition {definition_name!r}"
                )
    return SemanticRegistry(declarations, modifiers, combinators)


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
