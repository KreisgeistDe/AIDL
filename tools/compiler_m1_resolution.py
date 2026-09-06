"""M1 resolution diagnostics missing from the legacy compiler diagnostic collector.

This module closes only the Language Core resolution contract. It reuses the
existing compiler project, symbol table, imports, source spans and diagnostic
shape; it does not introduce new language or M2+ policy semantics.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Iterable

from tools.aidl_parser import Node, Span
from tools.compiler_diagnostics import (
    CompilerAnalysis,
    CompilerDiagnostic,
    CompilerDiagnosticSeverity,
    load_compiler_analysis,
)
from tools.compiler_project import CompilerDeclarationName, CompilerProject


class M1ResolutionDiagnosticCode(StrEnum):
    """Stable M1 resolution identities that complete the existing R001/R002 set."""

    UNRESOLVED_NAME = "AIDL-R003"
    CYCLIC_MODULE_DEPENDENCY = "AIDL-R004"


_QUALIFIED_NAME = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*"
)
_LIST_CLAUSE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:?\s*(\[.*\])$")
_OPERATION_ITEM = re.compile(
    r"^(query|mutation|consumer|workflow|saga|task)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)$"
)
_TRANSACTION_HEADER = re.compile(
    r"^transaction\s+on\s+"
    r"([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)"
    r"(?:\s+isolation\s+[A-Za-z_][A-Za-z0-9_]*)?$"
)
_FIELD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*:\s*(.+)$")
_PARAMETER = re.compile(r"(?:^|,)\s*[A-Za-z_][A-Za-z0-9_]*\s*:\s*([^,]+)")

_TYPE_LIKE_DECLARATIONS = frozenset({"alias", "opaque", "value", "error", "entity", "event"})
_OPERATION_DECLARATIONS = frozenset({"query", "mutation", "consumer", "workflow", "saga", "task"})
_IMPLICIT_STANDARD_TYPES = frozenset(
    {
        "SubjectId",
        "TenantId",
        "DeviceId",
        "OperationId",
        "MessageId",
        "Cursor",
        "PageInput",
        "Page",
        "OffsetPageInput",
    }
)


def _normalize(reference: str) -> str:
    return re.sub(r"\s*\.\s*", ".", reference.strip())


def _declaration_identity(declaration: CompilerDeclarationName) -> tuple[Path, int]:
    span = declaration.declaration.span
    return declaration.document.source_path, span.offset if span is not None else -1


def _resolve(
    project: CompilerProject,
    source: CompilerDeclarationName,
    reference: str,
    kinds: frozenset[str] | None = None,
) -> tuple[CompilerDeclarationName, ...]:
    reference = _normalize(reference)
    candidates: list[CompilerDeclarationName] = []
    if "." in reference:
        candidates.extend(project.symbol_table.lookup_declarations(reference))
    else:
        module = source.document.module
        if module is not None and module.name is not None:
            candidates.extend(project.symbol_table.lookup_declarations(f"{module.name}.{reference}"))
        for resolution in project.import_resolutions:
            if resolution.document is not source.document:
                continue
            candidates.extend(
                declaration
                for declaration in resolution.declarations
                if declaration.declaration.name == reference
            )

    resolved: list[CompilerDeclarationName] = []
    seen: set[tuple[Path, int]] = set()
    for candidate in candidates:
        if kinds is not None and candidate.declaration.kind not in kinds:
            continue
        identity = _declaration_identity(candidate)
        if identity in seen:
            continue
        seen.add(identity)
        resolved.append(candidate)
    return tuple(resolved)


def _type_references(expression: str) -> tuple[str, ...]:
    """Return declaration-looking type names from an already parsed type expression.

    Core declaration names are PascalCase. Restricting the diagnostic scan to names
    with an uppercase final segment avoids treating scalar/container/modifier words
    as declarations while still covering imported and fully qualified named types.
    """

    references: list[str] = []
    for match in _QUALIFIED_NAME.finditer(expression):
        reference = _normalize(match.group(0))
        final_segment = reference.rsplit(".", 1)[-1]
        if not final_segment or not final_segment[0].isupper():
            continue
        references.append(reference)
    return tuple(references)


def _list_items(node: Node, clause_name: str) -> tuple[str, ...]:
    if node.name is None:
        return ()
    match = _LIST_CLAUSE.fullmatch(node.name.strip())
    if match is None or match.group(1) != clause_name:
        return ()
    raw = match.group(2)
    return tuple(item.strip() for item in raw[1:-1].split(",") if item.strip())


def _unresolved_diagnostic(
    source: CompilerDeclarationName,
    reference: str,
    location: Span,
) -> CompilerDiagnostic:
    return CompilerDiagnostic(
        code=M1ResolutionDiagnosticCode.UNRESOLVED_NAME,
        phase="resolve",
        severity=CompilerDiagnosticSeverity.ERROR,
        message=f"unresolved name '{_normalize(reference)}'",
        source_path=source.document.source_path,
        location=location,
    )


def _collect_reference(
    diagnostics: list[CompilerDiagnostic],
    seen: set[tuple[Path, int, str]],
    project: CompilerProject,
    source: CompilerDeclarationName,
    reference: str,
    location: Span | None,
    kinds: frozenset[str] | None = None,
) -> None:
    if location is None:
        return
    normalized = _normalize(reference)
    if (
        not normalized
        or normalized in _IMPLICIT_STANDARD_TYPES
        or _resolve(project, source, normalized, kinds)
    ):
        return
    key = (source.document.source_path, location.offset, normalized)
    if key in seen:
        return
    seen.add(key)
    diagnostics.append(_unresolved_diagnostic(source, normalized, location))


def _visit_transactions(
    node: Node,
    callback,
) -> None:
    if node.name is not None and node.span is not None:
        match = _TRANSACTION_HEADER.fullmatch(node.name.strip())
        if match is not None:
            callback(match.group(1), node.span)
    for child in node.children:
        _visit_transactions(child, callback)


def _unresolved_name_diagnostics(project: CompilerProject) -> tuple[CompilerDiagnostic, ...]:
    diagnostics: list[CompilerDiagnostic] = []
    seen: set[tuple[Path, int, str]] = set()

    for source in project.declaration_names:
        declaration = source.declaration
        location = declaration.span

        if declaration.kind in {"alias", "opaque"}:
            raw_type = declaration.node.attrs.get("type")
            if isinstance(raw_type, str):
                for reference in _type_references(raw_type):
                    _collect_reference(diagnostics, seen, project, source, reference, location)

        if declaration.kind in _TYPE_LIKE_DECLARATIONS:
            for child in declaration.node.children:
                if child.name is None:
                    continue
                field = _FIELD.fullmatch(child.name.strip())
                if field is None:
                    continue
                for reference in _type_references(field.group(1)):
                    _collect_reference(
                        diagnostics, seen, project, source, reference, child.span
                    )

        if declaration.kind in _OPERATION_DECLARATIONS:
            parameters = declaration.node.attrs.get("parameters")
            if isinstance(parameters, str):
                inner = parameters[1:-1] if parameters.startswith("(") and parameters.endswith(")") else parameters
                for parameter in _PARAMETER.finditer(inner):
                    for reference in _type_references(parameter.group(1)):
                        _collect_reference(diagnostics, seen, project, source, reference, location)
            returns = declaration.node.attrs.get("returns")
            if isinstance(returns, str):
                for reference in _type_references(returns):
                    _collect_reference(diagnostics, seen, project, source, reference, location)

            for child in declaration.node.children:
                for item in _list_items(child, "errors"):
                    _collect_reference(
                        diagnostics,
                        seen,
                        project,
                        source,
                        item,
                        child.span,
                        frozenset({"error"}),
                    )

        if declaration.kind == "service":
            for child in declaration.node.children:
                for item in _list_items(child, "owns"):
                    _collect_reference(
                        diagnostics,
                        seen,
                        project,
                        source,
                        item,
                        child.span,
                        frozenset({"entity"}),
                    )
                for item in _list_items(child, "uses"):
                    _collect_reference(
                        diagnostics,
                        seen,
                        project,
                        source,
                        item,
                        child.span,
                        frozenset({"resource", "topic", "queue"}),
                    )
                for clause in ("exposes", "runs"):
                    for item in _list_items(child, clause):
                        match = _OPERATION_ITEM.fullmatch(item)
                        if match is None:
                            continue
                        _collect_reference(
                            diagnostics,
                            seen,
                            project,
                            source,
                            match.group(2),
                            child.span,
                            frozenset({match.group(1)}),
                        )

        if declaration.kind == "api":
            for child in declaration.node.children:
                for item in _list_items(child, "operations"):
                    match = _OPERATION_ITEM.fullmatch(item)
                    if match is None or match.group(1) not in {"query", "mutation"}:
                        continue
                    _collect_reference(
                        diagnostics,
                        seen,
                        project,
                        source,
                        match.group(2),
                        child.span,
                        frozenset({match.group(1)}),
                    )

        if declaration.kind == "consumer":
            event = declaration.node.attrs.get("on")
            if isinstance(event, str):
                for reference in _type_references(event):
                    _collect_reference(
                        diagnostics,
                        seen,
                        project,
                        source,
                        reference,
                        location,
                        frozenset({"event"}),
                    )
            topic = declaration.node.attrs.get("from")
            if isinstance(topic, str):
                for reference in _type_references(topic):
                    _collect_reference(
                        diagnostics,
                        seen,
                        project,
                        source,
                        reference,
                        location,
                        frozenset({"topic", "queue"}),
                    )

        def collect_transaction(reference: str, span: Span) -> None:
            _collect_reference(
                diagnostics,
                seen,
                project,
                source,
                reference,
                span,
                frozenset({"resource"}),
            )

        _visit_transactions(declaration.node, collect_transaction)

    return tuple(diagnostics)


def _cyclic_module_diagnostics(project: CompilerProject) -> tuple[CompilerDiagnostic, ...]:
    diagnostics: list[CompilerDiagnostic] = []
    for cycle in project.module_cycles:
        if not cycle.modules:
            continue
        first_module = cycle.modules[0]
        documents = project.modules.get(first_module, ())
        document = documents[0] if documents else None
        if document is None or document.module is None or document.module.span is None:
            continue
        path = " -> ".join((*cycle.modules, cycle.modules[0]))
        diagnostics.append(
            CompilerDiagnostic(
                code=M1ResolutionDiagnosticCode.CYCLIC_MODULE_DEPENDENCY,
                phase="resolve",
                severity=CompilerDiagnosticSeverity.ERROR,
                message=f"cyclic module dependency: {path}",
                source_path=document.source_path,
                location=document.module.span,
            )
        )
    return tuple(diagnostics)


def collect_m1_resolution_diagnostics(project: CompilerProject) -> tuple[CompilerDiagnostic, ...]:
    """Return the missing M1 name/cycle diagnostics in deterministic project order."""

    diagnostics = list(_unresolved_name_diagnostics(project))
    diagnostics.extend(_cyclic_module_diagnostics(project))
    document_order = {
        document.source_path: index for index, document in enumerate(project.documents)
    }
    diagnostics.sort(
        key=lambda diagnostic: (
            document_order.get(diagnostic.source_path, len(document_order)),
            diagnostic.location.offset,
            diagnostic.code.value,
            diagnostic.message,
        )
    )
    return tuple(diagnostics)


def load_m1_complete_analysis(paths: Iterable[Path]) -> CompilerAnalysis:
    """Load the existing compiler analysis and add only missing M1 resolution facts."""

    analysis = load_compiler_analysis(paths)
    supplemental = collect_m1_resolution_diagnostics(analysis.project)
    if not supplemental:
        return analysis

    document_order = {
        document.source_path: index for index, document in enumerate(analysis.project.documents)
    }
    phase_order = {"parse": 0, "resolve": 1, "policy": 2}
    combined = list(analysis.diagnostics) + list(supplemental)
    combined.sort(
        key=lambda diagnostic: (
            document_order.get(diagnostic.source_path, len(document_order)),
            diagnostic.location.offset,
            phase_order.get(diagnostic.phase, len(phase_order)),
            diagnostic.code.value,
            diagnostic.message,
        )
    )
    return CompilerAnalysis(project=analysis.project, diagnostics=tuple(combined))
