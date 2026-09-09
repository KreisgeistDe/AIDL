from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

import tools.m16_5_e4_introspection as e4
import tools.m16_5_e5_migration as e5
import tools.m16_5_e7_diagnostics as e7
from tools.m16_5_e7_diagnostics import (
    CompilerSemanticIntent,
    CurrentDiagnosticsContext,
    DiagnosticUnavailable,
    DiagnosticsContextError,
    E5MigrationDiagnosticsContext,
    ExperimentalDiagnosticsConsumer,
    SemanticDiagnosticProjection,
    StructuralDiagnostic,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "fixtures/m16-5/e7-diagnostics-cases.json").read_text())


class E7DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.consumer = ExperimentalDiagnosticsConsumer()
        self.ref = self.consumer.compiler_schema_ref()
        self.current = CurrentDiagnosticsContext(self.ref)

    def migration_context(
        self,
        source: str,
        *,
        state: str = "target",
        source_version: str = e5.OLD_VERSION,
    ) -> E5MigrationDiagnosticsContext:
        data = CASES["e5_context"]
        source_is_old = source_version == e5.OLD_VERSION
        return E5MigrationDiagnosticsContext(
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
            language_state=state,
        )

    def test_exact_e4_schema_tuple_is_the_only_current_context(self):
        expected = CASES["e4_schema"]
        self.assertEqual(self.ref.schema_id, expected["schema_id"])
        self.assertEqual(self.ref.semantic_version, expected["schema_version"])
        self.assertEqual(self.ref.content_fingerprint, expected["schema_fingerprint"])

    def test_representative_app_core_backend_sync_structural_diagnostics_are_e4_driven(self):
        app = CASES["structural"]["app_unknown_slot"]
        start = app["source"].index(app["anchor"])
        diagnostic = self.consumer.unknown_body_slot(
            app["source"], start, start + len(app["anchor"]), self.current, app["kind"], app["observed_slot"]
        )
        self.assertIsInstance(diagnostic, StructuralDiagnostic)
        assert isinstance(diagnostic, StructuralDiagnostic)
        self.assertEqual(diagnostic.code, app["code"])
        self.assertIn("profile", diagnostic.expected or "")

        core = CASES["structural"]["entity_bad_modifier"]
        start = core["source"].index(core["anchor"])
        diagnostic = self.consumer.invalid_modifier(
            core["source"], start, start + len(core["anchor"]), self.current,
            core["kind"], core["slot"], core["modifier"]
        )
        self.assertIsInstance(diagnostic, StructuralDiagnostic)
        assert isinstance(diagnostic, StructuralDiagnostic)
        self.assertEqual(diagnostic.code, core["code"])
        self.assertIn("required", diagnostic.expected or "")

        backend = CASES["structural"]["service_bad_nesting"]
        start = backend["source"].index(backend["anchor"])
        diagnostic = self.consumer.invalid_nesting(
            backend["source"], start, start + len(backend["anchor"]), self.current,
            backend["kind"], backend["slot"], backend["observed_nested_schema"]
        )
        self.assertIsInstance(diagnostic, StructuralDiagnostic)
        assert isinstance(diagnostic, StructuralDiagnostic)
        self.assertEqual(diagnostic.expected, backend["expected_nested_schema"])

        sync = CASES["structural"]["sync_bad_mode"]
        start = sync["source"].index(sync["anchor"])
        diagnostic = self.consumer.wrong_closed_value(
            sync["source"], start, start + len(sync["anchor"]), self.current,
            sync["shape"], sync["observed"]
        )
        self.assertIsInstance(diagnostic, StructuralDiagnostic)
        assert isinstance(diagnostic, StructuralDiagnostic)
        self.assertEqual(diagnostic.code, sync["code"])
        self.assertEqual(diagnostic.expected, " | ".join(sync["expected"]))

    def test_known_structural_facts_produce_no_diagnostic(self):
        source = "app Demo {\n  profile web version 1\n}\n"
        start = source.index("profile")
        self.assertIsNone(self.consumer.unknown_body_slot(source, start, start + 7, self.current, "app", "profile"))
        source = "entity Customer {\n  id: UUID required\n}\n"
        start = source.index("required")
        self.assertIsNone(self.consumer.invalid_modifier(source, start, start + 8, self.current, "entity", "field", "required"))
        source = "sync Mobile for Customer {\n  mode replicated\n}\n"
        start = source.index("replicated")
        self.assertIsNone(self.consumer.wrong_closed_value(source, start, start + 10, self.current, "sync-mode", "replicated"))
        source = "service Billing {\n  reliability {\n  }\n}\n"
        start = source.index("reliability")
        self.assertIsNone(self.consumer.invalid_nesting(source, start, start + 11, self.current, "service", "reliability", "profileProperty"))

    def test_open_value_and_generic_vocabularies_remain_unavailable(self):
        source = "app Demo {\n  defaultDeployment anything\n}\n"
        start = source.index("anything")
        result = self.consumer.wrong_closed_value(source, start, start + 8, self.current, "identifier", "anything")
        self.assertIsInstance(result, DiagnosticUnavailable)
        assert isinstance(result, DiagnosticUnavailable)
        self.assertEqual(result.reason, "value-validation-not-exported")
        for name in CASES["generic_sublanguages"]:
            with self.subTest(name=name):
                unavailable = self.consumer.sublanguage_vocabulary(self.current, name)
                self.assertEqual(unavailable.reason, "closed-vocabulary-not-exported")
                self.assertIn("compiler-owned", unavailable.detail)

    def test_unknown_and_stale_metadata_fail_closed_as_structural_context_mismatch(self):
        stale = CurrentDiagnosticsContext(e4.SchemaRef(self.ref.schema_id, "latest", self.ref.content_fingerprint))
        source = "app Demo {\n}\n"
        with self.assertRaises(DiagnosticsContextError) as stale_error:
            self.consumer.unknown_body_slot(source, 0, 3, stale, "app", "mystery")
        self.assertEqual(stale_error.exception.code, "AIDL-S008")
        with self.assertRaises(DiagnosticsContextError) as unknown_decl:
            self.consumer.unknown_body_slot(source, 0, 3, self.current, "unknown", "mystery")
        self.assertEqual(unknown_decl.exception.code, "AIDL-S008")
        with self.assertRaises(DiagnosticsContextError):
            self.consumer.wrong_closed_value(source, 0, 3, self.current, "unknown-shape", "x")
        with self.assertRaises(DiagnosticsContextError):
            self.consumer.sublanguage_vocabulary(self.current, "unknown-sublanguage")

    def test_source_locations_and_e7_ordering_are_deterministic(self):
        source = "app Demo {\n  first Bad\n  second Bad\n}\n"
        first_start = source.index("first")
        second_start = source.index("second")
        first = self.consumer.unknown_body_slot(source, first_start, first_start + 5, self.current, "app", "first")
        second = self.consumer.unknown_body_slot(source, second_start, second_start + 6, self.current, "app", "second")
        assert isinstance(first, StructuralDiagnostic) and isinstance(second, StructuralDiagnostic)
        ordered = self.consumer.order((second, first))
        self.assertEqual([item.location.start for item in ordered], [first_start, second_start])
        self.assertEqual(ordered[0].location.line, 2)
        self.assertEqual(ordered[0].location.column, 3)
        self.assertEqual(self.consumer.order(ordered), ordered)

    def test_structural_diagnostics_never_claim_compatibility_or_write_authority(self):
        case = CASES["structural"]["sync_bad_mode"]
        start = case["source"].index(case["anchor"])
        diagnostic = self.consumer.wrong_closed_value(
            case["source"], start, start + len(case["anchor"]), self.current, case["shape"], case["observed"]
        )
        assert isinstance(diagnostic, StructuralDiagnostic)
        self.assertIsNone(diagnostic.compatibility_class)
        self.assertFalse(diagnostic.migration_authorized)
        self.assertEqual(diagnostic.authority, "e4-compiler-schema")

    def test_migration_state_is_explicit_and_separates_legacy_coexistence_and_target(self):
        case = CASES["migration_supported"][0]
        source = case["old"]
        offset = source.index(case["anchor"]) + 1
        self.assertIsNone(self.consumer.migration_diagnostic(source, offset, self.migration_context(source, state="legacy")))
        deprecated = self.consumer.migration_diagnostic(source, offset, self.migration_context(source, state="coexistence"))
        invalid = self.consumer.migration_diagnostic(source, offset, self.migration_context(source, state="target"))
        self.assertIsInstance(deprecated, StructuralDiagnostic)
        self.assertIsInstance(invalid, StructuralDiagnostic)
        assert isinstance(deprecated, StructuralDiagnostic) and isinstance(invalid, StructuralDiagnostic)
        self.assertEqual(deprecated.code, "AIDL-S006")
        self.assertEqual(deprecated.severity, "warning")
        self.assertEqual(invalid.code, "AIDL-S007")
        self.assertEqual(invalid.severity, "error")
        self.assertEqual(deprecated.location, invalid.location)
        self.assertEqual(deprecated.replacement, invalid.replacement)
        self.assertFalse(invalid.migration_authorized)

    def test_target_snapshot_has_no_legacy_migration_diagnostic_under_explicit_target_context(self):
        case = CASES["migration_supported"][0]
        source = case["candidate"]
        context = self.migration_context(source, state="target", source_version=e5.TARGET_VERSION)
        self.assertIsNone(self.consumer.migration_diagnostic(source, source.index("service:"), context))

    def test_migration_context_has_no_latest_fallback_or_source_sniffing(self):
        case = CASES["migration_supported"][0]
        source = case["old"]
        offset = source.index(case["anchor"]) + 1
        good = self.migration_context(source)
        bad_contexts = (
            dataclasses.replace(good, old_schema_id="urn:aidl:schema:language:other"),
            dataclasses.replace(good, target_version="latest"),
            dataclasses.replace(good, target_schema_fingerprint="sha256:" + "0" * 64),
            dataclasses.replace(good, source_schema_id=e5.TARGET_SCHEMA_ID),
            dataclasses.replace(good, expected_source_fingerprint="sha256:" + "0" * 64),
            dataclasses.replace(good, language_state="auto"),
        )
        for context in bad_contexts:
            with self.subTest(context=context), self.assertRaises(DiagnosticsContextError) as error:
                self.consumer.migration_diagnostic(source, offset, context)
            self.assertEqual(error.exception.code, "AIDL-S008")

    def test_fact_complete_old_candidate_pair_preserves_compiler_semantic_intent(self):
        intent = CompilerSemanticIntent(
            code="AIDL-T123",
            phase="semantic",
            severity="error",
            message="reference must resolve to BillingService",
            expected="BillingService",
            documentation="docs/06-grammar.md",
        )
        for case in CASES["migration_supported"]:
            old = case["old"]
            offset = old.index(case["anchor"]) + 1
            result = self.consumer.equivalent_semantic_intent(
                old, case["candidate"], offset, self.migration_context(old), intent
            )
            with self.subTest(row=case["id"]):
                self.assertIsInstance(result, tuple)
                old_diag, new_diag = result
                self.assertIsInstance(old_diag, SemanticDiagnosticProjection)
                self.assertIsInstance(new_diag, SemanticDiagnosticProjection)
                self.assertEqual(old_diag.code, intent.code)
                self.assertEqual(new_diag.code, intent.code)
                self.assertEqual(old_diag.message, new_diag.message)
                self.assertEqual(old_diag.expected, new_diag.expected)
                self.assertEqual(old_diag.source_context, "explicit-e5-old")
                self.assertEqual(new_diag.source_context, "explicit-e5-target")
                self.assertNotEqual(old_diag.location.end, new_diag.location.end)
                self.assertIsNone(old_diag.compatibility_class)
                self.assertFalse(new_diag.migration_authorized)

    def test_semantic_projection_requires_exact_e5_target_snapshot(self):
        case = CASES["migration_supported"][0]
        old = case["old"]
        intent = CompilerSemanticIntent("AIDL-T123", "semantic", "error", "same intent")
        result = self.consumer.equivalent_semantic_intent(
            old,
            case["candidate"] + "// changed\n",
            old.index(case["anchor"]) + 1,
            self.migration_context(old),
            intent,
        )
        self.assertIsInstance(result, DiagnosticUnavailable)
        assert isinstance(result, DiagnosticUnavailable)
        self.assertEqual(result.reason, "candidate-snapshot-mismatch")

    def test_incomplete_e3_e5_shapes_remain_unavailable(self):
        intent = CompilerSemanticIntent("AIDL-T123", "semantic", "error", "same intent")
        for case in CASES["migration_unavailable"]:
            source = case["source"]
            offset = source.index(case["anchor"]) + 1
            result = self.consumer.migration_diagnostic(source, offset, self.migration_context(source))
            with self.subTest(row=case["id"]):
                self.assertIsInstance(result, DiagnosticUnavailable)
                assert isinstance(result, DiagnosticUnavailable)
                self.assertEqual(result.reason, "e5-target-shape-not-fact-complete")
            projected = self.consumer.equivalent_semantic_intent(
                source, source, offset, self.migration_context(source), intent
            )
            self.assertIsInstance(projected, DiagnosticUnavailable)

    def test_multi_source_projection_failure_is_preserved_not_papered_over(self):
        case = CASES["multi_source_projection"]
        source = case["source"]
        offset = source.index(case["anchor"]) + 1
        result = self.consumer.migration_diagnostic(source, offset, self.migration_context(source))
        self.assertIsInstance(result, StructuralDiagnostic)
        assert isinstance(result, StructuralDiagnostic)
        self.assertEqual(result.code, "AIDL-S004")
        intent = CompilerSemanticIntent("AIDL-T123", "semantic", "error", "same intent")
        projected = self.consumer.equivalent_semantic_intent(source, source, offset, self.migration_context(source), intent)
        self.assertIsInstance(projected, DiagnosticUnavailable)
        assert isinstance(projected, DiagnosticUnavailable)
        self.assertEqual(projected.reason, "e5-AIDL-S004")

    def test_e7_source_contains_no_second_language_schema_or_production_diagnostics_rollout(self):
        source = pathlib.Path(e7.__file__).read_text()
        self.assertIn("m16_5_e4_introspection", source)
        self.assertIn("m16_5_e5_migration", source)
        self.assertNotIn("ROW_IDS =", source)
        self.assertNotIn("RULES =", source)
        self.assertNotIn("serverAuthoritative", source)
        self.assertNotIn("projection-relationship", source)
        self.assertNotIn("client-target", source)
        self.assertNotIn("AidlCompilerDiagnostics", source)
        self.assertNotIn("aidl_parser", source)


if __name__ == "__main__":
    unittest.main()
