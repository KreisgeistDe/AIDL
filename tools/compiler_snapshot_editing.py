"""Compiler-owned snapshot usages, rename planning, and authorized diagnostic edits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from tools.aidl_parser import Lexer, Span
from tools.compiler_diagnostics import CompilerDiagnosticSeverity
from tools.compiler_resolution import CompilerReferenceTarget, resolve_project_reference
from tools.compiler_snapshot import CompilerSnapshot


def _normalize(path: Path) -> Path:
    return path.absolute().resolve(strict=False)


@dataclass(frozen=True)
class SnapshotUsage:
    source_path: Path
    location: Span
    length: int


@dataclass(frozen=True)
class SnapshotUsageResult:
    status: str
    target: CompilerReferenceTarget | None = None
    usages: tuple[SnapshotUsage, ...] = ()


@dataclass(frozen=True)
class SnapshotTextEdit:
    source_path: Path
    offset: int
    length: int
    replacement: str


@dataclass(frozen=True)
class SnapshotRenameResult:
    status: str
    target: CompilerReferenceTarget | None = None
    new_fully_qualified_name: str | None = None
    edits: tuple[SnapshotTextEdit, ...] = ()
    message: str | None = None


@dataclass(frozen=True)
class SnapshotAuthorizedFix:
    title: str
    diagnostic_code: str
    edit: SnapshotTextEdit


def _terminal_reference_tokens(tokens):
    for index, token in enumerate(tokens):
        if token.kind not in {"IDENT", "KEYWORD"}:
            continue
        if (
            index + 2 < len(tokens)
            and tokens[index + 1].kind == "SYMBOL"
            and tokens[index + 1].value == "."
            and tokens[index + 2].kind in {"IDENT", "KEYWORD"}
        ):
            continue
        yield token


def find_snapshot_usages(
    snapshot: CompilerSnapshot,
    source_path: Path,
    offset: int,
) -> SnapshotUsageResult:
    """Return references resolving to the same unique target inside one snapshot."""

    resolution = resolve_project_reference(
        snapshot.analysis.project,
        source_path,
        offset,
        source_texts=snapshot.source_texts,
    )
    if resolution.status != "resolved" or resolution.target is None:
        return SnapshotUsageResult(resolution.status)
    target = resolution.target

    usages: list[SnapshotUsage] = []
    seen: set[tuple[Path, int]] = set()
    for document in snapshot.analysis.project.documents:
        normalized = _normalize(document.source_path)
        text = snapshot.source_texts.get(normalized)
        if text is None:
            return SnapshotUsageResult("invalid")
        tokens, diagnostics = Lexer(text).tokenize()
        if diagnostics:
            return SnapshotUsageResult("invalid")
        for token in _terminal_reference_tokens(tokens):
            if normalized == _normalize(target.source_path) and token.start.offset == target.location.offset:
                continue
            candidate = resolve_project_reference(
                snapshot.analysis.project,
                document.source_path,
                token.start.offset,
                source_texts=snapshot.source_texts,
            )
            if (
                candidate.status != "resolved"
                or candidate.target is None
                or candidate.target.fully_qualified_name != target.fully_qualified_name
                or _normalize(candidate.target.source_path) != _normalize(target.source_path)
                or candidate.target.location.offset != target.location.offset
            ):
                continue
            key = (normalized, token.start.offset)
            if key in seen:
                continue
            seen.add(key)
            usages.append(SnapshotUsage(document.source_path, token.start, len(token.value)))

    usages.sort(key=lambda item: (str(_normalize(item.source_path)), item.location.offset))
    return SnapshotUsageResult("resolved", target, tuple(usages))


def _valid_identifier(name: str) -> bool:
    if not name:
        return False
    tokens, diagnostics = Lexer(name).tokenize()
    significant = [token for token in tokens if token.kind != "EOF"]
    return (
        not diagnostics
        and len(significant) == 1
        and significant[0].kind == "IDENT"
        and significant[0].value == name
    )


def plan_snapshot_rename(
    snapshot: CompilerSnapshot,
    source_path: Path,
    offset: int,
    new_name: str,
) -> SnapshotRenameResult:
    """Plan a conservative rename using only the exact snapshot semantic state."""

    if any(
        diagnostic.severity == CompilerDiagnosticSeverity.ERROR
        for diagnostic in snapshot.analysis.diagnostics
    ):
        return SnapshotRenameResult("invalid", message="snapshot has compiler errors before rename")
    if not _valid_identifier(new_name):
        return SnapshotRenameResult("invalidName", message="new name must be a non-keyword AIDL identifier")

    usages = find_snapshot_usages(snapshot, source_path, offset)
    if usages.status != "resolved" or usages.target is None:
        return SnapshotRenameResult(usages.status, message="rename target is not uniquely resolved")
    target = usages.target
    old_name = target.fully_qualified_name.rsplit(".", 1)[-1]
    if new_name == old_name:
        return SnapshotRenameResult("invalidName", target=target, message="new name must differ from current name")

    module_name = target.fully_qualified_name.rsplit(".", 1)[0] if "." in target.fully_qualified_name else ""
    new_fqn = f"{module_name}.{new_name}" if module_name else new_name
    if snapshot.analysis.project.symbol_table.lookup_declarations(new_fqn):
        return SnapshotRenameResult(
            "collision",
            target=target,
            new_fully_qualified_name=new_fqn,
            message="new fully qualified name already exists",
        )

    edits = [SnapshotTextEdit(target.source_path, target.location.offset, len(old_name), new_name)]
    edits.extend(
        SnapshotTextEdit(usage.source_path, usage.location.offset, usage.length, new_name)
        for usage in usages.usages
    )
    for edit in edits:
        text = snapshot.source_texts.get(_normalize(edit.source_path))
        if text is None or edit.offset < 0 or edit.offset + edit.length > len(text):
            return SnapshotRenameResult("invalid", target=target, message="rename edit is outside snapshot text")
        if text[edit.offset : edit.offset + edit.length] != old_name:
            return SnapshotRenameResult("invalid", target=target, message="snapshot text changed while planning rename")

    edits.sort(key=lambda item: (str(_normalize(item.source_path)), item.offset))
    return SnapshotRenameResult("ready", target, new_fqn, tuple(edits))


def _insert_clause_edit(text: str, anchor_offset: int, compiler_text: str) -> tuple[int, str] | None:
    if not compiler_text or anchor_offset < 0 or anchor_offset >= len(text):
        return None
    line_start = text.rfind("\n", 0, anchor_offset + 1) + 1
    line_end = text.find("\n", anchor_offset)
    if line_end < 0:
        return None
    open_brace = text.find("{", anchor_offset, line_end)
    if open_brace < 0:
        return None
    indentation = text[line_start:line_end]
    indentation = indentation[: len(indentation) - len(indentation.lstrip(" \t"))]
    return line_end + 1, f"{indentation}  {compiler_text}\n"


def authorized_snapshot_fixes(
    snapshot: CompilerSnapshot,
    source_path: Path,
    *,
    diagnostic_codes: Iterable[str] | None = None,
) -> tuple[SnapshotAuthorizedFix, ...]:
    """Return edits only for explicit compiler ``allowedFixes`` entries.

    The only currently authorized edit mapping is the existing ``insertClause``
    contract. Unknown fix kinds are omitted rather than guessed.
    """

    normalized = _normalize(source_path)
    text = snapshot.source_texts.get(normalized)
    if text is None:
        return ()
    allowed_codes = set(diagnostic_codes or ())
    filter_codes = diagnostic_codes is not None
    fixes: list[SnapshotAuthorizedFix] = []
    for diagnostic in snapshot.diagnostics(source_path):
        code = diagnostic.code.value
        if filter_codes and code not in allowed_codes:
            continue
        for fix in diagnostic.allowed_fixes:
            if fix.kind != "insertClause":
                continue
            planned = _insert_clause_edit(text, diagnostic.location.offset, fix.text)
            if planned is None:
                continue
            offset, replacement = planned
            fixes.append(
                SnapshotAuthorizedFix(
                    title=fix.text,
                    diagnostic_code=code,
                    edit=SnapshotTextEdit(source_path, offset, 0, replacement),
                )
            )
    return tuple(fixes)
