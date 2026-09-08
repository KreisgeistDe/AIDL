"""Close Consumer-specific Core materialization gaps before Canonical IR."""
from __future__ import annotations

import re

try:
    from .compiler_core_materialization import CoreMaterializationIssue
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from compiler_core_materialization import CoreMaterializationIssue


_INLINE_IDEMPOTENCY = re.compile(
    r"^idempotency\s*:\s*(.+?)\s+retain\s+([0-9]+(?:ms|s|m|h|d))$",
    re.S,
)
_BLOCK_MARKER = re.compile(r"^idempotency\s*:\s*$")


def _issue(item, location, message: str, expected: str) -> CoreMaterializationIssue:
    return CoreMaterializationIssue(
        code="AIDL-T005",
        message=message,
        source_path=item.document.source_path,
        location=location,
        subject_kind="consumer",
        subject_name=item.declaration.name or "<unnamed>",
        expected=expected,
    )


def collect_consumer_materialization_issues(project) -> tuple[CoreMaterializationIssue, ...]:
    """Reject parsed Consumer idempotency forms that current IR cannot preserve."""
    issues: list[CoreMaterializationIssue] = []
    for item in project.declaration_names:
        if item.declaration.kind != "consumer":
            continue
        children = item.declaration.node.children
        for index, child in enumerate(children):
            if not child.name or child.span is None:
                continue
            clause = child.name.strip()
            if not clause.startswith("idempotency"):
                continue

            if _BLOCK_MARKER.fullmatch(clause):
                following = children[index + 1] if index + 1 < len(children) else None
                if following is not None and following.kind == "blockClause" and not (following.name or "").strip():
                    issues.append(
                        _issue(
                            item,
                            child.span,
                            "consumer block idempotency is grammatical but the current parser/Canonical IR path does not preserve its key/scope/retain properties losslessly",
                            "inline idempotency: EXPRESSION retain DURATION until block idempotency projection is implemented",
                        )
                    )
                    continue
                issues.append(
                    _issue(
                        item,
                        child.span,
                        "consumer idempotency clause has no losslessly materializable inline value",
                        "idempotency: EXPRESSION retain DURATION",
                    )
                )
                continue

            match = _INLINE_IDEMPOTENCY.fullmatch(clause)
            if match is None or not match.group(1).strip():
                issues.append(
                    _issue(
                        item,
                        child.span,
                        "consumer inline idempotency is parsed but cannot be materialized losslessly by the closed Core Canonical IR contract",
                        "idempotency: EXPRESSION retain DURATION",
                    )
                )
    return tuple(issues)
