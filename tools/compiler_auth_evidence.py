"""Compiler-owned, diagnostic-neutral evidence for operation auth clauses.

The module projects parser/compiler facts only.  Built-in auth modes are complete
by grammar.  qualifiedName modes become complete only when the existing resolver
finds exactly one declaration satisfying the narrow M10.1 auth-target contract:
a non-generic, parameterless ``policy`` returning ``bool``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

try:
    from .compiler_project import CompilerDeclarationName, CompilerProject
    from .compiler_typecheck import _clauses, _resolve
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from compiler_project import CompilerDeclarationName, CompilerProject
    from compiler_typecheck import _clauses, _resolve


AUTH_BUILTIN_MODES = frozenset({"public", "authenticated", "service"})
AUTH_TARGET_KIND = "policy"
AUTH_TARGET_CONTRACT = "policy-bool-no-parameters/v1"


def _compact_signature(value: object) -> str:
    """Canonicalize parser-owned signature text without interpreting its grammar."""

    return "".join(str(value or "").split())


@dataclass(frozen=True)
class OperationAuthEvidence:
    """One parser-owned auth clause plus compiler-owned target evidence."""

    source: str
    mode: str
    resolution: str
    target: str | None = None
    target_kind: str | None = None
    target_status: str = "incomplete"
    target_contract: str | None = None
    target_parameters: str | None = None
    target_result: str | None = None

    @property
    def complete(self) -> bool:
        return self.target_status in {"builtin", "eligible"}

    def semantic(self) -> dict[str, object]:
        return {
            "source": self.source,
            "mode": self.mode,
            "resolution": self.resolution,
            "target": self.target,
            "target_kind": self.target_kind,
            "target_status": self.target_status,
            "target_contract": self.target_contract,
            "target_parameters": self.target_parameters,
            "target_result": self.target_result,
            "complete": self.complete,
        }


def _qualified_auth_evidence(
    project: CompilerProject,
    item: CompilerDeclarationName,
    source: str,
) -> OperationAuthEvidence:
    matches = _resolve(project, item, source)
    if not matches:
        return OperationAuthEvidence(
            source, "qualified_name", "unresolved", target_status="unresolved"
        )
    if len(matches) > 1:
        return OperationAuthEvidence(
            source, "qualified_name", "ambiguous", target_status="ambiguous"
        )

    target = matches[0]
    target_name = target.fully_qualified_name or source
    target_kind = target.declaration.kind
    if target_kind != AUTH_TARGET_KIND:
        return OperationAuthEvidence(
            source,
            "qualified_name",
            "resolved",
            target_name,
            target_kind,
            "wrong_kind",
            AUTH_TARGET_CONTRACT,
        )

    node = target.declaration.node
    parameters = _compact_signature(node.attrs.get("parameters"))
    result = _compact_signature(node.attrs.get("returns"))
    generic = bool(_compact_signature(node.attrs.get("typeParameters")))
    eligible = not generic and parameters == "()" and result == "bool"
    return OperationAuthEvidence(
        source,
        "qualified_name",
        "resolved",
        target_name,
        target_kind,
        "eligible" if eligible else "incomplete",
        AUTH_TARGET_CONTRACT,
        parameters or None,
        result or None,
    )


def operation_auth_evidence(
    project: CompilerProject,
    item: CompilerDeclarationName,
) -> tuple[OperationAuthEvidence, ...]:
    """Return ordered auth evidence for one query/mutation without diagnostics."""

    if item.declaration.kind not in {"query", "mutation"}:
        return ()

    evidence: list[OperationAuthEvidence] = []
    for raw, _ in _clauses(item, "auth"):
        source = raw.strip()
        if source in AUTH_BUILTIN_MODES:
            evidence.append(
                OperationAuthEvidence(
                    source,
                    "builtin",
                    "builtin",
                    target_status="builtin",
                )
            )
        else:
            evidence.append(_qualified_auth_evidence(project, item, source))
    return tuple(evidence)


def operation_auth_evidence_hash(
    project: CompilerProject,
    item: CompilerDeclarationName,
) -> str:
    """Stable SHA-256 over structured auth evidence, independent of source spacing."""

    payload = [entry.semantic() for entry in operation_auth_evidence(project, item)]
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
