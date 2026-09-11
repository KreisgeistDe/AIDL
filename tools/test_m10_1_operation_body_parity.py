#!/usr/bin/env python3
"""Focused regressions for contract-backed M10.1 operation body parity."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_language_surface import BodySlot, Declaration, TypeRef, UnsupportedMigration
from tools.compiler_language_surface_body_parity import ContractBodyParityBridge
from tools.compiler_language_surface_integration import normalize_compiler_analysis


class M101OperationBodyParityTest(unittest.TestCase):
    def _analysis(self, source_text: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "model.aidl"
        source.write_text(source_text, encoding="utf-8")
        return load_compiler_analysis([source])

    def test_bridge_normalizes_only_contract_backed_operation_body_slots(self) -> None:
        bridge = ContractBodyParityBridge()
        result = bridge.normalize_text(
            """query find() -> string {
  timeout: 5s
  allow: principal
  read: petById
}
mutation update() -> string {
  timeout: 10s
  call: persistPet
  audit: required
  allow: principal
}
"""
        )
        self.assertTrue(result.ok, result.diagnostics)
        query, mutation = result.document.declarations
        self.assertEqual(["read", "allow", "timeout"], [slot.slot_id for slot in query.body_slots])
        self.assertEqual(["allow", "call", "audit", "timeout"], [slot.slot_id for slot in mutation.body_slots])
        self.assertEqual("expression", query.body_slots[1].value_mode)
        self.assertEqual("literal", query.body_slots[2].value_mode)
        self.assertEqual("expression", mutation.body_slots[1].value_mode)
        self.assertEqual("literal", mutation.body_slots[2].value_mode)

    def test_production_integration_admits_complete_supported_operation_bodies(self) -> None:
        surface = normalize_compiler_analysis(
            self._analysis(
                """module demo
query find() -> string {
  allow: principal
  read: value
  timeout: 5s
}
mutation update() -> string {
  allow: principal
  call: persist
  audit: none
  timeout: 10s
}
"""
            )
        )
        self.assertTrue(surface.ok, (surface.diagnostics, surface.type_issues))
        self.assertEqual(["find", "update"], [item.name for item in surface.declarations])
        self.assertNotIn("AIDL-N013", [item.code for item in surface.diagnostics])

    def test_body_order_whitespace_and_source_location_do_not_change_semantics(self) -> None:
        first = normalize_compiler_analysis(
            self._analysis(
                """module demo
query find() -> string {
  read: value
  allow: principal
  timeout: 5s
}
"""
            )
        )
        second = normalize_compiler_analysis(
            self._analysis(
                """\n\nmodule demo
query find( ) -> string {
  timeout : 5s
  allow : principal
  read : value
}
"""
            )
        )
        self.assertTrue(first.ok, first.diagnostics)
        self.assertTrue(second.ok, second.diagnostics)
        self.assertEqual(first.semantic_json(), second.semantic_json())
        self.assertEqual(first.semantic_hash(), second.semantic_hash())

    def test_unrepresented_operation_mini_languages_remain_fail_closed(self) -> None:
        cases = (
            "query find() -> string {\n  auth: public\n  read: value\n}\n",
            "query find() -> string {\n  cache: public ttl 5s\n  read: value\n}\n",
            "mutation update() -> string {\n  authorize: remote query principal\n}\n",
            "mutation update() -> string {\n  idempotency: key retain 5s\n}\n",
        )
        for source in cases:
            with self.subTest(source=source.splitlines()[1].strip()):
                surface = normalize_compiler_analysis(self._analysis(source))
                self.assertFalse(surface.ok)
                self.assertIn("AIDL-N013", [item.code for item in surface.diagnostics])
                self.assertNotIn("find", [item.name for item in surface.declarations])
                self.assertNotIn("update", [item.name for item in surface.declarations])

    def test_legacy_and_independent_canonical_body_facts_share_hash_and_migration_stays_explicit(self) -> None:
        bridge = ContractBodyParityBridge()
        result = bridge.normalize_text(
            """query find() -> string {
  timeout: 5s
  allow: principal
  read: value
}
"""
        )
        self.assertTrue(result.ok, result.diagnostics)
        actual = result.document.declarations[0]
        canonical = Declaration(
            kind="query",
            name="find",
            name_policy="required",
            exported=False,
            result_type=TypeRef("scalar", name="string"),
            body_slots=(
                BodySlot("read", None, "expression", "value"),
                BodySlot("allow", None, "expression", "principal"),
                BodySlot("timeout", None, "literal", "5s"),
            ),
        )
        self.assertEqual(canonical.semantic_hash(), actual.semantic_hash())
        self.assertEqual(
            "query find() -> string {\n  read: value\n  allow: principal\n  timeout: 5s\n}\n",
            bridge.format_legacy(actual),
        )
        with self.assertRaises(UnsupportedMigration):
            bridge.migrate_to_canonical_preview(actual)


if __name__ == "__main__":
    unittest.main()
