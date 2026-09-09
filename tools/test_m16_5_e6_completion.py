from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

import tools.m16_5_e4_introspection as e4
import tools.m16_5_e5_migration as e5
import tools.m16_5_e6_completion as e6
from tools.m16_5_e6_completion import (
    CompletionContextError,
    CompletionSet,
    CompletionUnavailable,
    CurrentCompletionContext,
    E5MigrationCompletionContext,
    ExperimentalCompletionConsumer,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "fixtures/m16-5/e6-completion-cases.json").read_text())


class E6CompletionTests(unittest.TestCase):
    def setUp(self):
        self.consumer = ExperimentalCompletionConsumer()
        self.ref = self.consumer.compiler_schema_ref()
        self.current = CurrentCompletionContext(self.ref)

    def migration_context(self, source: str, *, source_version: str = e5.OLD_VERSION) -> E5MigrationCompletionContext:
        data = CASES["e5_context"]
        source_is_old = source_version == e5.OLD_VERSION
        return E5MigrationCompletionContext(
            old_schema_id=data["old_schema_id"],
            old_version=data["old_version"],
            old_schema_fingerprint=data["old_schema_fingerprint"],
            target_schema_id=data["target_schema_id"],
            target_version=data["target_version"],
            target_schema_fingerprint=data["target_schema_fingerprint"],
            source_schema_id=data["old_schema_id"] if source_is_old else data["target_schema_id"],
            source_version=source_version,
            source_schema_fingerprint=data["old_schema_fingerprint"] if source_is_old else data["target_schema_fingerprint"],
            expected_source_fingerprint=e5.source_fingerprint(source),
        )

    def test_exact_e4_schema_tuple_is_the_only_current_context(self):
        expected = CASES["e4_schema"]
        self.assertEqual(self.ref.schema_id, expected["schema_id"])
        self.assertEqual(self.ref.semantic_version, expected["schema_version"])
        self.assertEqual(self.ref.content_fingerprint, expected["schema_fingerprint"])

    def test_representative_app_core_backend_sync_completion_is_schema_driven(self):
        for case in CASES["representative_completion"]:
            with self.subTest(kind=case["kind"]):
                starters = self.consumer.declaration_starters(self.current, family=case["family"])
                self.assertEqual([item.insert_text for item in starters.items], [case["starter"]])
                body = self.consumer.body_slots(self.current, case["kind"])
                self.assertEqual([item.metadata_id for item in body.items], case["body_slot_ids"])
                self.assertEqual(body.semantic_order, "preserve")
                self.assertTrue(all(item.authority == "e4-compiler-schema" for item in body.items))
                self.assertTrue(all(item.documentation for item in body.items))

    def test_sync_header_and_value_completion_come_from_e4_metadata(self):
        sync_case = next(item for item in CASES["representative_completion"] if item["kind"] == "sync")
        header = self.consumer.header_arguments(self.current, "sync")
        self.assertEqual([item.insert_text for item in header.items], sync_case["header_tokens"])
        self.assertEqual(header.items[0].expected_value_shape, "type")
        values = self.consumer.value_candidates(self.current, "sync-mode")
        self.assertIsInstance(values, CompletionSet)
        assert isinstance(values, CompletionSet)
        self.assertEqual([item.insert_text for item in values.items], sync_case["mode_values"])

    def test_entity_modifier_completion_uses_compiler_modifier_metadata(self):
        result = self.consumer.modifier_candidates(self.current, "entity", "field")
        self.assertEqual([item.metadata_id for item in result.items], CASES["entity_field_modifiers"])
        default = next(item for item in result.items if item.metadata_id == "default")
        self.assertEqual(default.expected_value_shape, "expression")
        self.assertEqual(default.authority, "e4-compiler-schema")

    def test_keywordless_field_does_not_invent_an_insert_template(self):
        body = self.consumer.body_slots(self.current, "entity")
        field = next(item for item in body.items if item.metadata_id == "field")
        self.assertIsNone(field.insert_text)
        self.assertEqual(field.expected_name_shape, "identifier")
        self.assertEqual(field.expected_value_shape, "type")

    def test_order_is_preserved_when_e4_does_not_mark_unordered(self):
        for case in CASES["representative_completion"]:
            body = self.consumer.body_slots(self.current, case["kind"])
            self.assertEqual(body.semantic_order, "preserve")
            self.assertEqual([item.metadata_id for item in body.items], case["body_slot_ids"])

    def test_nested_and_generic_sublanguages_are_structurally_discoverable_but_closed(self):
        nested = self.consumer.nested_structure(self.current, "service", "reliability")
        self.assertIsInstance(nested, CompletionSet)
        assert isinstance(nested, CompletionSet)
        self.assertTrue(nested.items)
        self.assertTrue(all(item.insert_text is None for item in nested.items))
        for name in CASES["generic_sublanguages"]:
            with self.subTest(name=name):
                structure = self.consumer.sublanguage_structure(self.current, name)
                self.assertTrue(structure.items)
                self.assertTrue(all(item.insert_text is None for item in structure.items))
                vocab = self.consumer.sublanguage_vocabulary(self.current, name)
                self.assertEqual(vocab.reason, "closed-vocabulary-not-exported")
                self.assertIn("compiler-owned", vocab.detail)

    def test_unknown_or_stale_e4_metadata_fails_closed(self):
        stale = CurrentCompletionContext(
            e4.SchemaRef(self.ref.schema_id, "0.0.0-stale", self.ref.content_fingerprint)
        )
        with self.assertRaises(e4.SchemaLookupError):
            self.consumer.declaration_starters(stale)
        with self.assertRaises(e4.SchemaLookupError):
            self.consumer.body_slots(self.current, "unknown")
        with self.assertRaises(CompletionContextError) as slot_error:
            self.consumer.modifier_candidates(self.current, "entity", "unknown")
        self.assertEqual(slot_error.exception.reason, "unknown-body-slot")
        with self.assertRaises(e4.SchemaLookupError):
            self.consumer.value_candidates(self.current, "unknown")
        with self.assertRaises(e4.SchemaLookupError):
            self.consumer.sublanguage_structure(self.current, "unknown")

    def test_open_value_vocabulary_is_not_reconstructed_client_side(self):
        result = self.consumer.value_candidates(self.current, "identifier")
        self.assertIsInstance(result, CompletionUnavailable)
        assert isinstance(result, CompletionUnavailable)
        self.assertEqual(result.reason, "compiler-value-vocabulary-not-exported")

    def test_current_completion_never_emits_e5_candidate_spelling(self):
        sync = self.consumer.body_slots(self.current, "sync")
        changes = next(item for item in sync.items if item.metadata_id == "changes")
        self.assertEqual(changes.insert_text, "changes")
        self.assertNotEqual(changes.insert_text, "changes:")
        self.assertEqual(changes.expected_value_shape, "sync-changes-outbox")
        shape = e4.CompilerSchemaService().value_shape(self.ref, changes.expected_value_shape)
        self.assertEqual(shape.syntax, "to typeName via outbox")

    def test_supported_candidate_suggestions_are_exact_e5_dry_run_replacements(self):
        for case in CASES["migration_supported"]:
            source = case["source"]
            offset = source.index(case["anchor_text"]) + 1
            result = self.consumer.migration_completion(source, offset, self.migration_context(source))
            with self.subTest(row=case["id"]):
                self.assertIsInstance(result, CompletionSet)
                assert isinstance(result, CompletionSet)
                self.assertEqual(result.context, "explicit-e5-target")
                self.assertEqual(len(result.items), 1)
                item = result.items[0]
                self.assertEqual(item.metadata_id, case["id"])
                self.assertEqual(item.insert_text, case["expected_replacement"])
                self.assertEqual(item.authority, "e5-migrator")

    def test_e5_context_is_explicit_exact_and_has_no_latest_or_fallback(self):
        source = CASES["migration_supported"][0]["source"]
        offset = source.index(CASES["migration_supported"][0]["anchor_text"]) + 1
        good = self.migration_context(source)
        bad_contexts = (
            dataclasses.replace(good, old_schema_id="urn:aidl:schema:language:other"),
            dataclasses.replace(good, target_version="latest"),
            dataclasses.replace(good, target_schema_fingerprint="sha256:" + "0" * 64),
            dataclasses.replace(good, source_schema_id=e5.TARGET_SCHEMA_ID),
            dataclasses.replace(good, expected_source_fingerprint="sha256:" + "0" * 64),
        )
        for context in bad_contexts:
            with self.subTest(context=context), self.assertRaises(CompletionContextError):
                self.consumer.migration_completion(source, offset, context)

    def test_e5_fail_closed_gaps_are_unavailable_not_invented(self):
        for case in CASES["migration_unavailable"]:
            source = case["source"]
            offset = source.index(case["anchor_text"]) + 1
            result = self.consumer.migration_completion(source, offset, self.migration_context(source))
            with self.subTest(case=case["id"]):
                self.assertIsInstance(result, CompletionUnavailable)
                assert isinstance(result, CompletionUnavailable)
                self.assertTrue(result.reason.startswith(case["reason_prefix"]), result)
                self.assertEqual(result.authority, "e5-migrator")

    def test_explicit_target_version_is_noop_and_not_sniffed_as_current(self):
        source = (
            "client BillingClient {\n"
            "  service: BillingService\n"
            "  call create {\n"
            "    timeout 30s\n"
            "  }\n"
            "}\n"
        )
        context = self.migration_context(source, source_version=e5.TARGET_VERSION)
        result = self.consumer.migration_completion(source, source.index("service:"), context)
        self.assertIsInstance(result, CompletionUnavailable)
        assert isinstance(result, CompletionUnavailable)
        self.assertEqual(result.reason, "e5-no-modeled-migration-edit")

    def test_e6_source_contains_no_second_language_schema_tables(self):
        source = pathlib.Path(e6.__file__).read_text()
        self.assertIn("m16_5_e4_introspection", source)
        self.assertIn("m16_5_e5_migration", source)
        self.assertNotIn("ROW_IDS =", source)
        self.assertNotIn("RULES =", source)
        self.assertNotIn("serverAuthoritative", source)
        self.assertNotIn("projection-relationship", source)
        self.assertNotIn("client-target", source)
        self.assertNotIn("profileProperty\",", source)


if __name__ == "__main__":
    unittest.main()
