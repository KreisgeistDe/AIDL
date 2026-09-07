"""Closed Core Alias/Opaque target-type materialization boundary."""
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
_SCALAR_INVOCATION = re.compile(
    r"\b(string|int|decimal|bool|uuid|date|datetime|duration|revision|email|url|bytes)\s*\(([^()]*)\)"
)
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass(frozen=True)
class AliasOpaqueMaterializationIssue:
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


def _issue(item, message: str, expected: str) -> AliasOpaqueMaterializationIssue | None:
    location = item.declaration.span
    if location is None:
        return None
    return AliasOpaqueMaterializationIssue(
        code="AIDL-T005",
        message=message,
        source_path=item.document.source_path,
        location=location,
        subject_kind=item.declaration.kind,
        subject_name=item.declaration.name or "<unnamed>",
        expected=expected,
    )


def _known_standard_name(name: str) -> bool:
    if name in STD_TYPES:
        return True
    if name.startswith("aidl.std.") and name.count(".") == 2:
        return name.rsplit(".", 1)[-1] in STD_TYPES
    return False


def _constraint_issue(item, raw: str) -> AliasOpaqueMaterializationIssue | None:
    if re.search(r"\benum\s*\(", raw):
        return _issue(
            item,
            "inline enum target is grammatical but has no lossless Canonical IR typeRef representation",
            "scalar, nullable/list/set/map, resolved project nominal, ref, or known Core standard type",
        )

    for match in _SCALAR_INVOCATION.finditer(raw):
        scalar, arguments = match.groups()
        arguments = arguments.strip()
        if not arguments:
            continue
        if scalar == "string" and re.fullmatch(r"\d+\s*\.\.\s*\d+", arguments):
            continue
        if scalar in {"int", "decimal"}:
            seen: set[str] = set()
            valid = True
            for part in arguments.split(","):
                if ":" not in part:
                    valid = False
                    break
                key, value = (piece.strip() for piece in part.split(":", 1))
                if key not in {"min", "max"} or key in seen or _NUMBER.fullmatch(value) is None:
                    valid = False
                    break
                seen.add(key)
            if valid:
                continue
        return _issue(
            item,
            f"constraint form in target type '{raw}' is not losslessly represented by the current Canonical IR typeRef constraints contract",
            "string(MIN..MAX), int(min|max: NUMBER), decimal(min|max: NUMBER), or an unconstrained Core type",
        )
    return None


def _visit(project: CompilerProject, item, root: TypeRef, raw: str, issues: list[AliasOpaqueMaterializationIssue]) -> None:
    if root.kind == "entity-id":
        matches = _resolve(project, item, root.name or "")
        if len(matches) == 1 and matches[0].declaration.kind == "entity":
            issue = _issue(
                item,
                f"entity identity target '{root.name or ''}.id' would lose its source identity because the current Canonical IR projects it as scalar uuid",
                "target form with a lossless current Canonical IR typeRef representation",
            )
            if issue:
                issues.append(issue)
    elif root.kind == "named":
        name = root.name or ""
        if not _known_standard_name(name):
            matches = _resolve(project, item, name)
            if not matches:
                issue = _issue(
                    item,
                    f"nominal target type '{name}' is unresolved and may not fall back to a synthetic aidl.std identity",
                    "exactly one resolved project type or an explicitly known Core standard type",
                )
                if issue:
                    issues.append(issue)
            elif len(matches) > 1:
                issue = _issue(
                    item,
                    f"nominal target type '{name}' is ambiguous; found {len(matches)} declarations",
                    "exactly one resolved project type",
                )
                if issue:
                    issues.append(issue)
            # Resolved wrong-kind and generic project targets are already owned by
            # the shared Core AIDL-T005 materialization boundary; do not duplicate them here.
    for argument in root.args:
        _visit(project, item, argument, raw, issues)


def collect_alias_opaque_materialization_issues(
    project: CompilerProject,
) -> tuple[AliasOpaqueMaterializationIssue, ...]:
    """Reject Alias/Opaque target facts that current Canonical IR would widen or drop."""
    issues: list[AliasOpaqueMaterializationIssue] = []
    for item in project.declaration_names:
        declaration = item.declaration
        if declaration.kind not in {"alias", "opaque"}:
            continue
        if declaration.node.attrs.get("typeParameters"):
            continue  # Existing shared AIDL-T005 generic-declaration boundary owns this case.
        raw = declaration.node.attrs.get("type")
        if not isinstance(raw, str) or not raw.strip():
            issue = _issue(
                item,
                f"{declaration.kind} '{declaration.name or '<unnamed>'}' must declare '= type' before Canonical IR materialization",
                "one explicit non-generic target type",
            )
            if issue:
                issues.append(issue)
            continue
        raw = raw.strip()
        try:
            root = parse_type(raw)
        except TypeSyntaxError:
            continue  # AIDL-T001 owns malformed constructors.
        constraint_issue = _constraint_issue(item, raw)
        if constraint_issue:
            issues.append(constraint_issue)
            continue
        _visit(project, item, root, raw, issues)

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
