"""Executable M10.1-07 operation-execution parity audit.

This module is deliberately an audit projection, not a second grammar or semantic
inventory.  It derives dispositions from the frozen-v1 contract and the existing
compiler language-surface/body-parity bridges.  A concept is admitted only when
those authorities already expose a lossless fact; otherwise the audit records the
existing fail-closed boundary.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

try:
    from .compiler_language_surface import LanguageSurfaceBridge
    from .compiler_language_surface_body_parity import ContractBodyParityBridge
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from compiler_language_surface import LanguageSurfaceBridge
    from compiler_language_surface_body_parity import ContractBodyParityBridge


EXECUTION_PARITY_VERSION = "aidl.m10.1-operation-execution-parity/v1"


@dataclass(frozen=True)
class ExecutionDisposition:
    operation_kind: str
    concept: str
    contract_fact: str
    disposition: str
    diagnostic_boundary: str | None
    reason: str


def _operation_schema(bridge: LanguageSurfaceBridge, kind: str) -> dict[str, Any]:
    schema = bridge.kinds.get(kind)
    if not isinstance(schema, dict):
        raise ValueError(f"frozen contract does not define operation kind {kind!r}")
    return schema


def _parameter_modifiers(schema: dict[str, Any]) -> frozenset[str]:
    for header in schema.get("header_args", []):
        if header.get("name") != "parameters":
            continue
        parameter = header.get("parameter", {})
        return frozenset(str(item) for item in parameter.get("modifiers", []))
    return frozenset()


def _body_slots(bridge: ContractBodyParityBridge, kind: str) -> frozenset[str]:
    schema = bridge.kinds.get(kind, {})
    return frozenset(str(item.get("id")) for item in schema.get("body_slots", []))


def operation_execution_dispositions() -> dict[str, Any]:
    """Return deterministic, contract-derived M10.1-07 package dispositions."""

    surface = LanguageSurfaceBridge()
    body = ContractBodyParityBridge()
    revision = int(surface.contract["contract_revision"])
    declarations: list[ExecutionDisposition] = []

    for kind in ("query", "mutation"):
        schema = _operation_schema(surface, kind)
        parameter_modifiers = _parameter_modifiers(schema)

        declarations.append(
            ExecutionDisposition(
                operation_kind=kind,
                concept="type_ref_range",
                contract_fact="TypeRef.range",
                disposition="production_parity",
                diagnostic_boundary=None,
                reason=(
                    f"frozen-v1 revision {revision} owns structured TypeRef.range min/max facts; "
                    "CompilerLanguageSurfaceBridge preserves those facts recursively"
                ),
            )
        )
        declarations.append(
            ExecutionDisposition(
                operation_kind=kind,
                concept="parameter_default",
                contract_fact=f"{kind}.parameters.modifiers.default",
                disposition=(
                    "production_parity" if "default" in parameter_modifiers else "excluded"
                ),
                diagnostic_boundary=None if "default" in parameter_modifiers else "AIDL-N013",
                reason=(
                    f"frozen-v1 revision {revision} declares default for {kind} parameters and "
                    "CompilerLanguageSurfaceBridge preserves the ModifierCall"
                    if "default" in parameter_modifiers
                    else f"frozen-v1 revision {revision} does not declare default for {kind} parameters"
                ),
            )
        )
        declarations.append(
            ExecutionDisposition(
                operation_kind=kind,
                concept="generic_type_arguments",
                contract_fact="TypeRef.generic_arguments",
                disposition="excluded",
                diagnostic_boundary="AIDL-N015 -> AIDL-N013",
                reason=(
                    f"frozen-v1 revision {revision} has no TypeRef generic-argument fact; the existing "
                    "bridge emits AIDL-N015 and production admission rejects the lossy operation with AIDL-N013"
                ),
            )
        )
        declarations.append(
            ExecutionDisposition(
                operation_kind=kind,
                concept="non_range_constraints",
                contract_fact="TypeRef.constraints.other_than_range",
                disposition="excluded",
                diagnostic_boundary="AIDL-N015 -> AIDL-N013",
                reason=(
                    f"frozen-v1 revision {revision} owns only TypeRef.range constraints; other shapes "
                    "remain AIDL-N015 evidence and fail production losslessness with AIDL-N013"
                ),
            )
        )
        declarations.append(
            ExecutionDisposition(
                operation_kind=kind,
                concept="operation_generics",
                contract_fact=f"{kind}.type_parameters",
                disposition="excluded",
                diagnostic_boundary="AIDL-N013",
                reason=(
                    f"frozen-v1 revision {revision} defines no {kind} type-parameter header fact; "
                    "the existing production losslessness gate excludes generic operations"
                ),
            )
        )

    mutation_slots = _body_slots(body, "mutation")
    for concept in ("idempotency", "transaction"):
        declarations.append(
            ExecutionDisposition(
                operation_kind="mutation",
                concept=concept,
                contract_fact=f"mutation.body_slots.{concept}",
                disposition="production_parity" if concept in mutation_slots else "excluded",
                diagnostic_boundary=None if concept in mutation_slots else "AIDL-N010 -> AIDL-N013",
                reason=(
                    f"frozen-v1 revision {revision} owns mutation BodySlot {concept}"
                    if concept in mutation_slots
                    else (
                        f"frozen-v1 revision {revision} has no mutation BodySlot {concept}; legacy clauses "
                        "remain AIDL-N010 evidence and fail production losslessness with AIDL-N013"
                    )
                ),
            )
        )

    return {
        "schema_version": EXECUTION_PARITY_VERSION,
        "contract_revision": revision,
        "declarations": [asdict(item) for item in declarations],
    }


def operation_execution_dispositions_json() -> str:
    return json.dumps(
        operation_execution_dispositions(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
