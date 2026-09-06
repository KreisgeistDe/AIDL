"""Compiler-authoritative diagnostic explanations for one declaration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.compiler_diagnostics import CompilerAnalysis, CompilerDiagnostic
from tools.compiler_project import CompilerDeclarationName


_FQN_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*)+$"
)
_MAX_EXPLANATIONS = 64


@dataclass(frozen=True)
class CompilerExplanationDeclaration:
    fully_qualified_name: str
    kind: str
    source_path: Path
    line: int
    column: int
    offset: int

    def to_json(self) -> dict[str, object]:
        return {
            "fullyQualifiedName": self.fully_qualified_name,
            "kind": self.kind,
            "location": {
                "file": str(self.source_path),
                "line": self.line,
                "column": self.column,
                "offset": self.offset,
            },
        }


@dataclass(frozen=True)
class CompilerExplanation:
    diagnostic: CompilerDiagnostic

    def to_json(self) -> dict[str, object]:
        diagnostic = self.diagnostic.to_json()
        rule: dict[str, object] = {
            "code": diagnostic["code"],
            "phase": diagnostic["phase"],
            "message": diagnostic["message"],
        }
        if "expected" in diagnostic:
            rule["expected"] = diagnostic["expected"]
        if "docs" in diagnostic:
            rule["docs"] = diagnostic["docs"]

        evidence: dict[str, object] = {"location": diagnostic["location"]}
        if "subject" in diagnostic:
            evidence["subject"] = diagnostic["subject"]

        return {
            "rule": rule,
            "evidence": evidence,
            "remediation": list(diagnostic.get("allowedFixes", [])),
        }


@dataclass(frozen=True)
class CompilerExplanationResult:
    status: str
    query: str
    declaration: CompilerExplanationDeclaration | None = None
    explanations: tuple[CompilerExplanation, ...] = ()
    total_diagnostic_count: int | None = None
    truncated: bool | None = None
    match_count: int | None = None

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {"status": self.status, "query": self.query}
        if self.declaration is not None:
            payload["declaration"] = self.declaration.to_json()
            payload["explanations"] = [item.to_json() for item in self.explanations]
            payload["totalDiagnosticCount"] = self.total_diagnostic_count or 0
            payload["truncated"] = bool(self.truncated)
        if self.match_count is not None:
            payload["matchCount"] = self.match_count
        return payload


def explain_project_declaration(
    analysis: CompilerAnalysis,
    fully_qualified_name: str,
) -> CompilerExplanationResult:
    """Project existing compiler diagnostics for exactly one compiler symbol.

    The rule, evidence, and remediation fields are copied only from diagnostics
    already emitted by the compiler. This layer does not infer rules or fixes.
    """

    if not _FQN_PATTERN.fullmatch(fully_qualified_name):
        return CompilerExplanationResult("invalid", fully_qualified_name)

    matches = analysis.project.symbol_table.lookup_declarations(fully_qualified_name)
    if not matches:
        return CompilerExplanationResult("unknown", fully_qualified_name)
    if len(matches) != 1:
        return CompilerExplanationResult(
            "ambiguous", fully_qualified_name, match_count=len(matches)
        )

    item = matches[0]
    declaration = _declaration(item)
    if declaration is None:
        return CompilerExplanationResult("invalid", fully_qualified_name)

    diagnostics = tuple(
        sorted(
            _diagnostics_for_declaration(analysis, item),
            key=lambda diagnostic: (
                diagnostic.location.offset,
                diagnostic.code.value,
                diagnostic.message,
            ),
        )
    )
    visible = diagnostics[:_MAX_EXPLANATIONS]
    return CompilerExplanationResult(
        "resolved",
        fully_qualified_name,
        declaration=declaration,
        explanations=tuple(CompilerExplanation(item) for item in visible),
        total_diagnostic_count=len(diagnostics),
        truncated=len(diagnostics) > len(visible),
    )


def _declaration(
    item: CompilerDeclarationName,
) -> CompilerExplanationDeclaration | None:
    declaration = item.declaration
    if item.fully_qualified_name is None or declaration.span is None:
        return None
    return CompilerExplanationDeclaration(
        fully_qualified_name=item.fully_qualified_name,
        kind=declaration.kind,
        source_path=item.document.source_path,
        line=declaration.span.line,
        column=declaration.span.column,
        offset=declaration.span.offset,
    )


def _diagnostics_for_declaration(
    analysis: CompilerAnalysis,
    item: CompilerDeclarationName,
) -> tuple[CompilerDiagnostic, ...]:
    declaration = item.declaration
    if declaration.span is None:
        return ()
    start = declaration.span.offset
    end = declaration.end.offset if declaration.end is not None else None
    matches: list[CompilerDiagnostic] = []
    for diagnostic in analysis.diagnostics:
        if diagnostic.source_path != item.document.source_path:
            continue
        offset = diagnostic.location.offset
        if offset < start:
            continue
        if end is not None and offset >= end:
            continue
        matches.append(diagnostic)
    return tuple(matches)
