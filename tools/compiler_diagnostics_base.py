"""Stable source-located compiler diagnostics over existing boundaries.

This module projects parser failures, project resolution facts, and the current
Semantic Core policy rules into a deterministic compiler diagnostic stream with
stable diagnostic codes, severity contracts, and a minimal machine-readable
JSON surface. It intentionally does not add later M2 validation, a production
CLI, IR, or IDE integration.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from .aidl_parser import Diagnostic as ParserDiagnostic
    from .aidl_parser import Node, Span, iter_aidl_files, parse_text
    from .compiler_ast import CompilerDeclaration, compiler_document_from_ast
    from .compiler_project import (
        CompilerDeclarationName,
        CompilerProject,
        compiler_project_from_documents,
    )
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from aidl_parser import Diagnostic as ParserDiagnostic
    from aidl_parser import Node, Span, iter_aidl_files, parse_text
    from compiler_ast import CompilerDeclaration, compiler_document_from_ast
    from compiler_project import (
        CompilerDeclarationName,
        CompilerProject,
        compiler_project_from_documents,
    )


class CompilerDiagnosticCode(StrEnum):
    """Stable identities for compiler diagnostics currently emitted."""

    PARSE_FAILURE = "AIDL-P001"
    UNRESOLVED_IMPORT = "AIDL-R001"
    DUPLICATE_DECLARATION = "AIDL-R002"
    ENTITY_OWNER_CARDINALITY = "AIDL-DIST400"
    CROSS_SERVICE_REF = "AIDL-DIST401"
    TRANSACTION_BOUNDARY = "AIDL-DIST402"
    QUERY_SIDE_EFFECT = "AIDL-DIST403"
    MUTATION_REQUIRED_CLAUSE = "AIDL-DIST404"
    MUTATION_ROOT_EFFECT = "AIDL-DIST405"
    PUBLIC_REASON = "AIDL-DIST406"
    TRANSACTION_ISOLATION = "AIDL-DIST407"
    TRANSACTION_OUTBOX = "AIDL-DIST408"
    CONSUMER_IDEMPOTENCY = "AIDL-DIST411"
    API_CONTRACT = "AIDL-DIST412"
    BOUNDED_COLLECTION_QUERY = "AIDL-DIST413"


class CompilerDiagnosticSeverity(StrEnum):
    """Stable compiler severity contract ordered from most to least severe."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class CompilerDiagnosticSubject:
    """Structured subject metadata for actionable diagnostics."""

    kind: str
    name: str

    def to_json(self) -> dict[str, str]:
        return {"kind": self.kind, "name": self.name}


@dataclass(frozen=True)
class CompilerDiagnosticFix:
    """One documented, non-applied diagnostic fix suggestion."""

    kind: str
    text: str

    def to_json(self) -> dict[str, str]:
        return {"kind": self.kind, "text": self.text}


@dataclass(frozen=True)
class CompilerDiagnostic:
    """One deterministic compiler diagnostic anchored to a source location."""

    code: CompilerDiagnosticCode
    phase: str
    severity: CompilerDiagnosticSeverity
    message: str
    source_path: Path
    location: Span
    subject: CompilerDiagnosticSubject | None = None
    expected: str | None = None
    allowed_fixes: tuple[CompilerDiagnosticFix, ...] = ()
    docs: str | None = None

    def to_json(self) -> dict[str, Any]:
        """Return the stable machine-readable representation of this diagnostic."""

        payload: dict[str, Any] = {
            "code": self.code.value,
            "phase": self.phase,
            "severity": self.severity.value,
            "message": self.message,
            "location": {
                "file": str(self.source_path),
                "line": self.location.line,
                "column": self.location.column,
                "offset": self.location.offset,
            },
        }
        if self.subject is not None:
            payload["subject"] = self.subject.to_json()
        if self.expected is not None:
            payload["expected"] = self.expected
        if self.allowed_fixes:
            payload["allowedFixes"] = [fix.to_json() for fix in self.allowed_fixes]
        if self.docs is not None:
            payload["docs"] = self.docs
        return payload


@dataclass(frozen=True)
class CompilerAnalysis:
    """Compiler project plus its deterministic source-located diagnostics."""

    project: CompilerProject
    diagnostics: tuple[CompilerDiagnostic, ...]


def compiler_diagnostics_to_json(
    diagnostics: Iterable[CompilerDiagnostic],
) -> str:
    """Serialize diagnostics deterministically without changing their order."""

    return json.dumps(
        [diagnostic.to_json() for diagnostic in diagnostics],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _parser_severity(severity: str) -> CompilerDiagnosticSeverity:
    """Map parser severity onto the explicit compiler severity contract."""

    return CompilerDiagnosticSeverity(severity)


def _declaration_identity(
    declaration_name: CompilerDeclarationName,
) -> tuple[Path, int]:
    span = declaration_name.declaration.span
    return (
        declaration_name.document.source_path,
        span.offset if span is not None else -1,
    )


def _list_clause_references(
    declaration: CompilerDeclaration,
    clause_name: str,
) -> tuple[str, ...]:
    """Read one existing ``name [...]`` clause from retained generic nodes."""

    references: list[str] = []
    prefix = f"{clause_name} "
    for child in declaration.node.children:
        if child.name is None:
            continue
        clause = child.name.strip()
        if not clause.startswith(prefix):
            continue
        value = clause[len(prefix) :].strip()
        if not (value.startswith("[") and value.endswith("]")):
            continue
        references.extend(
            reference.strip()
            for reference in value[1:-1].split(",")
            if reference.strip()
        )
    return tuple(references)


def _owned_entity_references(service: CompilerDeclaration) -> tuple[str, ...]:
    """Read existing generic service ``owns [...]`` clauses without new syntax."""

    return _list_clause_references(service, "owns")


def _resolve_declaration_reference(
    project: CompilerProject,
    source: CompilerDeclarationName,
    reference: str,
    kinds: frozenset[str],
) -> tuple[CompilerDeclarationName, ...]:
    """Resolve one declaration name through existing local/import projections."""

    candidates: list[CompilerDeclarationName] = []
    if "." in reference:
        candidates.extend(project.symbol_table.lookup_declarations(reference))
    else:
        module = source.document.module
        if module is not None and module.name is not None:
            candidates.extend(
                project.symbol_table.lookup_declarations(f"{module.name}.{reference}")
            )
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
        if candidate.declaration.kind not in kinds:
            continue
        identity = _declaration_identity(candidate)
        if identity in seen:
            continue
        seen.add(identity)
        resolved.append(candidate)
    return tuple(resolved)


def _resolve_entity_reference(
    project: CompilerProject,
    source: CompilerDeclarationName,
    reference: str,
) -> tuple[CompilerDeclarationName, ...]:
    """Resolve one entity name through existing local/import projections."""

    return _resolve_declaration_reference(project, source, reference, frozenset({"entity"}))


def _resolve_owned_entity(
    project: CompilerProject,
    service: CompilerDeclarationName,
    reference: str,
) -> tuple[CompilerDeclarationName, ...]:
    """Resolve one ownership name through existing local/import projections."""

    return _resolve_entity_reference(project, service, reference)


def _entity_owner_index(
    project: CompilerProject,
) -> dict[tuple[Path, int], tuple[CompilerDeclarationName, ...]]:
    """Project the established resolved service owners for every entity."""

    entities = tuple(
        declaration_name
        for declaration_name in project.declaration_names
        if declaration_name.declaration.kind == "entity"
    )
    owners_by_entity: dict[
        tuple[Path, int], list[CompilerDeclarationName]
    ] = {_declaration_identity(entity): [] for entity in entities}

    for service in project.declaration_names:
        if service.declaration.kind != "service":
            continue
        seen_entities: set[tuple[Path, int]] = set()
        for reference in _owned_entity_references(service.declaration):
            resolved = _resolve_owned_entity(project, service, reference)
            if len(resolved) != 1:
                continue
            entity_identity = _declaration_identity(resolved[0])
            if entity_identity in seen_entities:
                continue
            seen_entities.add(entity_identity)
            owners_by_entity.setdefault(entity_identity, []).append(service)

    return {
        entity_identity: tuple(owners)
        for entity_identity, owners in owners_by_entity.items()
    }


def _entity_owner_diagnostics(
    project: CompilerProject,
    owners_by_entity: Mapping[
        tuple[Path, int], tuple[CompilerDeclarationName, ...]
    ] | None = None,
) -> tuple[CompilerDiagnostic, ...]:
    """Validate exactly one service owner for each persisted entity."""

    entities = tuple(
        declaration_name
        for declaration_name in project.declaration_names
        if declaration_name.declaration.kind == "entity"
    )
    owners_by_entity = owners_by_entity or _entity_owner_index(project)

    diagnostics: list[CompilerDiagnostic] = []
    for entity in entities:
        owners = owners_by_entity[_declaration_identity(entity)]
        if len(owners) == 1 or entity.declaration.span is None:
            continue
        entity_name = entity.fully_qualified_name or entity.declaration.name or "<unnamed>"
        if not owners:
            message = (
                f"persisted entity '{entity_name}' must have exactly one owner service; "
                "found none"
            )
        else:
            owner_names = [
                owner.fully_qualified_name or owner.declaration.name or "<unnamed>"
                for owner in owners
            ]
            message = (
                f"persisted entity '{entity_name}' must have exactly one owner service; "
                f"found {len(owners)}: {', '.join(owner_names)}"
            )
        diagnostics.append(
            CompilerDiagnostic(
                code=CompilerDiagnosticCode.ENTITY_OWNER_CARDINALITY,
                phase="policy",
                severity=CompilerDiagnosticSeverity.ERROR,
                message=message,
                source_path=entity.document.source_path,
                location=entity.declaration.span,
                subject=CompilerDiagnosticSubject(
                    kind="entity", name=entity.declaration.name or "<unnamed>"
                ),
                expected="exactly one owner service",
                docs="aidl://diagnostics/AIDL-DIST400",
            )
        )
    return tuple(diagnostics)


_REF_TARGET = re.compile(
    r"(?:^|\s)ref\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)"
)


def _entity_ref_references(
    entity: CompilerDeclaration,
) -> tuple[tuple[str, Span], ...]:
    """Read direct entity-field ``ref`` targets from retained generic clauses."""

    references: list[tuple[str, Span]] = []
    for child in entity.node.children:
        if child.name is None or child.span is None:
            continue
        match = _REF_TARGET.search(child.name)
        if match is None:
            continue
        reference = re.sub(r"\s*\.\s*", ".", match.group(1))
        references.append((reference, child.span))
    return tuple(references)


def _cross_service_ref_diagnostics(
    project: CompilerProject,
    owners_by_entity: Mapping[
        tuple[Path, int], tuple[CompilerDeclarationName, ...]
    ],
) -> tuple[CompilerDiagnostic, ...]:
    """Reject entity refs whose source and target have different owner services."""

    diagnostics: list[CompilerDiagnostic] = []
    for entity in project.declaration_names:
        if entity.declaration.kind != "entity":
            continue
        source_owners = owners_by_entity.get(_declaration_identity(entity), ())
        if len(source_owners) != 1:
            continue
        source_owner = source_owners[0]
        for reference, location in _entity_ref_references(entity.declaration):
            targets = _resolve_entity_reference(project, entity, reference)
            if len(targets) != 1:
                continue
            target = targets[0]
            target_owners = owners_by_entity.get(_declaration_identity(target), ())
            if len(target_owners) != 1:
                continue
            target_owner = target_owners[0]
            if _declaration_identity(source_owner) == _declaration_identity(target_owner):
                continue

            source_name = (
                entity.fully_qualified_name or entity.declaration.name or "<unnamed>"
            )
            target_name = (
                target.fully_qualified_name or target.declaration.name or "<unnamed>"
            )
            source_owner_name = (
                source_owner.fully_qualified_name
                or source_owner.declaration.name
                or "<unnamed>"
            )
            target_owner_name = (
                target_owner.fully_qualified_name or target_owner.declaration.name or "<unnamed>"
            )
            diagnostics.append(
                CompilerDiagnostic(
                    code=CompilerDiagnosticCode.CROSS_SERVICE_REF,
                    phase="policy",
                    severity=CompilerDiagnosticSeverity.ERROR,
                    message=(
                        f"ref from entity '{source_name}' to '{target_name}' crosses "
                        f"owner service boundary: '{source_owner_name}' -> "
                        f"'{target_owner_name}'"
                    ),
                    source_path=entity.document.source_path,
                    location=location,
                    subject=CompilerDiagnosticSubject(
                        kind="entity", name=entity.declaration.name or "<unnamed>"
                    ),
                    expected="source and target entities owned by same service",
                    docs="aidl://diagnostics/AIDL-DIST401",
                )
            )
    return tuple(diagnostics)


_OPERATION_ITEM = re.compile(
    r"^(mutation|consumer)\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)$"
)
_TRANSACTION_HEADER = re.compile(
    r"^transaction\s+on\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)"
    r"(?:\s+isolation\s+([A-Za-z_][A-Za-z0-9_]*))?$"
)
_QUALIFIED_CALL = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)\s*\."
)
_QUERY_SIDE_EFFECT_CLAUSE = re.compile(r"^(write|emit|call|start)\s*:")
_TRANSACTION_EMIT = re.compile(r"^emit\s*:")
_VIA_OUTBOX = re.compile(r"\bvia\s+outbox\b")
_CONSUMER_EFFECT_CLAUSE = re.compile(r"^(start|call)\s*:")
_MUTATION_REQUIRED_CLAUSES = ("auth", "allow", "errors", "idempotency")
_MUTATION_ROOT_CALL = re.compile(r"^call\s*:")
_MUTATION_ROOT_START = re.compile(r"^start\s*:\s*(workflow|saga)\b")
_PUBLIC_AUTH = re.compile(r"^auth\s*:\s*public(?:\s|$)")
_PUBLIC_REASON_STRING = re.compile(r'^\(\s*"((?:\\.|[^"\\])*)"\s*\)$')
_API_OPERATION_ITEM = re.compile(
    r"^(query|mutation)\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)$"
)
_API_TRANSPORTS = frozenset({"rest", "rpc", "graphql"})
_API_COMPATIBILITY_MODES = frozenset({"none", "backward", "forward", "full"})
_API_POSITIVE_MAJOR = re.compile(r"^[1-9][0-9]*$")
_QUERY_READ = re.compile(r"^read\s*:")


def _service_operation_references(
    service: CompilerDeclaration,
) -> tuple[tuple[str, str], ...]:
    """Read mutation/consumer bindings from existing exposes/runs clauses."""

    references: list[tuple[str, str]] = []
    for clause_name in ("exposes", "runs"):
        for item in _list_clause_references(service, clause_name):
            match = _OPERATION_ITEM.fullmatch(item)
            if match is None:
                continue
            references.append(
                (match.group(1), re.sub(r"\s*\.\s*", ".", match.group(2)))
            )
    return tuple(references)


def _operation_service_index(
    project: CompilerProject,
) -> dict[tuple[Path, int], tuple[CompilerDeclarationName, ...]]:
    """Project services that explicitly expose/run transaction-capable operations."""

    services_by_operation: dict[
        tuple[Path, int], list[CompilerDeclarationName]
    ] = {}
    for service in project.declaration_names:
        if service.declaration.kind != "service":
            continue
        seen: set[tuple[Path, int]] = set()
        for kind, reference in _service_operation_references(service.declaration):
            resolved = _resolve_declaration_reference(
                project, service, reference, frozenset({kind})
            )
            if len(resolved) != 1:
                continue
            operation_identity = _declaration_identity(resolved[0])
            if operation_identity in seen:
                continue
            seen.add(operation_identity)
            services_by_operation.setdefault(operation_identity, []).append(service)
    return {
        operation_identity: tuple(services)
        for operation_identity, services in services_by_operation.items()
    }


def _service_used_resources(
    project: CompilerProject,
    service: CompilerDeclarationName,
) -> tuple[CompilerDeclarationName, ...]:
    """Resolve resources named by an existing service ``uses [...]`` clause."""

    resources: list[CompilerDeclarationName] = []
    seen: set[tuple[Path, int]] = set()
    for reference in _list_clause_references(service.declaration, "uses"):
        resolved = _resolve_declaration_reference(
            project, service, reference, frozenset({"resource"})
        )
        if len(resolved) != 1:
            continue
        identity = _declaration_identity(resolved[0])
        if identity in seen:
            continue
        seen.add(identity)
        resources.append(resolved[0])
    return tuple(resources)


def _transaction_blocks(declaration: CompilerDeclaration) -> tuple[Node, ...]:
    """Find retained transaction block clauses without changing parser syntax."""

    blocks: list[Node] = []

    def visit(node: Node) -> None:
        if node.kind == "blockClause" and node.name is not None:
            if _TRANSACTION_HEADER.fullmatch(node.name.strip()) is not None:
                blocks.append(node)
                return
        for child in node.children:
            visit(child)

    for child in declaration.node.children:
        visit(child)
    return tuple(blocks)


def _transaction_target_reference(transaction: Node) -> str | None:
    if transaction.name is None:
        return None
    match = _TRANSACTION_HEADER.fullmatch(transaction.name.strip())
    if match is None:
        return None
    return re.sub(r"\s*\.\s*", ".", match.group(1))


def _transaction_isolation(transaction: Node) -> str | None:
    """Read an existing transaction header isolation without adding syntax."""

    if transaction.name is None:
        return None
    match = _TRANSACTION_HEADER.fullmatch(transaction.name.strip())
    if match is None:
        return None
    return match.group(2)


def _resource_transaction_isolations(resource: CompilerDeclaration) -> tuple[str, ...]:
    """Read existing resource ``transactions [...]`` capability declarations."""

    return _list_clause_references(resource, "transactions")


def _transaction_body_declaration_references(
    project: CompilerProject,
    operation: CompilerDeclarationName,
    transaction: Node,
) -> tuple[tuple[CompilerDeclarationName, Span], ...]:
    """Resolve explicit entity/resource receivers used inside one transaction."""

    references: list[tuple[CompilerDeclarationName, Span]] = []
    seen: set[tuple[tuple[Path, int], int]] = set()

    def visit(node: Node) -> None:
        if node.name is not None and node.span is not None:
            for match in _QUALIFIED_CALL.finditer(node.name):
                reference = re.sub(r"\s*\.\s*", ".", match.group(1))
                resolved = _resolve_declaration_reference(
                    project,
                    operation,
                    reference,
                    frozenset({"entity", "resource"}),
                )
                if len(resolved) != 1:
                    continue
                key = (_declaration_identity(resolved[0]), node.span.offset)
                if key in seen:
                    continue
                seen.add(key)
                references.append((resolved[0], node.span))
        for child in node.children:
            visit(child)

    for child in transaction.children:
        visit(child)
    return tuple(references)


def _transaction_boundary_diagnostics(
    project: CompilerProject,
    owners_by_entity: Mapping[
        tuple[Path, int], tuple[CompilerDeclarationName, ...]
    ],
) -> tuple[CompilerDiagnostic, ...]:
    """Reject transactions that cross their service or single-resource boundary."""

    services_by_operation = _operation_service_index(project)
    diagnostics: list[CompilerDiagnostic] = []

    for operation in project.declaration_names:
        if operation.declaration.kind not in {"mutation", "consumer"}:
            continue
        services = services_by_operation.get(_declaration_identity(operation), ())
        if len(services) != 1:
            continue
        service = services[0]
        service_name = (
            service.fully_qualified_name or service.declaration.name or "<unnamed>"
        )
        used_resource_ids = {
            _declaration_identity(resource)
            for resource in _service_used_resources(project, service)
        }

        for transaction in _transaction_blocks(operation.declaration):
            if transaction.span is None:
                continue
            target_reference = _transaction_target_reference(transaction)
            if target_reference is None:
                continue
            targets = _resolve_declaration_reference(
                project, operation, target_reference, frozenset({"resource"})
            )
            if len(targets) != 1:
                continue
            target = targets[0]
            target_identity = _declaration_identity(target)
            target_name = (
                target.fully_qualified_name or target.declaration.name or "<unnamed>"
            )
            operation_name = (
                operation.fully_qualified_name
                or operation.declaration.name
                or "<unnamed>"
            )
            subject_name = operation.declaration.name or "<unnamed>"

            if target_identity not in used_resource_ids:
                diagnostics.append(
                    CompilerDiagnostic(
                        code=CompilerDiagnosticCode.TRANSACTION_BOUNDARY,
                        phase="policy",
                        severity=CompilerDiagnosticSeverity.ERROR,
                        message=(
                            f"transaction in '{operation_name}' targets resource "
                            f"'{target_name}' outside service '{service_name}' resource boundary"
                        ),
                        source_path=operation.document.source_path,
                        location=transaction.span,
                        subject=CompilerDiagnosticSubject(
                            kind=operation.declaration.kind, name=subject_name
                        ),
                        expected="transaction confined to bound service and single target resource",
                        docs="aidl://diagnostics/AIDL-DIST402",
                    )
                )

            for referenced, location in _transaction_body_declaration_references(
                project, operation, transaction
            ):
                referenced_name = (
                    referenced.fully_qualified_name
                    or referenced.declaration.name
                    or "<unnamed>"
                )
                if referenced.declaration.kind == "resource":
                    if _declaration_identity(referenced) == target_identity:
                        continue
                    diagnostics.append(
                        CompilerDiagnostic(
                            code=CompilerDiagnosticCode.TRANSACTION_BOUNDARY,
                            phase="policy",
                            severity=CompilerDiagnosticSeverity.ERROR,
                            message=(
                                f"transaction in '{operation_name}' on '{target_name}' "
                                f"accesses second resource '{referenced_name}'"
                            ),
                            source_path=operation.document.source_path,
                            location=location,
                            subject=CompilerDiagnosticSubject(
                                kind=operation.declaration.kind, name=subject_name
                            ),
                            expected="transaction confined to bound service and single target resource",
                            docs="aidl://diagnostics/AIDL-DIST402",
                        )
                    )
                    continue

                owners = owners_by_entity.get(_declaration_identity(referenced), ())
                if len(owners) != 1:
                    continue
                owner = owners[0]
                if _declaration_identity(owner) == _declaration_identity(service):
                    continue
                owner_name = (
                    owner.fully_qualified_name or owner.declaration.name or "<unnamed>"
                )
                diagnostics.append(
                    CompilerDiagnostic(
                        code=CompilerDiagnosticCode.TRANSACTION_BOUNDARY,
                        phase="policy",
                        severity=CompilerDiagnosticSeverity.ERROR,
                        message=(
                            f"transaction in '{operation_name}' for service '{service_name}' "
                            f"accesses entity '{referenced_name}' owned by '{owner_name}'"
                        ),
                        source_path=operation.document.source_path,
                        location=location,
                        subject=CompilerDiagnosticSubject(
                            kind=operation.declaration.kind, name=subject_name
                        ),
                        expected="transaction confined to bound service and single target resource",
                        docs="aidl://diagnostics/AIDL-DIST402",
                    )
                )

    return tuple(diagnostics)


def _transaction_isolation_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Validate isolation only for uniquely bound owner-local transactions."""

    services_by_operation = _operation_service_index(project)
    diagnostics: list[CompilerDiagnostic] = []

    for operation in project.declaration_names:
        if operation.declaration.kind not in {"mutation", "consumer"}:
            continue
        services = services_by_operation.get(_declaration_identity(operation), ())
        if len(services) != 1:
            continue
        service = services[0]
        used_resources = {
            _declaration_identity(resource): resource
            for resource in _service_used_resources(project, service)
        }

        for transaction in _transaction_blocks(operation.declaration):
            if transaction.span is None:
                continue
            target_reference = _transaction_target_reference(transaction)
            if target_reference is None:
                continue
            targets = _resolve_declaration_reference(
                project, operation, target_reference, frozenset({"resource"})
            )
            if len(targets) != 1:
                continue
            target = targets[0]
            target_identity = _declaration_identity(target)
            if target_identity not in used_resources:
                continue

            operation_name = (
                operation.fully_qualified_name
                or operation.declaration.name
                or "<unnamed>"
            )
            subject_name = operation.declaration.name or "<unnamed>"
            target_name = (
                target.fully_qualified_name or target.declaration.name or "<unnamed>"
            )
            isolation = _transaction_isolation(transaction)
            if isolation is None:
                diagnostics.append(
                    CompilerDiagnostic(
                        code=CompilerDiagnosticCode.TRANSACTION_ISOLATION,
                        phase="policy",
                        severity=CompilerDiagnosticSeverity.ERROR,
                        message=(
                            f"transaction in '{operation_name}' on resource '{target_name}' "
                            "must declare isolation"
                        ),
                        source_path=operation.document.source_path,
                        location=transaction.span,
                        subject=CompilerDiagnosticSubject(
                            kind=operation.declaration.kind, name=subject_name
                        ),
                        expected="declared isolation supported by target resource",
                        docs="aidl://diagnostics/AIDL-DIST407",
                    )
                )
                continue

            supported = _resource_transaction_isolations(target.declaration)
            if isolation in supported:
                continue
            diagnostics.append(
                CompilerDiagnostic(
                    code=CompilerDiagnosticCode.TRANSACTION_ISOLATION,
                    phase="policy",
                    severity=CompilerDiagnosticSeverity.ERROR,
                    message=(
                        f"transaction in '{operation_name}' on resource '{target_name}' "
                        f"declares isolation '{isolation}' not supported by the resource"
                    ),
                    source_path=operation.document.source_path,
                    location=transaction.span,
                    subject=CompilerDiagnosticSubject(
                        kind=operation.declaration.kind, name=subject_name
                    ),
                    expected="declared isolation supported by target resource",
                    docs="aidl://diagnostics/AIDL-DIST407",
                )
            )

    return tuple(diagnostics)


def _transaction_emit_nodes(transaction: Node) -> tuple[Node, ...]:
    """Find retained ``emit:`` clauses anywhere inside one transaction."""

    emits: list[Node] = []

    def visit(node: Node) -> None:
        if node.name is not None and node.span is not None:
            if _TRANSACTION_EMIT.match(node.name.strip()) is not None:
                emits.append(node)
        for child in node.children:
            visit(child)

    for child in transaction.children:
        visit(child)
    return tuple(emits)


def _transaction_outbox_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Require existing transactional emits to use explicit ``via outbox`` markup."""

    diagnostics: list[CompilerDiagnostic] = []
    for operation in project.declaration_names:
        if operation.declaration.kind not in {"mutation", "consumer"}:
            continue
        operation_name = (
            operation.fully_qualified_name
            or operation.declaration.name
            or "<unnamed>"
        )
        subject_name = operation.declaration.name or "<unnamed>"
        for transaction in _transaction_blocks(operation.declaration):
            for emit in _transaction_emit_nodes(transaction):
                if emit.name is None or emit.span is None:
                    continue
                if _VIA_OUTBOX.search(emit.name) is not None:
                    continue
                diagnostics.append(
                    CompilerDiagnostic(
                        code=CompilerDiagnosticCode.TRANSACTION_OUTBOX,
                        phase="policy",
                        severity=CompilerDiagnosticSeverity.ERROR,
                        message=(
                            f"emit in transaction of '{operation_name}' must use 'via outbox'"
                        ),
                        source_path=operation.document.source_path,
                        location=emit.span,
                        subject=CompilerDiagnosticSubject(
                            kind=operation.declaration.kind, name=subject_name
                        ),
                        expected="transactional emits use via outbox",
                        docs="aidl://diagnostics/AIDL-DIST408",
                    )
                )
    return tuple(diagnostics)


def _consumer_idempotency_locations(
    consumer: CompilerDeclaration,
) -> tuple[Span, ...]:
    """Return top-level retained consumer ``idempotency:`` clauses."""

    locations: list[Span] = []
    for child in consumer.node.children:
        if child.name is None or child.span is None:
            continue
        if re.match(r"^idempotency\s*:", child.name.strip()) is not None:
            locations.append(child.span)
    return tuple(locations)


def _consumer_effects(consumer: CompilerDeclaration) -> tuple[tuple[str, Span], ...]:
    """Read existing structural consumer effects without resolving their targets."""

    effects: list[tuple[str, Span]] = []

    def visit(node: Node) -> None:
        if node.name is not None and node.span is not None:
            clause = node.name.strip()
            if node.kind == "blockClause" and _TRANSACTION_HEADER.fullmatch(clause):
                effects.append(("transaction", node.span))
                return
            match = _CONSUMER_EFFECT_CLAUSE.match(clause)
            if match is not None:
                effects.append((match.group(1), node.span))
        for child in node.children:
            visit(child)

    for child in consumer.node.children:
        visit(child)
    return tuple(effects)


def _consumer_idempotency_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Require exactly one idempotency contract for structurally effectful consumers."""

    diagnostics: list[CompilerDiagnostic] = []
    for consumer in project.declaration_names:
        if consumer.declaration.kind != "consumer":
            continue
        if consumer.declaration.span is None:
            continue
        if not _consumer_effects(consumer.declaration):
            continue

        locations = _consumer_idempotency_locations(consumer.declaration)
        if len(locations) == 1:
            continue
        location = locations[1] if len(locations) > 1 else consumer.declaration.span
        consumer_name = (
            consumer.fully_qualified_name or consumer.declaration.name or "<unnamed>"
        )
        subject_name = consumer.declaration.name or "<unnamed>"
        allowed_fixes = (
            (
                CompilerDiagnosticFix(
                    kind="insertClause",
                    text="idempotency: event.eventId retain 30d",
                ),
            )
            if not locations
            else ()
        )
        diagnostics.append(
            CompilerDiagnostic(
                code=CompilerDiagnosticCode.CONSUMER_IDEMPOTENCY,
                phase="policy",
                severity=CompilerDiagnosticSeverity.ERROR,
                message=(
                    f"effectful consumer '{consumer_name}' must declare exactly one "
                    f"'idempotency' clause; found {len(locations)}"
                ),
                source_path=consumer.document.source_path,
                location=location,
                subject=CompilerDiagnosticSubject(kind="consumer", name=subject_name),
                expected="idempotency clause or proven pure body",
                allowed_fixes=allowed_fixes,
                docs="aidl://diagnostics/AIDL-DIST411",
            )
        )
    return tuple(diagnostics)


def _query_side_effects(query: CompilerDeclaration) -> tuple[tuple[str, Span], ...]:
    """Read explicit effect constructs retained inside a query body."""

    effects: list[tuple[str, Span]] = []

    def visit(node: Node) -> None:
        if node.name is not None and node.span is not None:
            clause = node.name.strip()
            if node.kind == "blockClause" and _TRANSACTION_HEADER.fullmatch(clause):
                effects.append(("transaction", node.span))
                return
            match = _QUERY_SIDE_EFFECT_CLAUSE.match(clause)
            if match is not None:
                effects.append((match.group(1), node.span))
        for child in node.children:
            visit(child)

    for child in query.node.children:
        visit(child)
    return tuple(effects)


def _query_side_effect_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Reject explicit write/publish/root-effect constructs inside queries."""

    diagnostics: list[CompilerDiagnostic] = []
    for query in project.declaration_names:
        if query.declaration.kind != "query":
            continue
        query_name = query.fully_qualified_name or query.declaration.name or "<unnamed>"
        subject_name = query.declaration.name or "<unnamed>"
        for effect, location in _query_side_effects(query.declaration):
            diagnostics.append(
                CompilerDiagnostic(
                    code=CompilerDiagnosticCode.QUERY_SIDE_EFFECT,
                    phase="policy",
                    severity=CompilerDiagnosticSeverity.ERROR,
                    message=(
                        f"query '{query_name}' must be side-effect-free; "
                        f"found '{effect}' effect"
                    ),
                    source_path=query.document.source_path,
                    location=location,
                    subject=CompilerDiagnosticSubject(kind="query", name=subject_name),
                    expected="side-effect-free query body",
                    docs="aidl://diagnostics/AIDL-DIST403",
                )
            )
    return tuple(diagnostics)


def _mutation_clause_locations(
    mutation: CompilerDeclaration,
    clause_name: str,
) -> tuple[Span, ...]:
    """Return top-level retained mutation clauses with the requested name."""

    pattern = re.compile(rf"^{re.escape(clause_name)}\s*:")
    locations: list[Span] = []
    for child in mutation.node.children:
        if child.name is None or child.span is None:
            continue
        if pattern.match(child.name.strip()) is not None:
            locations.append(child.span)
    return tuple(locations)


def _mutation_root_effects(
    mutation: CompilerDeclaration,
) -> tuple[tuple[str, Span], ...]:
    """Read only already-defined top-level mutation root-effect constructs."""

    effects: list[tuple[str, Span]] = []
    for child in mutation.node.children:
        if child.name is None or child.span is None:
            continue
        clause = child.name.strip()
        if child.kind == "blockClause" and _TRANSACTION_HEADER.fullmatch(clause):
            effects.append(("transaction", child.span))
            continue
        if _MUTATION_ROOT_CALL.match(clause) is not None:
            effects.append(("call", child.span))
            continue
        start = _MUTATION_ROOT_START.match(clause)
        if start is not None:
            effects.append((f"start {start.group(1)}", child.span))
    return tuple(effects)


def _mutation_contract_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Validate required mutation clauses and exactly one existing root effect."""

    diagnostics: list[CompilerDiagnostic] = []
    for mutation in project.declaration_names:
        if mutation.declaration.kind != "mutation":
            continue
        if mutation.declaration.span is None:
            continue
        mutation_name = (
            mutation.fully_qualified_name or mutation.declaration.name or "<unnamed>"
        )
        subject_name = mutation.declaration.name or "<unnamed>"

        for clause_name in _MUTATION_REQUIRED_CLAUSES:
            locations = _mutation_clause_locations(mutation.declaration, clause_name)
            if len(locations) == 1:
                continue
            location = locations[1] if len(locations) > 1 else mutation.declaration.span
            diagnostics.append(
                CompilerDiagnostic(
                    code=CompilerDiagnosticCode.MUTATION_REQUIRED_CLAUSE,
                    phase="policy",
                    severity=CompilerDiagnosticSeverity.ERROR,
                    message=(
                        f"mutation '{mutation_name}' must declare exactly one "
                        f"'{clause_name}' clause; found {len(locations)}"
                    ),
                    source_path=mutation.document.source_path,
                    location=location,
                    subject=CompilerDiagnosticSubject(kind="mutation", name=subject_name),
                    expected=f"exactly one top-level {clause_name} clause",
                    docs="aidl://diagnostics/AIDL-DIST404",
                )
            )

        root_effects = _mutation_root_effects(mutation.declaration)
        if len(root_effects) != 1:
            location = (
                root_effects[1][1]
                if len(root_effects) > 1
                else mutation.declaration.span
            )
            diagnostics.append(
                CompilerDiagnostic(
                    code=CompilerDiagnosticCode.MUTATION_ROOT_EFFECT,
                    phase="policy",
                    severity=CompilerDiagnosticSeverity.ERROR,
                    message=(
                        f"mutation '{mutation_name}' must have exactly one root effect; "
                        f"found {len(root_effects)}"
                    ),
                    source_path=mutation.document.source_path,
                    location=location,
                    subject=CompilerDiagnosticSubject(kind="mutation", name=subject_name),
                    expected="exactly one top-level root effect",
                    docs="aidl://diagnostics/AIDL-DIST405",
                )
            )

    return tuple(diagnostics)


def _annotation_span(annotation: Mapping[str, Any]) -> Span | None:
    raw = annotation.get("span")
    if not isinstance(raw, Mapping):
        return None
    line = raw.get("line")
    column = raw.get("column")
    offset = raw.get("offset")
    if not all(isinstance(value, int) for value in (line, column, offset)):
        return None
    return Span(line=line, column=column, offset=offset)


def _public_auth_locations(declaration: CompilerDeclaration) -> tuple[Span, ...]:
    locations: list[Span] = []
    for child in declaration.node.children:
        if child.name is None or child.span is None:
            continue
        if _PUBLIC_AUTH.match(child.name.strip()) is not None:
            locations.append(child.span)
    return tuple(locations)


def _public_reason_annotations(
    declaration: CompilerDeclaration,
) -> tuple[tuple[Mapping[str, Any], Span], ...]:
    annotations = declaration.node.attrs.get("annotations", ())
    if not isinstance(annotations, list):
        return ()
    matches: list[tuple[Mapping[str, Any], Span]] = []
    for annotation in annotations:
        if not isinstance(annotation, Mapping):
            continue
        if annotation.get("name") != "publicReason":
            continue
        span = _annotation_span(annotation)
        if span is not None:
            matches.append((annotation, span))
    return tuple(matches)


def _has_valid_public_reason(annotation: Mapping[str, Any]) -> bool:
    arguments = annotation.get("arguments")
    if not isinstance(arguments, str):
        return False
    match = _PUBLIC_REASON_STRING.fullmatch(arguments.strip())
    return match is not None and bool(match.group(1).strip())


def _public_reason_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Validate the existing ``auth: public`` / ``publicReason`` contract."""

    diagnostics: list[CompilerDiagnostic] = []
    for operation in project.declaration_names:
        if operation.declaration.kind not in {"query", "mutation"}:
            continue
        operation_name = (
            operation.fully_qualified_name
            or operation.declaration.name
            or "<unnamed>"
        )
        subject_name = operation.declaration.name or "<unnamed>"
        public_auth = _public_auth_locations(operation.declaration)
        reasons = _public_reason_annotations(operation.declaration)

        if not public_auth:
            for _, location in reasons:
                diagnostics.append(
                    CompilerDiagnostic(
                        code=CompilerDiagnosticCode.PUBLIC_REASON,
                        phase="policy",
                        severity=CompilerDiagnosticSeverity.ERROR,
                        message=(
                            f"@publicReason on {operation.declaration.kind} "
                            f"'{operation_name}' requires 'auth: public'"
                        ),
                        source_path=operation.document.source_path,
                        location=location,
                        subject=CompilerDiagnosticSubject(
                            kind=operation.declaration.kind, name=subject_name
                        ),
                        expected=(
                            "public operations have exactly one non-empty @publicReason; "
                            "non-public operations have none"
                        ),
                        docs="aidl://diagnostics/AIDL-DIST406",
                    )
                )
            continue

        if len(reasons) != 1:
            location = reasons[1][1] if len(reasons) > 1 else public_auth[0]
            diagnostics.append(
                CompilerDiagnostic(
                    code=CompilerDiagnosticCode.PUBLIC_REASON,
                    phase="policy",
                    severity=CompilerDiagnosticSeverity.ERROR,
                    message=(
                        f"public {operation.declaration.kind} '{operation_name}' must "
                        f"declare exactly one @publicReason annotation; found {len(reasons)}"
                    ),
                    source_path=operation.document.source_path,
                    location=location,
                    subject=CompilerDiagnosticSubject(
                        kind=operation.declaration.kind, name=subject_name
                    ),
                    expected=(
                        "public operations have exactly one non-empty @publicReason; "
                        "non-public operations have none"
                    ),
                    docs="aidl://diagnostics/AIDL-DIST406",
                )
            )
            continue

        annotation, location = reasons[0]
        if not _has_valid_public_reason(annotation):
            diagnostics.append(
                CompilerDiagnostic(
                    code=CompilerDiagnosticCode.PUBLIC_REASON,
                    phase="policy",
                    severity=CompilerDiagnosticSeverity.ERROR,
                    message=(
                        f"@publicReason on public {operation.declaration.kind} "
                        f"'{operation_name}' must contain exactly one non-empty string reason"
                    ),
                    source_path=operation.document.source_path,
                    location=location,
                    subject=CompilerDiagnosticSubject(
                        kind=operation.declaration.kind, name=subject_name
                    ),
                    expected=(
                        "public operations have exactly one non-empty @publicReason; "
                        "non-public operations have none"
                    ),
                    docs="aidl://diagnostics/AIDL-DIST406",
                )
            )

    return tuple(diagnostics)


def _api_clause_nodes(
    api: CompilerDeclaration,
    clause_name: str,
) -> tuple[Node, ...]:
    """Return retained top-level API clauses with the requested name."""

    nodes: list[Node] = []
    for child in api.node.children:
        if child.name is None or child.span is None:
            continue
        clause = child.name.strip()
        if clause == clause_name or clause.startswith(f"{clause_name} "):
            nodes.append(child)
    return tuple(nodes)


def _api_clause_value(node: Node, clause_name: str) -> str:
    if node.name is None:
        return ""
    clause = node.name.strip()
    if clause == clause_name:
        return ""
    return clause[len(clause_name) :].strip()


def _api_diagnostic(
    api: CompilerDeclarationName,
    location: Span,
    message: str,
) -> CompilerDiagnostic:
    return CompilerDiagnostic(
        code=CompilerDiagnosticCode.API_CONTRACT,
        phase="policy",
        severity=CompilerDiagnosticSeverity.ERROR,
        message=message,
        source_path=api.document.source_path,
        location=location,
        subject=CompilerDiagnosticSubject(
            kind="api", name=api.declaration.name or "<unnamed>"
        ),
        expected="valid API transport, version, compatibility, and operation mappings",
        docs="aidl://diagnostics/AIDL-DIST412",
    )


def _api_contract_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Validate retained API exposure/version/compatibility operation contracts."""

    diagnostics: list[CompilerDiagnostic] = []
    for api in project.declaration_names:
        if api.declaration.kind != "api" or api.declaration.span is None:
            continue
        api_name = api.fully_qualified_name or api.declaration.name or "<unnamed>"

        scalar_nodes: dict[str, Node | None] = {}
        for clause_name in ("transport", "version", "compatibility"):
            nodes = _api_clause_nodes(api.declaration, clause_name)
            if len(nodes) != 1:
                location = nodes[1].span if len(nodes) > 1 else api.declaration.span
                if location is not None:
                    diagnostics.append(
                        _api_diagnostic(
                            api,
                            location,
                            f"api '{api_name}' must declare exactly one '{clause_name}' clause; found {len(nodes)}",
                        )
                    )
                scalar_nodes[clause_name] = None
            else:
                scalar_nodes[clause_name] = nodes[0]

        transport = scalar_nodes["transport"]
        if transport is not None and transport.span is not None:
            value = _api_clause_value(transport, "transport")
            if value not in _API_TRANSPORTS:
                diagnostics.append(
                    _api_diagnostic(
                        api,
                        transport.span,
                        f"api '{api_name}' transport must be one of rest, rpc, graphql; found '{value}'",
                    )
                )

        version = scalar_nodes["version"]
        if version is not None and version.span is not None:
            value = _api_clause_value(version, "version")
            if _API_POSITIVE_MAJOR.fullmatch(value) is None:
                diagnostics.append(
                    _api_diagnostic(
                        api,
                        version.span,
                        f"api '{api_name}' version must be a positive major integer; found '{value}'",
                    )
                )

        compatibility = scalar_nodes["compatibility"]
        if compatibility is not None and compatibility.span is not None:
            value = _api_clause_value(compatibility, "compatibility")
            if value not in _API_COMPATIBILITY_MODES:
                diagnostics.append(
                    _api_diagnostic(
                        api,
                        compatibility.span,
                        f"api '{api_name}' compatibility must be one of none, backward, forward, full; found '{value}'",
                    )
                )

        operation_nodes = _api_clause_nodes(api.declaration, "operations")
        if len(operation_nodes) != 1:
            location = (
                operation_nodes[1].span
                if len(operation_nodes) > 1
                else api.declaration.span
            )
            if location is not None:
                diagnostics.append(
                    _api_diagnostic(
                        api,
                        location,
                        f"api '{api_name}' must declare exactly one non-empty 'operations' list",
                    )
                )
            continue

        operations_node = operation_nodes[0]
        if operations_node.span is None:
            continue
        value = _api_clause_value(operations_node, "operations")
        if not (value.startswith("[") and value.endswith("]")):
            diagnostics.append(
                _api_diagnostic(
                    api,
                    operations_node.span,
                    f"api '{api_name}' must declare exactly one non-empty 'operations' list",
                )
            )
            continue
        items = tuple(
            item.strip() for item in value[1:-1].split(",") if item.strip()
        )
        if not items:
            diagnostics.append(
                _api_diagnostic(
                    api,
                    operations_node.span,
                    f"api '{api_name}' must declare exactly one non-empty 'operations' list",
                )
            )
            continue

        seen_mappings: set[tuple[Path, int]] = set()
        for item in items:
            match = _API_OPERATION_ITEM.fullmatch(item)
            if match is None:
                diagnostics.append(
                    _api_diagnostic(
                        api,
                        operations_node.span,
                        f"api '{api_name}' operation item '{item}' must be explicit 'query NAME' or 'mutation NAME'",
                    )
                )
                continue

            kind = match.group(1)
            reference = re.sub(r"\s*\.\s*", ".", match.group(2))
            candidates = _resolve_declaration_reference(
                project,
                api,
                reference,
                frozenset({"query", "mutation"}),
            )
            matching = tuple(
                candidate
                for candidate in candidates
                if candidate.declaration.kind == kind
            )
            if len(matching) == 1:
                target = matching[0]
                identity = _declaration_identity(target)
                if identity in seen_mappings:
                    target_name = (
                        target.fully_qualified_name
                        or target.declaration.name
                        or "<unnamed>"
                    )
                    diagnostics.append(
                        _api_diagnostic(
                            api,
                            operations_node.span,
                            f"api '{api_name}' maps operation '{target_name}' more than once",
                        )
                    )
                    continue
                seen_mappings.add(identity)
                continue

            if len(candidates) == 1:
                diagnostics.append(
                    _api_diagnostic(
                        api,
                        operations_node.span,
                        f"api '{api_name}' maps {kind} '{reference}' to declaration kind '{candidates[0].declaration.kind}'",
                    )
                )
                continue

            diagnostics.append(
                _api_diagnostic(
                    api,
                    operations_node.span,
                    f"api '{api_name}' operation {kind} '{reference}' must resolve uniquely; found {len(matching)} matching {kind} declarations",
                )
            )

    return tuple(diagnostics)


def _direct_collection_return(declaration: CompilerDeclaration) -> str | None:
    """Return a direct collection return form without resolving aliases/types."""

    raw = declaration.node.attrs.get("returns")
    if not isinstance(raw, str):
        return None
    compact = re.sub(r"\s+", "", raw)
    if compact.startswith("Page<") and compact.endswith(">") and len(compact) > 6:
        return compact
    if compact.startswith("[") and compact.endswith("]") and len(compact) > 2:
        return compact
    return None


def _query_read_paths(
    declaration: CompilerDeclaration,
) -> tuple[tuple[str, Span], ...]:
    """Project existing top-level ``read:`` paths and dotted continuations."""

    paths: list[tuple[str, Span]] = []
    children = declaration.node.children
    index = 0
    while index < len(children):
        child = children[index]
        if child.name is None or child.span is None:
            index += 1
            continue
        clause = child.name.strip()
        if _QUERY_READ.match(clause) is None:
            index += 1
            continue

        parts = [clause]
        next_index = index + 1
        while next_index < len(children):
            continuation = children[next_index]
            if continuation.name is None:
                break
            continuation_text = continuation.name.strip()
            if not continuation_text.startswith("."):
                break
            parts.append(continuation_text)
            next_index += 1
        paths.append((" ".join(parts), child.span))
        index = next_index
    return tuple(paths)


def _read_path_has_explicit_bound(path: str) -> bool:
    """Recognize only already-parseable page/limit calls in the retained path."""

    compact = re.sub(r"\s+", "", path)
    return ".page(" in compact or ".limit(" in compact


def _bounded_collection_query_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Require direct collection queries to expose an explicit read-path bound."""

    diagnostics: list[CompilerDiagnostic] = []
    for query in project.declaration_names:
        if query.declaration.kind != "query" or query.declaration.span is None:
            continue
        collection_return = _direct_collection_return(query.declaration)
        if collection_return is None:
            continue

        read_paths = _query_read_paths(query.declaration)
        if any(_read_path_has_explicit_bound(path) for path, _ in read_paths):
            continue

        query_name = query.fully_qualified_name or query.declaration.name or "<unnamed>"
        subject_name = query.declaration.name or "<unnamed>"
        location = read_paths[0][1] if read_paths else query.declaration.span
        diagnostics.append(
            CompilerDiagnostic(
                code=CompilerDiagnosticCode.BOUNDED_COLLECTION_QUERY,
                phase="policy",
                severity=CompilerDiagnosticSeverity.ERROR,
                message=(
                    f"collection query '{query_name}' returning '{collection_return}' "
                    "must declare an explicit page or limit bound in its read path"
                ),
                source_path=query.document.source_path,
                location=location,
                subject=CompilerDiagnosticSubject(kind="query", name=subject_name),
                expected="explicit page or limit bound in read path",
                docs="aidl://diagnostics/AIDL-DIST413",
            )
        )
    return tuple(diagnostics)


def collect_compiler_diagnostics(
    project: CompilerProject,
    parser_diagnostics: Mapping[Path, Iterable[ParserDiagnostic]] | None = None,
) -> tuple[CompilerDiagnostic, ...]:
    """Collect diagnostics without pulling forward later semantic rules."""

    diagnostics: list[CompilerDiagnostic] = []
    parser_diagnostics = parser_diagnostics or {}

    for document in project.documents:
        for diagnostic in parser_diagnostics.get(document.source_path, ()):
            diagnostics.append(
                CompilerDiagnostic(
                    code=CompilerDiagnosticCode.PARSE_FAILURE,
                    phase="parse",
                    severity=_parser_severity(diagnostic.severity),
                    message=diagnostic.message,
                    source_path=document.source_path,
                    location=diagnostic.start,
                )
            )

    for resolution in project.import_resolutions:
        if (
            resolution.import_.name is None
            or resolution.import_.span is None
            or resolution.declarations
        ):
            continue
        diagnostics.append(
            CompilerDiagnostic(
                code=CompilerDiagnosticCode.UNRESOLVED_IMPORT,
                phase="resolve",
                severity=CompilerDiagnosticSeverity.ERROR,
                message=f"unresolved import '{resolution.import_.name}'",
                source_path=resolution.document.source_path,
                location=resolution.import_.span,
            )
        )

    for fully_qualified_name, matches in project.symbol_table.declarations_by_fqn.items():
        for duplicate in matches[1:]:
            if duplicate.declaration.span is None:
                continue
            diagnostics.append(
                CompilerDiagnostic(
                    code=CompilerDiagnosticCode.DUPLICATE_DECLARATION,
                    phase="resolve",
                    severity=CompilerDiagnosticSeverity.ERROR,
                    message=f"duplicate declaration '{fully_qualified_name}'",
                    source_path=duplicate.document.source_path,
                    location=duplicate.declaration.span,
                )
            )

    owners_by_entity = _entity_owner_index(project)
    diagnostics.extend(_entity_owner_diagnostics(project, owners_by_entity))
    diagnostics.extend(_cross_service_ref_diagnostics(project, owners_by_entity))
    diagnostics.extend(_transaction_boundary_diagnostics(project, owners_by_entity))
    diagnostics.extend(_transaction_isolation_diagnostics(project))
    diagnostics.extend(_transaction_outbox_diagnostics(project))
    diagnostics.extend(_consumer_idempotency_diagnostics(project))
    diagnostics.extend(_query_side_effect_diagnostics(project))
    diagnostics.extend(_mutation_contract_diagnostics(project))
    diagnostics.extend(_public_reason_diagnostics(project))
    diagnostics.extend(_api_contract_diagnostics(project))
    diagnostics.extend(_bounded_collection_query_diagnostics(project))

    document_order = {
        document.source_path: index for index, document in enumerate(project.documents)
    }
    phase_order = {"parse": 0, "resolve": 1, "policy": 2}
    severity_order = {
        CompilerDiagnosticSeverity.ERROR: 0,
        CompilerDiagnosticSeverity.WARNING: 1,
        CompilerDiagnosticSeverity.INFO: 2,
    }
    diagnostics.sort(
        key=lambda diagnostic: (
            document_order.get(diagnostic.source_path, len(document_order)),
            diagnostic.location.offset,
            phase_order.get(diagnostic.phase, len(phase_order)),
            severity_order[diagnostic.severity],
            diagnostic.code.value,
            diagnostic.message,
        )
    )
    return tuple(diagnostics)


def load_compiler_analysis(paths: Iterable[Path]) -> CompilerAnalysis:
    """Load a project and preserve parser diagnostics for compiler reporting."""

    documents = []
    parser_diagnostics: dict[Path, tuple[ParserDiagnostic, ...]] = {}
    for source_path in iter_aidl_files(list(paths)):
        program, diagnostics, _ = parse_text(source_path.read_text(encoding="utf-8"))
        documents.append(compiler_document_from_ast(source_path, program))
        parser_diagnostics[source_path] = tuple(diagnostics)

    project = compiler_project_from_documents(documents)
    return CompilerAnalysis(
        project=project,
        diagnostics=collect_compiler_diagnostics(project, parser_diagnostics),
    )
