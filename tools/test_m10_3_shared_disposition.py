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

    def test_missing_shared_mismatch_fails_closed(self) -> None:
        manifest = json.loads((disposition.ROOT / disposition.MANIFEST).read_text(encoding="utf-8"))
        mutated = copy.deepcopy(manifest)
        mutated["shared_mismatch_dispositions"] = mutated["shared_mismatch_dispositions"][:-1]
        with self.assertRaisesRegex(ValueError, "coverage drift"):
            disposition.validate(manifest=mutated)

    def test_unknown_shared_mismatch_fails_closed(self) -> None:
        manifest = json.loads((disposition.ROOT / disposition.MANIFEST).read_text(encoding="utf-8"))
        mutated = copy.deepcopy(manifest)
        mutated["shared_mismatch_dispositions"].append(
            {
                "id": "invented.semantic",
                "disposition": "non-production-fail-closed",
                "detail": "must not be silently admitted",
            }
        )
        with self.assertRaisesRegex(ValueError, "coverage drift"):
            disposition.validate(manifest=mutated)

    def test_admission_and_contract_flags_fail_closed(self) -> None:
        manifest = json.loads((disposition.ROOT / disposition.MANIFEST).read_text(encoding="utf-8"))
        mutated = copy.deepcopy(manifest)
        mutated["constraints"]["production_admission_changed"] = True
        with self.assertRaisesRegex(ValueError, "constraint drift"):
            disposition.validate(manifest=mutated)

    def test_frozen_contract_revision_drift_fails_closed(self) -> None:
        manifest = json.loads((disposition.ROOT / disposition.MANIFEST).read_text(encoding="utf-8"))
        mutated = copy.deepcopy(manifest)
        mutated["frozen_language_contract"]["contract_revision"] = 5
        with self.assertRaisesRegex(ValueError, "contract identity drift"):
            disposition.validate(manifest=mutated)


if __name__ == "__main__":
    unittest.main()
