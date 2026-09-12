from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("spec/m10-3-shared-disposition.json")
CONTRACT = Path("spec/language-surface-v1.json")
SCHEMA_VERSION = "aidl.m10.3-shared-disposition/v1"
ALLOWED_DISPOSITIONS = {"non-production-fail-closed", "requires-versioned-admission"}
EXPECTED_CANONICAL_SUPPORT = {
    "app.profile-block",
    "entity.field-slot",
    "operation.parameters-header-arg",
}
REQUIRED_SHARED_MISMATCHES = {
    "app.links",
    "value",
    "union",
    "view",
    "entity.invariant",
    "operation.auth",
    "operation.cache",
    "operation.consistency",
    "operation.idempotency",
    "operation.transaction",
    "type-ref.generic-arguments",
    "error",
    "event",
    "topic",
    "policy",
    "workflow",
    "api",
    "resource",
    "service",
    "system",
    "deployment",
    "frontend",
    "theme",
    "component",
    "page",
    "form",
    "action",
    "sync",
    "syncStatus",
    "seo",
    "test",
}
CONTRACT_DECLARATION_IDS = {
    item
    for item in REQUIRED_SHARED_MISMATCHES
    if "." not in item and item != "type-ref.generic-arguments"
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path = ROOT, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = manifest or _load(root / MANIFEST)
    contract = _load(root / CONTRACT)

    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("shared disposition schema_version drift")
    frozen = manifest.get("frozen_language_contract")
    if frozen != {
        "path": str(CONTRACT),
        "authority": "M10.1",
        "status": "frozen",
        "contract_revision": 4,
    }:
        raise ValueError("frozen M10.1 contract identity drift")
    if contract.get("authority") != "M10.1" or contract.get("status") != "frozen":
        raise ValueError("language contract authority/status drift")
    if contract.get("contract_revision") != 4:
        raise ValueError("language contract revision drift")

    support = manifest.get("canonical_source_support")
    if not isinstance(support, list):
        raise ValueError("canonical_source_support must be a list")
    support_ids = [item.get("id") for item in support if isinstance(item, dict)]
    if len(support_ids) != len(set(support_ids)):
        raise ValueError("duplicate canonical source support id")
    if set(support_ids) != EXPECTED_CANONICAL_SUPPORT:
        raise ValueError("canonical source support coverage drift")
    for item in support:
        if item.get("disposition") != "supported-equivalent-source-form":
            raise ValueError(f"invalid canonical source support disposition for {item.get('id')}")
        if not item.get("detail"):
            raise ValueError(f"missing canonical source support detail for {item.get('id')}")

    dispositions = manifest.get("shared_mismatch_dispositions")
    if not isinstance(dispositions, list):
        raise ValueError("shared_mismatch_dispositions must be a list")
    ids = [item.get("id") for item in dispositions if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate shared mismatch disposition id")
    if set(ids) != REQUIRED_SHARED_MISMATCHES:
        missing = sorted(REQUIRED_SHARED_MISMATCHES - set(ids))
        extra = sorted(set(ids) - REQUIRED_SHARED_MISMATCHES)
        raise ValueError(f"shared mismatch disposition coverage drift: missing={missing}, extra={extra}")
    for item in dispositions:
        if item.get("disposition") not in ALLOWED_DISPOSITIONS:
            raise ValueError(f"invalid disposition for {item.get('id')}")
        if not item.get("detail"):
            raise ValueError(f"missing disposition detail for {item.get('id')}")

    contract_kinds = {
        item.get("kind")
        for item in contract.get("declaration_kinds", [])
        if isinstance(item, dict)
    }
    missing_contract_kinds = sorted(CONTRACT_DECLARATION_IDS - contract_kinds)
    if missing_contract_kinds:
        raise ValueError(f"shared disposition kind absent from frozen contract: {missing_contract_kinds}")

    constraints = manifest.get("constraints")
    expected_constraints = {
        "production_admission_changed": False,
        "canonical_ir_meaning_changed": False,
        "frozen_contract_changed": False,
        "m10_5_deferred": True,
        "m10_3_complete": False,
    }
    if constraints != expected_constraints:
        raise ValueError("M10.3 shared foundation constraint drift")

    return {
        "schema_version": SCHEMA_VERSION,
        "contract_revision": 4,
        "canonical_support_count": len(support_ids),
        "disposition_count": len(ids),
        "versioned_admission_count": sum(
            item["disposition"] == "requires-versioned-admission" for item in dispositions
        ),
    }


def main() -> int:
    print(json.dumps(validate(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
