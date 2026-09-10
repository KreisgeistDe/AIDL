"""M16.5 E7 bounded diagnostics consumer experiment.

Experimental evidence only.  This module does not parse or accept AIDL source, replace
production diagnostics, classify compatibility, or authorize migration writes.  Current
structural facts come only from the exact E4 compiler schema service.  Migration facts
come only from an explicit exact E5 context and E5's dry-run plan.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import tools.m16_5_e4_introspection as e4
import tools.m16_5_e5_migration as e5


class DiagnosticsSchemaService(Protocol):
    def schema_ref(self) -> e4.SchemaRef: ...
    def declaration(self, ref: e4.SchemaRef, kind: str) -> e4.DeclarationShape: ...
    def sublanguage(self, ref: e4.SchemaRef, name: str) -> e4.SublanguageShape: ...
    def value_shape(self, ref: e4.SchemaRef, shape_id: str) -> e4.ValueShape: ...
    def modifiers(self, ref: e4.SchemaRef, modifier_ids: tuple[str, ...]) -> tuple[e4.ModifierShape, ...]: ...


@dataclass(frozen=True)
class CurrentDiagnosticsContext:
    schema_ref: e4.SchemaRef


@dataclass(frozen=True)
class E5MigrationDiagnosticsContext:
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
    language_state: str


@dataclass(frozen=True)
class SourceLocation:
    start: int
    end: int
    line: int
    column: int


@dataclass(frozen=True)
class StructuralDiagnostic:
    code: str
    phase: str
    severity: str
    message: str
    location: SourceLocation
    expected: str | None
    authority: str
    documentation: str | None = None
    replacement: str | None = None
    compatibility_class: None = None
    migration_authorized: bool = False


@dataclass(frozen=True)
class CompilerSemanticIntent:
    """Semantic diagnostic supplied by compiler/M7-owned logic, never invented by E7."""

    code: str
    phase: str
    severity: str
    message: str
    expected: str | None = None
    documentation: str | None = None


@dataclass(frozen=True)
class SemanticDiagnosticProjection:
    code: str
    phase: str
    severity: str
    message: str
    location: SourceLocation
    expected: str | None
    documentation: str | None
    source_context: str
    authority: str = "compiler-semantic-intent"
    compatibility_class: None = None
    migration_authorized: bool = False


@dataclass(frozen=True)
class DiagnosticUnavailable:
    reason: str
    detail: str
    authority: str


class DiagnosticsContextError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _location(source: str, start: int, end: int | None = None) -> SourceLocation:
    end = start if end is None else end
    if start < 0 or end < start or end > len(source):
        raise DiagnosticsContextError("AIDL-S008", f"invalid source range {start}:{end}")
    line = source.count("\n", 0, start) + 1
    previous_newline = source.rfind("\n", 0, start)
    column = start + 1 if previous_newline < 0 else start - previous_newline
    return SourceLocation(start, end, line, column)


def _slot(shape: e4.DeclarationShape, slot_id: str) -> e4.BodySlot | None:
    return next((slot for slot in shape.body_slots if slot.slot_id == slot_id), None)


class ExperimentalDiagnosticsConsumer:
    """Non-authoritative deterministic projection over E4 structural and E5 migration evidence."""

    def __init__(self, service: DiagnosticsSchemaService | None = None):
        self._service = service or e4.CompilerSchemaService()

    def compiler_schema_ref(self) -> e4.SchemaRef:
        return self._service.schema_ref()

    @staticmethod
    def order(diagnostics: tuple[StructuralDiagnostic, ...]) -> tuple[StructuralDiagnostic, ...]:
        """Order only E7-owned diagnostics; production diagnostics are never reordered here."""
        severity_rank = {"error": 0, "warning": 1, "info": 2}
        return tuple(
            sorted(
                diagnostics,
                key=lambda item: (
                    item.location.start,
                    item.phase,
                    severity_rank.get(item.severity, 99),
                    item.code,
                    item.message,
                ),
            )
        )

    def unknown_body_slot(
        self,
        source: str,
        start: int,
        end: int,
        context: CurrentDiagnosticsContext,
        declaration_kind: str,
        observed_slot_id: str,
    ) -> StructuralDiagnostic | None:
        shape = self._declaration(context, declaration_kind)
        if _slot(shape, observed_slot_id) is not None:
            return None
        expected = ", ".join(slot.slot_id for slot in shape.body_slots)
        return StructuralDiagnostic(
            "AIDL-S003",
            "structural-schema",
            "error",
            f"unknown structural slot {observed_slot_id!r} for {declaration_kind}",
            _location(source, start, end),
            expected,
            "e4-compiler-schema",
            shape.documentation,
        )

    def wrong_closed_value(
        self,
        source: str,
        start: int,
        end: int,
        context: CurrentDiagnosticsContext,
        shape_id: str,
        observed_value: str,
    ) -> StructuralDiagnostic | DiagnosticUnavailable | None:
        shape = self._value_shape(context, shape_id)
        if not shape.closed_values:
            return DiagnosticUnavailable(
                "value-validation-not-exported",
                f"{shape_id} has no closed compiler-owned values in E4 metadata",
                "e4-compiler-schema",
            )
        if observed_value in shape.closed_values:
            return None
        return StructuralDiagnostic(
            "AIDL-S004",
            "structural-schema",
            "error",
            f"invalid value {observed_value!r} for {shape_id}",
            _location(source, start, end),
            " | ".join(shape.closed_values),
            "e4-compiler-schema",
            shape.documentation,
        )

    def invalid_modifier(
        self,
        source: str,
        start: int,
        end: int,
        context: CurrentDiagnosticsContext,
        declaration_kind: str,
        slot_id: str,
        observed_modifier: str,
    ) -> StructuralDiagnostic | DiagnosticUnavailable | None:
        shape = self._declaration(context, declaration_kind)
        slot = _slot(shape, slot_id)
        if slot is None:
            return DiagnosticUnavailable(
                "unmodeled-body-slot",
                f"{declaration_kind}.{slot_id} is not exported by E4",
                "e4-compiler-schema",
            )
        modifiers = self._modifiers(context, slot.modifiers)
        known = tuple(item.modifier_id for item in modifiers)
        if observed_modifier in known:
            return None
        if not known:
            return DiagnosticUnavailable(
                "modifier-vocabulary-not-exported",
                f"{declaration_kind}.{slot_id} has no exported modifier vocabulary",
                "e4-compiler-schema",
            )
        return StructuralDiagnostic(
            "AIDL-S005",
            "structural-schema",
            "error",
            f"invalid modifier {observed_modifier!r} for {declaration_kind}.{slot_id}",
            _location(source, start, end),
            " | ".join(known),
            "e4-compiler-schema",
            slot.documentation,
        )

    def invalid_nesting(
        self,
        source: str,
        start: int,
        end: int,
        context: CurrentDiagnosticsContext,
        declaration_kind: str,
        slot_id: str,
        observed_nested_schema: str,
    ) -> StructuralDiagnostic | DiagnosticUnavailable | None:
        shape = self._declaration(context, declaration_kind)
        slot = _slot(shape, slot_id)
        if slot is None:
            return DiagnosticUnavailable(
                "unmodeled-body-slot",
                f"{declaration_kind}.{slot_id} is not exported by E4",
                "e4-compiler-schema",
            )
        if slot.nested_schema is None:
            return DiagnosticUnavailable(
                "no-nested-schema",
                f"{declaration_kind}.{slot_id} has no nested schema in E4",
                "e4-compiler-schema",
            )
        self._sublanguage(context, slot.nested_schema)
        if observed_nested_schema == slot.nested_schema:
            return None
        return StructuralDiagnostic(
            "AIDL-S005",
            "structural-schema",
            "error",
            f"invalid nested schema {observed_nested_schema!r} for {declaration_kind}.{slot_id}",
            _location(source, start, end),
            slot.nested_schema,
            "e4-compiler-schema",
            slot.documentation,
        )

    def sublanguage_vocabulary(
        self,
        context: CurrentDiagnosticsContext,
        name: str,
    ) -> DiagnosticUnavailable:
        schema = self._sublanguage(context, name)
        if not schema.closed_vocabulary:
            raise DiagnosticsContextError("AIDL-S008", f"unexpected open sublanguage vocabulary: {name}")
        return DiagnosticUnavailable(
            "closed-vocabulary-not-exported",
            f"{name}: {schema.vocabulary_authority}",
            "e4-compiler-schema",
        )

    def migration_diagnostic(
        self,
        source: str,
        offset: int,
        context: E5MigrationDiagnosticsContext,
    ) -> StructuralDiagnostic | DiagnosticUnavailable | None:
        self._require_exact_e5_context(source, context)
        if context.language_state == "legacy":
            if context.source_version != e5.OLD_VERSION:
                return DiagnosticUnavailable(
                    "explicit-language-state-mismatch",
                    "legacy state requires the explicit old E5 source version",
                    "e5-migrator",
                )
            return None
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
            start = max(0, min(diagnostic.offset, len(source)))
            end = min(len(source), start + 1)
            return StructuralDiagnostic(
                diagnostic.code,
                "migration",
                "error",
                diagnostic.message,
                _location(source, start, end),
                None,
                "e5-migrator",
                "docs/m16-5-e5-migration-report.md",
            )
        if not plan.edits:
            return None
        matching = tuple(edit for edit in plan.edits if edit.start <= offset <= edit.end)
        if len(matching) != 1:
            return DiagnosticUnavailable(
                "e5-no-unique-edit-at-offset",
                f"expected one modeled E5 edit at offset {offset}, got {len(matching)}",
                "e5-migrator",
            )
        edit = matching[0]
        if edit.row_id not in plan.e3_replayed_rows:
            return DiagnosticUnavailable(
                "e5-target-shape-not-fact-complete",
                f"{edit.row_id} is not in E5's E3-replayed fact-complete set",
                "e5-migrator",
            )
        if context.language_state == "coexistence":
            code, severity, message = (
                "AIDL-S006",
                "warning",
                "legacy spelling is deprecated in the explicit E5 coexistence prototype context",
            )
        else:
            code, severity, message = (
                "AIDL-S007",
                "error",
                "legacy spelling is invalid in the explicit E5 target prototype context",
            )
        return StructuralDiagnostic(
            code,
            "migration",
            severity,
            message,
            _location(source, edit.start, edit.end),
            "explicit E5 migration replacement",
            "e5-migrator",
            "docs/m16-5-e2-compatibility-migration-contract.md",
            replacement=edit.replacement,
        )

    def equivalent_semantic_intent(
        self,
        old_source: str,
        candidate_source: str,
        old_offset: int,
        context: E5MigrationDiagnosticsContext,
        intent: CompilerSemanticIntent,
    ) -> tuple[SemanticDiagnosticProjection, SemanticDiagnosticProjection] | DiagnosticUnavailable:
        self._require_exact_e5_context(old_source, context)
        if context.source_version != e5.OLD_VERSION:
            return DiagnosticUnavailable(
                "equivalence-requires-old-source-context",
                "semantic projection starts from the explicit E5 old source snapshot",
                "e5-migrator",
            )
        try:
            plan = e5.plan_migration(
                old_source,
                source_version=context.source_version,
                old_version=context.old_version,
                target_version=context.target_version,
                source_schema_fingerprint=context.source_schema_fingerprint,
                target_schema_fingerprint=context.target_schema_fingerprint,
                expected_source_fingerprint=context.expected_source_fingerprint,
            )
        except e5.MigrationError as error:
            return DiagnosticUnavailable(
                f"e5-{error.diagnostic.code}",
                error.diagnostic.message,
                "e5-migrator",
            )
        matching = tuple(edit for edit in plan.edits if edit.start <= old_offset <= edit.end)
        if len(matching) != 1:
            return DiagnosticUnavailable(
                "e5-no-unique-edit-at-offset",
                f"expected one modeled E5 edit at offset {old_offset}, got {len(matching)}",
                "e5-migrator",
            )
        edit = matching[0]
        if edit.row_id not in plan.e3_replayed_rows:
            return DiagnosticUnavailable(
                "e5-target-shape-not-fact-complete",
                f"{edit.row_id} is not in E5's E3-replayed fact-complete set",
                "e5-migrator",
            )
        migrated = e5.apply_plan(old_source, plan).source
        if migrated != candidate_source:
            return DiagnosticUnavailable(
                "candidate-snapshot-mismatch",
                "candidate snapshot must be exactly the E5 dry-run target",
                "e5-migrator",
            )
        relocation = next((item for item in plan.relocations if item.anchor_id == edit.anchor_id), None)
        if relocation is None:
            return DiagnosticUnavailable(
                "missing-e5-relocation",
                edit.anchor_id,
                "e5-migrator",
            )
        old_projection = SemanticDiagnosticProjection(
            intent.code,
            intent.phase,
            intent.severity,
            intent.message,
            _location(old_source, edit.start, edit.end),
            intent.expected,
            intent.documentation,
            "explicit-e5-old",
        )
        candidate_projection = SemanticDiagnosticProjection(
            intent.code,
            intent.phase,
            intent.severity,
            intent.message,
            _location(candidate_source, relocation.new_start, relocation.new_end),
            intent.expected,
            intent.documentation,
            "explicit-e5-target",
        )
        return old_projection, candidate_projection

    def _declaration(self, context: CurrentDiagnosticsContext, kind: str) -> e4.DeclarationShape:
        try:
            return self._service.declaration(context.schema_ref, kind)
        except e4.SchemaLookupError as error:
            raise DiagnosticsContextError("AIDL-S008", f"{error.reason}: {error.detail}") from error

    def _value_shape(self, context: CurrentDiagnosticsContext, shape_id: str) -> e4.ValueShape:
        try:
            return self._service.value_shape(context.schema_ref, shape_id)
        except e4.SchemaLookupError as error:
            raise DiagnosticsContextError("AIDL-S008", f"{error.reason}: {error.detail}") from error

    def _modifiers(self, context: CurrentDiagnosticsContext, modifier_ids: tuple[str, ...]) -> tuple[e4.ModifierShape, ...]:
        try:
            return self._service.modifiers(context.schema_ref, modifier_ids)
        except e4.SchemaLookupError as error:
            raise DiagnosticsContextError("AIDL-S008", f"{error.reason}: {error.detail}") from error

    def _sublanguage(self, context: CurrentDiagnosticsContext, name: str) -> e4.SublanguageShape:
        try:
            return self._service.sublanguage(context.schema_ref, name)
        except e4.SchemaLookupError as error:
            raise DiagnosticsContextError("AIDL-S008", f"{error.reason}: {error.detail}") from error

    @staticmethod
    def _require_exact_e5_context(source: str, context: E5MigrationDiagnosticsContext) -> None:
        if context.language_state not in {"legacy", "coexistence", "target"}:
            raise DiagnosticsContextError("AIDL-S008", f"unknown explicit language state {context.language_state!r}")
        if context.old_schema_id != e5.OLD_SCHEMA_ID or context.target_schema_id != e5.TARGET_SCHEMA_ID:
            raise DiagnosticsContextError("AIDL-S008", "unknown E5 schema identity")
        if context.old_version != e5.OLD_VERSION or context.target_version != e5.TARGET_VERSION:
            raise DiagnosticsContextError("AIDL-S008", "unknown or stale E5 version pair")
        if context.old_schema_fingerprint != e5.OLD_SCHEMA_FINGERPRINT:
            raise DiagnosticsContextError("AIDL-S008", "stale E5 old schema fingerprint")
        if context.target_schema_fingerprint != e5.TARGET_SCHEMA_FINGERPRINT:
            raise DiagnosticsContextError("AIDL-S008", "stale E5 target schema fingerprint")
        if context.source_version == e5.OLD_VERSION:
            expected_id = e5.OLD_SCHEMA_ID
            expected_schema_fingerprint = e5.OLD_SCHEMA_FINGERPRINT
        elif context.source_version == e5.TARGET_VERSION:
            expected_id = e5.TARGET_SCHEMA_ID
            expected_schema_fingerprint = e5.TARGET_SCHEMA_FINGERPRINT
        else:
            raise DiagnosticsContextError("AIDL-S008", f"unknown E5 source version {context.source_version!r}")
        if context.source_schema_id != expected_id:
            raise DiagnosticsContextError("AIDL-S008", "E5 source schema ID mismatch")
        if context.source_schema_fingerprint != expected_schema_fingerprint:
            raise DiagnosticsContextError("AIDL-S008", "E5 source schema fingerprint mismatch")
        if context.expected_source_fingerprint != e5.source_fingerprint(source):
            raise DiagnosticsContextError("AIDL-S008", "stale E5 source fingerprint")
