from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import validate_main_protection_contract as protection


class MainProtectionContractTests(unittest.TestCase):
    def test_repository_contract_matches_current_workflows(self) -> None:
        self.assertEqual([], protection.validate())

    def test_duplicate_required_context_is_rejected(self) -> None:
        contract = json.loads(protection.CONTRACT.read_text(encoding="utf-8"))
        contract["requiredPullRequestChecks"].append(dict(contract["requiredPullRequestChecks"][0]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            with mock.patch.object(protection, "CONTRACT", path):
                self.assertIn("required check contexts must be unique", protection.validate())

    def test_required_status_checks_rule_cannot_be_removed(self) -> None:
        contract = json.loads(protection.CONTRACT.read_text(encoding="utf-8"))
        contract["requiredRepositoryRules"].remove("required_status_checks")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            with mock.patch.object(protection, "CONTRACT", path):
                self.assertIn(
                    "requiredRepositoryRules must match the M9-06 rule set",
                    protection.validate(),
                )


if __name__ == "__main__":
    unittest.main()
