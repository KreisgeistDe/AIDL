"""Compiler-authoritative bounded change-impact projection for one declaration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from tools.compiler_diagnostics import CompilerAnalysis
from tools.compiler_inspection import inspect_project_declaration
from tools.compiler_ir import IrBuildError, build_canonical_ir


MAX_IMPACT_DECLARATIONS = 128
MAX_IMPACT_PUBLIC_CONTRACTS = 128
MAX_IMPACT_PERSISTED_STATE = 128
MAX_IMPACT_COMPATIBILITY_CHECKS = 32


@dataclass(frozen=True)
class ImpactIdentity:
    declaration_id: str
    fully_qualified_name: str
    kind: str

    def to_json(self) -> dict[str, str]:
        return {
            "declarationId": self.declaration_id,
            "fullyQualifiedName": self.fully_qualified_name,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class ImpactEvidence:
    category: str
    identity: ImpactIdentity
    evidence: str

    def to_json(self) -> dict[str, object]:
        return {
            "category": self.category,
            "declaration": self.identity.to_json(),
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class CompatibilityCheck:
    surface: str
    command: str
    status: str
    evidence_declaration_ids: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "command": self.command,
            "evidenceDeclarationIds": list(self.evidence_declaration_ids),
            "status": self.status,
            "surface": self.surface,
        }


@dataclass(frozen=True)
class ChangeImpactResult:
    status: str
    query: str
    declaration: ImpactIdentity | None = None
    affected_declarations: tuple[ImpactEvidence, ...] = ()
    public_contracts: tuple[ImpactEvidence, ...] = ()
    persisted_state: tuple[ImpactEvidence, ...] = ()
    compatibility_checks: tuple[CompatibilityCheck, ...] = ()
    generated_artifacts_status: str | None = None
    generated_artifacts_reason: str | None = None
    match_count: int | None = None
    total_affected_declarations: int = 0
    total_public_contracts: int = 0
    total_persisted_state: int = 0
    total_compatibility_checks: int = 0

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {"query": self.query, "status": self.status}
        if self.declaration is not None:
            payload.update(
                {
                    "affectedDeclarations": [item.to_json() for item in self.affected_declarations],
                    "compatibilityChecks": [item.to_json() for item in self.compatibility_checks],
                    "declaration": self.declaration.to_json(),
                    "generatedArtifacts": {
                        "artifacts": [],
                        "reason": self.generated_artifacts_reason,
                        "status": self.generated_artifacts_status,
                    },
                    "persistedState": [item.to_json() for item in self.persisted_state],
                    "publicContracts": [item.to_json() for item in self.public_contracts],
                    "totals": {
                        "affectedDeclarations": self.total_affected_declarations,
                        "compatibilityChecks": self.total_compatibility_checks,
                        "persistedState": self.total_persisted_state,
                        "publicContracts": self.total_public_contracts,
                    },
                    "truncated": {
                        "affectedDeclarations": self.total_affected_declarations > len(self.affected_declarations),
                        "compatibilityChecks": self.total_compatibility_checks > len(self.compatibility_checks),
                        "persistedState": self.total_persisted_state > len(self.persisted_state),
                        "publicContracts": self.total_public_contracts > len(self.public_contracts),
                    },
                }
            )
        if self.match_count is not None:
            payload["matchCount"] = self.match_count
        return payload


def analyze_change_impact(analysis: CompilerAnalysis, fully_qualified_name: str) -> ChangeImpactResult:
    """Project direct impact evidence already materialized by compiler/Canonical IR.

    The projection deliberately does not infer transitive dependency semantics, generator
    ownership, or hypothetical compatibility outcomes. It reports missing generator
    evidence explicitly and points relevant surfaces at the existing `aidl diff` check.
    """

    inspected = inspect_project_declaration(analysis, fully_qualified_name)
    if inspected.status != "resolved" or inspected.declaration is None:
        return ChangeImpactResult(
            status=inspected.status,
            query=inspected.query,
            match_count=inspected.match_count,
        )

    canonical = build_canonical_ir(analysis)
    identities, nodes = _declaration_index(analysis, canonical)
    selected_node = inspected.declaration.canonical
    selected_id = selected_node.get("declarationId")
    if not isinstance(selected_id, str):
        raise IrBuildError(
            f"declaration '{fully_qualified_name}' has no Canonical-IR declarationId"
        )
    selected = identities.get(selected_id)
    if selected is None:
        selected = ImpactIdentity(selected_id, fully_qualified_name, inspected.declaration.kind)

    affected: list[ImpactEvidence] = []
    impacted_ids = {selected_id}
    for declaration_id, node in nodes.items():
        if declaration_id == selected_id:
            continue
        if _contains_exact_string(node, selected_id):
            impacted_ids.add(declaration_id)
            affected.append(
                ImpactEvidence(
                    category="directReference",
                    identity=identities[declaration_id],
                    evidence="Canonical-IR declaration contains the selected declarationId",
                )
            )
    affected.sort(key=_evidence_key)

    public_ids = _public_contract_ids(canonical, nodes)
    public_contracts = [
        ImpactEvidence(
            category=public_ids[declaration_id],
            identity=identities[declaration_id],
            evidence="Canonical IR materializes this declaration on a public API/topic contract surface",
        )
        for declaration_id in sorted(impacted_ids & set(public_ids), key=lambda item: _identity_key(identities[item]))
    ]

    persisted = [
        ImpactEvidence(
            category="entity",
            identity=identities[declaration_id],
            evidence="Canonical IR materializes this impacted declaration as persisted entity state",
        )
        for declaration_id in sorted(
            (item for item in impacted_ids if nodes[item].get("kind") == "entity"),
            key=lambda item: _identity_key(identities[item]),
        )
    ]

    checks: list[CompatibilityCheck] = []
    api_ids = tuple(sorted(
        (item.identity.declaration_id for item in public_contracts if item.category in {"api", "publicOperation"}),
    ))
    event_ids = tuple(sorted(
        (item.identity.declaration_id for item in public_contracts if item.category in {"event", "topic"}),
    ))
    persisted_ids = tuple(sorted(item.identity.declaration_id for item in persisted))
    if api_ids:
        checks.append(CompatibilityCheck("apiClient", "aidl diff", "requiresComparison", api_ids))
    if event_ids:
        checks.append(CompatibilityCheck("eventTopic", "aidl diff", "requiresComparison", event_ids))
    if persisted_ids:
        checks.append(CompatibilityCheck("persistedSchema", "aidl diff", "requiresComparison", persisted_ids))
    checks.sort(key=lambda item: (item.surface, item.evidence_declaration_ids))

    return ChangeImpactResult(
        status="resolved",
        query=fully_qualified_name,
        declaration=selected,
        affected_declarations=tuple(affected[:MAX_IMPACT_DECLARATIONS]),
        public_contracts=tuple(public_contracts[:MAX_IMPACT_PUBLIC_CONTRACTS]),
        persisted_state=tuple(persisted[:MAX_IMPACT_PERSISTED_STATE]),
        compatibility_checks=tuple(checks[:MAX_IMPACT_COMPATIBILITY_CHECKS]),
        generated_artifacts_status="unknown",
        generated_artifacts_reason=(
            "Compiler analysis and Canonical IR do not materialize per-declaration generated-artifact ownership"
        ),
        total_affected_declarations=len(affected),
        total_public_contracts=len(public_contracts),
        total_persisted_state=len(persisted),
        total_compatibility_checks=len(checks),
    )


def _identity_key(identity: ImpactIdentity) -> tuple[str, str, str]:
    return identity.fully_qualified_name, identity.kind, identity.declaration_id


def _evidence_key(item: ImpactEvidence) -> tuple[str, str, str, str]:
    return (*_identity_key(item.identity), item.category)


def _declaration_index(
    analysis: CompilerAnalysis,
    document: Mapping[str, Any],
) -> tuple[dict[str, ImpactIdentity], dict[str, Mapping[str, Any]]]:
    kinds_by_fqn = {
        item.fully_qualified_name: item.declaration.kind
        for item in analysis.project.declaration_names
        if item.fully_qualified_name is not None
    }
    identities: dict[str, ImpactIdentity] = {}
    nodes: dict[str, Mapping[str, Any]] = {}
    for node in _canonical_declarations(document):
        declaration_id = node.get("declarationId")
        fqn = node.get("fqn")
        if not isinstance(declaration_id, str) or not isinstance(fqn, str):
            continue
        kind = kinds_by_fqn.get(fqn)
        if kind is None:
            raw_kind = node.get("kind")
            if not isinstance(raw_kind, str) or not raw_kind:
                continue
            kind = raw_kind
        identities.setdefault(declaration_id, ImpactIdentity(declaration_id, fqn, kind))
        nodes.setdefault(declaration_id, node)
    return identities, nodes


def _canonical_declarations(document: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: object) -> None:
        if isinstance(value, Mapping):
            candidates.append(value)

    add(document.get("app"))
    for value in document.get("declarations", ()):
        add(value)
    system = document.get("system")
    add(system)
    if isinstance(system, Mapping):
        for value in system.get("services", ()):
            add(value)
        for value in system.get("resources", ()):
            add(value)
    for value in document.get("deployments", ()):
        add(value)
    return tuple(candidates)


def _contains_exact_string(value: object, target: str) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_exact_string(child, target) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_exact_string(child, target) for child in value)
    return value == target


def _string_ids(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def _public_contract_ids(
    document: Mapping[str, Any],
    nodes: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    result: dict[str, str] = {}
    app = document.get("app")
    system = document.get("system")
    api_ids: set[str] = set()
    topic_ids: set[str] = set()
    if isinstance(app, Mapping):
        api_ids |= _string_ids(app.get("apiIds"))
    if isinstance(system, Mapping):
        api_ids |= _string_ids(system.get("apiIds"))
        topic_ids |= _string_ids(system.get("topicIds"))

    for api_id in api_ids:
        if api_id in nodes:
            result[api_id] = "api"
            operations = nodes[api_id].get("operations")
            if isinstance(operations, list):
                for operation in operations:
                    if not isinstance(operation, Mapping):
                        continue
                    operation_id = operation.get("operationId")
                    if isinstance(operation_id, str) and operation_id in nodes:
                        result[operation_id] = "publicOperation"

    for topic_id in topic_ids:
        if topic_id in nodes:
            result[topic_id] = "topic"
            for event_id in _string_ids(nodes[topic_id].get("eventIds")):
                if event_id in nodes:
                    result[event_id] = "event"
    return result
