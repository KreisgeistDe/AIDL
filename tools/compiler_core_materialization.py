"""Reject Core semantics that current semantic/IR layers cannot materialize."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    from .compiler_project import CompilerProject
    from .compiler_typecheck import TypeRef, TypeSyntaxError, parse_type
except ImportError:  # pragma: no cover
    from compiler_project import CompilerProject
    from compiler_typecheck import TypeRef, TypeSyntaxError, parse_type

STD_TYPES = {
    "Page", "PageInput", "Cursor", "OperationId", "PrincipalId", "SubjectId",
    "FieldError", "FieldErrors", "ProblemDetails", "Unit",
}
STD_ERRORS = {
    "InternalFailure", "InvalidInput", "NotAuthenticated", "NotAuthorized",
    "ConcurrentChange", "IdempotencyMismatch", "DependencyUnavailable", "RateLimited",
}
MATERIALIZED_TYPE_KINDS = {"alias", "opaque", "enum", "value", "entity", "view"}
GENERIC_DECLARATION_KINDS = {
    "alias", "opaque", "value", "view", "query", "mutation", "workflow", "saga", "task",
}
FIELD = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+)$", re.S)
_CONSUMER_SERVICE = re.compile(
    r"^service\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)$"
)
_CONSUMER_START = re.compile(
    r"^start\s*:\s*(workflow|task|mutation)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*(?:\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)*)\s*\(",
    re.S,
)
_POSITIVE_DURATION = re.compile(r"^[1-9][0-9]*(?:ms|s|m|h|d)$")


@dataclass(frozen=True)
class CoreMaterializationIssue:
    code: str
    message: str
    source_path: Path
    location: object
    subject_kind: str
    subject_name: str
    expected: str


def _identity(item) -> tuple[Path, int]:
    span = item.declaration.span
    return item.document.source_path, span.offset if span else -1


def _resolve(project: CompilerProject, source, ref: str):
    ref = re.sub(r"\s*\.\s*", ".", ref)
    found = []
    if "." in ref:
        found.extend(project.symbol_table.lookup_declarations(ref))
    else:
        module = source.document.module
        if module and module.name:
            found.extend(project.symbol_table.lookup_declarations(f"{module.name}.{ref}"))
        for resolution in project.import_resolutions:
            if resolution.document is source.document:
                found.extend(
                    declaration for declaration in resolution.declarations
                    if declaration.declaration.name == ref
                )
    result = []
    seen = set()
    for candidate in found:
        key = _identity(candidate)
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return tuple(result)


def _issue(item, message: str, expected: str, location=None) -> CoreMaterializationIssue | None:
    location = location or item.declaration.span
    if location is None:
        return None
    return CoreMaterializationIssue(
        code="AIDL-T005",
        message=message,
        source_path=item.document.source_path,
        location=location,
        subject_kind=item.declaration.kind,
        subject_name=item.declaration.name or "<unnamed>",
        expected=expected,
    )


def _split(text: str) -> tuple[str, ...]:
    parts: list[str] = []
    buffer: list[str] = []
    stack: list[str] = []
    quote: str | None = None
    close = {")": "(", "]": "[", "}": "{", ">": "<"}
    for char in text:
        if quote:
            buffer.append(char)
            if char == quote and (len(buffer) < 2 or buffer[-2] != "\\"):
                quote = None
        elif char in "\"'":
            quote = char
            buffer.append(char)
        elif char in "([{<":
            stack.append(char)
            buffer.append(char)
        elif char in ")]}>":
            if stack and stack[-1] == close[char]:
                stack.pop()
            buffer.append(char)
        elif char == "," and not stack:
            part = "".join(buffer).strip()
            if part:
                parts.append(part)
            buffer = []
        else:
            buffer.append(char)
    part = "".join(buffer).strip()
    if part:
        parts.append(part)
    return tuple(parts)


def _normalize_type_spacing(text: str) -> str:
    text = re.sub(r"\s*\.\s*", ".", text.strip())
    text = re.sub(r"\s*<\s*", "<", text)
    text = re.sub(r"\s*>\s*", ">", text)
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
        elif char in ")]>":
            if stack and stack[-1] == close[char]:
                stack.pop()
        elif char.isspace() and not stack:
            return tail[:index], tail[index + 1 :].strip()
    return tail, ""


def _type_expressions(item):
    declaration = item.declaration
    if declaration.kind in {"alias", "opaque"}:
        raw = declaration.node.attrs.get("type")
        if isinstance(raw, str) and raw.strip():
            yield _normalize_type_spacing(raw), declaration.span
    if declaration.kind in {"value", "entity", "error", "event"}:
        for node in declaration.node.children:
            if not node.name:
                continue
            match = FIELD.match(node.name.strip())
            if match:
                type_expression, _ = _take_type(match.group(2))
                yield type_expression, node.span
    if declaration.kind in {"query", "mutation"}:
        raw = declaration.node.attrs.get("parameters")
        if isinstance(raw, str):
            raw = raw.strip()
            raw = raw[1:-1] if raw.startswith("(") and raw.endswith(")") else raw
            for part in _split(raw):
                match = FIELD.match(part)
                if match:
                    type_expression, _ = _take_type(match.group(2))
                    yield type_expression, declaration.span
        returns = declaration.node.attrs.get("returns")
        if isinstance(returns, str) and returns.strip():
            yield _normalize_type_spacing(returns), declaration.span


def _visit_type(project: CompilerProject, item, root: TypeRef, raw: str, location, issues: list[CoreMaterializationIssue]) -> None:
    if root.kind == "entity-id":
        matches = _resolve(project, item, root.name or "")
        if len(matches) == 1 and matches[0].declaration.kind != "entity":
            issue = _issue(
                item,
                f"entity-id type '{raw}' resolves to unsupported declaration kind '{matches[0].declaration.kind}'",
                "entity identity type resolves to one entity declaration",
                location,
            )
            if issue:
                issues.append(issue)
    elif root.kind == "named":
        name = root.name or ""
        if name.split(".")[-1] not in STD_TYPES:
            matches = _resolve(project, item, name)
            if len(matches) == 1:
                target = matches[0]
                if target.declaration.kind not in MATERIALIZED_TYPE_KINDS:
                    issue = _issue(
                        item,
                        f"nominal type '{name}' resolves to unsupported declaration kind '{target.declaration.kind}'",
                        "alias, opaque, enum, value, entity, view, or standard-library type",
                        location,
                    )
                    if issue:
                        issues.append(issue)
                elif root.args or target.declaration.node.attrs.get("typeParameters"):
                    issue = _issue(
                        item,
                        f"generic project type '{name}' is parsed but its type-parameter semantics are not materialized in canonical IR",
                        "non-generic project nominal type until generic IR semantics are implemented",
                        location,
                    )
                    if issue:
                        issues.append(issue)
            # Unresolved type names remain owned by the existing resolver/CLI path.
    for argument in root.args:
        _visit_type(project, item, argument, raw, location, issues)


def _error_name_issues(project: CompilerProject, item, issues: list[CoreMaterializationIssue]) -> None:
    pattern = re.compile(r"^errors(?:\s*:\s*|\s+)(.*)$", re.S)
    for node in item.declaration.node.children:
        if not node.name or not node.span:
            continue
        match = pattern.match(node.name.strip())
        if not match:
            continue
        raw = match.group(1).strip()
        if not (raw.startswith("[") and raw.endswith("]")):
            continue
        for entry in _split(raw[1:-1]):
            name = re.sub(r"\s*\.\s*", ".", entry)
            if name.split(".")[-1] in STD_ERRORS:
                continue
            matches = _resolve(project, item, name)
            if not matches:
                issue = _issue(
                    item,
                    f"declared error '{name}' is not materialized by the current project or Core standard library",
                    "resolved project error or declared Core standard error",
                    node.span,
                )
                if issue:
                    issues.append(issue)
            elif len(matches) > 1:
                issue = _issue(
                    item,
                    f"declared error '{name}' is ambiguous; found {len(matches)} declarations",
                    "exactly one resolved project error",
                    node.span,
                )
                if issue:
                    issues.append(issue)


def _list_clause(declaration, key: str) -> tuple[str, ...]:
    pattern = re.compile(rf"^{re.escape(key)}(?:\s*:\s*|\s+)(\[.*\])$", re.S)
    for child in declaration.node.children:
        if not child.name:
            continue
        match = pattern.match(child.name.strip())
        if match:
            raw = match.group(1).strip()
            return _split(raw[1:-1])
    return ()


def _service_runs_consumer(project: CompilerProject, service, consumer) -> bool:
    consumer_identity = _identity(consumer)
    for entry in _list_clause(service.declaration, "runs"):
        match = re.fullmatch(r"consumer\s+(.+)", entry.strip(), re.S)
        if not match:
            continue
        resolved = _resolve(project, service, match.group(1).strip())
        if len(resolved) == 1 and _identity(resolved[0]) == consumer_identity:
            return True
    return False


def _system_contains_service(project: CompilerProject, service) -> bool:
    service_identity = _identity(service)
    for system in project.declaration_names:
        if system.declaration.kind != "system":
            continue
        for reference in _list_clause(system.declaration, "services"):
            resolved = _resolve(project, system, reference)
            if len(resolved) == 1 and _identity(resolved[0]) == service_identity:
                return True
    return False


def _canonical_core_context(project: CompilerProject) -> bool:
    apps = sum(item.declaration.kind == "app" for item in project.declaration_names)
    systems = sum(item.declaration.kind == "system" for item in project.declaration_names)
    return apps == 1 and systems == 1


def _consumer_execution_issues(project: CompilerProject, item, issues: list[CoreMaterializationIssue]) -> None:
    """Reject only consumer execution facts that a full Core IR build would lose or widen."""
    if not _canonical_core_context(project):
        return
    event = item.declaration.node.attrs.get("on")
    topic = item.declaration.node.attrs.get("from")
    if not isinstance(event, str) or not isinstance(topic, str):
        return

    for child in item.declaration.node.children:
        if not child.name or not child.span:
            continue
        clause = child.name.strip()

        service_match = _CONSUMER_SERVICE.fullmatch(clause)
        if service_match:
            reference = re.sub(r"\s*\.\s*", ".", service_match.group(1))
            services = tuple(
                candidate
                for candidate in _resolve(project, item, reference)
                if candidate.declaration.kind == "service"
            )
            if len(services) != 1:
                issue = _issue(
                    item,
                    f"consumer service '{reference}' must resolve uniquely before Canonical IR materialization; found {len(services)} service declarations",
                    "one resolved service that runs the consumer and is included by the system",
                    child.span,
                )
                if issue:
                    issues.append(issue)
            else:
                service = services[0]
                service_name = service.fully_qualified_name or service.declaration.name or reference
                if not _service_runs_consumer(project, service, item):
                    issue = _issue(
                        item,
                        f"consumer service '{service_name}' does not list consumer '{item.declaration.name or '<unnamed>'}' in its runs clause",
                        "consumer service binding preserved by the canonical service runs contract",
                        child.span,
                    )
                    if issue:
                        issues.append(issue)
                elif not _system_contains_service(project, service):
                    issue = _issue(
                        item,
                        f"consumer service '{service_name}' is not included by the canonical system services clause",
                        "consumer service binding preserved by a service included in the canonical system",
                        child.span,
                    )
                    if issue:
                        issues.append(issue)
            continue

        if "retry" in clause and "immediate" in clause:
            issue = _issue(
                item,
                "consumer retry policy 'immediate' is grammatical but not representable by the closed Core Canonical IR retry contract",
                "retry none or fully specified exponential retry until immediate retry has a canonical IR representation",
                child.span,
            )
            if issue:
                issues.append(issue)
            continue

        if "retry" in clause and "exponential" in clause:
            match = re.search(r"exponential\s*\((.*)\)", clause, re.S)
            arguments: dict[str, str] = {}
            if match:
                for part in _split(match.group(1)):
                    if ":" not in part:
                        continue
                    key, value = (piece.strip() for piece in part.split(":", 1))
                    if key and key not in arguments:
                        arguments[key] = value
            valid = (
                set(arguments) == {"initial", "maxDelay", "attempts"}
                and _POSITIVE_DURATION.fullmatch(arguments.get("initial", "")) is not None
                and _POSITIVE_DURATION.fullmatch(arguments.get("maxDelay", "")) is not None
                and re.fullmatch(r"[1-9][0-9]*", arguments.get("attempts", "")) is not None
            )
            if not valid:
                issue = _issue(
                    item,
                    "consumer exponential retry must declare positive initial, maxDelay, and attempts values that Canonical IR can preserve",
                    "exponential(initial: POSITIVE_DURATION, maxDelay: POSITIVE_DURATION, attempts: POSITIVE_INT)",
                    child.span,
                )
                if issue:
                    issues.append(issue)
            continue

        start_match = _CONSUMER_START.match(clause)
        if start_match:
            target_kind, target_reference = start_match.groups()
            target_reference = re.sub(r"\s*\.\s*", ".", target_reference)
            if target_kind == "mutation":
                issue = _issue(
                    item,
                    "consumer start mutation is grammatical but not representable by the closed Core Canonical IR start effect",
                    "start workflow or task until mutation start has a canonical IR representation",
                    child.span,
                )
                if issue:
                    issues.append(issue)
            else:
                targets = tuple(
                    candidate
                    for candidate in _resolve(project, item, target_reference)
                    if candidate.declaration.kind == target_kind
                )
                if len(targets) != 1:
                    issue = _issue(
                        item,
                        f"consumer start {target_kind} target '{target_reference}' must resolve uniquely before Canonical IR materialization; found {len(targets)} declarations",
                        f"one resolved {target_kind} target",
                        child.span,
                    )
                    if issue:
                        issues.append(issue)
            continue

        if re.match(r"^call\s*:", clause):
            issue = _issue(
                item,
                "consumer call is grammatical but its execution contract is not materialized by the closed Core Canonical IR",
                "no consumer call until its target and execution semantics have a canonical IR representation",
                child.span,
            )
            if issue:
                issues.append(issue)
            continue

        if child.kind == "blockClause" and re.match(r"^transaction\s+on\s+", clause):
            issue = _issue(
                item,
                "consumer transaction is grammatical without the isolation required by the normative Core transaction contract and is not materialized by Canonical IR",
                "no consumer transaction until grammar, isolation semantics, and canonical IR agree",
                child.span,
            )
            if issue:
                issues.append(issue)


def collect_core_materialization_issues(project: CompilerProject) -> tuple[CoreMaterializationIssue, ...]:
    """Return deterministic errors for Core facts that would otherwise be widened or dropped."""
    issues: list[CoreMaterializationIssue] = []
    for item in project.declaration_names:
        declaration = item.declaration
        if declaration.kind in GENERIC_DECLARATION_KINDS and declaration.node.attrs.get("typeParameters"):
            issue = _issue(
                item,
                f"generic {declaration.kind} '{declaration.name or '<unnamed>'}' is parsed but type parameters are not materialized in canonical IR",
                "non-generic Core declaration until generic IR semantics are implemented",
            )
            if issue:
                issues.append(issue)
        else:
            for raw, location in _type_expressions(item):
                try:
                    root = parse_type(raw)
                except TypeSyntaxError:
                    continue  # M10-03 owns malformed constructors.
                _visit_type(project, item, root, raw, location, issues)
        if declaration.kind in {"query", "mutation"}:
            _error_name_issues(project, item, issues)
        if declaration.kind == "consumer":
            _consumer_execution_issues(project, item, issues)

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
