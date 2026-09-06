from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.ir_diff import IrDiffError, diff_canonical_ir, semantic_ir_diff_to_json


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "valid" / "m4-minimal" / "snapshots" / "ir.json"


class IrDiffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def _declaration(self, document: dict, kind: str) -> dict:
        return next(item for item in document["declarations"] if item["kind"] == kind)

    def test_identical_and_trace_hash_or_order_only_changes_have_no_semantic_diff(self) -> None:
        other = copy.deepcopy(self.base)
        other["semanticHash"] = "sha256:" + "0" * 64
        self._declaration(other, "entity")["semanticHash"] = "sha256:" + "1" * 64
        other["sourceMap"]["entries"][0]["span"]["startLine"] += 10
        other["sourceMap"]["entries"][0]["span"]["file"] = "reformatted/app.aidl"
        other["declarations"].reverse()
        other["profiles"].reverse()
        other["system"]["services"][0]["uses"].reverse()

        self.assertEqual([], diff_canonical_ir(self.base, self.base))
        self.assertEqual([], diff_canonical_ir(self.base, other))

    def test_declaration_add_and_remove_use_stable_identity_paths(self) -> None:
        extended = copy.deepcopy(self.base)
        added = copy.deepcopy(self._declaration(extended, "value"))
        added["declarationId"] = "fixtures.valid.m4minimal.ExtraInput@1"
        added["fqn"] = "fixtures.valid.m4minimal.ExtraInput"
        added["name"] = "ExtraInput"
        added["semanticHash"] = "sha256:" + "1" * 64
        extended["declarations"].insert(0, added)

        addition = diff_canonical_ir(self.base, extended)
        self.assertEqual(1, len(addition))
        self.assertEqual("added", addition[0].kind)
        self.assertEqual(
            "/declarations/value:fixtures.valid.m4minimal.ExtraInput@1",
            addition[0].path,
        )
        self.assertIsNone(addition[0].old_value)
        self.assertEqual("ExtraInput", addition[0].new_value["name"])
        self.assertNotIn("semanticHash", addition[0].new_value)

        removal = diff_canonical_ir(extended, self.base)
        self.assertEqual(1, len(removal))
        self.assertEqual("removed", removal[0].kind)
        self.assertEqual(addition[0].path, removal[0].path)
        self.assertEqual("ExtraInput", removal[0].old_value["name"])
        self.assertIsNone(removal[0].new_value)

    def test_nested_api_event_entity_and_persistence_changes_are_precise(self) -> None:
        changed = copy.deepcopy(self.base)
        api = self._declaration(changed, "api")
        event = self._declaration(changed, "event")
        entity = self._declaration(changed, "entity")
        resource = changed["system"]["resources"][0]

        api["rateLimit"]["requests"] += 1
        event["fields"][0]["sensitive"] = True
        entity["fields"][2]["mutable"] = False
        resource["transactionIsolation"].append("serializable")

        changes = diff_canonical_ir(self.base, changed)
        paths = [item.path for item in changes]
        expected_paths = sorted(
            [
                "/declarations/api:fixtures.valid.m4minimal.SnapshotApi@1/rateLimit/requests",
                "/declarations/entity:fixtures.valid.m4minimal.SnapshotItem@1/fields/2/mutable",
                "/declarations/event:fixtures.valid.m4minimal.SnapshotItemCreated@1/fields/0/sensitive",
                "/system/resources/fixtures.valid.m4minimal.SnapshotDb@1/transactionIsolation/1",
            ]
        )
        self.assertEqual(expected_paths, paths)

        by_path = {item.path: item for item in changes}
        self.assertEqual(
            300,
            by_path[
                "/declarations/api:fixtures.valid.m4minimal.SnapshotApi@1/rateLimit/requests"
            ].old_value,
        )
        self.assertEqual(
            {
                "kind": "added",
                "path": "/system/resources/fixtures.valid.m4minimal.SnapshotDb@1/transactionIsolation/1",
                "oldValue": None,
                "newValue": "serializable",
            },
            next(
                item
                for item in semantic_ir_diff_to_json(changes)
                if item["path"].endswith("transactionIsolation/1")
            ),
        )

    def test_output_order_is_deterministic(self) -> None:
        changed = copy.deepcopy(self.base)
        self._declaration(changed, "api")["rateLimit"]["burst"] = 51
        self._declaration(changed, "topic")["deadLetterAttempts"] = 9
        changed["app"]["auth"]["roles"].append("admin")

        first = semantic_ir_diff_to_json(diff_canonical_ir(self.base, changed))
        second_input = copy.deepcopy(changed)
        second_input["declarations"].reverse()
        second_input["app"]["auth"]["roles"].reverse()
        second = semantic_ir_diff_to_json(diff_canonical_ir(self.base, second_input))

        self.assertEqual(first, second)
        self.assertEqual(sorted(item["path"] for item in first), [item["path"] for item in first])

    def test_incompatible_version_and_schema_fail_explicitly(self) -> None:
        incompatible = copy.deepcopy(self.base)
        incompatible["irVersion"] = "1.0.0"
        with self.assertRaisesRegex(
            IrDiffError,
            r"new: unsupported Canonical IR version 1\.0\.0; expected 0\.3\.0",
        ):
            diff_canonical_ir(self.base, incompatible)

        malformed = copy.deepcopy(self.base)
        malformed["app"]["apiIds"] = "not-an-array"
        with self.assertRaisesRegex(IrDiffError, r"new: schema-invalid at /app/apiIds:"):
            diff_canonical_ir(self.base, malformed)


if __name__ == "__main__":
    unittest.main()
