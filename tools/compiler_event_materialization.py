"""Reject Event source facts that cannot map one-to-one into closed Core IR."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    from .compiler_project import CompilerProject
except ImportError:  # pragma: no cover
    from compiler_project import CompilerProject

_FIELD = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+)$", re.S)
_FIELD_MODIFIER = re.compile(
    r"^(required|mutable|sensitive|generated|primary|concurrencyToken)(?:\s+|$)|^onDelete\s+(restrict|cascade|setNull|none)(?:\s+|$)"
)


@dataclass(frozen=True)
class EventMaterializationIssue:
    code: str
    message: str
    source_path: Path
    location: object
    subject_kind: str
    subject_name: str
    expected: str


def _issue(item, message: str, expected: str, location=None) -> EventMaterializationIssue | None:
    location = location or item.declaration.span
    if location is None:
        return None
    return EventMaterializationIssue(
        code="AIDL-T005",
        message=message,
        source_path=item.document.source_path,
        location=location,
        subject_kind="event",
        subject_name=item.declaration.name or "<unnamed>",
        expected=expected,
    )


def _canonical_core_context(project: CompilerProject) -> bool:
    apps = sum(item.declaration.kind == "app" for item in project.declaration_names)
    systems = sum(item.declaration.kind == "system" for item in project.declaration_names)
    return apps == 1 and systems == 1


def _take_type_and_modifiers(tail: str) -> tuple[str, str]:
    tail = tail.strip()
    stack: list[str] = []
    close = {")": "(", "]": "[", ">": "<"}
    for index, char in enumerate(tail):
        if char in "([<":
            stack.append(char)
        elif char in ")]>" and stack and stack[-1] == close[char]:
            stack.pop()
        elif char.isspace() and not stack:
            remainder = tail[index:].strip()
            if _FIELD_MODIFIER.match(remainder):
                return tail[:index].strip(), remainder
    return tail, ""


def _modifiers_projectable(modifiers: str) -> bool:
    rest = modifiers.strip()
    while rest:
        match = _FIELD_MODIFIER.match(rest)
        if match is None:
            return False
        rest = rest[match.end():].strip()
    return True


def _event_issues(project: CompilerProject, item) -> tuple[EventMaterializationIssue, ...]:
    if not _canonical_core_context(project):
        return ()

    issues: list[EventMaterializationIssue] = []
    version = item.declaration.node.attrs.get("version")
    if not isinstance(version, str) or re.fullmatch(r"[1-9][0-9]*", version) is None:
        rendered = version if isinstance(version, str) and version else "missing"
        issue = _issue(
            item,
            f"event version must be an explicit positive major before Canonical IR materialization; found '{rendered}'",
            "event NAME version POSITIVE_MAJOR",
        )
        if issue:
            issues.append(issue)

    evolves = item.declaration.node.attrs.get("evolves")
    if isinstance(evolves, str) and evolves.strip():
        issue = _issue(
            item,
            f"event evolves clause '{evolves.strip()}' is outside the closed Core Event IR contract",
            "versioned Core event without evolves until evolution IR semantics are implemented",
        )
        if issue:
            issues.append(issue)

    seen_fields: set[str] = set()
    materialized_fields = 0
    for child in item.declaration.node.children:
        if child.name is None or child.span is None:
            continue
        text = child.name.strip()
        match = _FIELD.fullmatch(text)
        if match is None:
            issue = _issue(
                item,
                f"event body entry is not losslessly materializable as a field: '{text}'",
                "event field 'name: Type' with only Canonical-IR field modifiers",
                child.span,
            )
            if issue:
                issues.append(issue)
            continue
        name, tail = match.groups()
        type_expression, modifiers = _take_type_and_modifiers(tail)
        if not type_expression:
            issue = _issue(item, f"event field '{name}' has no materializable type", "non-empty field type", child.span)
            if issue:
                issues.append(issue)
            continue
        if modifiers and not _modifiers_projectable(modifiers):
            issue = _issue(
                item,
                f"event field '{name}' contains modifiers that Canonical IR would drop: '{modifiers}'",
                "only required, mutable, sensitive, generated, primary, concurrencyToken, or onDelete modifiers",
                child.span,
            )
            if issue:
                issues.append(issue)
        if type_expression.endswith("?") and re.search(r"(?:^|\s)required(?:\s|$)", modifiers):
            issue = _issue(
                item,
                f"event field '{name}' declares nullable type '{type_expression}' and required; Canonical IR cannot preserve both facts",
                "nullable field without required, or non-nullable required field",
                child.span,
            )
            if issue:
                issues.append(issue)
        if name in seen_fields:
            issue = _issue(item, f"event field '{name}' is duplicated", "unique event field names", child.span)
            if issue:
                issues.append(issue)
        else:
            seen_fields.add(name)
        materialized_fields += 1

    if materialized_fields == 0:
        issue = _issue(item, "event requires at least one materializable field", "one or more event fields")
        if issue:
            issues.append(issue)
    return tuple(issues)


def collect_event_materialization_issues(project: CompilerProject) -> tuple[EventMaterializationIssue, ...]:
    issues: list[EventMaterializationIssue] = []
    for item in project.declaration_names:
        if item.declaration.kind == "event":
            issues.extend(_event_issues(project, item))
    document_order = {document.source_path: index for index, document in enumerate(project.documents)}
    issues.sort(
        key=lambda issue: (
            document_order.get(issue.source_path, len(document_order)),
            issue.location.offset,
            issue.code,
            issue.message,
        )
    )
    return tuple(issues)
