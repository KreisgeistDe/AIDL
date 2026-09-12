"""Executable M10.1-06 policy-parity audit over the frozen language contract.

This module is deliberately *not* a second operation grammar or semantic table.
It asks the existing contract-driven production bridge which policy facts are
representable by frozen-v1 and records an explicit package-level disposition for
the four M10.1-06 policy concepts. Unsupported source clauses continue through
the existing fail-closed ``AIDL-N010``/``AIDL-N013`` path.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

try:
    from .compiler_language_surface_body_parity import ContractBodyParityBridge
except ImportError:  # pragma: no cover
    from compiler_language_surface_body_parity import ContractBodyParityBridge


POLICY_PARITY_VERSION = "aidl.m10.1-operation-policy-parity/v1"


@dataclass(frozen=True)
class PolicyDisposition:
    concept: str
    source_keyword: str
    contract_slot: str
    disposition: str
    diagnostic_boundary: str | None
    reason: str

    def semantic(self) -> dict[str, Any]:
        return asdict(self)


def _slot_ids(bridge: ContractBodyParityBridge, kind: str) -> set[str]:
    schema = bridge.kinds[kind]
    return {str(item["id"]) for item in schema.get("body_slots", [])}


def operation_policy_dispositions() -> dict[str, Any]:
    """Return deterministic contract-derived M10.1-06 dispositions.

    ``authorize`` is the roadmap concept represented by frozen-v1's ``allow``
    expression slot. ``auth``, ``cache`` and ``consistency`` are legacy source
    concepts whose absence from the frozen contract is an explicit exclusion,
    not permission to invent canonical facts. ContractBodyParityBridge leaves
    such unsupported clauses as ``AIDL-N010`` evidence, and the existing
    Production Normalization losslessness gate rejects those operations with
    ``AIDL-N013``. PR #67/#68 auth evidence remains useful compiler evidence but
    cannot turn an absent BodySlot into parity.
    """

    bridge = ContractBodyParityBridge()
    concepts = (
        ("auth", "auth", "auth"),
        ("authorize", "allow", "allow"),
        ("cache", "cache", "cache"),
        ("consistency", "consistency", "consistency"),
    )
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for kind in ("query", "mutation"):
        slots = _slot_ids(bridge, kind)
        items: list[dict[str, Any]] = []
        for concept, source_keyword, contract_slot in concepts:
            if contract_slot in slots:
                disposition = "production_parity"
                diagnostic_boundary = None
                reason = (
                    f"frozen contract revision {bridge.contract['contract_revision']} owns "
                    f"{kind}.{contract_slot}; ContractBodyParityBridge normalizes it"
                )
            else:
                disposition = "excluded"
                diagnostic_boundary = "AIDL-N010 -> AIDL-N013"
                reason = (
                    f"frozen contract revision {bridge.contract['contract_revision']} has no "
                    f"{kind}.{contract_slot} BodySlot; ContractBodyParityBridge retains the unsupported "
                    "clause as AIDL-N010 evidence and Production Normalization rejects the lossy operation "
                    "with AIDL-N013"
                )
            items.append(
                PolicyDisposition(
                    concept=concept,
                    source_keyword=source_keyword,
                    contract_slot=contract_slot,
                    disposition=disposition,
                    diagnostic_boundary=diagnostic_boundary,
                    reason=reason,
                ).semantic()
            )
        by_kind[kind] = items
    return {
        "schema_version": POLICY_PARITY_VERSION,
        "contract_revision": bridge.contract["contract_revision"],
        "declarations": by_kind,
    }


def operation_policy_dispositions_json() -> str:
    return json.dumps(
        operation_policy_dispositions(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
