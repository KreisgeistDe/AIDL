from __future__ import annotations

import copy
import unittest

from tools import m10_3_closure_certification as closure


class M103ClosureCertificationTest(unittest.TestCase):
    def test_m10_3_closure_certifies_current_repository(self) -> None:
        report = closure.validate()
        self.assertEqual(report["contract_revision"], 4)
        self.assertTrue(report["m10_3_complete"])
        self.assertFalse(report["production_admission_changed"])
        self.assertFalse(report["canonical_ir_meaning_changed"])
        self.assertEqual(
            {row["id"]: row["source_count"] for row in report["reference_applications"]},
            {"calendar-offline": 13, "petstore": 19, "videohub": 25},
        )
        self.assertEqual(
            report["canonical_source_support"],
            [
                "app.profile-block",
                "entity.field-slot",
                "operation.parameters-header-arg",
            ],
        )
        self.assertGreater(report["shared_mismatch_count"], 0)
        self.assertTrue(all(count > 0 for count in report["fixture_counts"].values()))

    def test_new_reference_source_without_inventory_entry_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "undocumented AIDL sources"):
            closure._validate_inventory(
                {"examples/example/app.aidl", "examples/example/new.aidl"},
                {"examples/example/app.aidl"},
                "example",
            )

    def test_shared_mismatch_removal_fails_closed(self) -> None:
        manifest = copy.deepcopy(closure._load(closure.ROOT / closure.MANIFEST))
        manifest["required_shared_mismatch_dispositions"].pop("app.links")
        with self.assertRaisesRegex(ValueError, "shared mismatch disposition drift"):
            closure.validate(manifest=manifest)

    def test_shared_mismatch_reclassification_fails_closed(self) -> None:
        manifest = copy.deepcopy(closure._load(closure.ROOT / closure.MANIFEST))
        manifest["required_shared_mismatch_dispositions"]["app.links"] = (
            "non-production-fail-closed"
        )
        with self.assertRaisesRegex(ValueError, "shared mismatch disposition drift"):
            closure.validate(manifest=manifest)

    def test_canonical_support_drift_fails_closed(self) -> None:
        manifest = copy.deepcopy(closure._load(closure.ROOT / closure.MANIFEST))
        manifest["required_canonical_source_support"].remove("entity.field-slot")
        with self.assertRaisesRegex(ValueError, "canonical source support drift"):
            closure.validate(manifest=manifest)

    def test_fixture_classification_drift_fails_closed(self) -> None:
        rows = [
            {"path": "fixtures/valid/example.aidl", "class": "negative-rejection-fixture"}
        ]
        with self.assertRaisesRegex(ValueError, "fixture classification drift"):
            closure._validate_fixture_classification(
                rows, "fixtures/valid", "legacy-readable-compatibility"
            )


if __name__ == "__main__":
    unittest.main()
