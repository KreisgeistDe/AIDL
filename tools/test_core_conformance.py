from __future__ import annotations

import copy
import unittest

from tools.conformance_manifest import ROOT, load_core_matrix, validate_core_data


class CoreConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = load_core_matrix(ROOT)

    def test_repository_core_matrix_is_valid(self) -> None:
        self.assertEqual([], validate_core_data(self.matrix, root=ROOT))

    def test_unknown_layer_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        candidate["features"][0]["layerStatus"]["runtime"] = "implemented"
        errors = validate_core_data(candidate, root=ROOT)
        self.assertTrue(any("schema" in error and "runtime" in error for error in errors), errors)

    def test_unknown_status_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        candidate["features"][0]["layerStatus"]["parse"] = "complete"
        errors = validate_core_data(candidate, root=ROOT)
        self.assertTrue(any("schema" in error and "complete" in error for error in errors), errors)

    def test_unknown_feature_id_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        candidate["features"][0]["id"] = "decl.unknown"
        errors = validate_core_data(candidate, root=ROOT)
        self.assertIn("core feature rows must be unique, complete, and sorted by stable id", errors)

    def test_duplicate_feature_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        candidate["features"].append(copy.deepcopy(candidate["features"][0]))
        errors = validate_core_data(candidate, root=ROOT)
        self.assertIn("core feature rows must be unique, complete, and sorted by stable id", errors)

    def test_unknown_evidence_id_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        feature = candidate["features"][0]
        feature["layerEvidence"]["parse"] = ["unknown-evidence"]
        errors = validate_core_data(candidate, root=ROOT)
        self.assertIn(f"{feature['id']}/parse: unknown evidence id unknown-evidence", errors)

    def test_missing_evidence_path_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        candidate["evidenceCatalog"]["parse-core"][0]["path"] = "missing/parser.py"
        errors = validate_core_data(candidate, root=ROOT)
        self.assertTrue(any("missing evidence path missing/parser.py" in error for error in errors), errors)

    def test_documentation_only_evidence_cannot_promote_to_implemented(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        feature = candidate["features"][0]
        feature["layerStatus"]["validate"] = "implemented"
        feature["layerEvidence"]["validate"] = ["spec-core"]
        errors = validate_core_data(candidate, root=ROOT)
        self.assertIn(f"{feature['id']}/validate: implemented status requires executable or machine-readable evidence", errors)

    def test_inventoried_ids_are_deterministic(self) -> None:
        candidate = copy.deepcopy(self.matrix)
        candidate["declarationIds"][0], candidate["declarationIds"][1] = candidate["declarationIds"][1], candidate["declarationIds"][0]
        errors = validate_core_data(candidate, root=ROOT)
        self.assertIn("core declaration inventory drift", errors)


if __name__ == "__main__":
    unittest.main()
