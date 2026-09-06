from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from tools.ir_compatibility import classify_ir_diff
from tools.ir_diff import diff_canonical_ir, semantic_ir_diff_to_json
from tools.ir_migration_guidance import (
    IrMigrationGuidanceError,
    build_ir_migration_guidance,
    ir_migration_guidance_to_json,
)


ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = ROOT / "fixtures" / "valid" / "m4-minimal" / "snapshots" / "ir.json"
_PHASE_ORDER = ["expand", "deployReaders", "backfill", "switchWrites", "verify", "contract"]


class IrMigrationGuidanceTest(unittest.TestCase):
    def _base(self) -> dict:
        return json.loads(_FIXTURE.read_text(encoding="utf-8"))

    def _declaration(self, document: dict, name: str) -> dict:
        return next(item for item in document["declarations"] if item["name"] == name)

    def _guidance(self, old: dict, new: dict):
        changes = diff_canonical_ir(old, new)
        classifications = classify_ir_diff(changes, old, new)
        guidance = build_ir_migration_guidance(changes, classifications, old, new)
        return changes, classifications, guidance

    def test_safe_guidance_is_empty_and_stable(self) -> None:
        old = self._base()
        new = self._base()
        self._declaration(new, "SnapshotItemEvents")["retentionMs"] += 1

        changes, classifications, first = self._guidance(old, new)
        second = build_ir_migration_guidance(changes, classifications, old, new)

        item = next(item for item in first if item.classification == "safe")
        self.assertEqual((), item.phases)
        self.assertEqual((), item.preconditions)
        self.assertEqual(first, second)
        self.assertEqual(ir_migration_guidance_to_json(first), ir_migration_guidance_to_json(second))

    def test_conditional_guidance_is_review_only_without_migration_phases(self) -> None:
        old = self._base()
        new = self._base()
        self._declaration(new, "SnapshotApi")["rateLimit"]["burst"] += 1

        _changes, _classifications, guidance = self._guidance(old, new)
        item = next(item for item in guidance if item.classification == "conditional")

        self.assertEqual((), item.phases)
        self.assertEqual(1, len(item.preconditions))
        self.assertIn("Review and coordinate", item.preconditions[0])
        self.assertIn(item.classification_rule, item.preconditions[0])

    def test_required_persisted_field_uses_full_expand_backfill_contract_order(self) -> None:
        old = self._base()
        new = self._base()
        entity = self._declaration(new, "SnapshotItem")
        field = deepcopy(entity["fields"][2])
        field.update({"name": "category", "required": True, "mutable": True})
        entity["fields"].append(field)

        _changes, classifications, guidance = self._guidance(old, new)
        target = next(
            item
            for item in guidance
            if item.classification_rule == "entity.required-field-added"
        )

        self.assertEqual("migration-required", target.classification)
        self.assertEqual(_PHASE_ORDER, [phase.phase for phase in target.phases])
        self.assertTrue(all(phase.evidence.endswith(target.path) for phase in target.phases))
        self.assertIn("does not encode a value source", target.preconditions[0])
        self.assertTrue(
            any(item.classification == "migration-required" for item in classifications)
        )

    def test_optional_persisted_field_has_expand_rollout_without_invented_backfill(self) -> None:
        old = self._base()
        new = self._base()
        entity = self._declaration(new, "SnapshotItem")
        field = deepcopy(entity["fields"][2])
        field.update({"name": "nickname", "required": False, "mutable": True})
        entity["fields"].append(field)

        _changes, _classifications, guidance = self._guidance(old, new)
        target = next(item for item in guidance if item.classification_rule == "entity.field-added")

        self.assertEqual(
            ["expand", "deployReaders", "switchWrites", "verify"],
            [phase.phase for phase in target.phases],
        )
        self.assertNotIn("backfill", [phase.phase for phase in target.phases])
        self.assertEqual((), target.preconditions)
        self.assertIn("No backfill is proposed", target.note)

    def test_breaking_guidance_never_pretends_safe_automation_and_names_recovery_preconditions(self) -> None:
        old = self._base()
        new = self._base()
        self._declaration(new, "SnapshotItem")["fields"].pop()

        _changes, _classifications, guidance = self._guidance(old, new)
        target = next(item for item in guidance if item.classification == "breaking")

        self.assertEqual((), target.phases)
        joined = " ".join(target.preconditions)
        self.assertIn("explicit compatibility review", joined)
        self.assertIn("rollback/recovery", joined)
        self.assertIn("backup", joined)
        self.assertIn("No apparently safe", target.note)

    def test_cross_surface_stricter_classification_drives_guidance_without_reclassifying(self) -> None:
        old = self._base()
        new = self._base()
        entity = self._declaration(new, "SnapshotItem")
        field = deepcopy(entity["fields"][2])
        field.update({"name": "nickname", "required": False})
        entity["fields"].append(field)

        changes, classifications, guidance = self._guidance(old, new)
        index = next(i for i, item in enumerate(classifications) if item.path.endswith("/fields/3"))

        self.assertEqual("migration-required", classifications[index].classification)
        self.assertEqual("entity.field-added", classifications[index].rule)
        self.assertEqual(classifications[index].classification, guidance[index].classification)
        self.assertEqual(classifications[index].rule, guidance[index].classification_rule)
        self.assertEqual(changes[index].path, guidance[index].path)

    def test_unrepresented_profile_evidence_stays_explicitly_review_only(self) -> None:
        old = self._base()
        new = self._base()
        new["profileExtensions"] = {
            "distributed@1": [
                {
                    "target": "/app",
                    "schema": "https://aidl.example/profiles/distributed/1/sync.schema.json",
                    "value": {"minClientVersion": "2"},
                }
            ]
        }

        _changes, classifications, guidance = self._guidance(old, new)
        self.assertTrue(guidance)
        self.assertEqual({"conditional"}, {item.classification for item in guidance})
        self.assertEqual({"unmodelled.review-required"}, {item.rule for item in classifications})
        self.assertTrue(all(not item.phases for item in guidance))
        self.assertTrue(all(item.preconditions for item in guidance))

    def test_guidance_preserves_raw_fact_order_and_rejects_non_authoritative_inputs(self) -> None:
        old = self._base()
        new = self._base()
        self._declaration(new, "SnapshotItemEvents")["retentionMs"] += 1
        self._declaration(new, "SnapshotApi")["rateLimit"]["burst"] += 1
        changes = diff_canonical_ir(old, new)
        classifications = classify_ir_diff(changes, old, new)
        raw_before = semantic_ir_diff_to_json(changes)

        guidance = build_ir_migration_guidance(changes, classifications, old, new)
        self.assertEqual([item.path for item in changes], [item.path for item in guidance])
        self.assertEqual(raw_before, semantic_ir_diff_to_json(changes))

        with self.assertRaisesRegex(IrMigrationGuidanceError, "classifications do not match"):
            build_ir_migration_guidance(changes, list(reversed(classifications)), old, new)


if __name__ == "__main__":
    unittest.main()
