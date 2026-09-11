#!/usr/bin/env python3
"""M10.1 production-integration parity and diagnostic regressions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_language_surface import TypeRef
from tools.compiler_language_surface_integration import normalize_compiler_analysis
from tools.compiler_summary import summarize_project


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

    def test_production_semantic_hash_ignores_source_locations_and_whitespace(self) -> None:
        first = normalize_compiler_analysis(self._analysis(_PROJECT))
        second = normalize_compiler_analysis(
            self._analysis("\n\n" + _PROJECT.replace("petId: Pet.id?", "petId:   Pet.id?"))
        )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(first.semantic_hash(), second.semantic_hash())
        self.assertEqual(first.semantic_json(), second.semantic_json())

    def test_existing_summary_is_a_real_downstream_semantic_hash_consumer(self) -> None:
        analysis = self._analysis(_PROJECT)
        surface = normalize_compiler_analysis(analysis)
        payload = summarize_project(analysis).to_json()

        self.assertEqual(surface.semantic_hash(), payload["languageSurface"]["semanticHash"])
        self.assertEqual(len(surface.declarations), payload["languageSurface"]["declarationCount"])
        self.assertTrue(payload["languageSurface"]["ok"])
        self.assertEqual([], payload["languageSurface"]["diagnosticCodes"])

    def test_legacy_ref_projection_remains_fail_closed_until_core_typechecker_accepts_it(self) -> None:
        source = _PROJECT.replace("Pet.id?", "ref Pet.id?")
        surface = normalize_compiler_analysis(self._analysis(source))

        self.assertFalse(surface.ok)
        self.assertIn("AIDL-T001", [issue.code for issue in surface.type_issues])
        owner = next(item for item in surface.declarations if item.name == "Owner")
        pet_id = owner.body_slots[0].value
        self.assertEqual("reference", pet_id.kind)
        self.assertEqual("Pet", pet_id.target)
        self.assertEqual("id", pet_id.projection)
        self.assertEqual("uuid", pet_id.resolved_type)

    def test_unresolved_projection_has_stable_m10_1_diagnostic(self) -> None:
        source = _PROJECT.replace("Pet.id?", "Missing.id?")
        surface = normalize_compiler_analysis(self._analysis(source))

        self.assertFalse(surface.ok)
        self.assertIn("AIDL-N012", [item.code for item in surface.diagnostics])

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
