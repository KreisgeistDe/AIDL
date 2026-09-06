"""Compiler-owned declaration and diagnostic documentation for editor consumers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from tools.aidl_parser import Lexer
from tools.compiler_diagnostics import CompilerAnalysis, CompilerDiagnostic
from tools.compiler_project import CompilerDeclarationName
from tools.compiler_resolution import CompilerReferenceTarget, resolve_project_reference


@dataclass(frozen=True)
class CompilerDeclarationDocumentation:
    fully_qualified_name: str
    kind: str
    source_path: Path
    line: int
    column: int
    offset: int
    representation: str

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
            "representation": self.representation,
        }


@dataclass(frozen=True)
class CompilerDocumentationResult:
    status: str
    declaration: CompilerDeclarationDocumentation | None = None
    diagnostics: tuple[CompilerDiagnostic, ...] = ()

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "diagnostics": [diagnostic.to_json() for diagnostic in self.diagnostics],
        }
        if self.declaration is not None:
            payload["declaration"] = self.declaration.to_json()
        return payload


def _normalized(path: Path) -> Path:
    return path.absolute().resolve(strict=False)


def _source_text(source_path: Path, source_texts: Mapping[Path, str] | None) -> str:
    if source_texts is not None:
        normalized = _normalized(source_path)
        if normalized in source_texts:
            return source_texts[normalized]
    return source_path.read_text(encoding="utf-8")


def document_project_source(
    analysis: CompilerAnalysis,
    source_path: Path,
    offset: int,
    source_texts: Mapping[Path, str] | None = None,
) -> CompilerDocumentationResult:
    """Return compiler-owned docs at one source position without guessing semantics.

    ``source_texts`` optionally supplies exact in-memory snapshot text for the source
    and target declarations. Omitting it preserves the saved-file contract.
    """

    normalized_source = _normalized(source_path)
    document = next(
        (
            item
            for item in analysis.project.documents
            if _normalized(item.source_path) == normalized_source
        ),
        None,
    )
    if document is None:
        return CompilerDocumentationResult("invalid")
    try:
        text = _source_text(document.source_path, source_texts)
    except OSError:
        return CompilerDocumentationResult("invalid")
    if offset < 0 or offset >= len(text):
        return CompilerDocumentationResult("invalid")

    tokens, lexer_diagnostics = Lexer(text).tokenize()
    if lexer_diagnostics:
        return CompilerDocumentationResult("invalid")
    token = next(
        (
            item
            for item in tokens
            if item.kind != "EOF" and item.start.offset <= offset < item.end.offset
        ),
        None,
    )
    if token is None:
        return CompilerDocumentationResult("invalid")

    resolution = resolve_project_reference(
        analysis.project,
        source_path,
        offset,
        source_texts=source_texts,
    )
    declaration = None
    if resolution.status == "resolved" and resolution.target is not None:
        declaration_name = _declaration_for_target(analysis, resolution.target)
        if declaration_name is not None:
            declaration = _declaration_documentation(declaration_name, source_texts)

    diagnostics = _diagnostics_for_position(
        analysis.diagnostics,
        normalized_source,
        token.start.offset,
    )

    if declaration is not None or diagnostics:
        return CompilerDocumentationResult(
            "resolved",
            declaration=declaration,
            diagnostics=diagnostics,
        )
    if resolution.status in {"unresolved", "ambiguous", "invalid"}:
        return CompilerDocumentationResult(resolution.status)
    return CompilerDocumentationResult("invalid")


def _declaration_for_target(
    analysis: CompilerAnalysis,
    target: CompilerReferenceTarget,
) -> CompilerDeclarationName | None:
    matches = analysis.project.symbol_table.lookup_declarations(target.fully_qualified_name)
    exact = [
        candidate
        for candidate in matches
        if _normalized(candidate.document.source_path) == _normalized(target.source_path)
        and candidate.declaration.name == target.fully_qualified_name.rsplit(".", 1)[-1]
    ]
    return exact[0] if len(exact) == 1 else None


def _declaration_documentation(
    declaration_name: CompilerDeclarationName,
    source_texts: Mapping[Path, str] | None = None,
) -> CompilerDeclarationDocumentation | None:
    declaration = declaration_name.declaration
    if (
        declaration_name.fully_qualified_name is None
        or declaration.name is None
        or declaration.span is None
    ):
        return None
    try:
        text = _source_text(declaration_name.document.source_path, source_texts)
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
    header = " ".join(text[start:header_end].strip().split())
    if not header:
        header = f"{declaration.kind} {declaration.name}"

    target = _target_location(declaration_name, source_texts)
    if target is None:
        return None
    return CompilerDeclarationDocumentation(
        fully_qualified_name=declaration_name.fully_qualified_name,
        kind=declaration.kind,
        source_path=declaration_name.document.source_path,
        line=target.line,
        column=target.column,
        offset=target.offset,
        representation=header,
    )


def _target_location(
    declaration_name: CompilerDeclarationName,
    source_texts: Mapping[Path, str] | None = None,
):
    declaration = declaration_name.declaration
    if declaration.name is None or declaration.span is None:
        return None
    try:
        text = _source_text(declaration_name.document.source_path, source_texts)
    except OSError:
        return None
    tokens, diagnostics = Lexer(text).tokenize()
    if diagnostics:
        return None
    end = declaration.end.offset if declaration.end is not None else len(text)
    token = next(
        (
            item
            for item in tokens
            if item.kind in {"IDENT", "KEYWORD"}
            and item.value == declaration.name
            and declaration.span.offset <= item.start.offset < end
        ),
        None,
    )
    return token.start if token is not None else None


def _diagnostics_for_position(
    diagnostics: Iterable[CompilerDiagnostic],
    normalized_source: Path,
    token_start: int,
) -> tuple[CompilerDiagnostic, ...]:
    return tuple(
        diagnostic
        for diagnostic in diagnostics
        if _normalized(diagnostic.source_path) == normalized_source
        and diagnostic.location.offset == token_start
    )
