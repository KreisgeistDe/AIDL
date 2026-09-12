from __future__ import annotations

import unittest

from tools.compiler_language_surface_body_parity import ContractBodyParityBridge
from tools.compiler_operation_policy_parity import (
    POLICY_PARITY_VERSION,
    operation_policy_dispositions,
    operation_policy_dispositions_json,
)


class OperationPolicyParityTests(unittest.TestCase):
    def test_contract_derived_dispositions_are_explicit(self) -> None:
        evidence = operation_policy_dispositions()
        self.assertEqual(POLICY_PARITY_VERSION, evidence["schema_version"])
        self.assertEqual(4, evidence["contract_revision"])
        for kind in ("query", "mutation"):
            items = {item["concept"]: item for item in evidence["declarations"][kind]}
            self.assertEqual("production_parity", items["authorize"]["disposition"])
            self.assertEqual("allow", items["authorize"]["contract_slot"])
            self.assertEqual("excluded", items["auth"]["disposition"])
            self.assertEqual("excluded", items["cache"]["disposition"])
            self.assertEqual("excluded", items["consistency"]["disposition"])

    def test_policy_audit_json_is_byte_stable(self) -> None:
        first = operation_policy_dispositions_json()
        second = operation_policy_dispositions_json()
        self.assertEqual(first, second)
        self.assertNotIn(": ", first)
        self.assertNotIn(", ", first)

    def test_allow_is_losslessly_normalized_as_authorize_parity(self) -> None:
        result = ContractBodyParityBridge().normalize_text(
            "module demo\nquery visible() -> bool {\n  allow: principal.authenticated\n}\n"
        )
        self.assertFalse(result.parser_diagnostics)
        declaration = result.document.declarations[0]
        self.assertEqual(["allow"], [slot.slot_id for slot in declaration.body_slots])
        self.assertEqual(
            [],
            [item for item in result.diagnostics if item.code == "AIDL-N010"],
        )

    def test_noncontract_policy_clauses_remain_fail_closed(self) -> None:
        result = ContractBodyParityBridge().normalize_text(
            "module demo\nquery visible() -> bool {\n"
            "  auth: authenticated\n"
            "  cache: public ttl 30s\n"
            "  consistency: strong\n"
            "}\n"
        )
        self.assertFalse(result.parser_diagnostics)
        unsupported = [item.message for item in result.diagnostics if item.code == "AIDL-N010"]
        self.assertTrue(any("auth" in message for message in unsupported))
        self.assertTrue(any("cache" in message for message in unsupported))
        self.assertTrue(any("consistency" in message for message in unsupported))
        self.assertEqual((), result.document.declarations[0].body_slots)


if __name__ == "__main__":
    unittest.main()
