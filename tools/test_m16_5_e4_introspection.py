from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

import tools.m16_5_e4_introspection as e4
from tools.m16_5_e4_introspection import CompilerSchemaService, SchemaLookupError, SchemaRef

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "fixtures/m16-5/e4-introspection-cases.json").read_text())


class E4IntrospectionTests(unittest.TestCase):
    def setUp(self):
        self.service = CompilerSchemaService()
        self.ref = self.service.schema_ref()

    def test_schema_identity_is_exact_deterministic_and_qualified(self):
        self.assertEqual(self.ref.schema_id, CASES["schema_id"])
        self.assertEqual(self.ref.semantic_version, CASES["schema_version"])
        self.assertRegex(self.ref.content_fingerprint, r"^sha256:[0-9a-f]{64}$")
        e4.build_catalog.cache_clear()
        self.assertEqual(self.ref, self.service.schema_ref())
        self.assertEqual(e4.build_catalog().source_base_commit, CASES["source_base_commit"])

    def test_unknown_stale_or_mismatched_schema_fails_closed(self):
        bad_refs = (
            (SchemaRef("urn:aidl:schema:meta:other", self.ref.semantic_version, self.ref.content_fingerprint), "unknown-schema-id"),
            (SchemaRef(self.ref.schema_id, "0.0.9-stale", self.ref.content_fingerprint), "stale-schema-version"),
            (SchemaRef(self.ref.schema_id, self.ref.semantic_version, "sha256:" + "0" * 64), "fingerprint-mismatch"),
        )
        for bad_ref, reason in bad_refs:
            with self.subTest(reason=reason), self.assertRaises(SchemaLookupError) as caught:
                self.service.declaration_kinds(bad_ref)
            self.assertEqual(caught.exception.reason, reason)

    def test_representative_app_core_backend_sync_clients_discover_shapes(self):
        for case in CASES["representative_clients"]:
            with self.subTest(kind=case["kind"]):
                shape = self.service.declaration(self.ref, case["kind"])
                self.assertEqual(shape.family, case["family"])
                self.assertEqual([item.argument_id for item in shape.header_arguments], case["header_arguments"])
                self.assertEqual([item.slot_id for item in shape.body_slots], case["body_slots"])
                self.assertTrue(shape.documentation.startswith("docs/06-grammar.md#"))

    def test_entity_field_shape_exposes_keywordless_entry_and_all_modifiers(self):
        entity = self.service.declaration(self.ref, "entity")
        field = next(slot for slot in entity.body_slots if slot.slot_id == "field")
        self.assertEqual(field.visible_tokens, ())
        self.assertEqual(field.name_shape, "identifier")
        self.assertEqual(field.value_shape, "type")
        modifiers = self.service.modifiers(self.ref, field.modifiers)
        self.assertEqual(
            [item.modifier_id for item in modifiers],
            ["required", "primary", "generated", "clientGenerated", "immutable", "mutable", "sensitive", "unique", "concurrencyToken", "default", "onDelete", "via"],
        )
        self.assertEqual(next(item for item in modifiers if item.modifier_id == "default").value_shape, "expression")

    def test_sync_exports_current_compound_forms_not_e3_candidate_syntax(self):
        sync = self.service.declaration(self.ref, "sync")
        self.assertEqual(sync.header_arguments[0].visible_tokens, ("for",))
        changes = next(slot for slot in sync.body_slots if slot.slot_id == "changes")
        self.assertEqual(changes.visible_tokens, ("changes",))
        self.assertEqual(self.service.value_shape(self.ref, changes.value_shape).syntax, "to typeName via outbox")
        legal = self.service.declaration_kinds(self.ref)
        for candidate in CASES["candidate_kinds_that_must_not_be_exported_as_legal"]:
            self.assertNotIn(candidate, legal)

    def test_every_slot_and_modifier_value_reference_resolves(self):
        catalog = e4.require_schema(self.ref)
        for declaration in catalog.declarations:
            for slot in declaration.body_slots:
                if slot.value_shape is not None:
                    self.service.value_shape(self.ref, slot.value_shape)
                for modifier in self.service.modifiers(self.ref, slot.modifiers):
                    if modifier.value_shape is not None:
                        self.service.value_shape(self.ref, modifier.value_shape)
        for declaration in catalog.declarations:
            for argument in declaration.header_arguments:
                self.service.value_shape(self.ref, argument.value_shape)

    def test_nesting_is_discoverable_without_client_side_reconstruction(self):
        service = self.service.declaration(self.ref, "service")
        reliability = next(slot for slot in service.body_slots if slot.slot_id == "reliability")
        self.assertEqual(reliability.nested_schema, "profileProperty")
        sync = self.service.declaration(self.ref, "sync")
        self.assertEqual(next(slot for slot in sync.body_slots if slot.slot_id == "operationLog").nested_schema, "profileProperty")
        self.assertEqual(next(slot for slot in sync.body_slots if slot.slot_id == "conflict").nested_schema, "conflictRule")

    def test_generic_profile_ui_and_test_sublanguages_are_mechanically_discoverable(self):
        for name in CASES["generic_sublanguages"]:
            with self.subTest(name=name):
                schema = self.service.sublanguage(self.ref, name)
                self.assertTrue(schema.closed_vocabulary)
                self.assertTrue(schema.vocabulary_authority.startswith("compiler-owned"))
                self.assertTrue(schema.alternatives)
                self.assertTrue(schema.documentation.startswith("docs/06-grammar.md#"))
        self.assertTrue(self.service.sublanguage(self.ref, "profileProperty").recursive)
        self.assertEqual([x.alternative_id for x in self.service.sublanguage(self.ref, "testStatement").alternatives], ["leaf", "block"])

    def test_catalog_is_read_only_and_has_no_mutation_api(self):
        catalog = e4.require_schema(self.ref)
        self.assertIsInstance(catalog.declarations, tuple)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            catalog.schema_ref.semantic_version = "mutated"  # type: ignore[misc]
        self.assertFalse(hasattr(self.service, "register"))
        self.assertFalse(hasattr(self.service, "update"))

    def test_export_is_deterministic_and_self_describing(self):
        first = self.service.export(self.ref)
        second = self.service.export(self.ref)
        self.assertEqual(first, second)
        self.assertEqual(first["schema_ref"]["content_fingerprint"], self.ref.content_fingerprint)
        self.assertEqual(first["source_grammar_blob_sha"], e4.GRAMMAR_BLOB_SHA)
        encoded = json.dumps(first, sort_keys=True, separators=(",", ":"))
        self.assertEqual(encoded, json.dumps(second, sort_keys=True, separators=(",", ":")))
        self.assertTrue(first["coverage"])
        self.assertTrue(first["omissions"])

    def test_unknown_kind_sublanguage_value_and_modifier_fail_explicitly(self):
        calls = (
            lambda: self.service.declaration(self.ref, "mystery"),
            lambda: self.service.sublanguage(self.ref, "mystery"),
            lambda: self.service.value_shape(self.ref, "mystery"),
            lambda: self.service.modifiers(self.ref, ["mystery"]),
        )
        for call in calls:
            with self.assertRaises(SchemaLookupError):
                call()

    def test_prototype_does_not_import_production_parser_or_e3_parser(self):
        source = pathlib.Path(e4.__file__).read_text()
        self.assertNotIn("tools.aidl_parser", source)
        self.assertNotIn("m16_5_e3_prototype", source)
        self.assertNotIn("parse_candidate", source)


if __name__ == "__main__":
    unittest.main()
