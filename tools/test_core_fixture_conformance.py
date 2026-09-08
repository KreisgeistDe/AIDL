from __future__ import annotations

import copy
import unittest

from tools.conformance_manifest import (
    ROOT,
    core_supported_ids,
    load_core_fixture_matrix,
    load_core_matrix,
    validate_core_fixture_data,
)


class CoreFixtureConformanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.core = load_core_matrix(ROOT)
        self.coverage = load_core_fixture_matrix(ROOT)

    def test_fixture_coverage_matches_derived_core_supported_rows(self) -> None:
        self.assertEqual(self.coverage["featureIds"], core_supported_ids(self.core))
        self.assertEqual(validate_core_fixture_data(self.coverage, self.core, root=ROOT), [])

    def test_missing_supported_row_fails_deterministically(self) -> None:
        payload = copy.deepcopy(self.coverage)
        removed = payload["featureIds"].pop()
        errors = validate_core_fixture_data(payload, self.core, root=ROOT)
        self.assertIn(f"Core fixture coverage missing supported ids: ['{removed}']", errors)

    def test_consumer_is_fixture_complete_after_validate_ir_promotion(self) -> None:
        self.assertIn("decl.consumer", self.coverage["featureIds"])
        row = next(item for item in self.core["features"] if item["id"] == "decl.consumer")
        self.assertEqual("implemented", row["layerStatus"]["validate"])
        self.assertEqual("implemented", row["layerStatus"]["ir"])
        paths = {
            entry["path"]
            for category in ("positive-core", "negative-core", "ir-core")
            for entry in self.coverage["evidenceCatalog"][category]
        }
        self.assertIn("tools/test_core_consumer_materialization_closure.py", paths)

    def test_module_and_import_are_fixture_complete_after_claim_correction(self) -> None:
        self.assertIn("decl.module", self.coverage["featureIds"])
        self.assertIn("decl.import", self.coverage["featureIds"])
        module = next(item for item in self.core["features"] if item["id"] == "decl.module")
        import_ = next(item for item in self.core["features"] if item["id"] == "decl.import")
        self.assertEqual("implemented", module["layerStatus"]["validate"])
        self.assertEqual("not-applicable", module["layerStatus"]["ir"])
        self.assertEqual("not-applicable", import_["layerStatus"]["validate"])
        self.assertEqual("not-applicable", import_["layerStatus"]["ir"])
        paths = {
            entry["path"]
            for category in ("positive-core", "negative-core", "ir-core")
            for entry in self.coverage["evidenceCatalog"][category]
        }
        self.assertIn("tools/test_core_module_import_claim_model.py", paths)

    def test_unknown_evidence_reference_fails(self) -> None:
        payload = copy.deepcopy(self.coverage)
        payload["defaultEvidence"]["negative"] = ["missing-negative-suite"]
        errors = validate_core_fixture_data(payload, self.core, root=ROOT)
        self.assertIn("Core fixture negative: unknown evidence id missing-negative-suite", errors)
        self.assertIn("Core fixture negative: missing evidence", errors)

    def test_ir_and_compatibility_require_machine_fixtures(self) -> None:
        payload = copy.deepcopy(self.coverage)
        payload["evidenceCatalog"]["ir-core"] = [
            {"path": "tools/test_ir_semantic_projection.py", "type": "test"}
        ]
        payload["evidenceCatalog"]["compatibility-core"] = [
            {"path": "tools/test_ir_compatibility.py", "type": "test"}
        ]
        errors = validate_core_fixture_data(payload, self.core, root=ROOT)
        self.assertIn("Core fixture ir: Canonical-IR snapshot evidence required", errors)
        self.assertIn("Core fixture compatibility: compatibility matrix evidence required", errors)


if __name__ == "__main__":
    unittest.main()
