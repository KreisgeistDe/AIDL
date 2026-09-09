from __future__ import annotations

import json
import pathlib
import unittest
from dataclasses import replace

from tools.m16_5_e5_migration import (
    OLD_SCHEMA_FINGERPRINT,
    OLD_VERSION,
    ROW_IDS,
    TARGET_SCHEMA_FINGERPRINT,
    TARGET_VERSION,
    Anchor,
    MigrationError,
    apply_plan,
    build_sidecar,
    extract_facts,
    format_candidate,
    migrate,
    plan_migration,
    source_fingerprint,
    with_anchors,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "fixtures/m16-5/e5-migration-cases.json").read_text())


def kwargs(source: str, *, source_version: str = OLD_VERSION, source_schema: str | None = None):
    return {
        "source_version": source_version,
        "old_version": OLD_VERSION,
        "target_version": TARGET_VERSION,
        "source_schema_fingerprint": source_schema or (
            OLD_SCHEMA_FINGERPRINT if source_version == OLD_VERSION else TARGET_SCHEMA_FINGERPRINT
        ),
        "target_schema_fingerprint": TARGET_SCHEMA_FINGERPRINT,
        "expected_source_fingerprint": source_fingerprint(source),
    }


class E5MigrationTests(unittest.TestCase):
    def assert_code(self, code: str, fn, *args, **call_kwargs):
        with self.assertRaises(MigrationError) as caught:
            fn(*args, **call_kwargs)
        self.assertEqual(caught.exception.diagnostic.code, code)

    def test_all_nine_rows_migrate_to_exact_canonical_fixture(self):
        rows = CASES["normalization_rows"]
        self.assertEqual([row["id"] for row in rows], list(ROW_IDS))
        for row in rows:
            with self.subTest(row=row["id"]):
                result = migrate(row["old"], **kwargs(row["old"]))
                self.assertEqual(result.source, row["candidate"])
                self.assertEqual(len(result.plan.edits), 1)
                self.assertEqual(result.plan.edits[0].row_id, row["id"])
                self.assertEqual(result.plan.semantic_result, "compatible")
                self.assertEqual(result.plan.old_facts, result.plan.target_facts)
                self.assertEqual(result.plan.rollback_source, row["old"])
                self.assertEqual(
                    format_candidate(
                        result.source,
                        source_version=TARGET_VERSION,
                        schema_fingerprint=TARGET_SCHEMA_FINGERPRINT,
                    ),
                    result.source,
                )

    def test_old_fixtures_are_production_parse_valid_and_e3_replay_is_used_where_exact(self):
        replayed = set()
        for row in CASES["normalization_rows"]:
            plan = plan_migration(row["old"], **kwargs(row["old"]))
            replayed.update(plan.e3_replayed_rows)
        self.assertTrue(
            {
                "projection-relationship",
                "client-target",
                "migration-source-target",
                "consumer-relationship",
                "explicit-field-child",
            }.issubset(replayed)
        )

    def test_second_application_is_explicit_target_version_noop(self):
        for row in CASES["normalization_rows"]:
            with self.subTest(row=row["id"]):
                first = migrate(row["old"], **kwargs(row["old"]))
                second = plan_migration(
                    first.source,
                    **kwargs(first.source, source_version=TARGET_VERSION),
                )
                self.assertEqual(second.edits, ())
                self.assertEqual(second.semantic_result, "compatible")
                self.assertEqual(second.rollback_source, first.source)

    def test_dry_run_is_non_mutating_and_apply_is_deterministic(self):
        row = CASES["normalization_rows"][0]
        old = row["old"]
        plan1 = plan_migration(old, **kwargs(old))
        plan2 = plan_migration(old, **kwargs(old))
        self.assertEqual(old, row["old"])
        self.assertEqual(plan1.edits, plan2.edits)
        self.assertEqual(plan1.relocations, plan2.relocations)
        applied = apply_plan(old, plan1)
        self.assertEqual(applied.source, row["candidate"])

    def test_untouched_ranges_are_byte_exact_and_changed_anchor_relocation_is_explicit(self):
        row = CASES["normalization_rows"][0]
        result = migrate(row["old"], **kwargs(row["old"]))
        edit = result.plan.edits[0]
        relocation = result.plan.relocations[0]
        self.assertEqual(row["old"][: edit.start], result.source[: relocation.new_start])
        self.assertEqual(row["old"][edit.end :], result.source[relocation.new_end :])
        self.assertIn("// lead stays byte-exact", result.source)
        self.assertIn("key orderId // untouched body", result.source)

    def test_comments_annotations_and_field_modifiers_survive_anchor_rewrite(self):
        old = "entity Customer {\n  @pii\n  email: String required unique // preserve me\n}\n"
        result = migrate(old, **kwargs(old))
        self.assertIn("  @pii\n  field email: String required unique // preserve me", result.source)
        facts = dict(result.plan.target_facts[0].facts)
        self.assertEqual(facts["modifiers"], ("required", "unique"))

    def test_fail_closed_on_stale_source_or_schema_fingerprints(self):
        row = CASES["normalization_rows"][1]
        old = row["old"]
        bad = kwargs(old)
        bad["expected_source_fingerprint"] = "sha256:stale"
        self.assert_code("AIDL-S008", plan_migration, old, **bad)

        sidecar = build_sidecar(
            old,
            source_version=OLD_VERSION,
            schema_fingerprint=OLD_SCHEMA_FINGERPRINT,
        )
        stale = replace(sidecar, schema_fingerprint="sha256:stale")
        self.assert_code("AIDL-S008", plan_migration, old, sidecar=stale, **kwargs(old))

    def test_fail_closed_on_missing_ambiguous_and_overlapping_anchors(self):
        old = CASES["normalization_rows"][3]["old"]
        sidecar = build_sidecar(
            old,
            source_version=OLD_VERSION,
            schema_fingerprint=OLD_SCHEMA_FINGERPRINT,
        )
        self.assertTrue(sidecar.anchors)

        missing = with_anchors(sidecar, ())
        self.assert_code("AIDL-S005", plan_migration, old, sidecar=missing, **kwargs(old))

        duplicate = with_anchors(sidecar, (*sidecar.anchors, sidecar.anchors[0]))
        self.assert_code("AIDL-S005", plan_migration, old, sidecar=duplicate, **kwargs(old))

        a = sidecar.anchors[0]
        overlap = Anchor("synthetic-overlap", a.row_id, a.role, a.start + 1, a.end)
        overlapping = with_anchors(sidecar, (*sidecar.anchors, overlap))
        self.assert_code("AIDL-S005", plan_migration, old, sidecar=overlapping, **kwargs(old))

    def test_formatter_is_same_version_only_and_never_migrates_legacy(self):
        candidate = CASES["normalization_rows"][6]["candidate"]
        messy = candidate.replace("deadLetter: 5 attempts", "deadLetter :   5   attempts")
        self.assertEqual(
            format_candidate(
                messy,
                source_version=TARGET_VERSION,
                schema_fingerprint=TARGET_SCHEMA_FINGERPRINT,
            ),
            candidate,
        )
        self.assert_code(
            "AIDL-S007",
            format_candidate,
            CASES["normalization_rows"][6]["old"],
            source_version=TARGET_VERSION,
            schema_fingerprint=TARGET_SCHEMA_FINGERPRINT,
        )
        self.assert_code(
            "AIDL-S008",
            format_candidate,
            candidate,
            source_version=OLD_VERSION,
            schema_fingerprint=TARGET_SCHEMA_FINGERPRINT,
        )

    def test_representative_unchanged_and_ordered_sources_are_not_rewritten_or_reordered(self):
        for case in CASES["unchanged"]:
            with self.subTest(case=case["id"]):
                plan = plan_migration(case["source"], **kwargs(case["source"]))
                self.assertEqual(plan.edits, ())
                result = apply_plan(case["source"], plan)
                self.assertEqual(result.source, case["source"])
                self.assertEqual(
                    format_candidate(
                        case["source"],
                        source_version=TARGET_VERSION,
                        schema_fingerprint=TARGET_SCHEMA_FINGERPRINT,
                    ),
                    case["source"],
                )

    def test_projection_multi_source_gap_fails_closed_instead_of_dropping_facts(self):
        source = CASES["negative"]["projection_multi_source"]
        self.assert_code("AIDL-S004", plan_migration, source, **kwargs(source))

    def test_coexistence_and_rollback_are_fixture_backed(self):
        row = CASES["normalization_rows"][8]
        first = migrate(row["old"], **kwargs(row["old"]))
        self.assertEqual(first.plan.rollback_source, row["old"])
        target_context = plan_migration(
            first.source,
            **kwargs(first.source, source_version=TARGET_VERSION),
        )
        self.assertEqual(target_context.edits, ())
        self.assertEqual(first.plan.rollback_source, row["old"])
        self.assertEqual(
            extract_facts(first.plan.rollback_source, source_version=OLD_VERSION),
            extract_facts(first.source, source_version=TARGET_VERSION),
        )


if __name__ == "__main__":
    unittest.main()
