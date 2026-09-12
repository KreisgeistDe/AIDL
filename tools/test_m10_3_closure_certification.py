from __future__ import annotations

import copy

import pytest

from tools import m10_3_closure_certification as closure


def test_m10_3_closure_certifies_current_repository() -> None:
    report = closure.validate()
    assert report["contract_revision"] == 4
    assert report["m10_3_complete"] is True
    assert report["production_admission_changed"] is False
    assert report["canonical_ir_meaning_changed"] is False
    assert {row["id"]: row["source_count"] for row in report["reference_applications"]} == {
        "calendar-offline": 13,
        "petstore": 19,
        "videohub": 25,
    }
    assert report["canonical_source_support"] == [
        "app.profile-block",
        "entity.field-slot",
        "operation.parameters-header-arg",
    ]
    assert report["shared_mismatch_count"] > 0
    assert all(count > 0 for count in report["fixture_counts"].values())


def test_new_reference_source_without_inventory_entry_fails_closed() -> None:
    with pytest.raises(ValueError, match="undocumented AIDL sources"):
        closure._validate_inventory(
            {"examples/example/app.aidl", "examples/example/new.aidl"},
            {"examples/example/app.aidl"},
            "example",
        )


def test_shared_mismatch_removal_fails_closed() -> None:
    manifest = copy.deepcopy(closure._load(closure.ROOT / closure.MANIFEST))
    manifest["required_shared_mismatch_dispositions"].pop("app.links")
    with pytest.raises(ValueError, match="shared mismatch disposition drift"):
        closure.validate(manifest=manifest)


def test_shared_mismatch_reclassification_fails_closed() -> None:
    manifest = copy.deepcopy(closure._load(closure.ROOT / closure.MANIFEST))
    manifest["required_shared_mismatch_dispositions"]["app.links"] = "non-production-fail-closed"
    with pytest.raises(ValueError, match="shared mismatch disposition drift"):
        closure.validate(manifest=manifest)


def test_canonical_support_drift_fails_closed() -> None:
    manifest = copy.deepcopy(closure._load(closure.ROOT / closure.MANIFEST))
    manifest["required_canonical_source_support"].remove("entity.field-slot")
    with pytest.raises(ValueError, match="canonical source support drift"):
        closure.validate(manifest=manifest)


def test_fixture_classification_drift_fails_closed() -> None:
    rows = [
        {"path": "fixtures/valid/example.aidl", "class": "negative-rejection-fixture"}
    ]
    with pytest.raises(ValueError, match="fixture classification drift"):
        closure._validate_fixture_classification(
            rows, "fixtures/valid", "legacy-readable-compatibility"
        )
