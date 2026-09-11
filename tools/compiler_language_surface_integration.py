"""Production integration for the frozen M10.1 language-surface model.

This module deliberately sits *after* the existing parser/typed compiler project
boundary. It reuses the compiler's project/typechecker evidence and the merged
``LanguageSurfaceBridge`` instead of defining another grammar, declaration
inventory, modifier table, or type system.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .compiler_diagnostics import CompilerAnalysis
    from .compiler_language_surface import (
        BridgeDiagnostic,
        Declaration,
        Document,
        LanguageSurfaceBridge,
        TypeRef as SurfaceTypeRef,
        _format_type as format_surface_type,
    )
    from .compiler_project import CompilerDeclarationName, CompilerProject
    from .compiler_typecheck import (
        TypeRef as CheckedTypeRef,
        TypeSyntaxError,
        _check_type as compiler_check_type,
        _resolve as compiler_resolve,
        collect_type_issues,
        parse_type,
        resolve_reference,
    )
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from compiler_diagnostics import CompilerAnalysis
    from compiler_language_surface import (
        BridgeDiagnostic,
        Declaration,
        Document,
        LanguageSurfaceBridge,
        TypeRef as SurfaceTypeRef,
        _format_type as format_surface_type,
    )
    from compiler_project import CompilerDeclarationName, CompilerProject
    from compiler_typecheck import (
        TypeRef as CheckedTypeRef,
        TypeSyntaxError,
        _check_type as compiler_check_type,
        _resolve as compiler_resolve,
        collect_type_issues,
        parse_type,
        resolve_reference,
    )


PRODUCTION_NORMALIZATION_VERSION = "aidl.m10.1-production/v2"
_ALWAYS_INTEGRATED = frozenset(
    {"alias", "opaque", "entity", "enum", "migration", "client", "consumer", "projection"}
)
_LOSSLESS_CANDIDATES = frozenset({"query", "mutation", "app"})
INTEGRATED_DECLARATION_KINDS = _ALWAYS_INTEGRATED | _LOSSLESS_CANDIDATES


@dataclass(frozen=True)
class ProductionLanguageSurface:
    """Canonical M10.1 evidence derived from real compiler project facts."""

    documents: tuple[Document, ...]
    diagnostics: tuple[BridgeDiagnostic, ...]
    type_issues: tuple[Any, ...]

    @property
    def declarations(self) -> tuple[Declaration, ...]:
        return tuple(
            declaration
            for document in self.documents
            for declaration in document.declarations
        )

    @property
    def ok(self) -> bool:
        return not self.type_issues and not any(
            diagnostic.severity == "error" for diagnostic in self.diagnostics
        )

    def semantic(self) -> dict[str, Any]:
        return {
            "normalization_version": PRODUCTION_NORMALIZATION_VERSION,
            "documents": [document.semantic() for document in self.documents],
        }

    def semantic_json(self) -> str:
        return json.dumps(
            self.semantic(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def semantic_hash(self) -> str:
        return "sha256:" + hashlib.sha256(
            self.semantic_json().encode("utf-8")
        ).hexdigest()


def _initial_surface_declaration(source: CompilerDeclarationName) -> Declaration:
    declaration, _ = LanguageSurfaceBridge().normalize_declaration(source.declaration.node)
    return declaration


def _surface_types(source: CompilerDeclarationName) -> tuple[SurfaceTypeRef, ...]:
    """Return contract-normalized types without requiring resolver evidence yet."""

    declaration = _initial_surface_declaration(source)
    values: list[SurfaceTypeRef] = []
    aliased = declaration.facts.get("aliased_type")
    if isinstance(aliased, SurfaceTypeRef):
        values.append(aliased)
    for slot in declaration.body_slots:
        if isinstance(slot.value, SurfaceTypeRef):
            values.append(slot.value)
    if declaration.result_type is not None:
        values.append(declaration.result_type)
    return tuple(values)


def _field_type(target: CompilerDeclarationName, projection: str) -> str | None:
    """Return a typechecker-parsable field type from canonical body-slot facts."""

    declaration = _initial_surface_declaration(target)
    for slot in declaration.body_slots:
        if slot.slot_id != "field" or slot.name != projection:
            continue
        if not isinstance(slot.value, SurfaceTypeRef):
            return None
        raw = format_surface_type(slot.value)
        try:
            parse_type(raw)
        except TypeSyntaxError:
            return None
        return raw
    return None


def _entity_matches(
    project: CompilerProject,
    source: CompilerDeclarationName,
    reference: str,
) -> tuple[CompilerDeclarationName, ...]:
    return tuple(
        item
        for item in compiler_resolve(project, source, reference)
        if item.declaration.kind == "entity"
    )


def _entity_id_projection(
    project: CompilerProject,
    source: CompilerDeclarationName,
    target_reference: str,
) -> tuple[dict[str, tuple[str, str, str]], list[BridgeDiagnostic]]:
    evidence: dict[str, tuple[str, str, str]] = {}
    diagnostics: list[BridgeDiagnostic] = []
    projection = "id"
    surface_reference = f"{target_reference}.{projection}"
    matches = _entity_matches(project, source, target_reference)
    if len(matches) != 1:
        diagnostics.append(
            BridgeDiagnostic(
                "AIDL-N012",
                f"reference projection {surface_reference} needs exactly one resolved entity; found {len(matches)}",
            )
        )
        return evidence, diagnostics
    resolved_type = _field_type(matches[0], projection)
    if resolved_type is None:
        diagnostics.append(
            BridgeDiagnostic(
                "AIDL-N012",
                f"reference projection {surface_reference} has no typechecker-backed field evidence",
            )
        )
        return evidence, diagnostics
    target_name = matches[0].declaration.name or target_reference
    evidence[surface_reference] = (target_name, projection, resolved_type)
    return evidence, diagnostics


def _projection_for_checked_type(
    project: CompilerProject,
    source: CompilerDeclarationName,
    checked: CheckedTypeRef,
) -> tuple[dict[str, tuple[str, str, str]], list[BridgeDiagnostic]]:
    evidence: dict[str, tuple[str, str, str]] = {}
    diagnostics: list[BridgeDiagnostic] = []

    if checked.kind in {"nullable", "list", "set", "map", "named"}:
        for argument in checked.args:
            child_evidence, child_diagnostics = _projection_for_checked_type(
                project, source, argument
            )
            evidence.update(child_evidence)
            diagnostics.extend(child_diagnostics)
        return evidence, diagnostics

    if checked.kind == "entity-id" and checked.name:
        return _entity_id_projection(project, source, checked.name)

    if checked.kind == "ref" and checked.name:
        resolution = resolve_reference(project, source, checked.name)
        if resolution is None:
            diagnostics.append(
                BridgeDiagnostic(
                    "AIDL-N012",
                    f"reference {checked.name} has no unique compiler-owned entity/projection resolution",
                )
            )
            return evidence, diagnostics
        if resolution.kind == "projection":
            target_reference, projection = checked.name.rsplit(".", 1)
            target_matches = _entity_matches(project, source, target_reference)
            target_name = (
                target_matches[0].declaration.name
                if len(target_matches) == 1 and target_matches[0].declaration.name
                else target_reference
            )
            evidence[checked.name] = (
                target_name,
                projection,
                resolution.projected_type or "",
            )
    return evidence, diagnostics


def _projection_evidence(
    project: CompilerProject,
    source: CompilerDeclarationName,
) -> tuple[
    dict[str, tuple[str, str, str]],
    list[BridgeDiagnostic],
    list[Any],
]:
    """Use canonical token normalization, then existing Core typechecker logic."""

    evidence: dict[str, tuple[str, str, str]] = {}
    diagnostics: list[BridgeDiagnostic] = []
    type_issues: list[Any] = []
    for surface_type in _surface_types(source):
        raw = format_surface_type(surface_type)
        try:
            checked = parse_type(raw)
        except TypeSyntaxError:
            continue
        type_issues.extend(compiler_check_type(project, source, raw))
        item_evidence, item_diagnostics = _projection_for_checked_type(
            project, source, checked
        )
        evidence.update(item_evidence)
        diagnostics.extend(item_diagnostics)
    return evidence, diagnostics, type_issues


def _candidate_is_lossless(
    source: CompilerDeclarationName,
) -> tuple[bool, tuple[BridgeDiagnostic, ...]]:
    """Admit query/mutation/app only when frozen facts cover the complete shape."""

    if source.declaration.kind in _ALWAYS_INTEGRATED:
        return True, ()
    if source.declaration.kind not in _LOSSLESS_CANDIDATES:
        return False, ()
    declaration, diagnostics = LanguageSurfaceBridge().normalize_declaration(
        source.declaration.node
    )
    reasons: list[str] = []
    if declaration.facts.get("legacy_parameters"):
        reasons.append("legacy operation parameters are not frozen as canonical HeaderArgs yet")
    if any(item.code == "AIDL-N010" for item in diagnostics):
        reasons.append("one or more body clauses are not normalized by the frozen contract")
    if reasons:
        name = source.fully_qualified_name or source.declaration.name or "<unnamed>"
        return False, (
            BridgeDiagnostic(
                "AIDL-N013",
                f"{source.declaration.kind} {name} is outside lossless production normalization: {'; '.join(reasons)}",
            ),
        )
    return True, ()


def _type_issue_key(issue: Any) -> tuple[Path, str, str]:
    return (issue.source_path, issue.subject_kind, issue.subject_name)


def _type_issue_identity(issue: Any) -> tuple[Any, ...]:
    return (
        issue.code,
        issue.source_path,
        getattr(issue.location, "offset", -1),
        issue.subject_kind,
        issue.subject_name,
        issue.message,
    )


def normalize_compiler_analysis(analysis: CompilerAnalysis) -> ProductionLanguageSurface:
    """Normalize the lossless production slice from an existing compiler analysis.

    Parser nodes and project resolution stay authoritative for the current source
    version. Type parsing/checking and reference candidates are supplied by the
    existing Core compiler helpers; ``LanguageSurfaceBridge`` remains the only
    declaration/body/modifier contract projection.
    """

    project = analysis.project
    item_by_node: dict[int, CompilerDeclarationName] = {}
    diagnostics: list[BridgeDiagnostic] = []
    for item in project.declaration_names:
        admitted, admission_diagnostics = _candidate_is_lossless(item)
        diagnostics.extend(admission_diagnostics)
        if admitted:
            item_by_node[id(item.declaration.node)] = item

    integrated_keys = {
        (
            item.document.source_path,
            item.declaration.kind,
            item.declaration.name or "<unnamed>",
        )
        for item in item_by_node.values()
    }
    type_issues: list[Any] = [
        issue
        for issue in collect_type_issues(project)
        if _type_issue_key(issue) in integrated_keys
    ]

    documents: list[Document] = []
    for compiler_document in project.documents:
        declarations: list[Declaration] = []
        for compiler_declaration in compiler_document.declarations:
            source = item_by_node.get(id(compiler_declaration.node))
            if source is None:
                continue
            (
                projection_evidence,
                projection_diagnostics,
                normalized_type_issues,
            ) = _projection_evidence(project, source)
            bridge = LanguageSurfaceBridge(reference_projections=projection_evidence)
            declaration, declaration_diagnostics = bridge.normalize_declaration(
                compiler_declaration.node
            )
            declarations.append(declaration)
            diagnostics.extend(projection_diagnostics)
            diagnostics.extend(declaration_diagnostics)
            type_issues.extend(normalized_type_issues)
        if declarations:
            module = (
                compiler_document.module.name
                if compiler_document.module is not None
                else None
            )
            documents.append(
                Document(
                    module=module,
                    imports=tuple(
                        import_.name
                        for import_ in compiler_document.imports
                        if import_.name is not None
                    ),
                    declarations=tuple(declarations),
                )
            )

    unique_type_issues: list[Any] = []
    seen_type_issues: set[tuple[Any, ...]] = set()
    for issue in type_issues:
        identity = _type_issue_identity(issue)
        if identity in seen_type_issues:
            continue
        seen_type_issues.add(identity)
        unique_type_issues.append(issue)

    diagnostics.sort(key=lambda item: (item.code, item.message, item.severity))
    return ProductionLanguageSurface(
        documents=tuple(documents),
        diagnostics=tuple(diagnostics),
        type_issues=tuple(unique_type_issues),
    )
