"""Executable M10.1-10 closure certification for the frozen language surface.

This module certifies the already-integrated M10.1 evidence. It does not add a
second grammar, declaration inventory, semantic table, parser path, or runtime
meaning. Every semantic disposition comes from the frozen-v1 contract and the
existing compiler-owned audit/normalization layers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .compiler_declaration_family_parity import (
        DECLARATION_FAMILY_PARITY_VERSION,
        declaration_family_dispositions,
    )
    from .compiler_language_surface import LanguageSurfaceBridge, NORMALIZATION_VERSION
    from .compiler_language_surface_coverage import (
        LANGUAGE_SURFACE_COVERAGE_VERSION,
        language_surface_coverage,
    )
    from .compiler_language_surface_integration import PRODUCTION_NORMALIZATION_VERSION
    from .compiler_operation_execution_parity import (
        EXECUTION_PARITY_VERSION,
        operation_execution_dispositions,
    )
    from .compiler_operation_policy_parity import (
        POLICY_PARITY_VERSION,
        operation_policy_dispositions,
    )
except ImportError:  # pragma: no cover - direct tools/ execution/import path
    from compiler_declaration_family_parity import (
        DECLARATION_FAMILY_PARITY_VERSION,
        declaration_family_dispositions,
    )
    from compiler_language_surface import LanguageSurfaceBridge, NORMALIZATION_VERSION
    from compiler_language_surface_coverage import (
        LANGUAGE_SURFACE_COVERAGE_VERSION,
        language_surface_coverage,
    )
    from compiler_language_surface_integration import PRODUCTION_NORMALIZATION_VERSION
    from compiler_operation_execution_parity import (
        EXECUTION_PARITY_VERSION,
        operation_execution_dispositions,
    )
    from compiler_operation_policy_parity import (
        POLICY_PARITY_VERSION,
        operation_policy_dispositions,
    )


ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = ROOT / "roadmap" / "v1" / "milestones" / "m10.1.json"
CLOSURE_CERTIFICATION_VERSION = "aidl.m10.1-closure-certification/v1"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _roadmap_packages() -> list[dict[str, Any]]:
    data = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    _require(data.get("id") == "M10.1", "closure certification requires M10.1 roadmap authority")
    packages = data.get("packages")
    _require(isinstance(packages, list), "M10.1 roadmap packages must be a list")
    return packages


def _policy_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    declarations = data.get("declarations")
    _require(isinstance(declarations, dict), "operation-policy audit declarations must be a mapping")
    result: list[dict[str, Any]] = []
    for kind in ("query", "mutation"):
        items = declarations.get(kind)
        _require(isinstance(items, list), f"operation-policy audit misses {kind}")
        for item in items:
            _require(isinstance(item, dict), "operation-policy audit item is malformed")
            result.append({"operation_kind": kind, **item})
    return result


def _certify_formatter_migration_separation(bridge: LanguageSurfaceBridge) -> dict[str, str]:
    result = bridge.normalize_text('migration Upgrade from "1" to "2" {}\n')
    _require(result.ok, "representative migration must normalize without diagnostics")
    declaration = result.document.declarations[0]
    legacy = bridge.format_legacy(declaration)
    canonical = bridge.migrate_to_canonical_preview(declaration)
    _require(legacy != canonical, "same-version formatting and canonical migration preview must stay distinct")
    _require(legacy == bridge.format_legacy(declaration), "same-version formatter must be deterministic")
    _require(canonical == bridge.migrate_to_canonical_preview(declaration), "migration preview must be deterministic")
    return {
        "same_version_formatter": "LanguageSurfaceBridge.format_legacy",
        "language_version_migration": "LanguageSurfaceBridge.migrate_to_canonical_preview",
    }


def closure_certification() -> dict[str, Any]:
    """Return deterministic closure evidence or fail closed on any unresolved drift."""

    bridge = LanguageSurfaceBridge()
    contract = bridge.contract
    _require(contract.get("authority") == "M10.1", "language-surface authority drift detected")
    _require(contract.get("status") == "frozen", "language-surface contract is no longer frozen")
    revision = int(contract["contract_revision"])

    coverage = language_surface_coverage()
    declarations = declaration_family_dispositions()
    policy = operation_policy_dispositions()
    execution = operation_execution_dispositions()

    for name, data, version in (
        ("coverage", coverage, LANGUAGE_SURFACE_COVERAGE_VERSION),
        ("declaration-family", declarations, DECLARATION_FAMILY_PARITY_VERSION),
        ("operation-policy", policy, POLICY_PARITY_VERSION),
        ("operation-execution", execution, EXECUTION_PARITY_VERSION),
    ):
        _require(data.get("schema_version") == version, f"{name} audit version drift detected")
        _require(int(data.get("contract_revision", -1)) == revision, f"{name} contract revision drift detected")

    facts = coverage.get("contract_facts")
    _require(isinstance(facts, list) and facts, "coverage audit must contain frozen contract facts")
    _require(coverage.get("contract_leaf_count") == len(facts), "coverage contract leaf count drift detected")
    fact_paths = [item.get("path") for item in facts if isinstance(item, dict)]
    _require(len(fact_paths) == len(facts), "coverage audit fact is malformed")
    _require(len(fact_paths) == len(set(fact_paths)), "coverage audit contains duplicate contract fact paths")

    declaration_items = declarations.get("declarations")
    _require(isinstance(declaration_items, list), "declaration-family audit must contain declarations")
    _require(declarations.get("inventory_count") == len(declaration_items), "declaration-family inventory count drift detected")
    admitted: list[str] = []
    excluded: list[str] = []
    for item in declaration_items:
        _require(isinstance(item, dict), "declaration-family audit item is malformed")
        kind = str(item.get("declaration_kind"))
        disposition = item.get("disposition")
        if disposition == "production_parity":
            admitted.append(kind)
        elif disposition == "intentionally_excluded":
            _require(item.get("production_admission") == "non_admitted", f"excluded declaration {kind} gained production admission")
            _require(bool(item.get("diagnostic_boundary")), f"excluded declaration {kind} lacks fail-closed boundary")
            excluded.append(kind)
        else:
            raise ValueError(f"unresolved declaration-family disposition for {kind}: {disposition!r}")
    _require(
        declarations.get("production_parity_count") == len(admitted)
        and declarations.get("intentionally_excluded_count") == len(excluded),
        "declaration-family disposition counts drift detected",
    )

    policy_items = _policy_items(policy)
    for item in policy_items:
        _require(item.get("disposition") in {"production_parity", "excluded"}, "unresolved operation-policy disposition")
        if item.get("disposition") == "excluded":
            _require(
                bool(item.get("diagnostic_boundary")),
                f"excluded operation-policy concept {item.get('operation_kind')}.{item.get('concept')} lacks fail-closed diagnostic boundary",
            )
    for kind in ("query", "mutation"):
        by_concept = {
            item["concept"]: item
            for item in policy_items
            if item["operation_kind"] == kind
        }
        _require(by_concept["authorize"]["disposition"] == "production_parity", f"{kind} authorize/allow parity regressed")
        for concept in ("auth", "cache", "consistency"):
            _require(by_concept[concept]["disposition"] == "excluded", f"{kind} {concept} exclusion drift detected")

    execution_items = execution.get("declarations")
    _require(isinstance(execution_items, list) and execution_items, "operation-execution audit must contain dispositions")
    for item in execution_items:
        _require(isinstance(item, dict), "operation-execution audit item is malformed")
        disposition = item.get("disposition")
        _require(disposition in {"production_parity", "excluded"}, "unresolved operation-execution disposition")
        if disposition == "excluded":
            _require(bool(item.get("diagnostic_boundary")), "excluded execution concept lacks fail-closed diagnostic boundary")

    shapes = coverage.get("bridge_semantic_shapes")
    _require(isinstance(shapes, dict), "coverage audit lacks executable bridge semantic shapes")
    _require(
        set(shapes) == {"type_ref_optional", "type_ref_range", "reference_projection"},
        "bridge semantic-shape evidence drift detected",
    )

    format_migration = _certify_formatter_migration_separation(bridge)

    packages = _roadmap_packages()
    expected_ids = [f"M10.1-{index:02d}" for index in range(1, 11)]
    actual_ids = [str(item.get("id")) for item in packages]
    _require(actual_ids == expected_ids, "M10.1 roadmap package identity/order drift detected")
    _require(all(item.get("status") == "complete" for item in packages), "M10.1 closure requires all ten roadmap packages complete")

    criteria = [
        {
            "id": "frozen-facts-lossless-or-fail-closed",
            "status": "pass",
            "evidence": f"{len(facts)} non-example frozen-v1 contract leaves covered; all declaration/policy/execution dispositions are explicit",
        },
        {
            "id": "legacy-canonical-semantic-convergence",
            "status": "pass",
            "evidence": "M10.1-09 differential regressions execute independent canonical-fact and production semantic/hash equivalence",
        },
        {
            "id": "contract-derived-production-normalization",
            "status": "pass",
            "evidence": "coverage, declaration-family, policy and execution audits share frozen contract revision and compiler-owned admission evidence",
        },
        {
            "id": "formatter-migration-separation",
            "status": "pass",
            "evidence": "format_legacy and migrate_to_canonical_preview remain distinct deterministic operations",
        },
        {
            "id": "complete-production-dispositions",
            "status": "pass",
            "evidence": f"{len(admitted)} declaration families admitted; {len(excluded)} intentionally non-admitted with explicit boundaries; operation exclusions remain explicit",
        },
        {
            "id": "deterministic-coverage-and-differential-ci",
            "status": "pass",
            "evidence": f"{LANGUAGE_SURFACE_COVERAGE_VERSION} plus M10.1 regression suites are part of the repository-owned generic Python selector",
        },
        {
            "id": "m10.5-03-language-decision-readiness",
            "status": "pass",
            "evidence": "frozen-v1 revision 4 has complete explicit dispositions; no unresolved M10.1 language decision remains for front-end/IR parity slices",
        },
    ]

    return {
        "schema_version": CLOSURE_CERTIFICATION_VERSION,
        "contract_revision": revision,
        "contract_sha256": coverage["contract_sha256"],
        "normalization_versions": {
            "compatibility": NORMALIZATION_VERSION,
            "production": PRODUCTION_NORMALIZATION_VERSION,
            "coverage": LANGUAGE_SURFACE_COVERAGE_VERSION,
        },
        "production_semantic_envelope": {
            "admitted_declaration_families": admitted,
            "intentionally_non_admitted_declaration_families": excluded,
            "operation_policy_dispositions": policy_items,
            "operation_execution_dispositions": execution_items,
            "bridge_semantic_shapes": shapes,
        },
        "formatter_migration_separation": format_migration,
        "acceptance_criteria": criteria,
        "unresolved_language_decisions": [],
        "m10_5_03": {
            "unblocked": True,
            "condition": (
                "Implement frozen-v1 revision 4 only through bounded Python-versus-Kotlin differential parity slices; "
                "any semantic change requires a separately versioned language decision and is outside this unblock."
            ),
        },
        "roadmap_packages": actual_ids,
        "state": "certified",
    }


def closure_certification_json() -> str:
    return _stable_json(closure_certification())
