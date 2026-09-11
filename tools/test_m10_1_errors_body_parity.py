#!/usr/bin/env python3
"""Focused regressions for compiler-evidence-backed M10.1 errors body parity."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_language_surface import BodySlot, Declaration, TypeRef, UnsupportedMigration
from tools.compiler_language_surface_body_parity import ContractBodyParityBridge
from tools.compiler_language_surface_integration import (
    PRODUCTION_NORMALIZATION_VERSION,
    normalize_compiler_analysis,
)
from tools.compiler_typecheck import collect_type_issues


class M101ErrorsBodyParityTest(unittest.TestCase):
    def _analysis(self, source_text: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "model.aidl"
        source.write_text(source_text, encoding="utf-8")
        return load_compiler_analysis([source])

    @staticmethod
    def _declaration(surface, name: str):
        return next(item for item in surface.declarations if item.name == name)

    def test_query_and_mutation_admit_only_complete_ordered_error_evidence(self) -> None:
        surface = normalize_compiler_analysis(
            self._analysis(
                """module demo
error KnownError {}
query find() -> string {
  errors: [InternalFailure, KnownError]
}
mutation update() -> string {
  errors: [KnownError, NotAuthorized]
}
"""
            )
        )
        self.assertTrue(surface.ok, (surface.diagnostics, surface.type_issues))
        self.assertEqual("aidl.m10.1-production/v5", PRODUCTION_NORMALIZATION_VERSION)
        query = self._declaration(surface, "find")
        mutation = self._declaration(surface, "update")
        self.assertEqual(["errors"], [slot.slot_id for slot in query.body_slots])
        self.assertEqual(["errors"], [slot.slot_id for slot in mutation.body_slots])
        self.assertEqual("type_ref_list", query.body_slots[0].value_mode)
        self.assertEqual(
            ["InternalFailure", "demo.KnownError"],
            [item.name for item in query.body_slots[0].value],
        )
        self.assertEqual(
            ["demo.KnownError", "NotAuthorized"],
            [item.name for item in mutation.body_slots[0].value],
        )

    def test_errors_list_and_clause_order_whitespace_do_not_change_semantics(self) -> None:
        first = normalize_compiler_analysis(
            self._analysis(
                """module demo
error KnownError {}
query find() -> string {
  read: value
  errors: [InternalFailure, KnownError]
  timeout: 5s
}
"""
            )
        )
        second = normalize_compiler_analysis(
            self._analysis(
                """\nmodule demo
error KnownError {}
query find( ) -> string {
  timeout : 5s
  errors : [ InternalFailure , demo.KnownError ]
  read : value
}
"""
            )
        )
        self.assertTrue(first.ok, first.diagnostics)
        self.assertTrue(second.ok, second.diagnostics)
        self.assertEqual(first.semantic_json(), second.semantic_json())
        self.assertEqual(first.semantic_hash(), second.semantic_hash())
        query = self._declaration(second, "find")
        self.assertEqual(
            ["InternalFailure", "demo.KnownError"],
            [item.name for item in next(slot for slot in query.body_slots if slot.slot_id == "errors").value],
        )

    def test_incomplete_error_evidence_stays_outside_complete_production_semantics(self) -> None:
        cases = {
            "unresolved": """module demo
query find() -> string { errors: [MissingError] }
""",
            "wrong-kind": """module demo
value NotError {}
query find() -> string { errors: [NotError] }
""",
            "ambiguous": """module demo
error Duplicate {}
error Duplicate {}
query find() -> string { errors: [Duplicate] }
""",
            "malformed": """module demo
query find() -> string { errors: [map<string>] }
""",
        }
        for label, source in cases.items():
            with self.subTest(label=label):
                analysis = self._analysis(source)
                surface = normalize_compiler_analysis(analysis)
                self.assertFalse(surface.ok)
                self.assertNotIn("find", [item.name for item in surface.declarations])
                self.assertIn("AIDL-N013", [item.code for item in surface.diagnostics])
                if label == "unresolved":
                    self.assertNotIn(
                        "AIDL-T001",
                        [item.code for item in collect_type_issues(analysis.project)],
                    )

    def test_legacy_and_independent_canonical_errors_facts_share_hash_and_migration_is_explicit(self) -> None:
        surface = normalize_compiler_analysis(
            self._analysis(
                """module demo
error KnownError {}
query find() -> string {
  errors: [InternalFailure, KnownError]
}
"""
            )
        )
        self.assertTrue(surface.ok, surface.diagnostics)
        actual = self._declaration(surface, "find")
        canonical = Declaration(
            kind="query",
            name="find",
            name_policy="required",
            exported=False,
            result_type=TypeRef("scalar", name="string"),
            body_slots=(
                BodySlot(
                    "errors",
                    None,
                    "type_ref_list",
                    (
                        TypeRef("named", name="InternalFailure"),
                        TypeRef("named", name="demo.KnownError"),
                    ),
                ),
            ),
        )
        self.assertEqual(canonical.semantic_hash(), actual.semantic_hash())
        bridge = ContractBodyParityBridge()
        self.assertEqual(
            "query find() -> string {\n  errors: [InternalFailure, demo.KnownError]\n}\n",
            bridge.format_legacy(actual),
        )
        with self.assertRaises(UnsupportedMigration):
            bridge.migrate_to_canonical_preview(actual)


if __name__ == "__main__":
    unittest.main()
