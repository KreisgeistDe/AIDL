"""Closed Core Value body materialization boundary."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    from .compiler_core_materialization import collect_core_materialization_issues
    from .compiler_project import CompilerProject
    from .compiler_typecheck import TypeSyntaxError, collect_type_issues, parse_type
except ImportError:  # pragma: no cover
    from compiler_core_materialization import collect_core_materialization_issues
    from compiler_project import CompilerProject
    from compiler_typecheck import TypeSyntaxError, collect_type_issues, parse_type

_FIELD = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+)$", re.S)
_SUPPORTED_MODIFIERS = {
    "required",
    "primary",
    "generated",
    "mutable",
    "sensitive",
    "concurrencyToken",
}
_UNSUPPORTED_MODIFIERS = {
    "clientGenerated",
    "immutable",
    "unique",
    "default",
    "onDelete",
    "via",
}


@dataclass(frozen=True)
class ValueMaterializationIssue:
    code: str
    message: str
    source_path: Path
    location: object
    subject_kind: str
    subject_name: str
    expected: str


def _issue(item, node, message: str, expected: str) -> ValueMaterializationIssue | None:
    location = node.span or item.declaration.span
    if location is None:
        return None
    return ValueMaterializationIssue(
        code="AIDL-T005",
        message=message,
        source_path=item.document.source_path,
        location=location,
        subject_kind="value",
        subject_name=item.declaration.name or "<unnamed>",
        expected=expected,
    )


def _normalize_type_spacing(text: str) -> str:
    text = re.sub(r"\s*\.\s*", ".", text.strip())
    text = re.sub(r"\s*<\s*", "<", text)
    text = re.sub(r"\s*>", ">", text)
    text = re.sub(r"\[\s*", "[", text)
    text = re.sub(r"\s*\]", "]", text)
    text = re.sub(r"\s*\?", "?", text)
    return text


def _take_type(tail: str) -> tuple[str, str]:
    tail = _normalize_type_spacing(tail)
    if tail.startswith("ref "):
        parts = tail.split(None, 2)
        return "ref " + parts[1], parts[2] if len(parts) > 2 else ""
    stack: list[str] = []
    close = {")": "(", "]": "[", ">": "<"}
    for index, char in enumerate(tail):
        if char in "([<":
            stack.append(char)
        elif char in ")]>" and stack and stack[-1] == close[char]:
            stack.pop()
        elif char.isspace() and not stack:
            return tail[:index].strip(), tail[index + 1 :].strip()
    return tail, ""


def _owned_type_locations(project: CompilerProject) -> set[tuple[Path, int]]:
    """Locations already owned by pre-existing AIDL-T001/T005 type boundaries."""
    return {
        (issue.source_path, issue.location.offset)
        for issue in (
            *collect_type_issues(project),
            *collect_core_materialization_issues(project),
        )
    }


def collect_value_materialization_issues(
    project: CompilerProject,
) -> tuple[ValueMaterializationIssue, ...]:
    """Reject Value body facts the current Canonical IR cannot preserve."""
    issues: list[ValueMaterializationIssue] = []
    owned_type_locations = _owned_type_locations(project)
    for item in project.declaration_names:
        declaration = item.declaration
        if declaration.kind != "value":
            continue
        if declaration.node.attrs.get("typeParameters"):
            continue  # Existing shared AIDL-T005 generic-declaration boundary owns this case.

        seen_fields: set[str] = set()
        for node in declaration.node.children:
            text = (node.name or "").strip()
            if text.startswith("invariant "):
                issue = _issue(
                    item,
                    node,
                    f"value '{declaration.name or '<unnamed>'}' invariant is not represented by the current Canonical IR value contract",
                    "Value body contains only losslessly materialized fields",
                )
                if issue:
                    issues.append(issue)
                continue

            match = _FIELD.fullmatch(text)
            if match is None:
                issue = _issue(
                    item,
                    node,
                    f"value '{declaration.name or '<unnamed>'}' contains a malformed or non-field body entry '{text or '<empty>'}'",
                    "field declaration 'name: Type' with supported Value modifiers",
                )
                if issue:
                    issues.append(issue)
                continue

            field_name, tail = match.groups()
            if field_name in seen_fields:
                issue = _issue(
                    item,
                    node,
                    f"value '{declaration.name or '<unnamed>'}' declares duplicate field '{field_name}'",
                    "unique Value field names",
                )
                if issue:
                    issues.append(issue)
            seen_fields.add(field_name)

            type_expression, modifiers = _take_type(tail)
            try:
                parsed_type = parse_type(type_expression)
            except TypeSyntaxError:
                location = node.span or declaration.span
                if location is not None and (
                    item.document.source_path,
                    location.offset,
                ) in owned_type_locations:
                    continue
                issue = _issue(
                    item,
                    node,
                    f"value field '{field_name}' type '{type_expression}' is not losslessly materialized by the current Canonical IR Value field contract",
                    "a Core type form accepted and losslessly materialized by the current Canonical IR",
                )
                if issue:
                    issues.append(issue)
                continue

            modifier_words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", modifiers)
            unsupported = next(
                (word for word in modifier_words if word in _UNSUPPORTED_MODIFIERS),
                None,
            )
            if unsupported is not None:
                issue = _issue(
                    item,
                    node,
                    f"value field '{field_name}' modifier '{unsupported}' is not represented by the current Canonical IR Value field contract",
                    "required, primary, generated, mutable, sensitive, or concurrencyToken",
                )
                if issue:
                    issues.append(issue)
                continue

            unknown = next(
                (word for word in modifier_words if word not in _SUPPORTED_MODIFIERS),
                None,
            )
            if unknown is not None:
                issue = _issue(
                    item,
                    node,
                    f"value field '{field_name}' contains unsupported or malformed modifier text '{modifiers}'",
                    "only modifiers losslessly represented by the current Canonical IR Value field contract",
                )
                if issue:
                    issues.append(issue)
                continue

            if len(modifier_words) != len(set(modifier_words)):
                issue = _issue(
                    item,
                    node,
                    f"value field '{field_name}' repeats a modifier that Canonical IR cannot preserve as a distinct source fact",
                    "each supported Value field modifier appears at most once",
                )
                if issue:
                    issues.append(issue)
                continue

            if parsed_type.kind == "nullable" and "required" in modifier_words:
                issue = _issue(
                    item,
                    node,
                    f"value field '{field_name}' is nullable but also marked required",
                    "nullable field without required, or non-nullable required field",
                )
                if issue:
                    issues.append(issue)

    document_order = {
        document.source_path: index for index, document in enumerate(project.documents)
    }
    issues.sort(
        key=lambda issue: (
            document_order.get(issue.source_path, len(document_order)),
            issue.location.offset,
            issue.code,
            issue.message,
        )
    )
    return tuple(issues)
