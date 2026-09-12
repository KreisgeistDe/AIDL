from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tools import m10_2_language_surface_classification as m10_2

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("spec/m10-3-closure-certification.json")
SCHEMA_VERSION = "aidl.m10.3-closure-certification/v1"
INVENTORY_PATH_RE = re.compile(r"`([^`\n]+\.aidl)`")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def _normalized_inventory_paths(root: Path, document: Path, app_root: Path) -> set[str]:
    text = document.read_text(encoding="utf-8")
    paths: set[str] = set()
    app_rel = app_root.relative_to(root).as_posix()
    for token in INVENTORY_PATH_RE.findall(text):
        token = token.strip()
        if token.startswith(app_rel + "/"):
            candidate = token
        else:
            candidate = f"{app_rel}/{token}"
        if (root / candidate).is_file():
            paths.add(candidate)
    return paths


def _validate_inventory(actual: set[str], documented: set[str], app_id: str) -> None:
    missing = sorted(actual - documented)
    if missing:
        raise ValueError(f"{app_id} inventory drift: undocumented AIDL sources={missing}")


def _validate_fixture_classification(
    source_rows: list[dict[str, str]], root_path: str, expected_class: str
) -> int:
    prefix = root_path.rstrip("/") + "/"
    rows = [row for row in source_rows if row["path"].startswith(prefix)]
    if not rows:
        raise ValueError(f"fixture class is empty: {root_path}")
    wrong = sorted(row["path"] for row in rows if row["class"] != expected_class)
    if wrong:
        raise ValueError(
            f"fixture classification drift for {root_path}: expected {expected_class}, wrong={wrong}"
        )
    return len(rows)


def validate(root: Path = ROOT, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    data = manifest or _load(root / MANIFEST)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("M10.3 closure schema version drift")
    if data.get("authority") != "M10.3-01" or data.get("status") != "certified":
        raise ValueError("M10.3 closure authority/status drift")

    frozen = data.get("frozen_language_contract", {})
    contract = _load(root / str(frozen.get("path", "")))
    frozen_identity = {"authority": "M10.1", "status": "frozen", "contract_revision": 4}
    if {key: contract.get(key) for key in frozen_identity} != frozen_identity:
        raise ValueError("frozen revision-4 contract identity drift")
    if {key: frozen.get(key) for key in frozen_identity} != frozen_identity:
        raise ValueError("M10.3 frozen-contract pin drift")

    classification_ref = data.get("classification_authority", {})
    if classification_ref.get("authority") != "M10.2-01":
        raise ValueError("M10.2 authority pin drift")
    classification_path = root / str(classification_ref.get("path", ""))
    classification = _load(classification_path)
    classification_report = m10_2.validate(root=root, manifest=classification)

    shared_ref = data.get("shared_disposition_authority", {})
    if shared_ref.get("authority") != "M10.3-01-shared-foundation":
        raise ValueError("shared M10.3 authority pin drift")
    shared = _load(root / str(shared_ref.get("path", "")))
    if shared.get("schema_version") != "aidl.m10.3-shared-disposition/v1":
        raise ValueError("shared M10.3 schema version drift")
    if shared.get("authority") != "M10.3-01-shared-foundation":
        raise ValueError("shared M10.3 authority drift")
    shared_frozen = shared.get("frozen_language_contract", {})
    if {key: shared_frozen.get(key) for key in frozen_identity} != frozen_identity:
        raise ValueError("shared M10.3 frozen-contract pin drift")

    allowed = data.get("allowed_dispositions", [])
    if len(allowed) != len(set(allowed)) or set(allowed) != {
        "supported-equivalent-source-form",
        "non-production-fail-closed",
        "requires-versioned-admission",
    }:
        raise ValueError("M10.3 disposition vocabulary drift")

    support_rows = shared.get("canonical_source_support", [])
    support_ids = [row.get("id") for row in support_rows if isinstance(row, dict)]
    required_support = data.get("required_canonical_source_support", [])
    if len(support_ids) != len(set(support_ids)) or set(support_ids) != set(required_support):
        raise ValueError(
            f"canonical source support drift: actual={sorted(support_ids)}, required={sorted(required_support)}"
        )
    for row in support_rows:
        if row.get("disposition") != "supported-equivalent-source-form":
            raise ValueError(f"canonical support disposition drift: {row.get('id')}")

    mismatch_rows = shared.get("shared_mismatch_dispositions", [])
    actual_mismatches: dict[str, str] = {}
    for row in mismatch_rows:
        if not isinstance(row, dict):
            raise ValueError("shared mismatch rows must be objects")
        mismatch_id = row.get("id")
        disposition = row.get("disposition")
        if not isinstance(mismatch_id, str) or mismatch_id in actual_mismatches:
            raise ValueError("shared mismatch ids must be unique strings")
        if disposition not in allowed:
            raise ValueError(f"invalid shared mismatch disposition: {mismatch_id}={disposition}")
        actual_mismatches[mismatch_id] = str(disposition)
    required_mismatches = data.get("required_shared_mismatch_dispositions", {})
    if actual_mismatches != required_mismatches:
        missing = sorted(set(required_mismatches) - set(actual_mismatches))
        extra = sorted(set(actual_mismatches) - set(required_mismatches))
        changed = sorted(
            key
            for key in set(required_mismatches) & set(actual_mismatches)
            if required_mismatches[key] != actual_mismatches[key]
        )
        raise ValueError(
            f"shared mismatch disposition drift: missing={missing}, extra={extra}, changed={changed}"
        )

    shared_constraints = shared.get("constraints", {})
    required_shared_constraints = {
        "production_admission_changed": False,
        "canonical_ir_meaning_changed": False,
        "frozen_contract_changed": False,
        "m10_5_deferred": True,
        "m10_3_complete": True,
    }
    if {key: shared_constraints.get(key) for key in required_shared_constraints} != required_shared_constraints:
        raise ValueError("shared M10.3 constraint drift")

    constraints = data.get("constraints", {})
    required_constraints = {
        "production_admission_changed": False,
        "canonical_ir_meaning_changed": False,
        "parser_compiler_runtime_semantics_changed": False,
        "frozen_contract_changed": False,
        "app_links_admitted": False,
        "m10_5_started": False,
        "m10_3_complete": True,
    }
    if constraints != required_constraints:
        raise ValueError("M10.3 closure constraint drift")

    source_rows = classification_report["sources"]
    source_class_by_path = {row["path"]: row["class"] for row in source_rows}
    app_reports: list[dict[str, Any]] = []
    app_ids: set[str] = set()
    for app in data.get("reference_applications", []):
        app_id = app.get("id")
        if not isinstance(app_id, str) or app_id in app_ids:
            raise ValueError("reference application ids must be unique strings")
        app_ids.add(app_id)
        app_root = root / str(app.get("root", ""))
        document = root / str(app.get("inventory_document", ""))
        if not app_root.is_dir() or not document.is_file():
            raise ValueError(f"reference application authority missing: {app_id}")
        actual = {
            path.relative_to(root).as_posix()
            for path in app_root.rglob("*.aidl")
            if path.is_file()
        }
        expected_count = app.get("expected_source_count")
        if len(actual) != expected_count:
            raise ValueError(
                f"{app_id} source-count drift: actual={len(actual)}, expected={expected_count}"
            )
        documented = _normalized_inventory_paths(root, document, app_root)
        _validate_inventory(actual, documented, app_id)
        unclassified = sorted(path for path in actual if path not in source_class_by_path)
        if unclassified:
            raise ValueError(f"{app_id} has unclassified sources: {unclassified}")
        app_reports.append(
            {
                "id": app_id,
                "source_count": len(actual),
                "inventory_document": document.relative_to(root).as_posix(),
            }
        )

    fixture_reports: dict[str, int] = {}
    fixture_roots: set[str] = set()
    for fixture in data.get("fixture_classes", []):
        root_path = fixture.get("root")
        expected_class = fixture.get("classification")
        if not isinstance(root_path, str) or root_path in fixture_roots:
            raise ValueError("fixture roots must be unique strings")
        fixture_roots.add(root_path)
        fixture_reports[root_path] = _validate_fixture_classification(
            source_rows, root_path, str(expected_class)
        )

    if set(app_ids) != {"calendar-offline", "petstore", "videohub"}:
        raise ValueError("reference application coverage drift")
    if fixture_roots != {"fixtures/valid", "fixtures/invalid", "tools/m2_semantic_fixtures"}:
        raise ValueError("fixture-class coverage drift")

    return {
        "schema_version": SCHEMA_VERSION,
        "contract_revision": 4,
        "m10_2_source_count": classification_report["source_count"],
        "m10_2_document_count": classification_report["document_count"],
        "reference_applications": app_reports,
        "fixture_counts": fixture_reports,
        "canonical_source_support": sorted(support_ids),
        "shared_mismatch_count": len(actual_mismatches),
        "production_admission_changed": False,
        "canonical_ir_meaning_changed": False,
        "m10_3_complete": True,
    }


def main() -> int:
    print(json.dumps(validate(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
