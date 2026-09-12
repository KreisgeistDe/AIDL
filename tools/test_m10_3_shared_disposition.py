from __future__ import annotations

import copy
import json
import unittest

from tools import m10_3_shared_disposition as disposition


class M103SharedDispositionTest(unittest.TestCase):
    def test_repository_manifest_is_complete_and_deterministic(self) -> None:
        first = disposition.validate()
        second = disposition.validate()
        self.assertEqual(first, second)
        self.assertEqual(first["contract_revision"], 4)
        self.assertEqual(first["canonical_support_count"], 3)
        self.assertEqual(first["disposition_count"], len(disposition.REQUIRED_SHARED_MISMATCHES))
        self.assertEqual(first["versioned_admission_count"], 1)
        self.assertTrue({"auth", "a11y", "privacy"} <= disposition.REQUIRED_SHARED_MISMATCHES)

    def _manifest(self) -> dict:
        return json.loads((disposition.ROOT / disposition.MANIFEST).read_text(encoding="utf-8"))

    def test_missing_shared_mismatch_fails_closed(self) -> None:
        mutated = copy.deepcopy(self._manifest())
        mutated["shared_mismatch_dispositions"] = mutated["shared_mismatch_dispositions"][:-1]
        with self.assertRaisesRegex(ValueError, "coverage drift"):
            disposition.validate(manifest=mutated)

    def test_unknown_shared_mismatch_fails_closed(self) -> None:
        mutated = copy.deepcopy(self._manifest())
        mutated["shared_mismatch_dispositions"].append(
            {
                "id": "invented.semantic",
                "disposition": "non-production-fail-closed",
                "detail": "must not be silently admitted",
            }
        )
        with self.assertRaisesRegex(ValueError, "coverage drift"):
            disposition.validate(manifest=mutated)

    def test_exact_disposition_mapping_is_pinned(self) -> None:
        manifest = self._manifest()
        actual = {
            item["id"]: item["disposition"]
            for item in manifest["shared_mismatch_dispositions"]
        }
        self.assertEqual(actual, disposition.EXPECTED_SHARED_DISPOSITIONS)
        self.assertEqual(actual["app.links"], "requires-versioned-admission")
        self.assertTrue(
            all(
                value == "non-production-fail-closed"
                for key, value in actual.items()
                if key != "app.links"
            )
        )

    def test_swapped_dispositions_fail_even_when_counts_match(self) -> None:
        mutated = copy.deepcopy(self._manifest())
        app_links = next(
            item for item in mutated["shared_mismatch_dispositions"] if item["id"] == "app.links"
        )
        auth = next(
            item for item in mutated["shared_mismatch_dispositions"] if item["id"] == "auth"
        )
        app_links["disposition"], auth["disposition"] = (
            auth["disposition"],
            app_links["disposition"],
        )
        with self.assertRaisesRegex(ValueError, "mapping drift"):
            disposition.validate(manifest=mutated)

    def test_admission_and_contract_flags_fail_closed(self) -> None:
        mutated = copy.deepcopy(self._manifest())
        mutated["constraints"]["production_admission_changed"] = True
        with self.assertRaisesRegex(ValueError, "constraint drift"):
            disposition.validate(manifest=mutated)

    def test_frozen_contract_revision_drift_fails_closed(self) -> None:
        mutated = copy.deepcopy(self._manifest())
        mutated["frozen_language_contract"]["contract_revision"] = 5
        with self.assertRaisesRegex(ValueError, "contract identity drift"):
            disposition.validate(manifest=mutated)


if __name__ == "__main__":
    unittest.main()
