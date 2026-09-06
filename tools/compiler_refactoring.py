"""Compiler-owned usage discovery and safe declaration rename support."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from tools.aidl_parser import Lexer, Span, Token
from tools.compiler_diagnostics import CompilerAnalysis, CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_resolution import CompilerReferenceTarget, resolve_project_reference


@dataclass(frozen=True)
class CompilerUsage:
    source_path: Path
    location: Span
    length: int

    def to_json(self) -> dict[str, object]:
        return {
            "file": str(self.source_path),
            "line": self.location.line,
            "column": self.location.column,
            "offset": self.location.offset,
            "length": self.length,
        }


@dataclass(frozen=True)
class CompilerUsageResult:
    status: str
    target: CompilerReferenceTarget | None = None
    usages: tuple[CompilerUsage, ...] = ()

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "usages": [usage.to_json() for usage in self.usages],
        }
        if self.target is not None:
            payload["target"] = self.target.to_json()
        return payload


@dataclass(frozen=True)
class CompilerRenameEdit:
    source_path: Path
    location: Span
    length: int
    replacement: str

    def to_json(self) -> dict[str, object]:
        return {
            "file": str(self.source_path),
            "line": self.location.line,
            "column": self.location.column,
            "offset": self.location.offset,
            "length": self.length,
            "replacement": self.replacement,
        }


@dataclass(frozen=True)
class CompilerRenameResult:
    status: str
    target: CompilerReferenceTarget | None = None
    new_fully_qualified_name: str | None = None
    edits: tuple[CompilerRenameEdit, ...] = ()
    message: str | None = None
    applied: bool = False

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "applied": self.applied,
            "edits": [edit.to_json() for edit in self.edits],
        }
        if self.target is not None:
            payload["target"] = self.target.to_json()
        if self.new_fully_qualified_name is not None:
            payload["newFullyQualifiedName"] = self.new_fully_qualified_name
        if self.message is not None:
            payload["message"] = self.message
        return payload


def find_project_usages(
    analysis: CompilerAnalysis,
    source_path: Path,
    offset: int,
) -> CompilerUsageResult:
    """Return all source references that resolve to the same unique compiler target."""

    resolution = resolve_project_reference(analysis.project, source_path, offset)
    if resolution.status != "resolved" or resolution.target is None:
        return CompilerUsageResult(status=resolution.status)
    target = resolution.target

    usages: list[CompilerUsage] = []
    seen: set[tuple[str, int]] = set()
    for document in analysis.project.documents:
        try:
            text = document.source_path.read_text(encoding="utf-8")
        except OSError:
            return CompilerUsageResult(status="invalid")
        tokens, diagnostics = Lexer(text).tokenize()
        if diagnostics:
            return CompilerUsageResult(status="invalid")
        for token in _terminal_reference_tokens(tokens):
            if _same_location(document.source_path, token.start.offset, target.source_path, target.location.offset):
                continue
            candidate = resolve_project_reference(analysis.project, document.source_path, token.start.offset)
            if (
                candidate.status != "resolved"
                or candidate.target is None
                or candidate.target.fully_qualified_name != target.fully_qualified_name
                or candidate.target.source_path.absolute().resolve(strict=False)
                != target.source_path.absolute().resolve(strict=False)
                or candidate.target.location.offset != target.location.offset
            ):
                continue
            key = (str(document.source_path.absolute().resolve(strict=False)), token.start.offset)
            if key in seen:
                continue
            seen.add(key)
            usages.append(
                CompilerUsage(
                    source_path=document.source_path,
                    location=token.start,
                    length=len(token.value),
                )
            )

    return CompilerUsageResult(status="resolved", target=target, usages=tuple(usages))


def rename_project_symbol(
    paths: Sequence[Path],
    source_path: Path,
    offset: int,
    new_name: str,
    *,
    apply: bool,
) -> CompilerRenameResult:
    """Plan and optionally apply one compiler-owned declaration rename safely.

    Rename is deliberately conservative: the project must start without compiler
    errors, the new name must be a plain identifier, the new FQN must not collide,
    every planned edit must still match the old declaration name, and a copied
    project must compile cleanly before any real source is changed. Apply mode then
    revalidates the real project and restores all original source text on failure.
    """

    root = _project_root(paths)
    if root is None:
        return CompilerRenameResult("invalid", message="rename requires one project directory")
    analysis = load_compiler_analysis(paths)
    if _has_errors(analysis):
        return CompilerRenameResult("invalid", message="project has compiler errors before rename")
    if not _valid_identifier(new_name):
        return CompilerRenameResult("invalidName", message="new name must be a non-keyword AIDL identifier")

    usages = find_project_usages(analysis, source_path, offset)
    if usages.status != "resolved" or usages.target is None:
        return CompilerRenameResult(usages.status, message="rename target is not uniquely resolved")
    target = usages.target
    old_name = target.fully_qualified_name.substring_after_last(".") if hasattr(target.fully_qualified_name, "substring_after_last") else target.fully_qualified_name.rsplit(".", 1)[-1]
    if new_name == old_name:
        return CompilerRenameResult("invalidName", target=target, message="new name must differ from current name")

    module_name = target.fully_qualified_name.rsplit(".", 1)[0] if "." in target.fully_qualified_name else ""
    new_fqn = f"{module_name}.{new_name}" if module_name else new_name
    if analysis.project.symbol_table.lookup_declarations(new_fqn):
        return CompilerRenameResult("collision", target=target, new_fully_qualified_name=new_fqn, message="new fully qualified name already exists")

    declaration_edit = CompilerRenameEdit(
        source_path=target.source_path,
        location=target.location,
        length=len(old_name),
        replacement=new_name,
    )
    edits = (declaration_edit,) + tuple(
        CompilerRenameEdit(usage.source_path, usage.location, usage.length, new_name)
        for usage in usages.usages
    )
    if not _edits_match(edits, old_name):
        return CompilerRenameResult("invalid", target=target, new_fully_qualified_name=new_fqn, message="source changed while planning rename")

    preflight = _preflight_rename(root, edits, new_fqn)
    if preflight is not None:
        return CompilerRenameResult(
            "validationFailed",
            target=target,
            new_fully_qualified_name=new_fqn,
            edits=edits,
            message=preflight,
        )
    if not apply:
        return CompilerRenameResult(
            "ready",
            target=target,
            new_fully_qualified_name=new_fqn,
            edits=edits,
        )

    originals = _read_originals(edits)
    if originals is None:
        return CompilerRenameResult(
            "invalid",
            target=target,
            new_fully_qualified_name=new_fqn,
            edits=edits,
            message="failed to read every source before applying rename",
        )
    try:
        _apply_edits_to_files(edits)
        after = load_compiler_analysis([root])
        if _has_errors(after) or len(after.project.symbol_table.lookup_declarations(new_fqn)) != 1:
            raise RuntimeError("compiler revalidation rejected renamed project")
    except Exception as exc:
        _restore_originals(originals)
        return CompilerRenameResult(
            "validationFailed",
            target=target,
            new_fully_qualified_name=new_fqn,
            edits=edits,
            message=str(exc),
        )

    return CompilerRenameResult(
        "applied",
        target=target,
        new_fully_qualified_name=new_fqn,
        edits=edits,
        applied=True,
    )


def _terminal_reference_tokens(tokens: Sequence[Token]) -> Iterable[Token]:
    for index, token in enumerate(tokens):
        if not _is_name(token):
            continue
        if index + 2 < len(tokens) and _is_dot(tokens[index + 1]) and _is_name(tokens[index + 2]):
            continue
        yield token


def _is_name(token: Token) -> bool:
    return token.kind in {"IDENT", "KEYWORD"}


def _is_dot(token: Token) -> bool:
    return token.kind == "SYMBOL" and token.value == "."


def _same_location(left_path: Path, left_offset: int, right_path: Path, right_offset: int) -> bool:
    return (
        left_path.absolute().resolve(strict=False) == right_path.absolute().resolve(strict=False)
        and left_offset == right_offset
    )


def _has_errors(analysis: CompilerAnalysis) -> bool:
    return any(diagnostic.severity == CompilerDiagnosticSeverity.ERROR for diagnostic in analysis.diagnostics)


def _valid_identifier(name: str) -> bool:
    if not name:
        return False
    tokens, diagnostics = Lexer(name).tokenize()
    significant = [token for token in tokens if token.kind != "EOF"]
    return not diagnostics and len(significant) == 1 and significant[0].kind == "IDENT" and significant[0].value == name


def _project_root(paths: Sequence[Path]) -> Path | None:
    if len(paths) != 1:
        return None
    root = paths[0].absolute().resolve(strict=False)
    return root if root.is_dir() else None


def _edits_match(edits: Sequence[CompilerRenameEdit], old_name: str) -> bool:
    for edit in edits:
        try:
            text = edit.source_path.read_text(encoding="utf-8")
        except OSError:
            return False
        if edit.location.offset < 0 or edit.location.offset + edit.length > len(text):
            return False
        if text[edit.location.offset : edit.location.offset + edit.length] != old_name:
            return False
    return True


def _preflight_rename(root: Path, edits: Sequence[CompilerRenameEdit], new_fqn: str) -> str | None:
    with tempfile.TemporaryDirectory() as directory:
        temp_root = Path(directory) / "project"
        shutil.copytree(root, temp_root)
        copied_edits: list[CompilerRenameEdit] = []
        try:
            for edit in edits:
                relative = edit.source_path.absolute().resolve(strict=False).relative_to(root)
                copied_edits.append(
                    CompilerRenameEdit(
                        source_path=temp_root / relative,
                        location=edit.location,
                        length=edit.length,
                        replacement=edit.replacement,
                    )
                )
        except ValueError:
            return "rename target or usage lies outside the project root"
        try:
            _apply_edits_to_files(copied_edits)
            analysis = load_compiler_analysis([temp_root])
        except Exception as exc:
            return f"failed to validate renamed project: {exc}"
        if _has_errors(analysis):
            return "compiler diagnostics reject renamed project"
        if len(analysis.project.symbol_table.lookup_declarations(new_fqn)) != 1:
            return "renamed declaration does not resolve uniquely"
    return None


def _read_originals(edits: Sequence[CompilerRenameEdit]) -> dict[Path, str] | None:
    originals: dict[Path, str] = {}
    try:
        for edit in edits:
            path = edit.source_path.absolute().resolve(strict=False)
            if path not in originals:
                originals[path] = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return originals


def _apply_edits_to_files(edits: Sequence[CompilerRenameEdit]) -> None:
    by_path: dict[Path, list[CompilerRenameEdit]] = {}
    for edit in edits:
        by_path.setdefault(edit.source_path.absolute().resolve(strict=False), []).append(edit)
    for path, path_edits in by_path.items():
        text = path.read_text(encoding="utf-8")
        for edit in sorted(path_edits, key=lambda item: item.location.offset, reverse=True):
            start = edit.location.offset
            end = start + edit.length
            if start < 0 or end > len(text):
                raise RuntimeError(f"invalid rename edit for {path}")
            text = text[:start] + edit.replacement + text[end:]
        _atomic_write(path, text)


def _atomic_write(path: Path, text: str) -> None:
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _restore_originals(originals: dict[Path, str]) -> None:
    for path, text in originals.items():
        _atomic_write(path, text)
