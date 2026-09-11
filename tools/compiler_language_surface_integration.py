"""Production integration for the frozen M10.1 language-surface model.

This module deliberately sits *after* the existing parser/typed compiler project
boundary.  It reuses the compiler's project/typechecker evidence and the merged
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
    )
    from .compiler_project import CompilerDeclarationName, CompilerProject
    from .compiler_typecheck import (
        TypeRef as CheckedTypeRef,
        TypeSyntaxError,
        _field as compiler_field,
        _resolve as compiler_resolve,
        collect_type_issues,
        parse_type,
    )
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from compiler_diagnostics import CompilerAnalysis
    from compiler_language_surface import (
        BridgeDiagnostic,
        Declaration,
        Document,
        LanguageSurfaceBridge,
        TypeRef as SurfaceTypeRef,
    )
    from compiler_project import CompilerDeclarationName, CompilerProject
    from compiler_typecheck import (
        TypeRef as CheckedTypeRef,
        TypeSyntaxError,
        _field as compiler_field,
        _resolve as compiler_resolve,
        collect_type_issues,
        parse_type,
    )


PRODUCTION_NORMALIZATION_VERSION = "aidl.m10.1-production/v1"
# This first production slice is intentionally limited to frozen surfaces that
# are already losslessly represented by both the existing parser and bridge.
INTEGRATED_DECLARATION_KINDS = frozenset(
    {"alias", "opaque", "entity", "enum", "migration", "client", "consumer", "projection"}
)


@dataclass(frozen=True)
class ProductionLanguageSurface:
    """Canonical M10.1 evidence derived from real compiler project facts."""

    documents: tuple[Document, ...]
    diagnostics: tuple[BridgeDiagnostic, ...]
    type_issues: tuple[Any, ...]

    @property
    def declarations(self) -> tuple[Declaration, ...]:
        return tuple(declaration for document in self.documents for declaration in document.declarations)

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
        return "sha256:" + hashlib.sha256(self.semantic_json().encode("utf-8")).hexdigest()


def _normalize_type_text(raw: str) -> str:
    return " ".join(raw.split()).replace(" . ", ".").replace(". ", ".").replace(" .", ".")


def _field_type(target: CompilerDeclarationName, projection: str) -> str | None:
    """Return a typechecker-parsable entity field type for one projection."""

    for child in target.declaration.node.children:
        field = compiler_field(child)
        if field is None or field[0] != projection:
            continue
        raw = _normalize_type_text(field[1])
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
        target_reference = checked.name
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

    if checked.kind == "ref" and checked.name and "." in checked.name:
        # A dotted legacy ref may be a fully qualified entity. Prefer that exact
        # compiler resolution before interpreting the final segment as a field
        # projection; this avoids inventing a new dotted-name ambiguity rule.
        if len(_entity_matches(project, source, checked.name)) == 1:
            return evidence, diagnostics
        target_reference, projection = checked.name.rsplit(".", 1)
        matches = _entity_matches(project, source, target_reference)
        if len(matches) != 1:
            diagnostics.append(
                BridgeDiagnostic(
                    "AIDL-N012",
                    f"reference projection {checked.name} needs exactly one resolved entity; found {len(matches)}",
                )
            )
            return evidence, diagnostics
        resolved_type = _field_type(matches[0], projection)
        if resolved_type is None:
            diagnostics.append(
                BridgeDiagnostic(
                    "AIDL-N012",
                    f"reference projection {checked.name} has no typechecker-backed field evidence",
                )
            )
            return evidence, diagnostics
        target_name = matches[0].declaration.name or target_reference
        evidence[checked.name] = (target_name, projection, resolved_type)
    return evidence, diagnostics


def _projection_evidence(
    project: CompilerProject,
    source: CompilerDeclarationName,
) -> tuple[dict[str, tuple[str, str, str]], list[BridgeDiagnostic]]:
    evidence: dict[str, tuple[str, str, str]] = {}
    diagnostics: list[BridgeDiagnostic] = []
    node = source.declaration.node

    raw_types: list[str] = []
    if source.declaration.kind in {"alias", "opaque"}:
        raw = node.attrs.get("type")
        if isinstance(raw, str) and raw.strip():
            raw_types.append(raw.strip())
    if source.declaration.kind == "entity":
        for child in node.children:
            field = compiler_field(child)
            if field is not None:
                raw_types.append(field[1])

    for raw in raw_types:
        try:
            checked = parse_type(raw)
        except TypeSyntaxError:
            # The existing typechecker owns the stable AIDL-T001 diagnostic.
            continue
        item_evidence, item_diagnostics = _projection_for_checked_type(
            project, source, checked
        )
        evidence.update(item_evidence)
        diagnostics.extend(item_diagnostics)
    return evidence, diagnostics


def _type_issue_key(issue: Any) -> tuple[Path, str, str]:
    return (issue.source_path, issue.subject_kind, issue.subject_name)


def normalize_compiler_analysis(analysis: CompilerAnalysis) -> ProductionLanguageSurface:
    """Normalize the supported production slice from an existing compiler analysis.

    Parser nodes and project resolution stay authoritative for the current source
    version.  Type syntax and reference candidates are taken from the existing
    Core typechecker helpers; the frozen language-surface contract remains the
    only declaration/body/modifier schema through ``LanguageSurfaceBridge``.
    """

    project = analysis.project
    item_by_node = {
        id(item.declaration.node): item
        for item in project.declaration_names
        if item.declaration.kind in INTEGRATED_DECLARATION_KINDS
    }
    integrated_keys = {
        (item.document.source_path, item.declaration.kind, item.declaration.name or "<unnamed>")
        for item in item_by_node.values()
    }
    type_issues = tuple(
        issue
        for issue in collect_type_issues(project)
        if _type_issue_key(issue) in integrated_keys
    )

    documents: list[Document] = []
    diagnostics: list[BridgeDiagnostic] = []
    for compiler_document in project.documents:
        declarations: list[Declaration] = []
        for compiler_declaration in compiler_document.declarations:
            source = item_by_node.get(id(compiler_declaration.node))
            if source is None:
                continue
            projection_evidence, projection_diagnostics = _projection_evidence(
                project, source
            )
            bridge = LanguageSurfaceBridge(reference_projections=projection_evidence)
            declaration, declaration_diagnostics = bridge.normalize_declaration(
                compiler_declaration.node
            )
            declarations.append(declaration)
            diagnostics.extend(projection_diagnostics)
            diagnostics.extend(declaration_diagnostics)
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

    return ProductionLanguageSurface(
        documents=tuple(documents),
        diagnostics=tuple(diagnostics),
        type_issues=type_issues,
    )
