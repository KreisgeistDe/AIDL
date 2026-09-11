"""Compiler-owned, diagnostic-neutral evidence for operation auth clauses.

This module does not admit ``auth`` into M10.1 production normalization.  It
projects only facts already present in the parser AST and compiler symbol table
so a later contract-backed slice can make an explicit admission decision.
"""
from __future__ import annotations

from dataclasses import dataclass

try:
    from .compiler_project import CompilerDeclarationName, CompilerProject
    from .compiler_typecheck import _clauses, _resolve
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from compiler_project import CompilerDeclarationName, CompilerProject
    from compiler_typecheck import _clauses, _resolve


AUTH_BUILTIN_MODES = frozenset({"public", "authenticated", "service"})


@dataclass(frozen=True)
class OperationAuthEvidence:
    """One parser-owned auth clause plus compiler-owned lookup evidence.

    ``source`` is the parser-preserved token identity after the existing generic
    clause parser has normalized whitespace between tokens.  Built-in modes are
    complete because their meaning is fixed by the current grammar.  A
    qualified name can be resolved deterministically with the existing symbol
    table, but no compiler-owned semantic target kind for auth profiles exists
    yet; therefore every qualified-name state remains deliberately incomplete.
    """

    source: str
    mode: str
    resolution: str
    target: str | None = None
    target_kind: str | None = None

    @property
    def complete(self) -> bool:
        return self.mode == "builtin" and self.resolution == "builtin"


def _qualified_auth_evidence(
    project: CompilerProject,
    item: CompilerDeclarationName,
    source: str,
) -> OperationAuthEvidence:
    matches = _resolve(project, item, source)
    if not matches:
        return OperationAuthEvidence(source, "qualified_name", "unresolved")
    if len(matches) > 1:
        return OperationAuthEvidence(source, "qualified_name", "ambiguous")
    target = matches[0]
    return OperationAuthEvidence(
        source,
        "qualified_name",
        "resolved",
        target.fully_qualified_name or source,
        target.declaration.kind,
    )


def operation_auth_evidence(
    project: CompilerProject,
    item: CompilerDeclarationName,
) -> tuple[OperationAuthEvidence, ...]:
    """Return ordered auth evidence for one query/mutation without diagnostics.

    The function intentionally owns no auth grammar, text splitter, resolver, or
    target-kind policy.  Clause discovery and name lookup are delegated to the
    existing compiler/typecheck primitives.  Qualified names stay incomplete
    even when lookup is unique until a separately authorized auth target kind is
    represented by the compiler and frozen contract.
    """

    if item.declaration.kind not in {"query", "mutation"}:
        return ()

    evidence: list[OperationAuthEvidence] = []
    for raw, _ in _clauses(item, "auth"):
        source = raw.strip()
        if source in AUTH_BUILTIN_MODES:
            evidence.append(OperationAuthEvidence(source, "builtin", "builtin"))
        else:
            evidence.append(_qualified_auth_evidence(project, item, source))
    return tuple(evidence)
