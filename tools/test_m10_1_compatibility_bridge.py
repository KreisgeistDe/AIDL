#!/usr/bin/env python3
"""M10.1 compatibility-bridge regressions."""

from __future__ import annotations

import unittest

from tools.compiler_language_surface import (
    Declaration,
    HeaderArg,
    LanguageSurfaceBridge,
    UnsupportedMigration,
)


class M101CompatibilityBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = LanguageSurfaceBridge(
            reference_projections={"Pet.id": ("Pet", "id", "uuid")}
        )

    def _one(self, source: str):
        result = self.bridge.normalize_text(source)
        self.assertFalse(result.parser_diagnostics)
        self.assertEqual(1, len(result.document.declarations))
        return result, result.document.declarations[0]

    def test_contract_is_the_single_m10_1_schema_source(self) -> None:
        self.assertEqual("M10.1", self.bridge.contract["authority"])
        self.assertEqual(
            set(self.bridge.kinds),
            {item["kind"] for item in self.bridge.contract["declaration_kinds"]},
        )

    def test_legacy_migration_normalizes_named_header_facts(self) -> None:
        result, declaration = self._one('migration V2 from "1" to "2" {}\n')
        self.assertTrue(result.ok)
        self.assertEqual(
            [("fromVersion", "literal", "1"), ("toVersion", "literal", "2")],
            [(item.name, item.value_mode, item.value) for item in declaration.header_args],
        )
        canonical = Declaration(
            kind="migration",
            name="V2",
            name_policy="required",
            exported=False,
            header_args=(
                HeaderArg("fromVersion", "literal", "1"),
                HeaderArg("toVersion", "literal", "2"),
            ),
        )
        self.assertEqual(canonical.semantic_hash(), declaration.semantic_hash())

    def test_relationship_headers_normalize_deterministically(self) -> None:
        source = """
client Mobile for PetService {}
consumer Audit on PetEvents from PetChanged {}
projection PetRead from [PetCreated, PetChanged] into Pet {}
"""
        result = self.bridge.normalize_text(source)
        self.assertTrue(result.ok)
        by_kind = {item.kind: item for item in result.document.declarations}
        self.assertEqual(["service"], [item.name for item in by_kind["client"].header_args])
        self.assertEqual(["topic", "messageType"], [item.name for item in by_kind["consumer"].header_args])
        self.assertEqual(["sources", "target"], [item.name for item in by_kind["projection"].header_args])
        self.assertEqual(result.document.semantic_hash(), self.bridge.normalize_text(source).document.semantic_hash())

    def test_opaque_alias_and_reference_projection_are_semantic_facts(self) -> None:
        result, declaration = self._one("opaque PetKey = ref Pet.id\n")
        self.assertTrue(result.ok)
        self.assertEqual("alias", declaration.kind)
        self.assertTrue(declaration.facts["opacity"])
        self.assertEqual(
            {
                "kind": "reference",
                "optional": False,
                "target": "Pet",
                "projection": "id",
                "resolved_type": "uuid",
            },
            declaration.facts["aliased_type"].semantic(),
        )
        self.assertEqual("opaque PetKey = ref Pet.id\n", self.bridge.format_legacy(declaration))
        with self.assertRaises(UnsupportedMigration):
            self.bridge.migrate_to_canonical_preview(declaration)

    def test_type_optionality_is_separate_from_slot_cardinality(self) -> None:
        result, declaration = self._one(
            """entity User {
  pet: ref Pet.id required unique
  nickname: string?
}
"""
        )
        self.assertTrue(result.ok)
        pet, nickname = declaration.body_slots
        self.assertEqual("field", pet.slot_id)
        self.assertEqual("reference", pet.value.kind)
        self.assertEqual("uuid", pet.value.resolved_type)
        self.assertFalse(pet.value.optional)
        self.assertTrue(nickname.value.optional)
        field_schema = self.bridge.kinds["entity"]["body_slots"][0]
        self.assertEqual({"min": 0, "max": None}, field_schema["occurrence"])

    def test_app_profile_and_enum_cases_become_body_slots(self) -> None:
        app_result, app = self._one(
            """app Store {
  profile core version 1
}
"""
        )
        self.assertTrue(app_result.ok)
        self.assertEqual("profile", app.body_slots[0].slot_id)
        self.assertEqual("core", app.body_slots[0].name)
        self.assertEqual(1, app.body_slots[0].value["slots"][0]["value"])

        enum_result, enum = self._one('enum State { active, disabled = "off" }\n')
        self.assertTrue(enum_result.ok)
        self.assertEqual(["active", "disabled"], [item.name for item in enum.body_slots])
        self.assertEqual("off", enum.body_slots[1].value["wire_literal"])

    def test_public_reason_and_expression_mode_are_structured(self) -> None:
        result, declaration = self._one(
            """@publicReason("public catalog lookup")
query getPet() -> Pet {
  read: petById
}
"""
        )
        self.assertTrue(result.ok)
        modifier = declaration.modifiers[0]
        self.assertEqual("publicReason", modifier.name)
        self.assertEqual("query", modifier.target)
        self.assertEqual(("public catalog lookup",), modifier.args)
        self.assertEqual("expression", declaration.body_slots[0].value_mode)
        self.assertEqual("petById", declaration.body_slots[0].value)

    def test_wrong_modifier_target_has_stable_diagnostic(self) -> None:
        result, _ = self._one(
            """@publicReason("why")
entity User {}
"""
        )
        self.assertIn("AIDL-N008", [item.code for item in result.diagnostics])

    def test_duplicate_unique_field_has_stable_diagnostic(self) -> None:
        result, _ = self._one(
            """entity User {
  id: uuid
  id: uuid
}
"""
        )
        self.assertIn("AIDL-N005", [item.code for item in result.diagnostics])

    def test_occurrence_overflow_has_stable_diagnostic(self) -> None:
        result, _ = self._one(
            """query getPet() -> Pet {
  read: first
  read: second
}
"""
        )
        self.assertIn("AIDL-N006", [item.code for item in result.diagnostics])

    def test_unresolved_projection_fails_closed_until_resolver_evidence(self) -> None:
        bridge = LanguageSurfaceBridge()
        result = bridge.normalize_text(
            """entity User {
  pet: ref Pet.id
}
"""
        )
        self.assertIn("AIDL-N012", [item.code for item in result.diagnostics])

    def test_formatter_is_same_version_and_idempotent(self) -> None:
        result, declaration = self._one('migration V2 from "1" to "2" {}\n')
        self.assertTrue(result.ok)
        formatted = self.bridge.format_legacy(declaration)
        self.assertEqual('migration V2 from "1" to "2" {}\n', formatted)
        again = self.bridge.normalize_text(formatted)
        self.assertTrue(again.ok)
        self.assertEqual(formatted, self.bridge.format_legacy(again.document.declarations[0]))

    def test_migrator_is_explicit_and_separate_from_formatter(self) -> None:
        result, declaration = self._one('migration V2 from "1" to "2" {}\n')
        self.assertTrue(result.ok)
        self.assertEqual(
            'migration V2(fromVersion: "1", toVersion: "2") {}\n',
            self.bridge.migrate_to_canonical_preview(declaration),
        )
        self.assertNotEqual(
            self.bridge.format_legacy(declaration),
            self.bridge.migrate_to_canonical_preview(declaration),
        )

    def test_entity_canonical_preview_uses_explicit_field_slot(self) -> None:
        result, declaration = self._one(
            """entity User {
  id: uuid required
}
"""
        )
        self.assertTrue(result.ok)
        self.assertEqual(
            """entity User {
  field id: uuid required
}
""",
            self.bridge.migrate_to_canonical_preview(declaration),
        )

    def test_literal_and_expression_modes_remain_distinct(self) -> None:
        migration_result, migration = self._one('migration V2 from "1" to "2" {}\n')
        query_result, query = self._one(
            """query getPet() -> Pet {
  read: petById
}
"""
        )
        self.assertTrue(migration_result.ok)
        self.assertTrue(query_result.ok)
        self.assertEqual(["literal", "literal"], [item.value_mode for item in migration.header_args])
        self.assertEqual("expression", query.body_slots[0].value_mode)

    def test_semantic_hash_ignores_parser_locations_and_whitespace(self) -> None:
        first = self.bridge.normalize_text('migration V2 from "1" to "2" {}\n')
        second = self.bridge.normalize_text('\n\nmigration V2   from "1"   to "2" {}\n')
        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(
            first.document.declarations[0].semantic_hash(),
            second.document.declarations[0].semantic_hash(),
        )


if __name__ == "__main__":
    unittest.main()
