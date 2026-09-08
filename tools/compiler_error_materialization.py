"""Closed Core Error materialization boundary for the existing Canonical IR shape."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    from .compiler_project import CompilerProject
except ImportError:  # pragma: no cover
    from compiler_project import CompilerProject

_STRING = re.compile(r'^"([^"\\]*(?:\\.[^"\\]*)*)"$')
_ALLOWED_CLAUSES = {"code", "httpStatus", "retry", "safeMessage"}


@dataclass(frozen=True)
class ErrorMaterializationIssue:
    code: str
    message: str
    source_path: Path
    location: object
    subject_kind: str
    subject_name: str
    expected: str


def _issue(item, node, message: str, expected: str) -> ErrorMaterializationIssue | None:
    location = (node.span if node is not None else None) or item.declaration.span
    if location is None:
        return None
    return ErrorMaterializationIssue(
        code="AIDL-T005",
        message=message,
        source_path=item.document.source_path,
        location=location,
        subject_kind="error",
        subject_name=item.declaration.name or "<unnamed>",
        expected=expected,
    )


def _clause(text: str) -> tuple[str, str] | None:
    match = re.fullmatch(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*|\s+)(.*)",
        text.strip(),
        re.S,
    )
    if match is None:
        return None
    return match.group(1), match.group(2).strip()


def _non_empty_string(raw: str) -> bool:
    match = _STRING.fullmatch(raw)
    return match is not None and bool(match.group(1).strip())


def _canonical_core_context(project: CompilerProject) -> bool:
    apps = sum(item.declaration.kind == "app" for item in project.declaration_names)
    systems = sum(item.declaration.kind == "system" for item in project.declaration_names)
    return apps == 1 and systems == 1


def collect_error_materialization_issues(
    project: CompilerProject,
) -> tuple[ErrorMaterializationIssue, ...]:
    """Reject Error source facts the current errorDecl IR cannot preserve truthfully."""
    if not _canonical_core_context(project):
        return ()

    issues: list[ErrorMaterializationIssue] = []
    for item in project.declaration_names:
        declaration = item.declaration
        if declaration.kind != "error":
            continue

        by_key: dict[str, list[tuple[str, object]]] = {
            key: [] for key in _ALLOWED_CLAUSES
        }
        for node in declaration.node.children:
            text = (node.name or "").strip()
            parsed = _clause(text)
            if parsed is None:
                issue = _issue(
                    item,
                    node,
                    f"error '{declaration.name or '<unnamed>'}' contains a malformed or non-contract body entry '{text or '<empty>'}'",
                    "only explicit code, httpStatus, retry, and safeMessage clauses",
                )
                if issue:
                    issues.append(issue)
                continue

            key, raw = parsed
            if key == "localizationKey":
                issue = _issue(
                    item,
                    node,
                    f"error '{declaration.name or '<unnamed>'}' localizationKey is not represented by the current Canonical IR error contract",
                    "explicit non-empty safeMessage until localizationKey has a Canonical IR representation",
                )
                if issue:
                    issues.append(issue)
                continue
            if key not in _ALLOWED_CLAUSES:
                issue = _issue(
                    item,
                    node,
                    f"error '{declaration.name or '<unnamed>'}' body fact '{key}' is not represented by the current Canonical IR error contract",
                    "only explicit code, httpStatus, retry, and safeMessage clauses",
                )
                if issue:
                    issues.append(issue)
                continue
            by_key[key].append((raw, node))

        # Exported errors already have AIDL-T003 ownership for missing/duplicate
        # public contract clauses and malformed code/status/message values. Keep
        # that stronger existing diagnostic authoritative instead of duplicating it.
        exported = declaration.exported
        for key in ("code", "httpStatus", "retry", "safeMessage"):
            entries = by_key[key]
            if len(entries) != 1:
                if not exported:
                    node = entries[1][1] if len(entries) > 1 else None
                    issue = _issue(
                        item,
                        node,
                        f"error '{declaration.name or '<unnamed>'}' must declare exactly one explicit {key} for lossless Canonical IR materialization",
                        "exactly one explicit code, httpStatus, retry, and safeMessage clause",
                    )
                    if issue:
                        issues.append(issue)
                continue

            raw, node = entries[0]
            if key == "code" and not _non_empty_string(raw):
                if not exported:
                    issue = _issue(
                        item,
                        node,
                        "error code must be an explicit non-empty string before Canonical IR",
                        "non-empty quoted error code",
                    )
                    if issue:
                        issues.append(issue)
            elif key == "safeMessage" and not _non_empty_string(raw):
                if not exported:
                    issue = _issue(
                        item,
                        node,
                        "error safeMessage must be an explicit non-empty string before Canonical IR",
                        "non-empty quoted safeMessage",
                    )
                    if issue:
                        issues.append(issue)
            elif key == "httpStatus":
                valid_status = bool(re.fullmatch(r"\d{3}", raw)) and 400 <= int(raw) <= 599
                if not valid_status and not exported:
                    issue = _issue(
                        item,
                        node,
                        f"error httpStatus '{raw}' is not a 4xx/5xx transport status",
                        "integer transport status from 400 through 599",
                    )
                    if issue:
                        issues.append(issue)
            elif key == "retry":
                # The closed schema values are not a 1:1 spelling match for the
                # wider source retry classes. `never` is the only normative source
                # spelling already represented unchanged; do not invent a mapping.
                if raw != "never":
                    # Invalid exported retry spellings remain owned by AIDL-T003.
                    t003_owned = exported and re.match(
                        r"^(never|immediate|backoff|after)(?:\s|\(|$)", raw
                    ) is None
                    if not t003_owned:
                        issue = _issue(
                            item,
                            node,
                            f"error retry source form '{raw}' has no normative 1:1 mapping to the current Canonical IR retry value",
                            "retry never",
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
