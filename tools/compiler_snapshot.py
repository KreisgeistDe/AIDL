"""Compiler-owned in-memory project snapshots for unsaved-buffer analysis.

A snapshot keeps ordinary project discovery on disk, then substitutes explicit
UTF-8 source-text overrides before invoking the same parser, compiler project,
type, and diagnostic pipeline used for saved files. Workspace ownership is
provided by ``tools.compiler_workspace`` when multiple roots are configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

from tools.aidl_parser import Diagnostic as ParserDiagnostic
from tools.aidl_parser import iter_aidl_files, parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_completion import CompilerCompletionResult, complete_project_reference
from tools.compiler_diagnostics import CompilerAnalysis, CompilerDiagnostic, collect_compiler_diagnostics
from tools.compiler_documentation import CompilerDocumentationResult, document_project_source
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import CompilerReferenceResolution, resolve_project_reference


def _normalize(path: Path) -> Path:
    return path.absolute().resolve(strict=False)


@dataclass(frozen=True)
class CompilerSnapshot:
    """One immutable compiler analysis plus the exact source text it analyzed."""

    roots: tuple[Path, ...]
    source_texts: Mapping[Path, str]
    analysis: CompilerAnalysis
    overridden_paths: frozenset[Path]

    def text(self, source_path: Path) -> str:
        """Return the analyzed source text for one project document."""

        normalized = _normalize(source_path)
        try:
            return self.source_texts[normalized]
        except KeyError as exc:
            raise ValueError(f"source is not part of snapshot: {source_path}") from exc

    def diagnostics(self, source_path: Path | None = None) -> tuple[CompilerDiagnostic, ...]:
        """Return all diagnostics or only diagnostics for one snapshot document."""

        if source_path is None:
            return self.analysis.diagnostics
        normalized = _normalize(source_path)
        if normalized not in self.source_texts:
            return ()
        return tuple(
            diagnostic
            for diagnostic in self.analysis.diagnostics
            if _normalize(diagnostic.source_path) == normalized
        )

    def resolve(self, source_path: Path, offset: int) -> CompilerReferenceResolution:
        return resolve_project_reference(
            self.analysis.project,
            source_path,
            offset,
            source_texts=self.source_texts,
        )

    def complete(self, source_path: Path, offset: int) -> CompilerCompletionResult:
        return complete_project_reference(
            self.analysis.project,
            source_path,
            offset,
            source_texts=self.source_texts,
        )

    def document(self, source_path: Path, offset: int) -> CompilerDocumentationResult:
        return document_project_source(
            self.analysis,
            source_path,
            offset,
            source_texts=self.source_texts,
        )


def create_compiler_snapshot(
    paths: Iterable[Path],
    overrides: Mapping[Path, str] | None = None,
    *,
    include_paths: Iterable[Path] | None = None,
) -> CompilerSnapshot:
    """Build a deterministic project snapshot from disk plus explicit overrides.

    Without ``include_paths`` this preserves M11-01 behavior: discovery is the
    existing saved-project discovery and overrides may replace only discovered
    files. M11-02 workspace code may provide an explicit owned file set; that set
    can include an unsaved new ``.aidl`` file only when override text is supplied.
    """

    roots = tuple(_normalize(path) for path in paths)
    normalized_overrides = {
        _normalize(path): text for path, text in (overrides or {}).items()
    }

    if include_paths is None:
        discovered = tuple(iter_aidl_files(list(roots)))
        discovered_by_normalized = {_normalize(path): path for path in discovered}
        unknown = sorted(
            normalized_overrides.keys() - discovered_by_normalized.keys(),
            key=str,
        )
        if unknown:
            joined = ", ".join(str(path) for path in unknown)
            raise ValueError(f"snapshot override is outside discovered project files: {joined}")
        source_paths = tuple(discovered_by_normalized[path] for path in sorted(discovered_by_normalized, key=str))
    else:
        source_paths = tuple(sorted({_normalize(path) for path in include_paths}, key=str))
        unknown = sorted(normalized_overrides.keys() - set(source_paths), key=str)
        if unknown:
            joined = ", ".join(str(path) for path in unknown)
            raise ValueError(f"snapshot override is outside included project files: {joined}")
        missing = [path for path in source_paths if not path.exists() and path not in normalized_overrides]
        if missing:
            joined = ", ".join(str(path) for path in missing)
            raise ValueError(f"snapshot included source has no saved or override text: {joined}")

    documents = []
    parser_diagnostics: dict[Path, tuple[ParserDiagnostic, ...]] = {}
    source_texts: dict[Path, str] = {}
    for source_path in source_paths:
        normalized = _normalize(source_path)
        text = normalized_overrides.get(normalized)
        if text is None:
            text = source_path.read_text(encoding="utf-8")
        program, diagnostics, _ = parse_text(text)
        documents.append(compiler_document_from_ast(source_path, program))
        parser_diagnostics[source_path] = tuple(diagnostics)
        source_texts[normalized] = text

    project = compiler_project_from_documents(documents)
    analysis = CompilerAnalysis(
        project=project,
        diagnostics=collect_compiler_diagnostics(project, parser_diagnostics),
    )
    return CompilerSnapshot(
        roots=roots,
        source_texts=MappingProxyType(source_texts),
        analysis=analysis,
        overridden_paths=frozenset(normalized_overrides),
    )
