from __future__ import annotations

import copy
import unittest

from tools.conformance_manifest import ROOT, load_manifest, validate_data, validate_manifest


class ConformanceManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(ROOT)
        self.support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")

    def test_repository_manifest_is_valid(self) -> None:
        self.assertEqual([], validate_manifest(ROOT))

    def test_unknown_status_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["surfaces"][0]["status"] = "complete"
        errors = validate_data(candidate, root=ROOT, support_text=self.support)
        self.assertTrue(any("schema" in error and "complete" in error for error in errors), errors)

    def test_missing_evidence_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["surfaces"][0]["evidence"] = []
        errors = validate_data(candidate, root=ROOT, support_text=self.support)
        self.assertTrue(any("schema" in error and "non-empty" in error for error in errors), errors)

    def test_missing_evidence_path_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["surfaces"][0]["evidence"][0]["path"] = "does/not/exist.json"
        errors = validate_data(candidate, root=ROOT, support_text=self.support)
        self.assertIn(
            f"{candidate['surfaces'][0]['id']}: missing evidence path does/not/exist.json",
            errors,
        )

    def test_unknown_required_surface_id_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["surfaces"][0]["requires"] = ["profile.unknown"]
        errors = validate_data(candidate, root=ROOT, support_text=self.support)
        self.assertIn(
            f"{candidate['surfaces'][0]['id']}: unknown required surface id profile.unknown",
            errors,
        )

    def test_unknown_profile_id_is_rejected_against_registry(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        fake = copy.deepcopy(next(item for item in candidate["surfaces"] if item["id"] == "profile.web"))
        fake["id"] = "profile.unknown"
        fake["requires"] = ["profile.core"]
        fake["supportStatement"] = "unknown profile fixture"
        candidate["surfaces"].append(fake)
        candidate["surfaces"].sort(key=lambda item: item["id"])
        errors = validate_data(candidate, root=ROOT, support_text=self.support + "\n`profile.unknown`\nunknown profile fixture\n")
        self.assertTrue(any("unknown registry profile ids" in error for error in errors), errors)

    def test_support_statement_drift_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        surface = candidate["surfaces"][0]
        drifted_support = self.support.replace(surface["supportStatement"], "drifted statement")
        errors = validate_data(candidate, root=ROOT, support_text=drifted_support)
        self.assertIn(f"{surface['id']}: SUPPORT.md support statement drift", errors)

    def test_surface_ids_are_deterministically_sorted(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["surfaces"][0], candidate["surfaces"][1] = candidate["surfaces"][1], candidate["surfaces"][0]
        errors = validate_data(candidate, root=ROOT, support_text=self.support)
        self.assertIn("surfaces must be sorted by stable id", errors)


if __name__ == "__main__":
    unittest.main()
