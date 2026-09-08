"""Stable compiler diagnostics with project-wide App/Auth losslessness closure."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

try:
    from . import compiler_diagnostics_pre_app_leaf_shape as _layer
    from .aidl_parser import Diagnostic as ParserDiagnostic
    from .compiler_project import CompilerDeclarationName, CompilerProject
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    import compiler_diagnostics_pre_app_leaf_shape as _layer
    from aidl_parser import Diagnostic as ParserDiagnostic
    from compiler_project import CompilerDeclarationName, CompilerProject

for _name in dir(_layer):
    if not _name.startswith("__") and _name != "_previous":
        globals()[_name] = getattr(_layer, _name)

_APP_BLOCK_LEAF_KINDS = frozenset({"profile", "system", "api", "defaultDeployment"})
_AUTH_BLOCK_LEAF_KINDS = frozenset({"subject", "roles", "scopes", "serviceIdentities"})


def _stable_declarations(
    project: CompilerProject,
    kind: str,
) -> tuple[CompilerDeclarationName, ...]:
    items = [
        item
        for item in project.declaration_names
        if item.declaration.kind == kind and item.declaration.span is not None
    ]
    items.sort(
        key=lambda item: (
            item.document.source_path.as_posix(),
            item.declaration.span.offset if item.declaration.span is not None else -1,
        )
    )
    return tuple(items)


def _project_app_diagnostic(
    *,
    source_path: Path,
    location: Span,
    app_name: str,
    message: str,
) -> CompilerDiagnostic:
    return CompilerDiagnostic(
        code=AppDiagnosticCode.APP_CONTRACT,
        phase="policy",
        severity=CompilerDiagnosticSeverity.ERROR,
        message=message,
        source_path=source_path,
        location=location,
        subject=CompilerDiagnosticSubject(kind="app", name=app_name),
        expected="exactly one project app with at most one losslessly materializable colocated auth block",
        docs="aidl://diagnostics/AIDL-DIST414",
    )


def _app_cardinality_diagnostics(project: CompilerProject) -> tuple[CompilerDiagnostic, ...]:
    apps = _stable_declarations(project, "app")
    if len(apps) == 1:
        return ()
    if not project.documents:
        return ()
    if len(apps) > 1:
        anchor = apps[1]
        assert anchor.declaration.span is not None
        return (
            _project_app_diagnostic(
                source_path=anchor.document.source_path,
                location=anchor.declaration.span,
                app_name=anchor.declaration.name or "<unnamed>",
                message=f"project must declare exactly one app; found {len(apps)}",
            ),
        )
    document = min(project.documents, key=lambda item: item.source_path.as_posix())
    if document.span is None:
        return ()
    return (
        _project_app_diagnostic(
            source_path=document.source_path,
            location=document.span,
            app_name="<missing>",
            message="project must declare exactly one app; found 0",
        ),
    )


def _auth_diagnostic(
    app: CompilerDeclarationName,
    auth: CompilerDeclarationName,
    location: Span,
    message: str,
) -> CompilerDiagnostic:
    app_name = app.fully_qualified_name or app.declaration.name or "<unnamed>"
    return _project_app_diagnostic(
        source_path=auth.document.source_path,
        location=location,
        app_name=app.declaration.name or "<unnamed>",
        message=f"app '{app_name}' {message}",
    )


def _project_auth_diagnostics(project: CompilerProject) -> tuple[CompilerDiagnostic, ...]:
    apps = _stable_declarations(project, "app")
    if len(apps) != 1:
        return ()
    app = apps[0]
    auths = _stable_declarations(project, "auth")
    if len(auths) > 1:
        anchor = auths[1]
        assert anchor.declaration.span is not None
        return (
            _auth_diagnostic(
                app,
                anchor,
                anchor.declaration.span,
                f"must declare at most one project auth block; found {len(auths)}",
            ),
        )
    if not auths:
        return ()
    auth = auths[0]
    if auth.document is not app.document:
        assert auth.declaration.span is not None
        return (
            _auth_diagnostic(
                app,
                auth,
                auth.declaration.span,
                "auth block must be declared in the same source document as the app; cross-file auth association is not represented by the current Canonical IR app contract",
            ),
        )
    diagnostics: list[CompilerDiagnostic] = []
    for child in auth.declaration.node.children:
        if child.name is None or child.span is None:
            continue
        if _layer._auth_clause_kind(child.name.strip()) is None:
            diagnostics.append(
                _auth_diagnostic(
                    app,
                    auth,
                    child.span,
                    f"auth clause is not a normative auth clause: '{child.name.strip()}'",
                )
            )
    return tuple(diagnostics)


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
    apps = _stable_declarations(project, "app")
    if len(apps) != 1:
        return ()
    app = apps[0]
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

    for auth in _stable_declarations(project, "auth"):
        if auth.document is not app.document:
            continue
        for child in auth.declaration.node.children:
            if child.kind != "blockClause" or child.name is None or child.span is None:
                continue
            clause_kind = _layer._auth_clause_kind(child.name)
            if clause_kind not in _AUTH_BLOCK_LEAF_KINDS:
                continue
            diagnostics.append(
                _auth_diagnostic(
                    app,
                    auth,
                    child.span,
                    f"auth {clause_kind} must be a leaf clause; nested block content is not represented by the current Canonical IR app.auth contract",
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
        apps = _stable_declarations(project, "app")
        auths = _stable_declarations(project, "auth")
        if len(apps) == 1 and len(auths) > 1:
            diagnostics = [
                diagnostic
                for diagnostic in diagnostics
                if not (
                    diagnostic.code.value == AppDiagnosticCode.APP_CONTRACT.value
                    and "must declare at most one auth block" in diagnostic.message
                )
            ]
        diagnostics.extend(_app_cardinality_diagnostics(project))
        diagnostics.extend(_project_auth_diagnostics(project))
        diagnostics.extend(_app_auth_leaf_shape_diagnostics(project))
    phase_order = {"parse": 0, "resolve": 1, "type": 2, "policy": 3}
    severity_order = {
        CompilerDiagnosticSeverity.ERROR: 0,
        CompilerDiagnosticSeverity.WARNING: 1,
        CompilerDiagnosticSeverity.INFO: 2,
    }
    diagnostics.sort(
        key=lambda diagnostic: (
            diagnostic.source_path.as_posix(),
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
