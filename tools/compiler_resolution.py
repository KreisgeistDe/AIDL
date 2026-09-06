"""Compiler-owned source reference resolution for editor/navigation consumers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from tools.aidl_parser import Lexer, Span, Token
from tools.compiler_project import CompilerDeclarationName, CompilerProject


@dataclass(frozen=True)
class CompilerReferenceTarget:
    fully_qualified_name: str
    kind: str
    source_path: Path
    location: Span

    def to_json(self) -> dict[str, object]:
        return {
            "fullyQualifiedName": self.fully_qualified_name,
            "kind": self.kind,
            "location": {
                "file": str(self.source_path),
                "line": self.location.line,
                "column": self.location.column,
                "offset": self.location.offset,
            },
        }


@dataclass(frozen=True)
class CompilerReferenceResolution:
    status: str
    reference: str | None = None
    target: CompilerReferenceTarget | None = None

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {"status": self.status}
        if self.reference is not None:
            payload["reference"] = self.reference
        if self.target is not None:
            payload["target"] = self.target.to_json()
        return payload


def _normalized(path: Path) -> Path:
    return path.absolute().resolve(strict=False)


def _source_text(
    source_path: Path,
    source_texts: Mapping[Path, str] | None,
) -> str:
    if source_texts is not None:
        normalized = _normalized(source_path)
        if normalized in source_texts:
            return source_texts[normalized]
    return source_path.read_text(encoding="utf-8")


def resolve_project_reference(
    project: CompilerProject,
    source_path: Path,
    offset: int,
    source_texts: Mapping[Path, str] | None = None,
) -> CompilerReferenceResolution:
    """Resolve one source reference through existing compiler symbol/import tables.

    This function does not add name-resolution semantics. It identifies the lexical
    reference at ``offset`` and delegates candidate selection to the compiler's
    existing FQN symbol table and deterministic import resolutions. ``source_texts``
    optionally supplies the exact compiler-snapshot text for offset-sensitive editor
    queries while preserving the saved-file API when omitted.
    """

    normalized_source = _normalized(source_path)
    document = next(
        (
            item
            for item in project.documents
            if _normalized(item.source_path) == normalized_source
        ),
        None,
    )
    if document is None:
        return CompilerReferenceResolution("invalid")

    try:
        text = _source_text(document.source_path, source_texts)
    except OSError:
        return CompilerReferenceResolution("invalid")

    reference = _reference_at(text, offset)
    if reference is None:
        return CompilerReferenceResolution("invalid")

    candidates = _reference_candidates(project, document, reference)
    if len(candidates) == 0:
        return CompilerReferenceResolution("unresolved", reference=reference)
    if len(candidates) != 1:
        return CompilerReferenceResolution("ambiguous", reference=reference)

    target = _target_for(candidates[0], source_texts=source_texts)
    if target is None:
        return CompilerReferenceResolution("invalid", reference=reference)
    return CompilerReferenceResolution("resolved", reference=reference, target=target)


def _reference_candidates(project: CompilerProject, document, reference: str) -> tuple[CompilerDeclarationName, ...]:
    if "." in reference:
        return project.symbol_table.lookup_declarations(reference)

    candidates: list[CompilerDeclarationName] = []
    module_name = document.module.name if document.module is not None else None
    if module_name is not None:
        candidates.extend(project.symbol_table.lookup_declarations(f"{module_name}.{reference}"))

    for resolution in project.import_resolutions:
        if resolution.document is not document:
            continue
        candidates.extend(
            declaration
            for declaration in resolution.declarations
            if declaration.declaration.name == reference
        )

    unique: list[CompilerDeclarationName] = []
    seen: set[tuple[str, int]] = set()
    for candidate in candidates:
        span = candidate.declaration.span
        key = (str(candidate.document.source_path), span.offset if span is not None else -1)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return tuple(unique)


def _reference_at(text: str, offset: int) -> str | None:
    if offset < 0 or offset >= len(text):
        return None
    tokens, diagnostics = Lexer(text).tokenize()
    if diagnostics:
        # Lexical errors make offset-based navigation unsafe; do not guess.
        return None
    index = next(
        (
            position
            for position, token in enumerate(tokens)
            if token.kind in {"IDENT", "KEYWORD"}
            and token.start.offset <= offset < token.end.offset
        ),
        None,
    )
    if index is None:
        return None

    start = index
    while start >= 2 and _is_dot(tokens[start - 1]) and _is_name(tokens[start - 2]):
        start -= 2
    end = index
    while end + 2 < len(tokens) and _is_dot(tokens[end + 1]) and _is_name(tokens[end + 2]):
        end += 2

    parts = [token.value for token in tokens[start : end + 1] if token.kind != "NEWLINE"]
    reference = "".join(parts)
    return reference or None


def _is_name(token: Token) -> bool:
    return token.kind in {"IDENT", "KEYWORD"}


def _is_dot(token: Token) -> bool:
    return token.kind == "SYMBOL" and token.value == "."


def _target_for(
    candidate: CompilerDeclarationName,
    source_texts: Mapping[Path, str] | None = None,
) -> CompilerReferenceTarget | None:
    declaration = candidate.declaration
    fqn = candidate.fully_qualified_name
    if fqn is None or declaration.name is None or declaration.span is None:
        return None
    try:
        text = _source_text(candidate.document.source_path, source_texts)
    except OSError:
        return None
    tokens, diagnostics = Lexer(text).tokenize()
    if diagnostics:
        return None
    start_offset = declaration.span.offset
    end_offset = declaration.end.offset if declaration.end is not None else len(text)
    name_token = next(
        (
            token
            for token in tokens
            if token.kind in {"IDENT", "KEYWORD"}
            and token.value == declaration.name
            and start_offset <= token.start.offset < end_offset
        ),
        None,
    )
    if name_token is None:
        return None
    return CompilerReferenceTarget(
        fully_qualified_name=fqn,
        kind=declaration.kind,
        source_path=candidate.document.source_path,
        location=name_token.start,
    )
