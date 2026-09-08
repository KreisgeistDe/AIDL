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
    from .compiler_alias_opaque_materialization import collect_alias_opaque_materialization_issues
    from .compiler_consumer_materialization import collect_consumer_materialization_issues
    from .compiler_core_materialization import collect_core_materialization_issues
    from .compiler_event_materialization import collect_event_materialization_issues
    from .compiler_module_validation import collect_module_validation_issues
    from .compiler_project import CompilerProject
    from .compiler_topic_materialization import collect_topic_materialization_issues
    from .compiler_typecheck import collect_type_issues
    from .compiler_value_materialization import collect_value_materialization_issues
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    import compiler_diagnostics_base as _base
    from aidl_parser import Diagnostic as ParserDiagnostic
    from compiler_alias_opaque_materialization import collect_alias_opaque_materialization_issues
    from compiler_consumer_materialization import collect_consumer_materialization_issues
    from compiler_core_materialization import collect_core_materialization_issues
    from compiler_event_materialization import collect_event_materialization_issues
    from compiler_module_validation import collect_module_validation_issues
    from compiler_project import CompilerProject
    from compiler_topic_materialization import collect_topic_materialization_issues
    from compiler_typecheck import collect_type_issues
    from compiler_value_materialization import collect_value_materialization_issues

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


class ModuleDiagnosticCode(StrEnum):
    MODULE_STRUCTURE = "AIDL-R005"


class AppDiagnosticCode(StrEnum):
    APP_CONTRACT = "AIDL-DIST414"


class ConsumerDiagnosticCode(StrEnum):
    CONSUMER_BINDING = "AIDL-DIST415"


_APP_PROFILE = re.compile(
    r"^profile\s+([a-z][A-Za-z0-9_]*)\s+version\s+([1-9][0-9]*)$"
)
_APP_TYPED_REFERENCE = re.compile(
    r"^(system|frontend|api)\s+([A-Z][A-Za-z0-9_]*)$"
)
_APP_IDENTIFIER_VALUE = re.compile(
    r"^(defaultDeployment|compatibility)\s+([A-Za-z_][A-Za-z0-9_]*)$"
)
_AUTH_PROVIDER = re.compile(r"^provider\s+[A-Za-z_][A-Za-z0-9_]*$")
_AUTH_SUBJECT_ALIAS = re.compile(r"\s+as\s+[A-Za-z_][A-Za-z0-9_]*\s*$")
_TOPIC_DELIVERY = re.compile(r"^delivery\s+([A-Za-z_][A-Za-z0-9_]*)$")


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
            "losslessly materializable normative app structure and uniquely resolved app references"
        ),
        docs="aidl://diagnostics/AIDL-DIST414",
    )


def _app_reference_candidates(
    project: CompilerProject,
    app: CompilerDeclarationName,
    reference: str,
) -> tuple[CompilerDeclarationName, ...]:
    kinds = frozenset(
        item.declaration.kind for item in project.declaration_names
    )
    return _resolve_declaration_reference(project, app, reference, kinds)


def _validate_app_reference(
    project: CompilerProject,
    app: CompilerDeclarationName,
    app_name: str,
    clause_name: str,
    reference: str,
    expected_kind: str,
    location: Span,
) -> tuple[CompilerDiagnostic, ...]:
    candidates = _app_reference_candidates(project, app, reference)
    matching = tuple(
        candidate
        for candidate in candidates
        if candidate.declaration.kind == expected_kind
    )
    if len(matching) == 1 and len(candidates) == 1:
        return ()
    if not candidates:
        message = (
            f"app '{app_name}' {clause_name} reference '{reference}' is unresolved"
        )
    elif not matching:
        kinds = ", ".join(candidate.declaration.kind for candidate in candidates)
        message = (
            f"app '{app_name}' {clause_name} reference '{reference}' must target "
            f"{expected_kind}; found {kinds}"
        )
    else:
        message = (
            f"app '{app_name}' {clause_name} reference '{reference}' must resolve "
            f"uniquely to {expected_kind}; found {len(matching)} matching declarations"
        )
    return (_app_diagnostic(app, location, message),)


def _app_contract_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Validate the bounded lossless App structure/reference pre-IR contract."""

    registry = _profile_registry()
    diagnostics: list[CompilerDiagnostic] = []
    for app in project.declaration_names:
        if app.declaration.kind != "app" or app.declaration.span is None:
            continue

        app_name = app.fully_qualified_name or app.declaration.name or "<unnamed>"
        if app.declaration.node.attrs.get("version") is not None:
            diagnostics.append(
                _app_diagnostic(
                    app,
                    app.declaration.span,
                    f"app '{app_name}' header version is parser-only and is not represented by the current Canonical IR app contract",
                )
            )

        profile_clauses: list[tuple[tuple[str, int], Span]] = []
        seen_profiles: set[tuple[str, int]] = set()
        saw_profile_clause = False
        singleton_clauses: dict[str, list[tuple[str, Span]]] = {
            "system": [],
            "defaultDeployment": [],
        }
        api_clauses: list[tuple[str, Span]] = []
        seen_apis: set[str] = set()

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
                if key in seen_profiles:
                    diagnostics.append(
                        _app_diagnostic(
                            app,
                            child.span,
                            f"app '{app_name}' repeats profile '{key[0]}@{key[1]}'",
                        )
                    )
                else:
                    seen_profiles.add(key)
                if key not in registry:
                    diagnostics.append(
                        _app_diagnostic(
                            app,
                            child.span,
                            f"app '{app_name}' selects unregistered profile '{key[0]}@{key[1]}'",
                        )
                    )
                continue

            typed = _APP_TYPED_REFERENCE.fullmatch(clause)
            if typed is not None:
                clause_name, reference = typed.groups()
                if clause_name == "frontend":
                    diagnostics.append(
                        _app_diagnostic(
                            app,
                            child.span,
                            f"app '{app_name}' frontend clause is not represented by the current Canonical IR app contract",
                        )
                    )
                elif clause_name == "system":
                    singleton_clauses["system"].append((reference, child.span))
                elif clause_name == "api":
                    api_clauses.append((reference, child.span))
                    if reference in seen_apis:
                        diagnostics.append(
                            _app_diagnostic(
                                app,
                                child.span,
                                f"app '{app_name}' repeats api reference '{reference}'",
                            )
                        )
                    else:
                        seen_apis.add(reference)
                continue

            identifier = _APP_IDENTIFIER_VALUE.fullmatch(clause)
            if identifier is not None:
                clause_name, reference = identifier.groups()
                if clause_name == "compatibility":
                    diagnostics.append(
                        _app_diagnostic(
                            app,
                            child.span,
                            f"app '{app_name}' compatibility clause is not represented by the current Canonical IR app contract",
                        )
                    )
                elif clause_name == "defaultDeployment":
                    singleton_clauses["defaultDeployment"].append(
                        (reference, child.span)
                    )
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

        expected_singletons = {
            "system": "system",
            "defaultDeployment": "deployment",
        }
        for clause_name, expected_kind in expected_singletons.items():
            clauses = singleton_clauses[clause_name]
            if not clauses:
                diagnostics.append(
                    _app_diagnostic(
                        app,
                        app.declaration.span,
                        f"app '{app_name}' must declare exactly one {clause_name} clause; found 0",
                    )
                )
                continue
            if len(clauses) > 1:
                diagnostics.append(
                    _app_diagnostic(
                        app,
                        clauses[1][1],
                        f"app '{app_name}' must declare exactly one {clause_name} clause; found {len(clauses)}",
                    )
                )
            for reference, location in clauses:
                diagnostics.extend(
                    _validate_app_reference(
                        project,
                        app,
                        app_name,
                        clause_name,
                        reference,
                        expected_kind,
                        location,
                    )
                )

        for reference, location in api_clauses:
            diagnostics.extend(
                _validate_app_reference(
                    project,
                    app,
                    app_name,
                    "api",
                    reference,
                    "api",
                    location,
                )
            )

        for declaration in app.document.declarations:
            if declaration.kind != "auth":
                continue
            for child in declaration.node.children:
                if child.name is None or child.span is None:
                    continue
                clause = child.name.strip()
                if clause.startswith("provider ") and _AUTH_PROVIDER.fullmatch(clause) is None:
                    diagnostics.append(
                        _app_diagnostic(
                            app,
                            child.span,
                            f"app '{app_name}' auth provider configuration is not represented by the current Canonical IR app.auth contract",
                        )
                    )
                elif clause.startswith("subject ") and _AUTH_SUBJECT_ALIAS.search(clause) is not None:
                    diagnostics.append(
                        _app_diagnostic(
                            app,
                            child.span,
                            f"app '{app_name}' auth subject alias/type is not represented by the current Canonical IR app.auth contract",
                        )
                    )

    return tuple(diagnostics)


def _consumer_diagnostic(
    consumer: CompilerDeclarationName,
    location: Span,
    message: str,
) -> CompilerDiagnostic:
    return CompilerDiagnostic(
        code=ConsumerDiagnosticCode.CONSUMER_BINDING,
        phase="policy",
        severity=CompilerDiagnosticSeverity.ERROR,
        message=message,
        source_path=consumer.document.source_path,
        location=location,
        subject=CompilerDiagnosticSubject(
            kind="consumer", name=consumer.declaration.name or "<unnamed>"
        ),
        expected=(
            "consumer on EVENT from TOPIC where TOPIC contains EVENT and uses atLeastOnce delivery"
        ),
        docs="aidl://diagnostics/AIDL-DIST415",
    )


def _topic_delivery_values(topic: CompilerDeclaration) -> tuple[str, ...]:
    values: list[str] = []
    for child in topic.node.children:
        if child.name is None:
            continue
        match = _TOPIC_DELIVERY.fullmatch(child.name.strip())
        if match is not None:
            values.append(match.group(1))
    return tuple(values)


def _topic_contains_event(
    project: CompilerProject,
    topic: CompilerDeclarationName,
    event: CompilerDeclarationName,
) -> bool:
    event_identity = _declaration_identity(event)
    for reference in _list_clause_references(topic.declaration, "events"):
        resolved = _resolve_declaration_reference(
            project,
            topic,
            reference,
            frozenset({"event"}),
        )
        if len(resolved) == 1 and _declaration_identity(resolved[0]) == event_identity:
            return True
    return False


def _consumer_binding_diagnostics(
    project: CompilerProject,
) -> tuple[CompilerDiagnostic, ...]:
    """Validate the explicit Core consumer binding and at-least-once boundary."""

    diagnostics: list[CompilerDiagnostic] = []
    has_messaging_context = any(
        item.declaration.kind in {"event", "topic"}
        for item in project.declaration_names
    )
    for consumer in project.declaration_names:
        if consumer.declaration.kind != "consumer" or consumer.declaration.span is None:
            continue

        consumer_name = (
            consumer.fully_qualified_name
            or consumer.declaration.name
            or "<unnamed>"
        )
        event_reference = consumer.declaration.node.attrs.get("on")
        topic_reference = consumer.declaration.node.attrs.get("from")
        if not isinstance(event_reference, str) or not event_reference.strip():
            if not has_messaging_context:
                continue
            diagnostics.append(
                _consumer_diagnostic(
                    consumer,
                    consumer.declaration.span,
                    f"consumer '{consumer_name}' must declare 'on EVENT from TOPIC'",
                )
            )
            continue
        if not isinstance(topic_reference, str) or not topic_reference.strip():
            diagnostics.append(
                _consumer_diagnostic(
                    consumer,
                    consumer.declaration.span,
                    f"consumer '{consumer_name}' must declare 'on EVENT from TOPIC'",
                )
            )
            continue

        events = _resolve_declaration_reference(
            project,
            consumer,
            event_reference.strip(),
            frozenset({"event"}),
        )
        if len(events) != 1:
            diagnostics.append(
                _consumer_diagnostic(
                    consumer,
                    consumer.declaration.span,
                    f"consumer '{consumer_name}' event '{event_reference.strip()}' must resolve uniquely; found {len(events)} matching event declarations",
                )
            )

        topics = _resolve_declaration_reference(
            project,
            consumer,
            topic_reference.strip(),
            frozenset({"topic"}),
        )
        if len(topics) != 1:
            diagnostics.append(
                _consumer_diagnostic(
                    consumer,
                    consumer.declaration.span,
                    f"consumer '{consumer_name}' topic '{topic_reference.strip()}' must resolve uniquely; found {len(topics)} matching topic declarations",
                )
            )

        if len(events) != 1 or len(topics) != 1:
            continue

        event = events[0]
        topic = topics[0]
        event_name = event.fully_qualified_name or event.declaration.name or "<unnamed>"
        topic_name = topic.fully_qualified_name or topic.declaration.name or "<unnamed>"
        if not _topic_contains_event(project, topic, event):
            diagnostics.append(
                _consumer_diagnostic(
                    consumer,
                    consumer.declaration.span,
                    f"consumer '{consumer_name}' event '{event_name}' is not declared by topic '{topic_name}'",
                )
            )

        delivery_values = _topic_delivery_values(topic.declaration)
        if not delivery_values or any(value != "atLeastOnce" for value in delivery_values):
            rendered = ", ".join(delivery_values) if delivery_values else "none"
            diagnostics.append(
                _consumer_diagnostic(
                    consumer,
                    consumer.declaration.span,
                    f"consumer '{consumer_name}' requires topic '{topic_name}' delivery atLeastOnce; found {rendered}",
                )
            )

    return tuple(diagnostics)


def _with_module_diagnostics(
    project: CompilerProject,
    base_diagnostics: Iterable[CompilerDiagnostic],
) -> tuple[CompilerDiagnostic, ...]:
    diagnostics = list(base_diagnostics)
    for issue in collect_module_validation_issues(project):
        diagnostics.append(
            CompilerDiagnostic(
                code=ModuleDiagnosticCode(issue.code),
                phase="resolve",
                severity=CompilerDiagnosticSeverity.ERROR,
                message=issue.message,
                source_path=issue.source_path,
                location=issue.location,
                subject=CompilerDiagnosticSubject(kind="module", name=issue.subject_name),
                expected=issue.expected,
                docs=f"aidl://diagnostics/{issue.code}",
            )
        )
    return tuple(diagnostics)


def _with_core_contract_diagnostics(
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
        diagnostics.extend(_app_contract_diagnostics(project))
        diagnostics.extend(_consumer_binding_diagnostics(project))
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
        ModuleDiagnosticCode.MODULE_STRUCTURE.value,
    }
    if not any(diagnostic.code.value in blocking_codes for diagnostic in diagnostics):
        issues = (
            *collect_type_issues(project),
            *collect_alias_opaque_materialization_issues(project),
            *collect_core_materialization_issues(project),
            *collect_consumer_materialization_issues(project),
            *collect_event_materialization_issues(project),
            *collect_topic_materialization_issues(project),
            *collect_value_materialization_issues(project),
        )
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
        _with_core_contract_diagnostics(
            project,
            _with_module_diagnostics(
                project,
                _base.collect_compiler_diagnostics(project, parser_diagnostics),
            ),
        ),
    )


def load_compiler_analysis(paths: Iterable[Path]) -> CompilerAnalysis:
    analysis = _base.load_compiler_analysis(paths)
    return CompilerAnalysis(
        project=analysis.project,
        diagnostics=_with_type_diagnostics(
            analysis.project,
            _with_core_contract_diagnostics(
                analysis.project,
                _with_module_diagnostics(analysis.project, analysis.diagnostics),
            ),
        ),
    )
