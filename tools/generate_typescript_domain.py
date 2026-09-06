from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


IR_VERSION = "0.3.0"
GENERATED_DOMAIN_PATH = "generated/domain.ts"
_DOMAIN_KINDS = {"enum", "alias", "opaque", "value", "entity", "view"}
_TS_SCALARS = {
    "string": "string",
    "int": "number",
    "decimal": "number",
    "bool": "boolean",
    "uuid": "string",
    "date": "string",
    "datetime": "string",
    "duration": "string",
    "revision": "string",
    "email": "string",
    "url": "string",
    "bytes": "Uint8Array",
}
_TS_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


class TypeScriptDomainGeneratorError(ValueError):
    pass


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeScriptDomainGeneratorError(f"{label} must be a non-empty string")
    return value


def _declaration_symbol(declaration: Mapping[str, Any]) -> str:
    name = _string(declaration.get("name"), "declaration name")
    if not _TS_IDENTIFIER.fullmatch(name):
        raise TypeScriptDomainGeneratorError(
            f"declaration '{name}' is not a valid TypeScript identifier"
        )
    return name


def _property_name(name: Any) -> str:
    value = _string(name, "field name")
    return value if _TS_IDENTIFIER.fullmatch(value) else json.dumps(value, ensure_ascii=False)


def _parenthesize(type_text: str) -> str:
    return f"({type_text})" if " | " in type_text else type_text


def _type_ref(
    type_ref: Any,
    symbols_by_id: Mapping[str, str],
) -> str:
    if not isinstance(type_ref, Mapping):
        raise TypeScriptDomainGeneratorError("type reference must be an object")

    kind = type_ref.get("kind")
    if kind == "scalar":
        name = type_ref.get("name")
        if name not in _TS_SCALARS:
            raise TypeScriptDomainGeneratorError(f"unsupported scalar type '{name}'")
        return _TS_SCALARS[name]

    if kind == "named":
        declaration_id = _string(type_ref.get("declarationId"), "named declarationId")
        symbol = symbols_by_id.get(declaration_id)
        if symbol is None:
            raise TypeScriptDomainGeneratorError(
                f"named type '{declaration_id}' is outside the M4-02 domain generator boundary"
            )
        arguments = type_ref.get("typeArguments")
        if not isinstance(arguments, list):
            raise TypeScriptDomainGeneratorError("named typeArguments must be an array")
        if arguments:
            raise TypeScriptDomainGeneratorError(
                f"generic named type '{declaration_id}' is not supported by M4-02"
            )
        return symbol

    if kind == "ref":
        entity_id = _string(type_ref.get("entityId"), "ref entityId")
        symbol = symbols_by_id.get(entity_id)
        if symbol is None:
            raise TypeScriptDomainGeneratorError(
                f"entity ref '{entity_id}' is outside the M4-02 domain generator boundary"
            )
        return symbol

    if kind in {"list", "set", "nullable"}:
        inner = _type_ref(type_ref.get("element"), symbols_by_id)
        if kind == "list":
            return f"ReadonlyArray<{inner}>"
        if kind == "set":
            return f"ReadonlySet<{inner}>"
        return f"{_parenthesize(inner)} | null"

    if kind == "map":
        key = _type_ref(type_ref.get("key"), symbols_by_id)
        value = _type_ref(type_ref.get("value"), symbols_by_id)
        return f"ReadonlyMap<{key}, {value}>"

    if kind == "record":
        fields = type_ref.get("fields")
        if not isinstance(fields, list):
            raise TypeScriptDomainGeneratorError("record fields must be an array")
        if not fields:
            return "Readonly<Record<string, never>>"
        parts: list[str] = []
        for field in fields:
            if not isinstance(field, Mapping):
                raise TypeScriptDomainGeneratorError("record field must be an object")
            name = _property_name(field.get("name"))
            required = field.get("required")
            if not isinstance(required, bool):
                raise TypeScriptDomainGeneratorError("record field required must be boolean")
            optional = "" if required else "?"
            parts.append(
                f"readonly {name}{optional}: {_type_ref(field.get('type'), symbols_by_id)}"
            )
        return "{ " + "; ".join(parts) + " }"

    raise TypeScriptDomainGeneratorError(f"unsupported type reference kind '{kind}'")


def _field_lines(
    fields: Any,
    symbols_by_id: Mapping[str, str],
) -> list[str]:
    if not isinstance(fields, list):
        raise TypeScriptDomainGeneratorError("declaration fields must be an array")

    result: list[str] = []
    for field in fields:
        if not isinstance(field, Mapping):
            raise TypeScriptDomainGeneratorError("field must be an object")
        name = _property_name(field.get("name"))
        required = field.get("required")
        if not isinstance(required, bool):
            raise TypeScriptDomainGeneratorError("field required must be boolean")
        optional = "" if required else "?"
        result.append(
            f"  readonly {name}{optional}: {_type_ref(field.get('type'), symbols_by_id)};"
        )
    return result


def _render_declaration(
    declaration: Mapping[str, Any],
    symbols_by_id: Mapping[str, str],
) -> str:
    kind = declaration.get("kind")
    symbol = _declaration_symbol(declaration)

    if kind == "enum":
        values = declaration.get("values")
        if not isinstance(values, list) or not values:
            raise TypeScriptDomainGeneratorError(f"enum '{symbol}' must contain values")
        literals = " | ".join(json.dumps(_string(value, "enum value"), ensure_ascii=False) for value in values)
        return f"export type {symbol} = {literals};"

    if kind == "alias":
        return f"export type {symbol} = {_type_ref(declaration.get('target'), symbols_by_id)};"

    if kind == "opaque":
        representation = _type_ref(declaration.get("representation"), symbols_by_id)
        fqn = _string(declaration.get("fqn"), "opaque fqn")
        brand = json.dumps(fqn, ensure_ascii=False)
        return (
            f"export type {symbol} = {representation} & "
            f"{{ readonly __aidlOpaque: {brand} }};"
        )

    if kind in {"value", "entity", "view"}:
        lines = [f"export interface {symbol} {{"]
        lines.extend(_field_lines(declaration.get("fields"), symbols_by_id))
        lines.append("}")
        return "\n".join(lines)

    raise TypeScriptDomainGeneratorError(f"unsupported declaration kind '{kind}'")


def generate_typescript_domain(ir: Mapping[str, Any]) -> str:
    """Generate deterministic M4-02 TypeScript domain declarations from canonical IR only.

    This function deliberately accepts an IR mapping rather than source paths or compiler
    objects. It generates only enum/alias/opaque/value/entity/view declarations; API routes,
    persistence, transactions, idempotency, events, runtime wiring, and application build
    scaffolding remain later M4 work.
    """

    if ir.get("irVersion") != IR_VERSION:
        raise TypeScriptDomainGeneratorError(
            f"unsupported canonical IR version '{ir.get('irVersion')}'"
        )

    declarations = ir.get("declarations")
    if not isinstance(declarations, list):
        raise TypeScriptDomainGeneratorError("canonical IR declarations must be an array")

    domain_declarations: list[Mapping[str, Any]] = []
    symbols_by_id: dict[str, str] = {}
    ids_by_symbol: dict[str, str] = {}

    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            raise TypeScriptDomainGeneratorError("canonical IR declaration must be an object")
        if declaration.get("kind") not in _DOMAIN_KINDS:
            continue
        declaration_id = _string(declaration.get("declarationId"), "declarationId")
        symbol = _declaration_symbol(declaration)
        prior_id = ids_by_symbol.get(symbol)
        if prior_id is not None and prior_id != declaration_id:
            raise TypeScriptDomainGeneratorError(
                f"domain declarations '{prior_id}' and '{declaration_id}' collide on TypeScript symbol '{symbol}'"
            )
        ids_by_symbol[symbol] = declaration_id
        symbols_by_id[declaration_id] = symbol
        domain_declarations.append(declaration)

    domain_declarations.sort(
        key=lambda declaration: (
            _string(declaration.get("fqn"), "declaration fqn"),
            _string(declaration.get("declarationId"), "declarationId"),
        )
    )

    blocks = [
        "// Generated from canonical AIDL IR by the M4 TypeScript domain generator.",
        "// M4-02 domain declarations only; runtime behavior is intentionally absent.",
    ]
    blocks.extend(
        _render_declaration(declaration, symbols_by_id)
        for declaration in domain_declarations
    )
    return "\n\n".join(blocks) + "\n"


def generate_typescript_domain_files(ir: Mapping[str, Any]) -> dict[str, str]:
    """Return the deterministic generated-file set for the M4-02 stack contract."""

    return {GENERATED_DOMAIN_PATH: generate_typescript_domain(ir)}
