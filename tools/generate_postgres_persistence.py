from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


IR_VERSION = "0.3.0"
GENERATED_SCHEMA_PATH = "generated/schema.sql"
GENERATED_MIGRATION_PATH = "generated/migrations/0001_initial.sql"


class PostgresPersistenceGeneratorError(ValueError):
    pass


_SCALAR_SQL = {
    "string": "text",
    "int": "bigint",
    "decimal": "numeric",
    "bool": "boolean",
    "uuid": "uuid",
    "date": "date",
    "datetime": "timestamptz",
    "duration": "bigint",
    "revision": "bigint",
    "email": "text",
    "url": "text",
    "bytes": "bytea",
}


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PostgresPersistenceGeneratorError(f"{label} must be a non-empty string")
    return value


def _sql_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _table_name(declaration: Mapping[str, Any]) -> str:
    fqn = _string(declaration.get("fqn"), "entity fqn")
    value = re.sub(r"[^A-Za-z0-9]+", "_", fqn).strip("_").lower()
    if not value:
        raise PostgresPersistenceGeneratorError(f"entity '{fqn}' has no usable PostgreSQL table name")
    return value


def _column_name(field: Mapping[str, Any]) -> str:
    return _string(field.get("name"), "field name")


def _declarations(ir: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    raw = ir.get("declarations")
    if not isinstance(raw, list):
        raise PostgresPersistenceGeneratorError("canonical IR declarations must be an array")
    declarations: list[Mapping[str, Any]] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for declaration in raw:
        if not isinstance(declaration, Mapping):
            raise PostgresPersistenceGeneratorError("canonical IR declaration must be an object")
        declaration_id = declaration.get("declarationId")
        if isinstance(declaration_id, str) and declaration_id:
            by_id[declaration_id] = declaration
        declarations.append(declaration)
    return declarations, by_id


def _unwrap_nullable(type_ref: Any) -> tuple[Mapping[str, Any], bool]:
    if not isinstance(type_ref, Mapping):
        raise PostgresPersistenceGeneratorError("type reference must be an object")
    if type_ref.get("kind") == "nullable":
        element = type_ref.get("element")
        if not isinstance(element, Mapping):
            raise PostgresPersistenceGeneratorError("nullable element must be a type reference")
        return element, True
    return type_ref, False


def _named_storage_type(
    declaration: Mapping[str, Any],
    declarations_by_id: Mapping[str, Mapping[str, Any]],
    stack: tuple[str, ...],
) -> tuple[str, list[str]]:
    declaration_id = _string(declaration.get("declarationId"), "named declarationId")
    if declaration_id in stack:
        raise PostgresPersistenceGeneratorError(f"cyclic persistence type alias involving '{declaration_id}'")
    kind = declaration.get("kind")
    if kind == "enum":
        values = declaration.get("values")
        if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
            raise PostgresPersistenceGeneratorError(f"enum '{declaration_id}' has invalid values")
        return "text", list(values)
    if kind == "alias":
        return _storage_type(declaration.get("target"), declarations_by_id, stack + (declaration_id,))
    if kind == "opaque":
        return _storage_type(declaration.get("representation"), declarations_by_id, stack + (declaration_id,))
    raise PostgresPersistenceGeneratorError(
        f"named type '{declaration_id}' is outside the M4-04 PostgreSQL persistence subset"
    )


def _storage_type(
    type_ref: Any,
    declarations_by_id: Mapping[str, Mapping[str, Any]],
    stack: tuple[str, ...] = (),
) -> tuple[str, list[str]]:
    type_ref, nullable = _unwrap_nullable(type_ref)
    kind = type_ref.get("kind")
    if kind == "scalar":
        name = type_ref.get("name")
        sql_type = _SCALAR_SQL.get(name)
        if sql_type is None:
            raise PostgresPersistenceGeneratorError(f"unsupported scalar persistence type '{name}'")
        return sql_type, []
    if kind == "named":
        arguments = type_ref.get("typeArguments")
        if not isinstance(arguments, list):
            raise PostgresPersistenceGeneratorError("named typeArguments must be an array")
        if arguments:
            raise PostgresPersistenceGeneratorError("generic named types are outside the M4-04 persistence subset")
        declaration_id = _string(type_ref.get("declarationId"), "named declarationId")
        declaration = declarations_by_id.get(declaration_id)
        if declaration is None:
            raise PostgresPersistenceGeneratorError(f"named persistence type '{declaration_id}' is unresolved")
        return _named_storage_type(declaration, declarations_by_id, stack)
    if kind == "ref":
        entity_id = _string(type_ref.get("entityId"), "ref entityId")
        entity = declarations_by_id.get(entity_id)
        if entity is None or entity.get("kind") != "entity":
            raise PostgresPersistenceGeneratorError(f"entity ref '{entity_id}' is unresolved")
        identity_fields = entity.get("identityFields")
        fields = entity.get("fields")
        if not isinstance(identity_fields, list) or len(identity_fields) != 1 or not isinstance(fields, list):
            raise PostgresPersistenceGeneratorError(
                f"entity ref '{entity_id}' requires exactly one identity field in M4-04"
            )
        identity_name = identity_fields[0]
        identity = next((field for field in fields if isinstance(field, Mapping) and field.get("name") == identity_name), None)
        if identity is None:
            raise PostgresPersistenceGeneratorError(f"entity ref '{entity_id}' identity field is missing")
        sql_type, enum_values = _storage_type(identity.get("type"), declarations_by_id, stack)
        if enum_values:
            raise PostgresPersistenceGeneratorError(f"entity ref '{entity_id}' cannot use an enum identity in M4-04")
        return sql_type, []
    suffix = " nullable" if nullable else ""
    raise PostgresPersistenceGeneratorError(
        f"type reference kind '{kind}'{suffix} is outside the M4-04 PostgreSQL persistence subset"
    )


def _constraint_checks(field: Mapping[str, Any], column: str, enum_values: Sequence[str]) -> list[str]:
    checks: list[str] = []
    type_ref, _ = _unwrap_nullable(field.get("type"))
    constraints = type_ref.get("constraints") if isinstance(type_ref, Mapping) else None
    if isinstance(constraints, Mapping):
        if isinstance(constraints.get("minLength"), int):
            checks.append(f"char_length({_sql_ident(column)}) >= {constraints['minLength']}")
        if isinstance(constraints.get("maxLength"), int):
            checks.append(f"char_length({_sql_ident(column)}) <= {constraints['maxLength']}")
        if isinstance(constraints.get("minimum"), (int, float)) and not isinstance(constraints.get("minimum"), bool):
            checks.append(f"{_sql_ident(column)} >= {json.dumps(constraints['minimum'])}")
        if isinstance(constraints.get("maximum"), (int, float)) and not isinstance(constraints.get("maximum"), bool):
            checks.append(f"{_sql_ident(column)} <= {json.dumps(constraints['maximum'])}")
    if enum_values:
        literals = ", ".join("'" + value.replace("'", "''") + "'" for value in enum_values)
        checks.append(f"{_sql_ident(column)} IN ({literals})")
    return checks


def _generated_revision_default(field: Mapping[str, Any]) -> str:
    type_ref, nullable = _unwrap_nullable(field.get("type"))
    if nullable:
        return ""
    if (
        field.get("generated") is True
        and field.get("concurrencyToken") is True
        and type_ref.get("kind") == "scalar"
        and type_ref.get("name") == "revision"
    ):
        return " DEFAULT 1"
    return ""


def _render_entity(entity: Mapping[str, Any], declarations_by_id: Mapping[str, Mapping[str, Any]]) -> str:
    entity_id = _string(entity.get("declarationId"), "entity declarationId")
    fields = entity.get("fields")
    identity_fields = entity.get("identityFields")
    if not isinstance(fields, list) or not fields:
        raise PostgresPersistenceGeneratorError(f"entity '{entity_id}' must contain fields")
    if not isinstance(identity_fields, list) or not identity_fields or not all(isinstance(name, str) for name in identity_fields):
        raise PostgresPersistenceGeneratorError(f"entity '{entity_id}' must contain identityFields")

    table = _table_name(entity)
    column_lines: list[str] = []
    table_constraints: list[str] = []
    field_names: set[str] = set()

    for field in fields:
        if not isinstance(field, Mapping):
            raise PostgresPersistenceGeneratorError(f"entity '{entity_id}' field must be an object")
        name = _column_name(field)
        if name in field_names:
            raise PostgresPersistenceGeneratorError(f"entity '{entity_id}' has duplicate field '{name}'")
        field_names.add(name)
        sql_type, enum_values = _storage_type(field.get("type"), declarations_by_id)
        _, nullable = _unwrap_nullable(field.get("type"))
        required = field.get("required")
        if not isinstance(required, bool):
            raise PostgresPersistenceGeneratorError(f"entity '{entity_id}' field '{name}' required must be boolean")
        if required and nullable:
            raise PostgresPersistenceGeneratorError(
                f"entity '{entity_id}' field '{name}' is both required and nullable"
            )
        null_sql = "" if nullable or not required else " NOT NULL"
        default_sql = _generated_revision_default(field)
        column_lines.append(f"  {_sql_ident(name)} {sql_type}{null_sql}{default_sql}")
        for check in _constraint_checks(field, name, enum_values):
            table_constraints.append(f"  CONSTRAINT {_sql_ident('ck_' + table + '_' + name + '_' + str(len(table_constraints) + 1))} CHECK ({check})")

        type_ref, _ = _unwrap_nullable(field.get("type"))
        if type_ref.get("kind") == "ref":
            target_id = _string(type_ref.get("entityId"), "ref entityId")
            target = declarations_by_id.get(target_id)
            if target is None or target.get("kind") != "entity":
                raise PostgresPersistenceGeneratorError(f"entity ref '{target_id}' is unresolved")
            target_identity = target.get("identityFields")
            if not isinstance(target_identity, list) or len(target_identity) != 1:
                raise PostgresPersistenceGeneratorError(f"entity ref '{target_id}' requires exactly one identity field")
            on_delete = field.get("onDelete", "none")
            action = {"restrict": " RESTRICT", "cascade": " CASCADE", "setNull": " SET NULL", "none": ""}.get(on_delete)
            if action is None:
                raise PostgresPersistenceGeneratorError(f"unsupported onDelete '{on_delete}' for field '{name}'")
            if on_delete == "setNull" and required:
                raise PostgresPersistenceGeneratorError(f"field '{name}' cannot use onDelete setNull while required")
            table_constraints.append(
                f"  CONSTRAINT {_sql_ident('fk_' + table + '_' + name)} FOREIGN KEY ({_sql_ident(name)}) "
                f"REFERENCES {_sql_ident(_table_name(target))} ({_sql_ident(str(target_identity[0]))}) ON DELETE{action or ' NO ACTION'}"
            )

    missing_identity = [name for name in identity_fields if name not in field_names]
    if missing_identity:
        raise PostgresPersistenceGeneratorError(
            f"entity '{entity_id}' identity field(s) missing: {', '.join(missing_identity)}"
        )
    primary = ", ".join(_sql_ident(name) for name in identity_fields)
    table_constraints.append(f"  PRIMARY KEY ({primary})")

    body = ",\n".join(column_lines + table_constraints)
    return f"CREATE TABLE {_sql_ident(table)} (\n{body}\n);"


def generate_postgres_schema(ir: Mapping[str, Any]) -> str:
    """Generate deterministic M4-04 PostgreSQL DDL from canonical IR only."""
    if ir.get("irVersion") != IR_VERSION:
        raise PostgresPersistenceGeneratorError(f"unsupported canonical IR version '{ir.get('irVersion')}'")
    declarations, declarations_by_id = _declarations(ir)
    entities = [declaration for declaration in declarations if declaration.get("kind") == "entity"]
    entities.sort(key=lambda declaration: (_string(declaration.get("fqn"), "entity fqn"), _string(declaration.get("declarationId"), "entity declarationId")))
    if not entities:
        raise PostgresPersistenceGeneratorError("canonical IR contains no entities to persist")

    table_names: dict[str, str] = {}
    for entity in entities:
        table = _table_name(entity)
        entity_id = _string(entity.get("declarationId"), "entity declarationId")
        prior = table_names.get(table)
        if prior is not None and prior != entity_id:
            raise PostgresPersistenceGeneratorError(
                f"entities '{prior}' and '{entity_id}' collide on PostgreSQL table '{table}'"
            )
        table_names[table] = entity_id

    blocks = [
        "-- Generated from canonical AIDL IR by the M4 PostgreSQL persistence generator.",
        "-- M4-04 schema/migrations only; transaction and concurrency runtime behavior is intentionally absent.",
    ]
    blocks.extend(_render_entity(entity, declarations_by_id) for entity in entities)
    return "\n\n".join(blocks) + "\n"


def generate_postgres_persistence_files(ir: Mapping[str, Any]) -> dict[str, str]:
    schema = generate_postgres_schema(ir)
    migration = "-- AIDL M4-04 initial PostgreSQL migration.\n\n" + schema
    return {
        GENERATED_SCHEMA_PATH: schema,
        GENERATED_MIGRATION_PATH: migration,
    }
