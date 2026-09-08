"""Stable compiler diagnostics with App/Auth leaf-shape losslessness closure."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

try:
    from . import compiler_diagnostics_pre_app_leaf_shape as _layer
    from .aidl_parser import Diagnostic as ParserDiagnostic
    from .compiler_project import CompilerProject
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    import compiler_diagnostics_pre_app_leaf_shape as _layer
    from aidl_parser import Diagnostic as ParserDiagnostic
    from compiler_project import CompilerProject

for _name in dir(_layer):
    if not _name.startswith("__") and _name != "_previous":
        globals()[_name] = getattr(_layer, _name)

_APP_BLOCK_LEAF_KINDS = frozenset({"profile", "system", "api", "defaultDeployment"})
_AUTH_BLOCK_LEAF_KINDS = frozenset({"subject", "roles", "scopes", "serviceIdentities"})


def _represented_app_leaf_kind(clause: str) -> str | None:
    text = clause.strip()
    if _layer._APP_PROFILE.fullmatch(text) is not None:
        return "profile"
    typed = _layer._APP_TYPED_REFERENCE.fullmatch(text)
    if typed is not None and typed.group(1) in {"system", "api"}:
        return typed.group(1)
    identifier = _layer._APP_IDENTIFIER_VALUE.fullmatch(text)
    if identifier is not None and identifier.group(1) == "defaultDeployment":
        return "defaultDeployment"
    return None


def _app_auth_leaf_shape_diagnostics(project: CompilerProject) -> tuple[CompilerDiagnostic, ...]:
    diagnostics: list[CompilerDiagnostic] = []
    for app in project.declaration_names:
        if app.declaration.kind != "app" or app.declaration.span is None:
            continue
        app_name = app.fully_qualified_name or app.declaration.name or "<unnamed>"

        for child in app.declaration.node.children:
            if child.kind != "blockClause" or child.name is None or child.span is None:
                continue
            clause_kind = _represented_app_leaf_kind(child.name)
            if clause_kind not in _APP_BLOCK_LEAF_KINDS:
                continue
            diagnostics.append(
                _layer._app_diagnostic(
                    app,
                    child.span,
                    f"app '{app_name}' {clause_kind} must be a leaf clause; nested block content is not represented by the current Canonical IR app contract",
                )
            )

        for declaration in app.document.declarations:
            if declaration.kind != "auth":
                continue
            for child in declaration.node.children:
                if child.kind != "blockClause" or child.name is None or child.span is None:
                    continue
                clause_kind = _layer._auth_clause_kind(child.name)
                if clause_kind not in _AUTH_BLOCK_LEAF_KINDS:
                    continue
                diagnostics.append(
                    _layer._app_diagnostic(
                        app,
                        child.span,
                        f"app '{app_name}' auth {clause_kind} must be a leaf clause; nested block content is not represented by the current Canonical IR app.auth contract",
                    )
                )
    return tuple(diagnostics)


def _with_leaf_shape_diagnostics(
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
        diagnostics.extend(_app_auth_leaf_shape_diagnostics(project))
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
    return _with_leaf_shape_diagnostics(
        project,
        _layer.collect_compiler_diagnostics(project, parser_diagnostics),
    )


def load_compiler_analysis(paths: Iterable[Path]) -> CompilerAnalysis:
    analysis = _layer.load_compiler_analysis(paths)
    return CompilerAnalysis(
        project=analysis.project,
        diagnostics=_with_leaf_shape_diagnostics(
            analysis.project,
            analysis.diagnostics,
        ),
    )
