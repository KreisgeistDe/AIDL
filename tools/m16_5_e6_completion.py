"""M16.5 E6 bounded IDE/completion consumer experiment.

Experimental evidence only.  This module does not register an IDE provider, parse AIDL,
change accepted syntax, authorize migration writes, or become a semantic authority.
Current-language construction comes only from the exact E4 compiler schema service.
Candidate migration suggestions come only from an explicit exact E5 migration context
and from E5's own dry-run edit plan.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import tools.m16_5_e4_introspection as e4
import tools.m16_5_e5_migration as e5


class CompletionSchemaService(Protocol):
    """The E4 read-only service surface consumed by this prototype."""

    def schema_ref(self) -> e4.SchemaRef: ...
    def declaration_kinds(self, ref: e4.SchemaRef, *, family: str | None = None) -> tuple[str, ...]: ...
    def declaration(self, ref: e4.SchemaRef, kind: str) -> e4.DeclarationShape: ...
    def sublanguage(self, ref: e4.SchemaRef, name: str) -> e4.SublanguageShape: ...
    def value_shape(self, ref: e4.SchemaRef, shape_id: str) -> e4.ValueShape: ...
    def modifiers(self, ref: e4.SchemaRef, modifier_ids: tuple[str, ...]) -> tuple[e4.ModifierShape, ...]: ...


@dataclass(frozen=True)
class CurrentCompletionContext:
    """Explicit current-language context pinned to one exact E4 schema tuple."""

    schema_ref: e4.SchemaRef


@dataclass(frozen=True)
class E5MigrationCompletionContext:
    """Explicit old/target migration context; every identity is caller-supplied."""

    old_schema_id: str
    old_version: str
    old_schema_fingerprint: str
    target_schema_id: str
    target_version: str
    target_schema_fingerprint: str
    source_schema_id: str
    source_version: str
    source_schema_fingerprint: str
    expected_source_fingerprint: str


@dataclass(frozen=True)
class CompletionItem:
    metadata_id: str
    kind: str
    insert_text: str | None
    display_text: str
    authority: str
    documentation: str | None
    expected_name_shape: str | None = None
    expected_value_shape: str | None = None
    nested_schema: str | None = None
    semantic_order: str = "preserve"


@dataclass(frozen=True)
class CompletionSet:
    context: str
    items: tuple[CompletionItem, ...]
    semantic_order: str = "preserve"


@dataclass(frozen=True)
class CompletionUnavailable:
    reason: str
    detail: str
    authority: str


class CompletionContextError(ValueError):
    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _visible_text(tokens: tuple[str, ...]) -> str | None:
    return " ".join(tokens) if tokens else None


def _slot(shape: e4.DeclarationShape, slot_id: str) -> e4.BodySlot:
    for slot in shape.body_slots:
        if slot.slot_id == slot_id:
            return slot
    raise CompletionContextError("unknown-body-slot", f"{shape.kind}.{slot_id}")


def _item_from_slot(service: CompletionSchemaService, ref: e4.SchemaRef, slot: e4.BodySlot) -> CompletionItem:
    if slot.value_shape is not None:
        service.value_shape(ref, slot.value_shape)
    if slot.nested_schema is not None:
        service.sublanguage(ref, slot.nested_schema)
    insert_text = _visible_text(slot.visible_tokens)
    display = insert_text or slot.slot_id
    return CompletionItem(
        metadata_id=slot.slot_id,
        kind="body-slot",
        insert_text=insert_text,
        display_text=display,
        authority="e4-compiler-schema",
        documentation=slot.documentation,
        expected_name_shape=slot.name_shape,
        expected_value_shape=slot.value_shape,
        nested_schema=slot.nested_schema,
        semantic_order=slot.semantic_order,
    )


class ExperimentalCompletionConsumer:
    """Non-authoritative completion projection over compiler-owned E4/E5 evidence."""

    def __init__(self, service: CompletionSchemaService | None = None):
        self._service = service or e4.CompilerSchemaService()

    def compiler_schema_ref(self) -> e4.SchemaRef:
        """Return the exact compiler-embedded E4 tuple, not a 'latest' selection."""
        return self._service.schema_ref()

    def declaration_starters(
        self,
        context: CurrentCompletionContext,
        *,
        family: str | None = None,
    ) -> CompletionSet:
        kinds = self._service.declaration_kinds(context.schema_ref, family=family)
        items = []
        for kind in kinds:
            shape = self._service.declaration(context.schema_ref, kind)
            insert = _visible_text(shape.starter_tokens)
            if insert is None:
                raise CompletionContextError("unmodeled-starter", kind)
            items.append(
                CompletionItem(
                    metadata_id=shape.kind,
                    kind="declaration-starter",
                    insert_text=insert,
                    display_text=insert,
                    authority="e4-compiler-schema",
                    documentation=shape.documentation,
                    expected_name_shape=shape.identity_shape,
                    semantic_order="preserve",
                )
            )
        return CompletionSet("current-accepted", tuple(items), "preserve")

    def header_arguments(
        self,
        context: CurrentCompletionContext,
        declaration_kind: str,
    ) -> CompletionSet:
        shape = self._service.declaration(context.schema_ref, declaration_kind)
        items = []
        for argument in shape.header_arguments:
            self._service.value_shape(context.schema_ref, argument.value_shape)
            insert = _visible_text(argument.visible_tokens)
            if insert is None:
                raise CompletionContextError("unmodeled-header-token", argument.argument_id)
            items.append(
                CompletionItem(
                    metadata_id=argument.argument_id,
                    kind="header-argument",
                    insert_text=insert,
                    display_text=insert,
                    authority="e4-compiler-schema",
                    documentation=argument.documentation,
                    expected_value_shape=argument.value_shape,
                    semantic_order="preserve",
                )
            )
        return CompletionSet("current-accepted", tuple(items), "preserve")

    def body_slots(
        self,
        context: CurrentCompletionContext,
        declaration_kind: str,
    ) -> CompletionSet:
        shape = self._service.declaration(context.schema_ref, declaration_kind)
        if shape.body_semantic_order not in {"preserve", "unordered"}:
            raise CompletionContextError(
                "unknown-semantic-order",
                f"{shape.kind}: {shape.body_semantic_order}",
            )
        # Client ranking is allowed only when the compiler explicitly says unordered.
        # The E4 representative metadata says preserve, so this projection never sorts.
        items = tuple(_item_from_slot(self._service, context.schema_ref, slot) for slot in shape.body_slots)
        return CompletionSet("current-accepted", items, shape.body_semantic_order)

    def value_candidates(
        self,
        context: CurrentCompletionContext,
        shape_id: str,
    ) -> CompletionSet | CompletionUnavailable:
        shape = self._service.value_shape(context.schema_ref, shape_id)
        if not shape.closed_values:
            return CompletionUnavailable(
                "compiler-value-vocabulary-not-exported",
                f"{shape_id} has no closed values in E4 metadata",
                "e4-compiler-schema",
            )
        items = tuple(
            CompletionItem(
                metadata_id=value,
                kind="closed-value",
                insert_text=value,
                display_text=value,
                authority="e4-compiler-schema",
                documentation=shape.documentation,
                expected_value_shape=shape.shape_id,
            )
            for value in shape.closed_values
        )
        return CompletionSet("current-accepted", items, "preserve")

    def modifier_candidates(
        self,
        context: CurrentCompletionContext,
        declaration_kind: str,
        slot_id: str,
    ) -> CompletionSet:
        declaration = self._service.declaration(context.schema_ref, declaration_kind)
        slot = _slot(declaration, slot_id)
        modifiers = self._service.modifiers(context.schema_ref, slot.modifiers)
        items = []
        for modifier in modifiers:
            if modifier.value_shape is not None:
                self._service.value_shape(context.schema_ref, modifier.value_shape)
            insert = _visible_text(modifier.visible_tokens)
            if insert is None:
                raise CompletionContextError("unmodeled-modifier-token", modifier.modifier_id)
            items.append(
                CompletionItem(
                    metadata_id=modifier.modifier_id,
                    kind="modifier",
                    insert_text=insert,
                    display_text=insert,
                    authority="e4-compiler-schema",
                    documentation=modifier.documentation,
                    expected_value_shape=modifier.value_shape,
                )
            )
        return CompletionSet("current-accepted", tuple(items), slot.semantic_order)

    def nested_structure(
        self,
        context: CurrentCompletionContext,
        declaration_kind: str,
        slot_id: str,
    ) -> CompletionSet | CompletionUnavailable:
        declaration = self._service.declaration(context.schema_ref, declaration_kind)
        slot = _slot(declaration, slot_id)
        if slot.nested_schema is None:
            return CompletionUnavailable(
                "no-nested-schema",
                f"{declaration_kind}.{slot_id} has no nested schema",
                "e4-compiler-schema",
            )
        return self.sublanguage_structure(context, slot.nested_schema)

    def sublanguage_structure(
        self,
        context: CurrentCompletionContext,
        name: str,
    ) -> CompletionSet:
        schema = self._service.sublanguage(context.schema_ref, name)
        if not schema.closed_vocabulary:
            raise CompletionContextError("open-sublanguage-vocabulary", name)
        items = tuple(
            CompletionItem(
                metadata_id=alternative.alternative_id,
                kind="sublanguage-structure",
                insert_text=None,
                display_text=alternative.syntax,
                authority="e4-compiler-schema",
                documentation=schema.documentation,
                nested_schema=alternative.child_schema,
                semantic_order="preserve",
            )
            for alternative in schema.alternatives
        )
        return CompletionSet("current-accepted", items, "preserve")

    def sublanguage_vocabulary(
        self,
        context: CurrentCompletionContext,
        name: str,
    ) -> CompletionUnavailable:
        schema = self._service.sublanguage(context.schema_ref, name)
        if not schema.closed_vocabulary:
            raise CompletionContextError("open-sublanguage-vocabulary", name)
        # E4 intentionally exports the closed structural contract and authority, not
        # the concrete profile/UI/test vocabularies. E6 must not fill that omission.
        return CompletionUnavailable(
            "closed-vocabulary-not-exported",
            f"{name}: {schema.vocabulary_authority}",
            "e4-compiler-schema",
        )

    def migration_completion(
        self,
        source: str,
        offset: int,
        context: E5MigrationCompletionContext,
    ) -> CompletionSet | CompletionUnavailable:
        self._require_exact_e5_context(source, context)
        try:
            plan = e5.plan_migration(
                source,
                source_version=context.source_version,
                old_version=context.old_version,
                target_version=context.target_version,
                source_schema_fingerprint=context.source_schema_fingerprint,
                target_schema_fingerprint=context.target_schema_fingerprint,
                expected_source_fingerprint=context.expected_source_fingerprint,
            )
        except e5.MigrationError as error:
            diagnostic = error.diagnostic
            return CompletionUnavailable(
                f"e5-{diagnostic.code}",
                diagnostic.message,
                "e5-migrator",
            )

        if not plan.edits:
            return CompletionUnavailable(
                "e5-no-modeled-migration-edit",
                "explicit E5 context produced no migration edit; no candidate syntax is guessed",
                "e5-migrator",
            )

        matching = tuple(edit for edit in plan.edits if edit.start <= offset <= edit.end)
        if len(matching) != 1:
            return CompletionUnavailable(
                "e5-no-unique-edit-at-offset",
                f"expected one modeled migration edit at offset {offset}, got {len(matching)}",
                "e5-migrator",
            )
        edit = matching[0]

        # E5 exposes which migrated rows can be replayed through the E3 candidate
        # shape without inventing facts. Any other E5 edit remains unavailable here;
        # this automatically preserves the documented index/dead-letter/schedule/
        # sync shape gaps and modifier-sensitive field gaps.
        if edit.row_id not in plan.e3_replayed_rows:
            return CompletionUnavailable(
                "e5-target-shape-not-fact-complete",
                f"{edit.row_id} is not in E5's E3-replayed fact-complete set",
                "e5-migrator",
            )

        item = CompletionItem(
            metadata_id=edit.row_id,
            kind="migration-replacement",
            insert_text=edit.replacement,
            display_text=f"E5 migration: {edit.row_id}",
            authority="e5-migrator",
            documentation="docs/m16-5-e5-migration-report.md",
            semantic_order="preserve",
        )
        return CompletionSet("explicit-e5-target", (item,), "preserve")

    @staticmethod
    def _require_exact_e5_context(source: str, context: E5MigrationCompletionContext) -> None:
        if context.old_schema_id != e5.OLD_SCHEMA_ID:
            raise CompletionContextError("unknown-e5-old-schema-id", context.old_schema_id)
        if context.target_schema_id != e5.TARGET_SCHEMA_ID:
            raise CompletionContextError("unknown-e5-target-schema-id", context.target_schema_id)
        if context.old_version != e5.OLD_VERSION or context.target_version != e5.TARGET_VERSION:
            raise CompletionContextError(
                "unknown-e5-version-pair",
                f"{context.old_version} -> {context.target_version}",
            )
        if context.old_schema_fingerprint != e5.OLD_SCHEMA_FINGERPRINT:
            raise CompletionContextError("stale-e5-old-fingerprint", context.old_schema_fingerprint)
        if context.target_schema_fingerprint != e5.TARGET_SCHEMA_FINGERPRINT:
            raise CompletionContextError("stale-e5-target-fingerprint", context.target_schema_fingerprint)

        expected_source_schema_id = (
            e5.OLD_SCHEMA_ID if context.source_version == e5.OLD_VERSION
            else e5.TARGET_SCHEMA_ID if context.source_version == e5.TARGET_VERSION
            else None
        )
        expected_source_fingerprint = (
            e5.OLD_SCHEMA_FINGERPRINT if context.source_version == e5.OLD_VERSION
            else e5.TARGET_SCHEMA_FINGERPRINT if context.source_version == e5.TARGET_VERSION
            else None
        )
        if expected_source_schema_id is None or expected_source_fingerprint is None:
            raise CompletionContextError("unknown-e5-source-version", context.source_version)
        if context.source_schema_id != expected_source_schema_id:
            raise CompletionContextError(
                "e5-source-schema-id-mismatch",
                context.source_schema_id,
            )
        if context.source_schema_fingerprint != expected_source_fingerprint:
            raise CompletionContextError(
                "e5-source-schema-fingerprint-mismatch",
                context.source_schema_fingerprint,
            )
        actual_fingerprint = e5.source_fingerprint(source)
        if context.expected_source_fingerprint != actual_fingerprint:
            raise CompletionContextError(
                "stale-e5-source-fingerprint",
                context.expected_source_fingerprint,
            )
