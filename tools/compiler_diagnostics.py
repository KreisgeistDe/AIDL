"""Stable compiler diagnostics with M10-04 Core materialization rejection.

The pre-M10-03 implementation is retained byte-for-byte in
``compiler_diagnostics_base``. This module preserves that public surface, adds
Core type checking, and rejects parsed Core nominal/generic semantics that the
current semantic and canonical-IR path cannot materialize.
"""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Iterable, Mapping

try:
    from . import compiler_diagnostics_base as _base
    from .aidl_parser import Diagnostic as ParserDiagnostic
    from .compiler_core_materialization import collect_core_materialization_issues
    from .compiler_project import CompilerProject
    from .compiler_typecheck import collect_type_issues
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    import compiler_diagnostics_base as _base
    from aidl_parser import Diagnostic as ParserDiagnostic
    from compiler_core_materialization import collect_core_materialization_issues
    from compiler_project import CompilerProject
    from compiler_typecheck import collect_type_issues

# Preserve every existing public and test-visible helper without reimplementing
# M1/M2 policy semantics here.
for _name in dir(_base):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_base, _name)


class CoreTypeDiagnosticCode(StrEnum):
    TYPE_CONSTRUCTOR = "AIDL-T001"
    OPERATION_SIGNATURE = "AIDL-T002"
    ERROR_CONTRACT = "AIDL-T003"
    PUBLIC_SERIALIZATION = "AIDL-T004"
    UNSUPPORTED_MATERIALIZATION = "AIDL-T005"


def _with_type_diagnostics(
    project: CompilerProject,
    base_diagnostics: Iterable[CompilerDiagnostic],
) -> tuple[CompilerDiagnostic, ...]:
    diagnostics = list(base_diagnostics)
    blocking_codes = {
        CompilerDiagnosticCode.PARSE_FAILURE.value,
        CompilerDiagnosticCode.UNRESOLVED_IMPORT.value,
        CompilerDiagnosticCode.DUPLICATE_DECLARATION.value,
    }
    if not any(diagnostic.code.value in blocking_codes for diagnostic in diagnostics):
        issues = (*collect_type_issues(project), *collect_core_materialization_issues(project))
        for issue in issues:
            diagnostics.append(
                CompilerDiagnostic(
                    code=CoreTypeDiagnosticCode(issue.code),
                    phase="type",
                    severity=CompilerDiagnosticSeverity.ERROR,
                    message=issue.message,
                    source_path=issue.source_path,
                    location=issue.location,
                    subject=CompilerDiagnosticSubject(
                        kind=issue.subject_kind,
                        name=issue.subject_name,
                    ),
                    expected=issue.expected,
                    docs=f"aidl://diagnostics/{issue.code}",
                )
            )

    document_order = {
        document.source_path: index for index, document in enumerate(project.documents)
    }
    phase_order = {"parse": 0, "resolve": 1, "type": 2, "policy": 3}
    severity_order = {
        CompilerDiagnosticSeverity.ERROR: 0,
        CompilerDiagnosticSeverity.WARNING: 1,
        CompilerDiagnosticSeverity.INFO: 2,
    }
    diagnostics.sort(
        key=lambda diagnostic: (
            document_order.get(diagnostic.source_path, len(document_order)),
            diagnostic.location.offset,
            phase_order.get(diagnostic.phase, len(phase_order)),
            severity_order[diagnostic.severity],
            diagnostic.code.value,
            diagnostic.message,
        )
    )
    return tuple(diagnostics)


def collect_compiler_diagnostics(
    project: CompilerProject,
    parser_diagnostics: Mapping[Path, Iterable[ParserDiagnostic]] | None = None,
) -> tuple[CompilerDiagnostic, ...]:
    return _with_type_diagnostics(
        project,
        _base.collect_compiler_diagnostics(project, parser_diagnostics),
    )


def load_compiler_analysis(paths: Iterable[Path]) -> CompilerAnalysis:
    analysis = _base.load_compiler_analysis(paths)
    return CompilerAnalysis(
        project=analysis.project,
        diagnostics=_with_type_diagnostics(analysis.project, analysis.diagnostics),
    )
