"""M16.5 E4 bounded read-only compiler schema/introspection prototype.

Experimental metadata only.  It describes a representative subset of the
currently accepted grammar surface and never parses, accepts, rewrites, or
formats AIDL source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Iterable

BASE_COMMIT = "49c1552a4a0f620b4de4bc12fac87ecb395aac01"
GRAMMAR_BLOB_SHA = "834629dab9198c1e78090e31a5ce2a29180a05f1"
SCHEMA_ID = "urn:aidl:schema:meta:m16.5-e4-introspection"
SCHEMA_VERSION = "0.1.0-e4"


class SchemaLookupError(ValueError):
    """Fail-closed error for an unknown or stale introspection schema reference."""

    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class SchemaRef:
    schema_id: str
    semantic_version: str
    content_fingerprint: str


@dataclass(frozen=True)
class ValueShape:
    shape_id: str
    kind: str
    syntax: str
    documentation: str
    closed_values: tuple[str, ...] = ()
    item_shape: str | None = None
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModifierShape:
    modifier_id: str
    visible_tokens: tuple[str, ...]
    value_shape: str | None
    documentation: str


@dataclass(frozen=True)
class HeaderArgument:
    argument_id: str
    visible_tokens: tuple[str, ...]
    value_shape: str
    cardinality: str
    documentation: str


@dataclass(frozen=True)
class BodySlot:
    slot_id: str
    visible_tokens: tuple[str, ...]
    cardinality: str
    value_shape: str | None
    documentation: str
    name_shape: str | None = None
    modifiers: tuple[str, ...] = ()
    nested_schema: str | None = None
    semantic_order: str = "preserve"


@dataclass(frozen=True)
class DeclarationShape:
    kind: str
    family: str
    starter_tokens: tuple[str, ...]
    identity_shape: str
    header_arguments: tuple[HeaderArgument, ...]
    body_slots: tuple[BodySlot, ...]
    documentation: str
    annotations_allowed: bool = True
    body_semantic_order: str = "preserve"


@dataclass(frozen=True)
class SublanguageAlternative:
    alternative_id: str
    syntax: str
    child_schema: str | None = None


@dataclass(frozen=True)
class SublanguageShape:
    name: str
    generic_production: str
    alternatives: tuple[SublanguageAlternative, ...]
    vocabulary_authority: str
    vocabulary_scope: str
    closed_vocabulary: bool
    documentation: str
    recursive: bool = False


@dataclass(frozen=True)
class IntrospectionCatalog:
    schema_ref: SchemaRef
    source_base_commit: str
    source_grammar_blob_sha: str
    declarations: tuple[DeclarationShape, ...]
    value_shapes: tuple[ValueShape, ...]
    modifiers: tuple[ModifierShape, ...]
    sublanguages: tuple[SublanguageShape, ...]
    coverage: tuple[str, ...]
    omissions: tuple[str, ...]

    def declaration(self, kind: str) -> DeclarationShape:
        for item in self.declarations:
            if item.kind == kind:
                return item
        raise KeyError(kind)

    def value_shape(self, shape_id: str) -> ValueShape:
        for item in self.value_shapes:
            if item.shape_id == shape_id:
                return item
        raise KeyError(shape_id)

    def modifier(self, modifier_id: str) -> ModifierShape:
        for item in self.modifiers:
            if item.modifier_id == modifier_id:
                return item
        raise KeyError(modifier_id)

    def sublanguage(self, name: str) -> SublanguageShape:
        for item in self.sublanguages:
            if item.name == name:
                return item
        raise KeyError(name)


def _values() -> tuple[ValueShape, ...]:
    return (
        ValueShape("identifier", "lexical", "identifier", "docs/06-grammar.md#Lexikalische-Regeln"),
        ValueShape("typeName", "lexical", "typeName", "docs/06-grammar.md#Lexikalische-Regeln"),
        ValueShape("type", "type", "type", "docs/06-grammar.md#Typen"),
        ValueShape("expression", "expression", "expression", "docs/06-grammar.md#Ausdrücke"),
        ValueShape("integer", "literal", "integer", "docs/06-grammar.md#Lexikalische-Regeln"),
        ValueShape("duration", "literal", "durationLiteral", "docs/06-grammar.md#Lexikalische-Regeln"),
        ValueShape("delete-action", "enum", "deleteAction", "docs/06-grammar.md#Typdeklarationen", closed_values=("restrict", "cascade", "nullify")),
        ValueShape("profilePropertyValue", "generic-value", "profilePropertyValue", "docs/06-grammar.md#Ressourcen-und-Medien"),
        ValueShape("typeName-list", "list", "[ typeName { , typeName } ]", "docs/06-grammar.md#Systeme-und-Services", item_shape="typeName"),
        ValueShape("typed-exposed-list", "list", "[ exposedItem { , exposedItem } ]", "docs/06-grammar.md#Systeme-und-Services", alternatives=("query qualifiedName", "mutation qualifiedName", "channel qualifiedName", "sync qualifiedName")),
        ValueShape("typed-runnable-list", "list", "[ runnableItem { , runnableItem } ]", "docs/06-grammar.md#Systeme-und-Services", alternatives=("consumer qualifiedName", "workflow qualifiedName", "task qualifiedName", "schedule qualifiedName", "projection qualifiedName", "sync qualifiedName", "channel qualifiedName")),
        ValueShape("app-profile", "compound", "identifier version integer", "docs/06-grammar.md#App-und-Profile"),
        ValueShape("compatibility-mode", "enum", "identifier", "docs/06-grammar.md#Events-Messaging-und-Verarbeitung", closed_values=("none", "backward", "forward", "full")),
        ValueShape("index-fields", "compound-list", "( indexField { , indexField } )", "docs/06-grammar.md#Typdeklarationen"),
        ValueShape("sync-mode", "enum", "syncMode", "docs/06-grammar.md#Offline-Synchronisation", closed_values=("serverAuthoritative", "queuedCommands", "replicated")),
        ValueShape("sync-authority", "enum", "syncAuthority", "docs/06-grammar.md#Offline-Synchronisation", closed_values=("server", "serverValidated", "merge")),
        ValueShape("sync-changes-outbox", "compound", "to typeName via outbox", "docs/06-grammar.md#Offline-Synchronisation"),
        ValueShape("sync-delete-tombstone", "compound", "tombstone retain durationLiteral", "docs/06-grammar.md#Offline-Synchronisation"),
        ValueShape("sync-schema-migration", "literal", "required", "docs/06-grammar.md#Offline-Synchronisation", closed_values=("required",)),
        ValueShape("profilePropertyValue+", "sequence", "profilePropertyValue { profilePropertyValue }", "docs/06-grammar.md#Ressourcen-und-Medien", item_shape="profilePropertyValue"),
    )


def _modifiers() -> tuple[ModifierShape, ...]:
    doc = "docs/06-grammar.md#Typdeklarationen"
    return (
        ModifierShape("required", ("required",), None, doc),
        ModifierShape("primary", ("primary",), None, doc),
        ModifierShape("generated", ("generated",), None, doc),
        ModifierShape("clientGenerated", ("clientGenerated",), None, doc),
        ModifierShape("immutable", ("immutable",), None, doc),
        ModifierShape("mutable", ("mutable",), None, doc),
        ModifierShape("sensitive", ("sensitive",), None, doc),
        ModifierShape("unique", ("unique",), None, doc),
        ModifierShape("concurrencyToken", ("concurrencyToken",), None, doc),
        ModifierShape("default", ("default",), "expression", doc),
        ModifierShape("onDelete", ("onDelete",), "delete-action", doc),
        ModifierShape("via", ("via",), "identifier", doc),
    )


def _field_modifier_ids() -> tuple[str, ...]:
    return tuple(item.modifier_id for item in _modifiers())


def _declarations() -> tuple[DeclarationShape, ...]:
    app_doc = "docs/06-grammar.md#App-und-Profile"
    core_doc = "docs/06-grammar.md#Typdeklarationen"
    backend_doc = "docs/06-grammar.md#Systeme-und-Services"
    sync_doc = "docs/06-grammar.md#Offline-Synchronisation"
    return (
        DeclarationShape(
            kind="app",
            family="App",
            starter_tokens=("app",),
            identity_shape="typeName",
            header_arguments=(),
            documentation=app_doc,
            body_slots=(
                BodySlot("profile", ("profile",), "many", "app-profile", app_doc),
                BodySlot("system", ("system",), "many", "typeName", app_doc),
                BodySlot("frontend", ("frontend",), "many", "typeName", app_doc),
                BodySlot("api", ("api",), "many", "typeName", app_doc),
                BodySlot("defaultDeployment", ("defaultDeployment",), "many", "identifier", app_doc),
                BodySlot("compatibility", ("compatibility",), "many", "identifier", app_doc),
            ),
        ),
        DeclarationShape(
            kind="entity",
            family="Core",
            starter_tokens=("entity",),
            identity_shape="typeName",
            header_arguments=(),
            documentation=core_doc,
            body_slots=(
                BodySlot("field", (), "many", "type", core_doc, name_shape="identifier", modifiers=_field_modifier_ids()),
                BodySlot("index", ("index",), "many", "index-fields", core_doc, name_shape="identifier"),
                BodySlot("invariant", ("invariant",), "many", "expression", core_doc, name_shape="identifier"),
            ),
        ),
        DeclarationShape(
            kind="service",
            family="Backend",
            starter_tokens=("service",),
            identity_shape="typeName",
            header_arguments=(),
            documentation=backend_doc,
            body_slots=(
                BodySlot("owns", ("owns",), "many", "typeName-list", backend_doc),
                BodySlot("uses", ("uses",), "many", "typeName-list", backend_doc),
                BodySlot("exposes", ("exposes",), "many", "typed-exposed-list", backend_doc),
                BodySlot("runs", ("runs",), "many", "typed-runnable-list", backend_doc),
                BodySlot("dependsOn", ("dependsOn",), "many", "typeName-list", backend_doc),
                BodySlot("reliability", ("reliability",), "many", None, backend_doc, nested_schema="profileProperty"),
                BodySlot("telemetry", ("telemetry",), "many", "identifier", backend_doc),
            ),
        ),
        DeclarationShape(
            kind="sync",
            family="Sync",
            starter_tokens=("sync",),
            identity_shape="typeName",
            header_arguments=(HeaderArgument("target", ("for",), "type", "one", sync_doc),),
            documentation=sync_doc,
            body_slots=(
                BodySlot("mode", ("mode",), "many", "sync-mode", sync_doc),
                BodySlot("authority", ("authority",), "many", "sync-authority", sync_doc),
                BodySlot("scope", ("scope", ":"), "many", "expression", sync_doc),
                BodySlot("localStore", ("localStore",), "many", "typeName", sync_doc),
                BodySlot("serverStore", ("serverStore",), "many", "typeName", sync_doc),
                BodySlot("operationLog", ("operationLog",), "many", None, sync_doc, nested_schema="profileProperty"),
                BodySlot("push", ("push",), "many", "profilePropertyValue+", sync_doc),
                BodySlot("pull", ("pull",), "many", "profilePropertyValue+", sync_doc),
                BodySlot("changes", ("changes",), "many", "sync-changes-outbox", sync_doc),
                BodySlot("delete", ("delete",), "many", "sync-delete-tombstone", sync_doc),
                BodySlot("conflict", ("conflict",), "many", None, sync_doc, nested_schema="conflictRule"),
                BodySlot("rejected", ("rejected",), "many", "profilePropertyValue+", sync_doc),
                BodySlot("schemaMigration", ("schemaMigration",), "many", "sync-schema-migration", sync_doc),
            ),
        ),
    )


def _sublanguages() -> tuple[SublanguageShape, ...]:
    return (
        SublanguageShape(
            name="profileProperty",
            generic_production="profileProperty",
            alternatives=(
                SublanguageAlternative("path-value", "propertyPath [ : ] profilePropertyValue newline"),
                SublanguageAlternative("path-block", "propertyPath { { profileProperty } }", "profileProperty"),
            ),
            vocabulary_authority="compiler-owned profile schema for the enclosing declaration/profile",
            vocabulary_scope="contextual property paths and value types",
            closed_vocabulary=True,
            recursive=True,
            documentation="docs/06-grammar.md#Ressourcen-und-Medien",
        ),
        SublanguageShape(
            name="uiStatement",
            generic_production="uiStatement",
            alternatives=(
                SublanguageAlternative("statement", "identifier { uiAtom } [ { { uiStatement } } ] newline", "uiStatement"),
            ),
            vocabulary_authority="compiler-owned web profile schema",
            vocabulary_scope="contextual UI statement identifiers and typed atoms",
            closed_vocabulary=True,
            recursive=True,
            documentation="docs/06-grammar.md#Frontend",
        ),
        SublanguageShape(
            name="testStatement",
            generic_production="testStatement",
            alternatives=(
                SublanguageAlternative("leaf", "identifier { expression | qualifiedName | profilePropertyValue } newline"),
                SublanguageAlternative("block", "identifier { expression | qualifiedName } { { testStatement } }", "testStatement"),
            ),
            vocabulary_authority="compiler-owned test profile schema",
            vocabulary_scope="typed test verbs such as arrange/act/assert and their operands",
            closed_vocabulary=True,
            recursive=True,
            documentation="docs/06-grammar.md#Tests-und-Fixtures",
        ),
        SublanguageShape(
            name="conflictRule",
            generic_production="conflictRule",
            alternatives=(
                SublanguageAlternative("field", "field identifier merge mergeStrategy newline"),
                SublanguageAlternative("group", "group identifier fields [ identifier { , identifier } ] merge mergeStrategy newline"),
            ),
            vocabulary_authority="standard language schema",
            vocabulary_scope="offline-sync conflict rules",
            closed_vocabulary=True,
            recursive=False,
            documentation="docs/06-grammar.md#Offline-Synchronisation",
        ),
    )


def _unsigned_payload() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "semantic_version": SCHEMA_VERSION,
        "source_base_commit": BASE_COMMIT,
        "source_grammar_blob_sha": GRAMMAR_BLOB_SHA,
        "declarations": [asdict(item) for item in _declarations()],
        "value_shapes": [asdict(item) for item in _values()],
        "modifiers": [asdict(item) for item in _modifiers()],
        "sublanguages": [asdict(item) for item in _sublanguages()],
        "coverage": [
            "representative App/Core/Backend/Sync declaration construction metadata",
            "header arguments, body slots, value/type shapes, field modifiers, documentation and nesting",
            "generic profileProperty, uiStatement and testStatement structural discoverability",
            "exact introspection schema id/version/fingerprint authority with fail-closed lookup",
        ],
        "omissions": [
            "not a complete 49-form declaration corpus schema",
            "does not export profile-specific property/UI/test vocabularies beyond their compiler-owned authority boundary",
            "does not parse source or alter production parser acceptance",
            "does not implement formatter/migration, IDE completion, diagnostics rollout, compatibility, IR or runtime behavior",
        ],
    }


def _fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


@lru_cache(maxsize=1)
def build_catalog() -> IntrospectionCatalog:
    payload = _unsigned_payload()
    ref = SchemaRef(SCHEMA_ID, SCHEMA_VERSION, _fingerprint(payload))
    return IntrospectionCatalog(
        schema_ref=ref,
        source_base_commit=BASE_COMMIT,
        source_grammar_blob_sha=GRAMMAR_BLOB_SHA,
        declarations=_declarations(),
        value_shapes=_values(),
        modifiers=_modifiers(),
        sublanguages=_sublanguages(),
        coverage=tuple(payload["coverage"]),
        omissions=tuple(payload["omissions"]),
    )


def current_schema_ref() -> SchemaRef:
    """Return the one exact compiler-embedded E4 introspection schema reference."""
    return build_catalog().schema_ref


def require_schema(ref: SchemaRef) -> IntrospectionCatalog:
    """Resolve only an exact immutable schema tuple; never guess or fall back."""
    current = build_catalog()
    if ref.schema_id != current.schema_ref.schema_id:
        raise SchemaLookupError("unknown-schema-id", ref.schema_id)
    if ref.semantic_version != current.schema_ref.semantic_version:
        raise SchemaLookupError("stale-schema-version", ref.semantic_version)
    if ref.content_fingerprint != current.schema_ref.content_fingerprint:
        raise SchemaLookupError("fingerprint-mismatch", ref.content_fingerprint)
    return current


class CompilerSchemaService:
    """Read-only transport-neutral projection over compiler-owned E4 metadata."""

    def schema_ref(self) -> SchemaRef:
        return current_schema_ref()

    def declaration_kinds(self, ref: SchemaRef, *, family: str | None = None) -> tuple[str, ...]:
        catalog = require_schema(ref)
        return tuple(item.kind for item in catalog.declarations if family is None or item.family == family)

    def declaration(self, ref: SchemaRef, kind: str) -> DeclarationShape:
        catalog = require_schema(ref)
        try:
            return catalog.declaration(kind)
        except KeyError as error:
            raise SchemaLookupError("unknown-declaration-kind", kind) from error

    def sublanguage(self, ref: SchemaRef, name: str) -> SublanguageShape:
        catalog = require_schema(ref)
        try:
            return catalog.sublanguage(name)
        except KeyError as error:
            raise SchemaLookupError("unknown-sublanguage", name) from error

    def value_shape(self, ref: SchemaRef, shape_id: str) -> ValueShape:
        catalog = require_schema(ref)
        try:
            return catalog.value_shape(shape_id)
        except KeyError as error:
            raise SchemaLookupError("unknown-value-shape", shape_id) from error

    def modifiers(self, ref: SchemaRef, modifier_ids: Iterable[str]) -> tuple[ModifierShape, ...]:
        catalog = require_schema(ref)
        result: list[ModifierShape] = []
        for modifier_id in modifier_ids:
            try:
                result.append(catalog.modifier(modifier_id))
            except KeyError as error:
                raise SchemaLookupError("unknown-modifier", modifier_id) from error
        return tuple(result)

    def export(self, ref: SchemaRef) -> dict[str, Any]:
        catalog = require_schema(ref)
        return {
            "schema_ref": asdict(catalog.schema_ref),
            "source_base_commit": catalog.source_base_commit,
            "source_grammar_blob_sha": catalog.source_grammar_blob_sha,
            "declarations": [asdict(item) for item in catalog.declarations],
            "value_shapes": [asdict(item) for item in catalog.value_shapes],
            "modifiers": [asdict(item) for item in catalog.modifiers],
            "sublanguages": [asdict(item) for item in catalog.sublanguages],
            "coverage": list(catalog.coverage),
            "omissions": list(catalog.omissions),
        }


def _parse_ref(args: argparse.Namespace) -> SchemaRef:
    return SchemaRef(args.schema_id, args.schema_version, args.schema_fingerprint)


def _add_ref_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--schema-id", required=True)
    parser.add_argument("--schema-version", required=True)
    parser.add_argument("--schema-fingerprint", required=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("schema-ref", help="print the exact compiler-owned E4 schema tuple")
    export = commands.add_parser("export", help="export the complete bounded read-only catalog")
    _add_ref_args(export)
    declaration = commands.add_parser("declaration", help="describe one declaration kind")
    declaration.add_argument("kind")
    _add_ref_args(declaration)
    sublanguage = commands.add_parser("sublanguage", help="describe one generic sublanguage")
    sublanguage.add_argument("name")
    _add_ref_args(sublanguage)
    args = parser.parse_args(argv)
    service = CompilerSchemaService()
    try:
        if args.command == "schema-ref":
            value: Any = asdict(service.schema_ref())
        elif args.command == "export":
            value = service.export(_parse_ref(args))
        elif args.command == "declaration":
            value = asdict(service.declaration(_parse_ref(args), args.kind))
        elif args.command == "sublanguage":
            value = asdict(service.sublanguage(_parse_ref(args), args.name))
        else:  # pragma: no cover
            parser.error("unsupported command")
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except SchemaLookupError as error:
        print(json.dumps({"error": error.reason, "detail": error.detail}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
