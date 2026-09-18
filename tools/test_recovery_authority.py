from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.recovery_authority import validate_authority

ROOT = Path(__file__).resolve().parents[1]


class RecoveryAuthorityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.transition = json.loads((ROOT / "spec/core-authority-transition-v1.json").read_text(encoding="utf-8"))
        cls.milestone = json.loads((ROOT / "roadmap/v1/milestones/m16.5.json").read_text(encoding="utf-8"))

    def test_repository_authority_chain_is_consistent(self) -> None:
        self.assertEqual([], validate_authority(self.transition, self.milestone))

    def test_open_historical_gate_fails_closed(self) -> None:
        milestone = copy.deepcopy(self.milestone)
        milestone["packages"][2]["status"] = "open"
        self.assertTrue(any("M16.5-E3 must be terminal" in error for error in validate_authority(self.transition, milestone)))

    def test_missing_superseding_authority_link_fails_closed(self) -> None:
        milestone = copy.deepcopy(self.milestone)
        milestone["packages"][2]["superseded_by_authority"] = []
        self.assertTrue(any("M16.5-E3 must point" in error for error in validate_authority(self.transition, milestone)))

    def test_second_active_authority_fails_closed(self) -> None:
        transition = copy.deepcopy(self.transition)
        transition["activeLanguageAuthority"]["path"] = "spec/language-surface-v1.json"
        self.assertTrue(any("active language authority" in error for error in validate_authority(transition, self.milestone)))


if __name__ == "__main__":
    unittest.main()
