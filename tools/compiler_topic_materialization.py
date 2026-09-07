"""Reject Topic source facts that cannot map one-to-one into closed Core IR."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    from .compiler_project import CompilerProject
except ImportError:  # pragma: no cover
    from compiler_project import CompilerProject

_SYMBOL_PATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_DURATION = re.compile(r"^[1-9][0-9]*(?:ms|s|m|h|d)$")
_CLAUSE_PATTERNS = {
    "events": re.compile(r"^events(?:\s*:\s*|\s+)(\[.*\])$", re.S),
    "delivery": re.compile(r"^delivery(?:\s*:\s*|\s+)([A-Za-z_][A-Za-z0-9_]*)$"),
    "partition": re.compile(r"^partition(?:\s*:\s*|\s+)by\s+(.+)$", re.S),
    "ordering": re.compile(r"^ordering(?:\s*:\s*|\s+)([A-Za-z_][A-Za-z0-9_]*)$"),
    "retention": re.compile(r"^retention(?:\s*:\s*|\s+)(\S+)$"),
    "compatibility": re.compile(r"^compatibility(?:\s*:\s*|\s+)([A-Za-z_][A-Za-z0-9_]*)$"),
    "deadLetter": re.compile(r"^deadLetter(?:\s*:\s*|\s+)after\s+([1-9][0-9]*)\s+attempts$"),
}


@dataclass(frozen=True)
class TopicMaterializationIssue:
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
    ref = re.sub(r"\s*\.\s*", ".", ref.strip())
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
                    declaration
                    for declaration in resolution.declarations
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


def _issue(item, message: str, expected: str, location=None) -> TopicMaterializationIssue | None:
    location = location or item.declaration.span
    if location is None:
        return None
    return TopicMaterializationIssue(
        code="AIDL-T005",
        message=message,
        source_path=item.document.source_path,
        location=location,
        subject_kind="topic",
        subject_name=item.declaration.name or "<unnamed>",
        expected=expected,
    )


def _split_list(raw: str) -> tuple[str, ...]:
    if not (raw.startswith("[") and raw.endswith("]")):
        return ()
    return tuple(part.strip() for part in raw[1:-1].split(",") if part.strip())


def _canonical_core_context(project: CompilerProject) -> bool:
    apps = sum(item.declaration.kind == "app" for item in project.declaration_names)
    systems = sum(item.declaration.kind == "system" for item in project.declaration_names)
    return apps == 1 and systems == 1


def _topic_issues(project: CompilerProject, item) -> tuple[TopicMaterializationIssue, ...]:
    if not _canonical_core_context(project):
        return ()

    issues: list[TopicMaterializationIssue] = []
    clauses: dict[str, list[tuple[str, object]]] = {key: [] for key in _CLAUSE_PATTERNS}
    for child in item.declaration.node.children:
        if not child.name or child.span is None:
            continue
        text = child.name.strip()
        for key in clauses:
            if re.match(rf"^{re.escape(key)}(?:\s|:)", text):
                clauses[key].append((text, child.span))
                break

    for key, entries in clauses.items():
        if not entries:
            issue = _issue(
                item,
                f"topic requires one explicit '{key}' clause before Canonical IR materialization",
                "exactly one explicit value for every closed Topic IR field",
            )
            if issue:
                issues.append(issue)
        elif len(entries) > 1:
            for _, location in entries[1:]:
                issue = _issue(
                    item,
                    f"topic '{key}' must be a singleton clause; found {len(entries)} values",
                    f"exactly one explicit '{key}' clause",
                    location,
                )
                if issue:
                    issues.append(issue)

    if any(len(entries) != 1 for entries in clauses.values()):
        return tuple(issues)

    parsed: dict[str, tuple[str, object]] = {}
    for key, entries in clauses.items():
        text, location = entries[0]
        match = _CLAUSE_PATTERNS[key].fullmatch(text)
        if match is None:
            issue = _issue(
                item,
                f"topic '{key}' clause is not losslessly materializable: '{text}'",
                f"closed Core Topic {key} syntax",
                location,
            )
            if issue:
                issues.append(issue)
            continue
        parsed[key] = (match.group(1).strip(), location)

    if len(parsed) != len(clauses):
        return tuple(issues)

    raw_events, events_location = parsed["events"]
    references = _split_list(raw_events)
    if not references:
        issue = _issue(item, "topic events must contain at least one event", "one or more uniquely resolved event references", events_location)
        if issue:
            issues.append(issue)
    else:
        seen_events: set[tuple[Path, int]] = set()
        for reference in references:
            matches = _resolve(project, item, reference)
            if len(matches) != 1:
                issue = _issue(
                    item,
                    f"topic event '{reference}' must resolve uniquely; found {len(matches)} declarations",
                    "exactly one resolved event declaration",
                    events_location,
                )
                if issue:
                    issues.append(issue)
                continue
            target = matches[0]
            if target.declaration.kind != "event":
                issue = _issue(
                    item,
                    f"topic event '{reference}' resolves to unsupported declaration kind '{target.declaration.kind}'",
                    "event reference",
                    events_location,
                )
                if issue:
                    issues.append(issue)
                continue
            identity = _identity(target)
            if identity in seen_events:
                issue = _issue(
                    item,
                    f"topic events contain duplicate canonical event '{target.fully_qualified_name or target.declaration.name}'",
                    "unique canonical event IDs",
                    events_location,
                )
                if issue:
                    issues.append(issue)
            seen_events.add(identity)

    delivery, location = parsed["delivery"]
    if delivery != "atLeastOnce":
        issue = _issue(item, f"topic delivery '{delivery}' is outside the closed Core Topic IR contract", "delivery atLeastOnce", location)
        if issue:
            issues.append(issue)

    partition, location = parsed["partition"]
    partition = re.sub(r"\s*\.\s*", ".", partition)
    if _SYMBOL_PATH.fullmatch(partition) is None:
        issue = _issue(item, f"topic partition expression '{partition}' is not losslessly projectable as partitionField", "partition by a simple field or symbol path", location)
        if issue:
            issues.append(issue)

    ordering, location = parsed["ordering"]
    if ordering not in {"none", "perPartition"}:
        issue = _issue(item, f"topic ordering '{ordering}' is outside the closed Core Topic IR contract", "ordering none or perPartition", location)
        if issue:
            issues.append(issue)

    retention, location = parsed["retention"]
    if _DURATION.fullmatch(retention) is None:
        issue = _issue(item, f"topic retention '{retention}' is not a positive materializable duration", "positive integer duration", location)
        if issue:
            issues.append(issue)

    compatibility, location = parsed["compatibility"]
    if compatibility not in {"none", "backward", "forward", "full"}:
        issue = _issue(item, f"topic compatibility '{compatibility}' is outside the closed Core Topic IR contract", "compatibility none, backward, forward, or full", location)
        if issue:
            issues.append(issue)

    return tuple(issues)


def collect_topic_materialization_issues(project: CompilerProject) -> tuple[TopicMaterializationIssue, ...]:
    issues: list[TopicMaterializationIssue] = []
    for item in project.declaration_names:
        if item.declaration.kind == "topic":
            issues.extend(_topic_issues(project, item))
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
