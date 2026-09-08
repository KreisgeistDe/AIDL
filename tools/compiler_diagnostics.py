"""Stable compiler diagnostics with App/Auth cardinality closure layered on M10 diagnostics."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

try:
    from . import compiler_diagnostics_pre_app_auth_cardinality as _previous
    from .aidl_parser import Diagnostic as ParserDiagnostic
    from .compiler_project import CompilerProject
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    import compiler_diagnostics_pre_app_auth_cardinality as _previous
    from aidl_parser import Diagnostic as ParserDiagnostic
    from compiler_project import CompilerProject

for _name in dir(_previous):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_previous, _name)

_AUTH_REQUIRED = ("provider", "subject", "roles", "scopes", "serviceIdentities")


def _auth_clause_kind(clause: str) -> str | None:
    text = clause.strip()
    for key in _AUTH_REQUIRED:
        if text == key or text.startswith(f"{key} "):
            return key
    return None


def _auth_cardinality_diagnostics(project: CompilerProject) -> tuple[CompilerDiagnostic, ...]:
    diagnostics: list[CompilerDiagnostic] = []
    for app in project.declaration_names:
        if app.declaration.kind != "app" or app.declaration.span is None:
            continue
        app_name = app.fully_qualified_name or app.declaration.name or "<unnamed>"
        auth_declarations = tuple(
            declaration
            for declaration in app.document.declarations
            if declaration.kind == "auth" and declaration.span is not None
        )
        for declaration in auth_declarations[1:]:
            diagnostics.append(
                _previous._app_diagnostic(
                    app,
                    declaration.span,
                    f"app '{app_name}' must declare at most one auth block; found {len(auth_declarations)}",
                )
            )
        for declaration in auth_declarations:
            occurrences: dict[str, list[Span]] = {key: [] for key in _AUTH_REQUIRED}
            for child in declaration.node.children:
                if child.name is None or child.span is None:
                    continue
                key = _auth_clause_kind(child.name)
                if key is not None:
                    occurrences[key].append(child.span)
            for key in _AUTH_REQUIRED:
                spans = occurrences[key]
                if not spans:
                    diagnostics.append(
                        _previous._app_diagnostic(
                            app,
                            declaration.span,
                            f"app '{app_name}' auth block must declare exactly one {key} clause; found 0",
                        )
                    )
                elif len(spans) > 1:
                    diagnostics.append(
                        _previous._app_diagnostic(
                            app,
                            spans[1],
                            f"app '{app_name}' auth block must declare exactly one {key} clause; found {len(spans)}",
                        )
                    )
    return tuple(diagnostics)


def _with_auth_cardinality_diagnostics(
    project: CompilerProject,
    base_diagnostics: Iterable[CompilerDiagnostic],
) -> tuple[CompilerDiagnostic, ...]:
    diagnostics = list(base_diagnostics)
    blocking_codes = {
        CompilerDiagnosticCode.PARSE_FAILURE.value,
        CompilerDiagnosticCode.UNRESOLVED_IMPORT.value,
        CompilerDiagnosticCode.DUPLICATE_DECLARATION.value,
        ModuleDiagnosticCode.MODULE_STRUCTURE.value,
    }
    if not any(diagnostic.code.value in blocking_codes for diagnostic in diagnostics):
        diagnostics.extend(_auth_cardinality_diagnostics(project))
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
    return _with_auth_cardinality_diagnostics(
        project,
        _previous.collect_compiler_diagnostics(project, parser_diagnostics),
    )


def load_compiler_analysis(paths: Iterable[Path]) -> CompilerAnalysis:
    analysis = _previous.load_compiler_analysis(paths)
    return CompilerAnalysis(
        project=analysis.project,
        diagnostics=_with_auth_cardinality_diagnostics(
            analysis.project,
            analysis.diagnostics,
        ),
    )
