from __future__ import annotations

import copy
import json
import pathlib
import tempfile
import unittest
from dataclasses import replace

from tools import m16_5_e3_prototype as e3
from tools import m16_5_e4_introspection as e4
from tools import m16_5_e5_migration as e5
from tools.m16_5_candidate_projection import (
    ProjectionError,
    compiler_evidence,
    exact_context,
    project_source,
    project_worktree,
    projection_ref,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "fixtures/m16-5/evaluation-candidate-projection-cases.json").read_text(
        encoding="utf-8"
    )
)


class CandidateProjectionTests(unittest.TestCase):
    def assert_reason(self, reason: str, fn, *args, **kwargs) -> ProjectionError:
        with self.assertRaises(ProjectionError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)
        return caught.exception

    def test_exact_versioned_projection_contract(self):
        expected = CASES["projection_contract"]
        ref = projection_ref()
        self.assertEqual(ref.projection_id, expected["id"])
        self.assertEqual(ref.semantic_version, expected["version"])
        self.assertEqual(ref.content_fingerprint, expected["fingerprint"])
        context = exact_context()
        self.assertEqual(context.projection_ref, ref)
        self.assertEqual(context.e3_schema_id, e3.CANDIDATE_SCHEMA_ID)
        self.assertEqual(context.e3_schema_version, e3.CANDIDATE_SCHEMA_VERSION)
        self.assertEqual(context.e3_schema_fingerprint, e3.build_catalog().fingerprint)
        self.assertEqual(context.e4_schema_id, e4.SCHEMA_ID)
        self.assertEqual(context.e4_schema_version, e4.SCHEMA_VERSION)
        self.assertEqual(context.e4_schema_fingerprint, e4.current_schema_ref().content_fingerprint)
        self.assertEqual(context.candidate_schema_version, e5.TARGET_VERSION)
        self.assertEqual(context.current_schema_version, e5.OLD_VERSION)

    def test_every_normalization_row_projects_from_independent_candidate_instance(self):
        context = exact_context()
        self.assertEqual(
            [item["id"] for item in CASES["normalization_rows"]],
            list(e5.ROW_IDS),
        )
        for item in CASES["normalization_rows"]:
            with self.subTest(row=item["id"]):
                result = project_source(item["candidate"], context=context)
                expected_current_facts = e5.extract_facts(
                    item["current"], source_version=e5.OLD_VERSION
                )
                self.assertEqual(result.candidate_facts, expected_current_facts)
                self.assertEqual(result.current_facts, expected_current_facts)
                self.assertEqual(set(result.row_ids), {item["id"]})
                remigrated = e5.migrate(
                    result.source,
                    source_version=e5.OLD_VERSION,
                    old_version=e5.OLD_VERSION,
                    target_version=e5.TARGET_VERSION,
                    source_schema_fingerprint=e5.OLD_SCHEMA_FINGERPRINT,
                    target_schema_fingerprint=e5.TARGET_SCHEMA_FINGERPRINT,
                    expected_source_fingerprint=e5.source_fingerprint(result.source),
                ).source
                canonical_candidate = e5.format_candidate(
                    item["candidate"],
                    source_version=e5.TARGET_VERSION,
                    schema_fingerprint=e5.TARGET_SCHEMA_FINGERPRINT,
                )
                self.assertEqual(remigrated, canonical_candidate)

    def test_repeated_projection_sources_preserve_order_and_multiplicity(self):
        item = CASES["reordered_repeated"]
        result = project_source(item["candidate"], context=exact_context())
        facts = dict(result.current_facts[0].facts)
        self.assertEqual(facts["sources"], tuple(item["sources"]))
        expected = e5.extract_facts(item["current"], source_version=e5.OLD_VERSION)
        self.assertEqual(result.current_facts, expected)

    def test_stale_or_mismatched_schema_identity_fails_before_projection(self):
        context = exact_context()
        stale_candidate = replace(context, candidate_schema_version="m16.5-e5-candidate-stale")
        self.assert_reason(
            "schema-context-mismatch",
            project_source,
            CASES["normalization_rows"][0]["candidate"],
            context=stale_candidate,
        )
        stale_ref = replace(
            context,
            projection_ref=replace(context.projection_ref, content_fingerprint="sha256:stale"),
        )
        self.assert_reason(
            "schema-context-mismatch",
            project_source,
            CASES["normalization_rows"][0]["candidate"],
            context=stale_ref,
        )

    def test_missing_and_ambiguous_inverse_facts_fail_closed(self):
        fail = CASES["fail_closed"]
        self.assert_reason(
            "incomplete-candidate-anchor",
            project_source,
            fail["missing_fact"],
            context=exact_context(),
        )
        self.assert_reason(
            "ambiguous-inverse-fact",
            project_source,
            fail["ambiguous_fact"],
            context=exact_context(),
        )

    def test_unmodeled_e3_representative_construct_is_not_promoted(self):
        self.assert_reason(
            "unsupported-candidate-construct",
            project_source,
            CASES["fail_closed"]["unsupported_e3"],
            context=exact_context(),
        )

    def test_legacy_normalization_spelling_is_not_sniffed_as_candidate(self):
        current = CASES["normalization_rows"][0]["current"]
        self.assert_reason(
            "legacy-spelling-in-candidate-context",
            project_source,
            current,
            context=exact_context(),
        )

    @staticmethod
    def _semantic_ir(document):
        result = copy.deepcopy(document)
        if isinstance(result, dict):
            result.pop("sourceMap", None)
        return result

    def test_project_projection_is_accepted_only_by_unchanged_compiler_and_matches_current_ir(self):
        fixture = CASES["accepted_project"]
        with tempfile.TemporaryDirectory(prefix="aidl-m16-projection-test-") as temporary:
            root = pathlib.Path(temporary)
            candidate = root / "candidate"
            current = root / "current"
            output = root / "projected"
            candidate.mkdir()
            current.mkdir()
            (candidate / "main.aidl").write_text(fixture["candidate"], encoding="utf-8")
            (candidate / "note.txt").write_text("unchanged evidence\n", encoding="utf-8")
            (current / "main.aidl").write_text(fixture["current"], encoding="utf-8")

            current_compiler = compiler_evidence(current)
            self.assertTrue(current_compiler.accepted)
            projected = project_worktree(candidate, output, context=exact_context())
            self.assertTrue(projected.compiler.accepted)
            self.assertEqual((candidate / "main.aidl").read_text(encoding="utf-8"), fixture["candidate"])
            self.assertEqual((output / "note.txt").read_text(encoding="utf-8"), "unchanged evidence\n")

            projected_source = (output / "main.aidl").read_text(encoding="utf-8")
            self.assertEqual(
                e5.extract_facts(projected_source, source_version=e5.OLD_VERSION),
                e5.extract_facts(fixture["current"], source_version=e5.OLD_VERSION),
            )
            self.assertEqual(
                self._semantic_ir(projected.compiler.ir.result),
                self._semantic_ir(current_compiler.ir.result),
            )
            self.assertEqual(
                projected.compiler.ir.result["semanticHash"],
                current_compiler.ir.result["semanticHash"],
            )

    def test_existing_schedule_parser_gap_is_not_worked_around(self):
        candidate_source = CASES["compiler_rejection_project"]["candidate"]
        with tempfile.TemporaryDirectory(prefix="aidl-m16-schedule-projection-") as temporary:
            root = pathlib.Path(temporary)
            candidate = root / "candidate"
            output = root / "projected"
            candidate.mkdir()
            (candidate / "main.aidl").write_text(candidate_source, encoding="utf-8")
            error = self.assert_reason(
                "compiler-rejected",
                project_worktree,
                candidate,
                output,
                context=exact_context(),
            )
            self.assertIsNotNone(error.evidence)
            assert error.evidence is not None
            self.assertFalse(error.evidence.accepted)
            self.assertFalse(error.evidence.check.ok)
            self.assertFalse(output.exists())

    def test_consumer_contains_no_second_row_or_syntax_table(self):
        implementation = (ROOT / "tools/m16_5_candidate_projection.py").read_text(encoding="utf-8")
        self.assertNotIn("ROW_IDS =", implementation)
        self.assertNotIn("RULES =", implementation)
        self.assertIn("e5.RULES", implementation)
        self.assertIn("e5._matches", implementation)
        for item in CASES["normalization_rows"]:
            self.assertNotIn(item["current"].strip(), implementation)
            self.assertNotIn(item["candidate"].strip(), implementation)


if __name__ == "__main__":
    unittest.main()
