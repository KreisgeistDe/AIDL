"""Compiler-owned semantic completion for editor consumers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from tools.aidl_parser import Lexer, Node, Token
from tools.compiler_ast import CompilerDocument
from tools.compiler_project import CompilerDeclarationName, CompilerProject
from tools.compiler_resolution import _target_for


@dataclass(frozen=True)
class CompilerCompletionCandidate:
    insert_text: str
    display_text: str
    fully_qualified_name: str
    kind: str
    origin: str
    source_path: Path
    source_offset: int

    def to_json(self) -> dict[str, object]:
        return {
            "insertText": self.insert_text,
            "displayText": self.display_text,
            "fullyQualifiedName": self.fully_qualified_name,
            "kind": self.kind,
            "origin": self.origin,
            "location": {
                "file": str(self.source_path),
                "offset": self.source_offset,
            },
        }


@dataclass(frozen=True)
class CompilerCompletionResult:
    status: str
    prefix: str | None = None
    qualifier: str | None = None
    candidates: tuple[CompilerCompletionCandidate, ...] = ()

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "candidates": [candidate.to_json() for candidate in self.candidates],
        }
        if self.prefix is not None:
            payload["prefix"] = self.prefix
        if self.qualifier is not None:
            payload["qualifier"] = self.qualifier
        return payload


@dataclass(frozen=True)
class _CompletionContext:
    prefix: str
    qualifier: str | None


def _normalized(path: Path) -> Path:
    return path.absolute().resolve(strict=False)


def _source_text(source_path: Path, source_texts: Mapping[Path, str] | None) -> str:
    if source_texts is not None:
        normalized = _normalized(source_path)
        if normalized in source_texts:
            return source_texts[normalized]
    return source_path.read_text(encoding="utf-8")


def complete_project_reference(
    project: CompilerProject,
    source_path: Path,
    offset: int,
    source_texts: Mapping[Path, str] | None = None,
) -> CompilerCompletionResult:
    """Return deterministic declaration completions using existing compiler visibility.

    Completion deliberately owns no parallel language semantics. It derives only a
    parser-backed reference-value prefix/qualifier at ``file + offset`` and projects
    declarations through the same local FQN, import-resolution, and qualified FQN
    tables used by M6-04 reference resolution. Ambiguous simple names are omitted
    instead of guessed. Positions that the parser does not establish as reference
    values are rejected conservatively. ``source_texts`` optionally supplies the
    exact text of a compiler snapshot while preserving saved-file callers.
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
        return CompilerCompletionResult("invalid")
    try:
        text = _source_text(document.source_path, source_texts)
    except OSError:
        return CompilerCompletionResult("invalid")

    context = _completion_context(document, text, offset)
    if context is None:
        return CompilerCompletionResult("invalid")

    if context.qualifier is not None:
        candidates = _qualified_candidates(
            project, context.qualifier, context.prefix, source_texts
        )
    else:
        candidates = _visible_unqualified_candidates(
            project, document, context.prefix, source_texts
        )

    return CompilerCompletionResult(
        "resolved",
        prefix=context.prefix,
        qualifier=context.qualifier,
        candidates=candidates,
    )


def _visible_unqualified_candidates(
    project: CompilerProject,
    document,
    prefix: str,
    source_texts: Mapping[Path, str] | None = None,
) -> tuple[CompilerCompletionCandidate, ...]:
    visible: dict[str, list[tuple[CompilerDeclarationName, str]]] = {}
    module_name = document.module.name if document.module is not None else None

    if module_name is not None:
        for declaration_name in project.declaration_names:
            declaration = declaration_name.declaration
            candidate_module = (
                declaration_name.document.module.name
                if declaration_name.document.module is not None
                else None
            )
            if candidate_module != module_name:
                continue
            if declaration.name is None or declaration_name.fully_qualified_name is None:
                continue
            if declaration.name.startswith(prefix):
                visible.setdefault(declaration.name, []).append(
                    (declaration_name, f"local:{module_name}")
                )

    for resolution in project.import_resolutions:
        if resolution.document is not document:
            continue
        import_name = resolution.import_.name
        if import_name is None:
            continue
        origin = (
            f"wildcardImport:{import_name}"
            if resolution.import_.wildcard
            else f"exactImport:{import_name}"
        )
        for declaration_name in resolution.declarations:
            name = declaration_name.declaration.name
            if name is None or not name.startswith(prefix):
                continue
            visible.setdefault(name, []).append((declaration_name, origin))

    result: list[CompilerCompletionCandidate] = []
    for name in sorted(visible):
        unique = _unique_declarations(visible[name])
        if len(unique) != 1:
            continue
        declaration_name, origin = unique[0]
        candidate = _candidate_for(declaration_name, name, origin, source_texts)
        if candidate is not None:
            result.append(candidate)
    return tuple(result)


def _qualified_candidates(
    project: CompilerProject,
    qualifier: str,
    prefix: str,
    source_texts: Mapping[Path, str] | None = None,
) -> tuple[CompilerCompletionCandidate, ...]:
    fqn_prefix = f"{qualifier}."
    result: list[CompilerCompletionCandidate] = []
    for fully_qualified_name in sorted(project.symbol_table.declarations_by_fqn):
        if not fully_qualified_name.startswith(fqn_prefix):
            continue
        remainder = fully_qualified_name[len(fqn_prefix) :]
        if "." in remainder or not remainder.startswith(prefix):
            continue
        matches = project.symbol_table.lookup_declarations(fully_qualified_name)
        if len(matches) != 1:
            continue
        candidate = _candidate_for(
            matches[0], remainder, f"qualified:{qualifier}", source_texts
        )
        if candidate is not None:
            result.append(candidate)
    return tuple(result)


def _unique_declarations(
    entries: list[tuple[CompilerDeclarationName, str]],
) -> list[tuple[CompilerDeclarationName, str]]:
    unique: list[tuple[CompilerDeclarationName, str]] = []
    seen: set[tuple[str, int]] = set()
    for declaration_name, origin in entries:
        span = declaration_name.declaration.span
        key = (
            str(_normalized(declaration_name.document.source_path)),
            span.offset if span is not None else -1,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append((declaration_name, origin))
    return unique


def _candidate_for(
    declaration_name: CompilerDeclarationName,
    insert_text: str,
    origin: str,
    source_texts: Mapping[Path, str] | None = None,
) -> CompilerCompletionCandidate | None:
    target = _target_for(declaration_name, source_texts=source_texts)
    if target is None:
        return None
    return CompilerCompletionCandidate(
        insert_text=insert_text,
        display_text=f"{insert_text} ({target.kind})",
        fully_qualified_name=target.fully_qualified_name,
        kind=target.kind,
        origin=origin,
        source_path=target.source_path,
        source_offset=target.location.offset,
    )


def _completion_context(
    document: CompilerDocument,
    text: str,
    offset: int,
) -> _CompletionContext | None:
    if offset < 0 or offset > len(text):
        return None
    tokens, diagnostics = Lexer(text).tokenize()
    if diagnostics:
        return None
    significant = [token for token in tokens if token.kind not in {"NEWLINE", "EOF"}]
    if not significant:
        return None

    current_index = next(
        (
            index
            for index, token in enumerate(significant)
            if _is_name(token) and token.start.offset <= offset <= token.end.offset
        ),
        None,
    )
    if current_index is not None:
        token = significant[current_index]
        if not _is_parser_backed_reference_value(document, significant, token.start.offset):
            return None
        prefix_end = min(offset, token.end.offset)
        prefix = text[token.start.offset : prefix_end]
        qualifier = _qualifier_before(significant, current_index)
        return _CompletionContext(prefix=prefix, qualifier=qualifier)

    previous_index = next(
        (
            index
            for index in range(len(significant) - 1, -1, -1)
            if significant[index].end.offset <= offset
        ),
        None,
    )
    if previous_index is None:
        return None
    previous = significant[previous_index]
    if _is_dot(previous) and previous.end.offset == offset:
        if not _is_parser_backed_reference_value(document, significant, previous.start.offset):
            return None
        qualifier = _qualified_name_ending_at(significant, previous_index - 1)
        if qualifier is None:
            return None
        return _CompletionContext(prefix="", qualifier=qualifier)
    return None


def _is_parser_backed_reference_value(
    document: CompilerDocument,
    tokens: list[Token],
    offset: int,
) -> bool:
    clause = _deepest_clause_at(document, offset)
    if clause is None or clause.span is None:
        return False
    colon = next(
        (
            token
            for token in tokens
            if token.kind == "SYMBOL"
            and token.value == ":"
            and clause.span.offset <= token.start.offset < offset
            and (clause.end is None or token.start.offset < clause.end.offset)
        ),
        None,
    )
    return colon is not None and colon.end.offset <= offset


def _deepest_clause_at(document: CompilerDocument, offset: int) -> Node | None:
    for declaration in document.declarations:
        match = _deepest_clause_in(declaration.node.children, offset)
        if match is not None:
            return match
    return None


def _deepest_clause_in(nodes: list[Node], offset: int) -> Node | None:
    for node in nodes:
        if not _contains_offset(node, offset):
            continue
        nested = _deepest_clause_in(node.children, offset)
        if nested is not None:
            return nested
        if node.kind in {"clause", "blockClause"}:
            return node
    return None


def _contains_offset(node: Node, offset: int) -> bool:
    if node.span is None or node.end is None:
        return False
    return node.span.offset <= offset <= node.end.offset


def _qualifier_before(tokens: list[Token], current_index: int) -> str | None:
    if current_index < 2 or not _is_dot(tokens[current_index - 1]):
        return None
    return _qualified_name_ending_at(tokens, current_index - 2)


def _qualified_name_ending_at(tokens: list[Token], end_index: int) -> str | None:
    if end_index < 0 or not _is_name(tokens[end_index]):
        return None
    start = end_index
    while start >= 2 and _is_dot(tokens[start - 1]) and _is_name(tokens[start - 2]):
        start -= 2
    parts = tokens[start : end_index + 1]
    if any(not (_is_name(token) or _is_dot(token)) for token in parts):
        return None
    value = "".join(token.value for token in parts)
    return value or None


def _is_name(token: Token) -> bool:
    return token.kind in {"IDENT", "KEYWORD"}


def _is_dot(token: Token) -> bool:
    return token.kind == "SYMBOL" and token.value == "."
