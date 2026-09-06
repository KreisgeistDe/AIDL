"""Compiler-owned declaration dependencies for agent tooling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from tools.compiler_diagnostics import CompilerAnalysis
from tools.compiler_inspection import inspect_project_declaration
from tools.compiler_ir import IrBuildError, build_canonical_ir


MAX_DIRECT_DEPENDENCIES = 128
MAX_TRANSITIVE_DEPENDENCIES = 128


@dataclass(frozen=True)
class CompilerDependency:
    declaration_id: str
    fully_qualified_name: str
    kind: str

    def to_json(self) -> dict[str, str]:
        return {
            "declarationId": self.declaration_id,
            "fullyQualifiedName": self.fully_qualified_name,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class CompilerDependenciesResult:
    status: str
    query: str
    declaration: CompilerDependency | None = None
    dependencies: tuple[CompilerDependency, ...] = ()
    transitive_dependencies: tuple[CompilerDependency, ...] = ()
    direct_total: int = 0
    transitive_total: int = 0
    direct_truncated: bool = False
    transitive_truncated: bool = False
    match_count: int | None = None

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {"status": self.status, "query": self.query}
        if self.declaration is not None:
            payload["declaration"] = self.declaration.to_json()
            payload["dependencies"] = [item.to_json() for item in self.dependencies]
            payload["transitiveDependencies"] = [
                item.to_json() for item in self.transitive_dependencies
            ]
            payload["totals"] = {
                "directDependencies": self.direct_total,
                "transitiveDependencies": self.transitive_total,
            }
            payload["truncated"] = {
                "directDependencies": self.direct_truncated,
                "transitiveDependencies": self.transitive_truncated,
            }
        if self.match_count is not None:
            payload["matchCount"] = self.match_count
        return payload


def collect_project_dependencies(
    analysis: CompilerAnalysis,
    fully_qualified_name: str,
) -> CompilerDependenciesResult:
    """Return bounded direct and transitive Canonical-IR declaration references.

    Name/error handling is delegated to the existing compiler inspection boundary.
    The graph contains only declaration IDs already materialized inside Canonical-IR
    declaration nodes. Transitivity is the cycle-safe reachability closure over that
    exact direct relation; no source-text, PSI, or new semantic inference is used.
    """

    inspected = inspect_project_declaration(analysis, fully_qualified_name)
    if inspected.status != "resolved" or inspected.declaration is None:
        return CompilerDependenciesResult(
            status=inspected.status,
            query=inspected.query,
            match_count=inspected.match_count,
        )

    canonical = inspected.declaration.canonical
    declaration_id = canonical.get("declarationId")
    if not isinstance(declaration_id, str):
        raise IrBuildError(
            f"declaration '{fully_qualified_name}' has no Canonical-IR declarationId"
        )

    document = build_canonical_ir(analysis)
    canonical_by_id = _canonical_declarations_by_id(document)
    by_id = _declaration_index(analysis, document)
    declaration = CompilerDependency(
        declaration_id=declaration_id,
        fully_qualified_name=fully_qualified_name,
        kind=inspected.declaration.kind,
    )

    known_ids = set(by_id)
    direct_by_id = {
        item_id: _direct_dependency_ids(node, known_ids, item_id)
        for item_id, node in canonical_by_id.items()
        if item_id in known_ids
    }
    direct_ids = set(direct_by_id.get(declaration_id, ()))
    direct_ids.discard(declaration_id)

    reachable_ids: set[str] = set()
    pending = list(sorted(direct_ids, reverse=True))
    while pending:
        current = pending.pop()
        if current == declaration_id or current in reachable_ids:
            continue
        reachable_ids.add(current)
        for nested in sorted(direct_by_id.get(current, ()), reverse=True):
            if nested != declaration_id and nested not in reachable_ids:
                pending.append(nested)

    transitive_ids = reachable_ids - direct_ids
    direct_all = _sorted_dependencies(by_id, direct_ids)
    transitive_all = _sorted_dependencies(by_id, transitive_ids)
    dependencies = direct_all[:MAX_DIRECT_DEPENDENCIES]
    transitive_dependencies = transitive_all[:MAX_TRANSITIVE_DEPENDENCIES]

    return CompilerDependenciesResult(
        status="resolved",
        query=fully_qualified_name,
        declaration=declaration,
        dependencies=dependencies,
        transitive_dependencies=transitive_dependencies,
        direct_total=len(direct_all),
        transitive_total=len(transitive_all),
        direct_truncated=len(direct_all) > MAX_DIRECT_DEPENDENCIES,
        transitive_truncated=len(transitive_all) > MAX_TRANSITIVE_DEPENDENCIES,
    )


def _sorted_dependencies(
    by_id: Mapping[str, CompilerDependency],
    declaration_ids: set[str],
) -> tuple[CompilerDependency, ...]:
    return tuple(
        sorted(
            (by_id[item] for item in declaration_ids if item in by_id),
            key=lambda item: (
                item.fully_qualified_name,
                item.kind,
                item.declaration_id,
            ),
        )
    )


def _direct_dependency_ids(
    canonical: Mapping[str, Any],
    known_ids: set[str],
    declaration_id: str,
) -> set[str]:
    referenced_ids: set[str] = set()
    _collect_known_declaration_ids(canonical, known_ids, referenced_ids)
    referenced_ids.discard(declaration_id)
    return referenced_ids


def _declaration_index(
    analysis: CompilerAnalysis,
    document: Mapping[str, Any],
) -> dict[str, CompilerDependency]:
    kinds_by_fqn: dict[str, str] = {}
    for item in analysis.project.declaration_names:
        if item.fully_qualified_name:
            kinds_by_fqn.setdefault(item.fully_qualified_name, item.declaration.kind)

    result: dict[str, CompilerDependency] = {}
    for item in _canonical_declarations(document):
        declaration_id = item.get("declarationId")
        fqn = item.get("fqn")
        if not isinstance(declaration_id, str) or not isinstance(fqn, str):
            continue
        kind = kinds_by_fqn.get(fqn)
        if kind is None:
            canonical_kind = item.get("kind")
            if not isinstance(canonical_kind, str) or not canonical_kind:
                continue
            kind = canonical_kind
        result.setdefault(
            declaration_id,
            CompilerDependency(
                declaration_id=declaration_id,
                fully_qualified_name=fqn,
                kind=kind,
            ),
        )
    return result


def _canonical_declarations_by_id(
    document: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for item in _canonical_declarations(document):
        declaration_id = item.get("declarationId")
        if isinstance(declaration_id, str):
            result.setdefault(declaration_id, item)
    return result


def _canonical_declarations(document: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: object) -> None:
        if isinstance(value, Mapping):
            candidates.append(value)

    add(document.get("app"))
    for value in document.get("declarations", ()):
        add(value)
    system = document.get("system")
    add(system)
    if isinstance(system, Mapping):
        for value in system.get("services", ()):
            add(value)
        for value in system.get("resources", ()):
            add(value)
    for value in document.get("deployments", ()):
        add(value)
    return tuple(candidates)


def _collect_known_declaration_ids(
    value: object,
    known_ids: set[str],
    result: set[str],
) -> None:
    if isinstance(value, Mapping):
        for nested in value.values():
            _collect_known_declaration_ids(nested, known_ids, result)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            _collect_known_declaration_ids(nested, known_ids, result)
        return
    if isinstance(value, str) and value in known_ids:
        result.add(value)
