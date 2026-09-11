#!/usr/bin/env python3
"""M10.1 production-integration parity and diagnostic regressions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.compiler_language_surface import Declaration, TypeRef
from tools.compiler_language_surface_integration import normalize_compiler_analysis
from tools.compiler_summary import summarize_project
from tools.compiler_typecheck import resolve_reference
from tools.test_aidl_ir import _MINIMAL_PROJECT


_PROJECT = """module demo
entity Pet {
  id: uuid required
}
entity Owner {
  petId: Pet.id?
}
enum State { active, disabled = \"off\" }
opaque Token = uuid
"""


class M101ProductionIntegrationTest(unittest.TestCase):
    def _analysis(self, source_text: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "model.aidl"
        source.write_text(source_text, encoding="utf-8")
        return load_compiler_analysis([source])

    def test_real_project_nodes_normalize_with_typechecker_projection_evidence(self) -> None:
        analysis = self._analysis(_PROJECT)
        surface = normalize_compiler_analysis(analysis)

        self.assertTrue(surface.ok, (surface.diagnostics, surface.type_issues))
        self.assertEqual(4, len(surface.declarations))
        owner = next(item for item in surface.declarations if item.name == "Owner")
        pet_id = owner.body_slots[0].value
        self.assertIsInstance(pet_id, TypeRef)
        self.assertEqual("reference", pet_id.kind)
        self.assertEqual("Pet", pet_id.target)
        self.assertEqual("id", pet_id.projection)
        self.assertEqual("uuid", pet_id.resolved_type)
        self.assertTrue(pet_id.optional)

    def test_legacy_ref_projection_is_accepted_by_core_typechecker_and_keeps_optionality(self) -> None:
        source = _PROJECT.replace("Pet.id?", "ref Pet.id?")
        analysis = self._analysis(source)
        surface = normalize_compiler_analysis(analysis)

        self.assertTrue(surface.ok, (surface.diagnostics, surface.type_issues))
        self.assertNotIn("AIDL-T001", [issue.code for issue in surface.type_issues])
        owner_source = next(
            item for item in analysis.project.declaration_names if item.declaration.name == "Owner"
        )
        resolution = resolve_reference(analysis.project, owner_source, "Pet.id")
        self.assertIsNotNone(resolution)
        assert resolution is not None
        self.assertEqual("projection", resolution.kind)
        self.assertEqual("demo.Pet", resolution.target)
        self.assertEqual("id", resolution.projection)
        self.assertEqual("uuid", resolution.projected_type)

        owner = next(item for item in surface.declarations if item.name == "Owner")
        pet_id = owner.body_slots[0].value
        self.assertEqual("reference", pet_id.kind)
        self.assertEqual("Pet", pet_id.target)
        self.assertEqual("id", pet_id.projection)
        self.assertEqual("uuid", pet_id.resolved_type)
        self.assertTrue(pet_id.optional)

    def test_qualified_entity_reference_keeps_nominal_meaning(self) -> None:
        analysis = self._analysis(
            """module demo
entity Pet { id: uuid required }
entity Owner { pet: ref demo.Pet }
"""
        )
        surface = normalize_compiler_analysis(analysis)
        owner_source = next(
            item for item in analysis.project.declaration_names if item.declaration.name == "Owner"
        )
        resolution = resolve_reference(analysis.project, owner_source, "demo.Pet")

        self.assertTrue(surface.ok, (surface.diagnostics, surface.type_issues))
        self.assertIsNotNone(resolution)
        assert resolution is not None
        self.assertEqual("entity", resolution.kind)
        self.assertEqual("demo.Pet", resolution.target)
        owner = next(item for item in surface.declarations if item.name == "Owner")
        pet = owner.body_slots[0].value
        self.assertEqual("reference", pet.kind)
        self.assertEqual("demo.Pet", pet.target)
        self.assertIsNone(pet.projection)
        self.assertIsNone(pet.resolved_type)

    def test_unresolved_projection_has_stable_m10_1_diagnostic(self) -> None:
        source = _PROJECT.replace("Pet.id?", "ref Missing.id?")
        surface = normalize_compiler_analysis(self._analysis(source))

        self.assertFalse(surface.ok)
        self.assertIn("AIDL-N012", [item.code for item in surface.diagnostics])
        self.assertIn("AIDL-T001", [issue.code for issue in surface.type_issues])

    def test_ambiguous_projection_fails_closed(self) -> None:
        surface = normalize_compiler_analysis(
            self._analysis(
                """module demo
entity Pet { id: uuid }
entity Pet { id: uuid }
entity Owner { pet: ref Pet.id }
"""
            )
        )
        self.assertFalse(surface.ok)
        self.assertIn("AIDL-N012", [item.code for item in surface.diagnostics])
        self.assertIn("AIDL-T001", [issue.code for issue in surface.type_issues])

    def test_lossless_query_mutation_app_and_modifier_evidence_are_integrated(self) -> None:
        source = """module demo
entity Pet { id: uuid required }
@publicReason("public lookup")
query getPet() -> Pet {
  read: petById
}
@publicReason("public update")
mutation updatePet() -> Pet {}
app Store {
  profile core version 1
}
"""
        surface = normalize_compiler_analysis(self._analysis(source))

        self.assertTrue(surface.ok, (surface.diagnostics, surface.type_issues))
        by_name = {item.name: item for item in surface.declarations}
        query = by_name["getPet"]
        mutation = by_name["updatePet"]
        app = by_name["Store"]
        self.assertEqual("literal", query.modifiers[0].argument_mode)
        self.assertEqual(("public lookup",), query.modifiers[0].args)
        self.assertEqual("expression", query.body_slots[0].value_mode)
        self.assertEqual("petById", query.body_slots[0].value)
        self.assertEqual("literal", mutation.modifiers[0].argument_mode)
        self.assertEqual("profile", app.body_slots[0].slot_id)

    def test_modifier_target_arity_and_literal_value_mode_fail_closed(self) -> None:
        wrong_target = normalize_compiler_analysis(
            self._analysis(
                """module demo
@publicReason("why")
app Store { profile core version 1 }
"""
            )
        )
        wrong_arity = normalize_compiler_analysis(
            self._analysis(
                """module demo
@publicReason()
query getPet() -> string { read: value }
"""
            )
        )
        wrong_mode = normalize_compiler_analysis(
            self._analysis(
                """module demo
@publicReason(reason)
query getPet() -> string { read: value }
"""
            )
        )

        self.assertIn("AIDL-N008", [item.code for item in wrong_target.diagnostics])
        self.assertIn("AIDL-N009", [item.code for item in wrong_arity.diagnostics])
        self.assertIn("AIDL-N014", [item.code for item in wrong_mode.diagnostics])
        self.assertFalse(wrong_target.ok)
        self.assertFalse(wrong_arity.ok)
        self.assertFalse(wrong_mode.ok)

    def test_non_lossless_operation_parameters_are_explicitly_not_integrated(self) -> None:
        surface = normalize_compiler_analysis(
            self._analysis(
                """module demo
query getPet(id: uuid) -> string { read: value }
"""
            )
        )
        self.assertFalse(surface.ok)
        self.assertIn("AIDL-N013", [item.code for item in surface.diagnostics])
        self.assertNotIn("getPet", [item.name for item in surface.declarations])

    def test_production_semantic_hash_ignores_source_locations_and_whitespace(self) -> None:
        first = normalize_compiler_analysis(self._analysis(_PROJECT))
        second = normalize_compiler_analysis(
            self._analysis("\n\n" + _PROJECT.replace("petId: Pet.id?", "petId:   Pet.id?"))
        )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(first.semantic_hash(), second.semantic_hash())
        self.assertEqual(first.semantic_json(), second.semantic_json())
        self.assertEqual(
            [(item.code, item.message) for item in first.diagnostics],
            [(item.code, item.message) for item in second.diagnostics],
        )

    def test_existing_summary_is_a_real_downstream_semantic_hash_consumer(self) -> None:
        analysis = self._analysis(_PROJECT)
        surface = normalize_compiler_analysis(analysis)
        summary = summarize_project(analysis)
        payload = summary.to_json()

        self.assertEqual(surface.semantic_hash(), summary.language_surface_semantic_hash)
        self.assertEqual(len(surface.declarations), summary.language_surface_declaration_count)
        self.assertTrue(summary.language_surface_ok)
        self.assertEqual((), summary.language_surface_diagnostic_codes)
        self.assertNotIn("languageSurface", payload)

    def test_legacy_alias_normalization_matches_independent_canonical_facts(self) -> None:
        surface = normalize_compiler_analysis(self._analysis(_PROJECT))
        token = next(item for item in surface.declarations if item.name == "Token")
        canonical = Declaration(
            kind="alias",
            name="Token",
            name_policy="required",
            exported=False,
            facts={"opacity": True, "aliased_type": TypeRef("scalar", name="uuid")},
        )

        self.assertEqual(canonical.semantic_hash(), token.semantic_hash())

    def test_ir_diagnostics_and_m10_1_hash_are_source_location_independent(self) -> None:
        first_analysis = self._analysis(_MINIMAL_PROJECT)
        second_analysis = self._analysis("\n\n" + _MINIMAL_PROJECT)
        first_surface = normalize_compiler_analysis(first_analysis)
        second_surface = normalize_compiler_analysis(second_analysis)
        first_ir = build_canonical_ir(first_analysis)
        second_ir = build_canonical_ir(second_analysis)

        self.assertEqual(
            [diagnostic.code.value for diagnostic in first_analysis.diagnostics],
            [diagnostic.code.value for diagnostic in second_analysis.diagnostics],
        )
        self.assertEqual(first_ir["semanticHash"], second_ir["semanticHash"])
        self.assertEqual(first_surface.semantic_hash(), second_surface.semantic_hash())

    def test_same_version_formatter_and_explicit_migrator_remain_separate(self) -> None:
        surface = normalize_compiler_analysis(self._analysis(_PROJECT))
        token = next(item for item in surface.declarations if item.name == "Token")

        from tools.compiler_language_surface import LanguageSurfaceBridge, UnsupportedMigration

        bridge = LanguageSurfaceBridge()
        self.assertEqual("opaque Token = uuid\n", bridge.format_legacy(token))
        with self.assertRaises(UnsupportedMigration):
            bridge.migrate_to_canonical_preview(token)


if __name__ == "__main__":
    unittest.main()
