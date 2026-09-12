"""Executable M10.1-08 declaration-family production-parity audit.

This module is an audit projection only. It derives the canonical declaration-kind
inventory from the frozen language-surface contract and derives production admission
from the existing Production Normalization gates. It does not maintain a parallel
semantic declaration inventory or widen parser/runtime/schema behavior.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

try:
    from .compiler_language_surface import LanguageSurfaceBridge
    from .compiler_language_surface_integration import (
        _ALWAYS_INTEGRATED,
        _LOSSLESS_CANDIDATES,
    )
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from compiler_language_surface import LanguageSurfaceBridge
    from compiler_language_surface_integration import (
        _ALWAYS_INTEGRATED,
        _LOSSLESS_CANDIDATES,
    )


DECLARATION_FAMILY_PARITY_VERSION = "aidl.m10.1-declaration-family-parity/v1"
_LEGACY_KIND_ALIASES = {"opaque": "alias"}


@dataclass(frozen=True)
class DeclarationFamilyDisposition:
    declaration_kind: str
    disposition: str
    production_admission: str
    diagnostic_boundary: str | None
    evidence: str
    reason: str


def _canonical_kind(kind: str) -> str:
    return _LEGACY_KIND_ALIASES.get(kind, kind)


def _contract_declaration_kinds(contract: dict[str, Any]) -> tuple[str, ...]:
    raw = contract.get("declaration_kinds")
    if not isinstance(raw, list):
        raise ValueError("frozen contract declaration_kinds must be a list")
    kinds: list[str] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("kind"), str):
            raise ValueError("frozen contract declaration kind must have a string kind")
        if item.get("disposition") != "canonical":
            raise ValueError(f"declaration kind {item['kind']!r} is not canonical")
        kinds.append(item["kind"])
    if len(kinds) != len(set(kinds)):
        raise ValueError("frozen contract declaration kinds must be unique")
    return tuple(kinds)


def _canonicalized_gate(kinds: frozenset[str]) -> frozenset[str]:
    return frozenset(_canonical_kind(kind) for kind in kinds)


def _build_dispositions(
    contract: dict[str, Any],
    always_integrated: frozenset[str],
    lossless_candidates: frozenset[str],
) -> dict[str, Any]:
    contract_kinds = _contract_declaration_kinds(contract)
    contract_set = frozenset(contract_kinds)
    always = _canonicalized_gate(always_integrated) & contract_set
    conditional = _canonicalized_gate(lossless_candidates) & contract_set
    overlap = always & conditional
    if overlap:
        raise ValueError(f"production admission gates overlap: {sorted(overlap)!r}")
    admitted = always | conditional

    dispositions: list[DeclarationFamilyDisposition] = []
    revision = int(contract["contract_revision"])
    for kind in contract_kinds:
        if kind in always:
            dispositions.append(
                DeclarationFamilyDisposition(
                    declaration_kind=kind,
                    disposition="production_parity",
                    production_admission="always_lossless",
                    diagnostic_boundary=None,
                    evidence="compiler_language_surface_integration._ALWAYS_INTEGRATED",
                    reason=(
                        f"frozen-v1 revision {revision} defines canonical {kind}; the existing "
                        "Production Normalization gate admits this family as always lossless"
                    ),
                )
            )
        elif kind in conditional:
            dispositions.append(
                DeclarationFamilyDisposition(
                    declaration_kind=kind,
                    disposition="production_parity",
                    production_admission="conditional_lossless",
                    diagnostic_boundary="AIDL-N013 on incomplete represented facts",
                    evidence="compiler_language_surface_integration._LOSSLESS_CANDIDATES",
                    reason=(
                        f"frozen-v1 revision {revision} defines canonical {kind}; the existing "
                        "Production Normalization gate admits this family only when all represented facts are lossless"
                    ),
                )
            )
        else:
            dispositions.append(
                DeclarationFamilyDisposition(
                    declaration_kind=kind,
                    disposition="intentionally_excluded",
                    production_admission="non_admitted",
                    diagnostic_boundary="omitted from complete Production Normalization semantics",
                    evidence="compiler_language_surface_integration production admission gates",
                    reason=(
                        f"frozen-v1 revision {revision} defines canonical {kind}, but no existing "
                        "compiler-owned Production Normalization admission gate proves complete lossless family semantics"
                    ),
                )
            )

    return {
        "schema_version": DECLARATION_FAMILY_PARITY_VERSION,
        "contract_revision": revision,
        "inventory_count": len(contract_kinds),
        "production_parity_count": len(admitted),
        "intentionally_excluded_count": len(contract_kinds) - len(admitted),
        "declarations": [asdict(item) for item in dispositions],
    }


def declaration_family_dispositions() -> dict[str, Any]:
    """Return complete deterministic dispositions for every frozen declaration kind."""

    bridge = LanguageSurfaceBridge()
    return _build_dispositions(
        bridge.contract,
        _ALWAYS_INTEGRATED,
        _LOSSLESS_CANDIDATES,
    )


def declaration_family_dispositions_json() -> str:
    return json.dumps(
        declaration_family_dispositions(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
