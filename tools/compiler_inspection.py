"""Compiler-owned fully-qualified declaration inspection for agent tooling."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from tools.compiler_diagnostics import CompilerAnalysis
from tools.compiler_ir import IrBuildError, build_canonical_ir
from tools.compiler_project import CompilerDeclarationName


_FQN_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*)+$"
)


@dataclass(frozen=True)
class CompilerInspectionDeclaration:
    fully_qualified_name: str
    name: str
    kind: str
    module: str
    exported: bool
    source_path: Path
    line: int
    column: int
    offset: int
    representation: str
    canonical: Mapping[str, Any]

    def to_json(self) -> dict[str, object]:
        return {
            "fullyQualifiedName": self.fully_qualified_name,
            "name": self.name,
            "kind": self.kind,
            "module": self.module,
            "exported": self.exported,
            "location": {
                "file": str(self.source_path),
                "line": self.line,
                "column": self.column,
                "offset": self.offset,
            },
            "representation": self.representation,
            "canonical": dict(self.canonical),
        }


@dataclass(frozen=True)
class CompilerInspectionResult:
    status: str
    query: str
    declaration: CompilerInspectionDeclaration | None = None
    match_count: int | None = None

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {"status": self.status, "query": self.query}
        if self.declaration is not None:
            payload["declaration"] = self.declaration.to_json()
        if self.match_count is not None:
            payload["matchCount"] = self.match_count
        return payload


def inspect_project_declaration(
    analysis: CompilerAnalysis,
    fully_qualified_name: str,
) -> CompilerInspectionResult:
    """Inspect exactly one compiler-indexed declaration by FQN.

    Name lookup comes exclusively from the compiler project symbol table. The
    semantic payload is the matching Canonical-IR node from the already-owned IR
    projection; this layer does not infer additional language meaning.
    """

    if not _FQN_PATTERN.fullmatch(fully_qualified_name):
        return CompilerInspectionResult("invalid", fully_qualified_name)

    matches = analysis.project.symbol_table.lookup_declarations(fully_qualified_name)
    if not matches:
        return CompilerInspectionResult("unknown", fully_qualified_name)
    if len(matches) != 1:
        return CompilerInspectionResult(
            "ambiguous", fully_qualified_name, match_count=len(matches)
        )

    canonical_ir = build_canonical_ir(analysis)
    canonical = _canonical_declaration(canonical_ir, fully_qualified_name)
    if canonical is None:
        raise IrBuildError(
            f"declaration '{fully_qualified_name}' has no Canonical-IR projection"
        )

    declaration = _inspection_declaration(matches[0], canonical)
    if declaration is None:
        return CompilerInspectionResult("invalid", fully_qualified_name)
    return CompilerInspectionResult(
        "resolved", fully_qualified_name, declaration=declaration
    )


def _canonical_declaration(
    document: Mapping[str, Any], fully_qualified_name: str
) -> Mapping[str, Any] | None:
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

    matches = [item for item in candidates if item.get("fqn") == fully_qualified_name]
    return matches[0] if len(matches) == 1 else None


def _inspection_declaration(
    item: CompilerDeclarationName,
    canonical: Mapping[str, Any],
) -> CompilerInspectionDeclaration | None:
    declaration = item.declaration
    module = item.document.module
    if (
        item.fully_qualified_name is None
        or declaration.name is None
        or declaration.span is None
        or module is None
        or module.name is None
    ):
        return None
    try:
        text = item.document.source_path.read_text(encoding="utf-8")
    except OSError:
        return None

    start = declaration.span.offset
    end = declaration.end.offset if declaration.end is not None else len(text)
    if start < 0 or start >= len(text) or end <= start:
        return None
    header_end = end
    for marker in ("{", "\n", "\r"):
        position = text.find(marker, start, end)
        if position != -1:
            header_end = min(header_end, position)
    representation = " ".join(text[start:header_end].strip().split())
    if not representation:
        representation = f"{declaration.kind} {declaration.name}"

    return CompilerInspectionDeclaration(
        fully_qualified_name=item.fully_qualified_name,
        name=declaration.name,
        kind=declaration.kind,
        module=module.name,
        exported=declaration.exported,
        source_path=item.document.source_path,
        line=declaration.span.line,
        column=declaration.span.column,
        offset=declaration.span.offset,
        representation=representation,
        canonical=canonical,
    )
