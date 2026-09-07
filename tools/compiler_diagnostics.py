"""Stable compiler diagnostics with M10-04 Core materialization rejection.

The pre-M10-03 implementation is retained byte-for-byte in
``compiler_diagnostics_base``. This module preserves that public surface, adds
Core type checking, and rejects parsed Core nominal/generic semantics that the
current semantic and canonical-IR path cannot materialize.
"""
from __future__ import annotations

import json
import re
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


class AppDiagnosticCode(StrEnum):
    APP_CONTRACT = "AIDL-DIST414"


_APP_PROFILE = re.compile(
    r"^profile\s+([a-z][A-Za-z0-9_]*)\s+version\s+([1-9][0-9]*)$"
)
_APP_TYPED_REFERENCE = re.compile(
    r"^(system|frontend|api)\s+[A-Z][A-Za-z0-9_]*$"
)
_APP_IDENTIFIER_VALUE = re.compile(
    r"^(defaultDeployment|compatibility)\s+[A-Za-z_][A-Za-z0-9_]*$"
)


def _profile_registry() -> dict[tuple[str, int], tuple[tuple[str, int], ...]]:
    path = Path(__file__).resolve().parents[1] / "spec" / "profile-registry.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    registry: dict[tuple[str, int], tuple[tuple[str, int], ...]] = {}
    for profile in payload.get("profiles", []):
        profile_id = profile.get("id")
        major = profile.get("major")
        if not isinstance(profile_id, str) or not isinstance(major, int):
            continue
        requires: list[tuple[str, int]] = []
        for requirement in profile.get("requires", []):
            if not isinstance(requirement, str):
                continue
            match = re.fullmatch(r"([a-z][A-Za-z0-9_]*)@([1-9][0-9]*)", requirement)
            if match is not None:
                requires.append((match.group(1), int(match.group(2))))
        registry[(profile_id, major)] = tuple(requires)
    return registry


def _app_diagnostic(
    app: CompilerDeclarationName,
    location: Span,
    message: str,
) -> CompilerDiagnostic:
    return CompilerDiagnostic(
        code=AppDiagnosticCode.APP_CONTRACT,
        phase="policy",
        severity=CompilerDiagnosticSeverity.ERROR,
        message=message,
        source_path=app.document.source_path,
        location=location,
        subject=CompilerDiagnosticSubject(
            kind="app", name=app.declaration.name or "<unnamed>"
        ),
        expected=(
            "at least one explicit registered profile selection and only normative app clauses"
        ),
        docs="aidl://diagnostics/AIDL-DIST414",
    )


def _app_contract_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Validate only App rules explicitly fixed by Core grammar/profile registry."""

    registry = _profile_registry()
    diagnostics: list[CompilerDiagnostic] = []
    for app in project.declaration_names:
        if app.declaration.kind != "app" or app.declaration.span is None:
            continue

        app_name = app.fully_qualified_name or app.declaration.name or "<unnamed>"
        profile_clauses: list[tuple[tuple[str, int], Span]] = []
        saw_profile_clause = False

        for child in app.declaration.node.children:
            if child.name is None or child.span is None:
                continue
            clause = child.name.strip()
            if clause.startswith("profile"):
                saw_profile_clause = True
                match = _APP_PROFILE.fullmatch(clause)
                if match is None:
                    diagnostics.append(
                        _app_diagnostic(
                            app,
                            child.span,
                            f"app '{app_name}' profile clause must be 'profile ID version POSITIVE_MAJOR'; found '{clause}'",
                        )
                    )
                    continue
                key = (match.group(1), int(match.group(2)))
                profile_clauses.append((key, child.span))
                if key not in registry:
                    diagnostics.append(
                        _app_diagnostic(
                            app,
                            child.span,
                            f"app '{app_name}' selects unregistered profile '{key[0]}@{key[1]}'",
                        )
                    )
                continue

            if (
                _APP_TYPED_REFERENCE.fullmatch(clause) is not None
                or _APP_IDENTIFIER_VALUE.fullmatch(clause) is not None
            ):
                continue
            diagnostics.append(
                _app_diagnostic(
                    app,
                    child.span,
                    f"app '{app_name}' clause is not a normative app clause: '{clause}'",
                )
            )

        if not saw_profile_clause:
            diagnostics.append(
                _app_diagnostic(
                    app,
                    app.declaration.span,
                    f"app '{app_name}' must select at least one explicit profile",
                )
            )

        selected = {key for key, _ in profile_clauses}
        for key, location in profile_clauses:
            if key not in registry:
                continue
            for required in registry[key]:
                if required in selected:
                    continue
                diagnostics.append(
                    _app_diagnostic(
                        app,
                        location,
                        f"app '{app_name}' profile '{key[0]}@{key[1]}' requires explicit profile '{required[0]}@{required[1]}'",
                    )
                )

    return tuple(diagnostics)


def _with_app_diagnostics(
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
        diagnostics.extend(_app_contract_diagnostics(project))
    return tuple(diagnostics)


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
        _with_app_diagnostics(
            project,
            _base.collect_compiler_diagnostics(project, parser_diagnostics),
        ),
    )


def load_compiler_analysis(paths: Iterable[Path]) -> CompilerAnalysis:
    analysis = _base.load_compiler_analysis(paths)
    return CompilerAnalysis(
        project=analysis.project,
        diagnostics=_with_type_diagnostics(
            analysis.project,
            _with_app_diagnostics(analysis.project, analysis.diagnostics),
        ),
    )
