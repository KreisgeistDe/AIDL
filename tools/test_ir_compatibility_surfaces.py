from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from tools.ir_compatibility import classify_ir_diff
from tools.ir_diff import diff_canonical_ir, semantic_ir_diff_to_json


ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = ROOT / "fixtures" / "valid" / "m4-minimal" / "snapshots" / "ir.json"


class IrCompatibilitySurfaceMatrixTest(unittest.TestCase):
    def _base(self) -> dict:
        return json.loads(_FIXTURE.read_text(encoding="utf-8"))

    def _declaration(self, document: dict, name: str) -> dict:
        return next(item for item in document["declarations"] if item["name"] == name)

    def _classes(self, old: dict, new: dict):
        changes = diff_canonical_ir(old, new)
        return changes, classify_ir_diff(changes, old, new)

    def _rules(self, old: dict, new: dict) -> dict[str, str]:
        _changes, classifications = self._classes(old, new)
        return {item.rule: item.classification for item in classifications}

    def test_api_surface_add_remove_and_auth_matrix(self) -> None:
        base = self._base()

        added = deepcopy(base)
        api = self._declaration(added, "SnapshotApi")
        api["operations"].append(
            {"kind": "mutation", "operationId": "fixtures.valid.m4minimal.futureOperation@1"}
        )
        self.assertEqual("safe", self._rules(base, added)["api.operation-added"])

        removed_old = deepcopy(base)
        self._declaration(removed_old, "SnapshotApi")["operations"].append(
            {"kind": "mutation", "operationId": "fixtures.valid.m4minimal.futureOperation@1"}
        )
        removed_new = deepcopy(base)
        self.assertEqual(
            "breaking",
            self._rules(removed_old, removed_new)["api.operation-removed"],
        )

        auth_changed = deepcopy(base)
        self._declaration(auth_changed, "SnapshotApi")["auth"]["mode"] = "authenticated"
        self.assertEqual("breaking", self._rules(base, auth_changed)["api.auth-changed"])

    def test_event_surface_immutable_schema_topic_versions_and_retention_matrix(self) -> None:
        base = self._base()

        mutated = deepcopy(base)
        event = self._declaration(mutated, "SnapshotItemCreated")
        extra = deepcopy(event["fields"][1])
        extra["name"] = "source"
        extra["required"] = False
        event["fields"].append(extra)
        self.assertEqual("breaking", self._rules(base, mutated)["event.schema-mutated"])

        version_added = deepcopy(base)
        new_event = deepcopy(self._declaration(version_added, "SnapshotItemCreated"))
        new_event.update(
            {
                "name": "SnapshotItemCreatedV2",
                "fqn": "fixtures.valid.m4minimal.SnapshotItemCreatedV2",
                "declarationId": "fixtures.valid.m4minimal.SnapshotItemCreatedV2@2",
                "majorVersion": 2,
            }
        )
        version_added["declarations"].append(new_event)
        self.assertEqual("safe", self._rules(base, version_added)["event.version-added"])

        topic_added = deepcopy(version_added)
        self._declaration(topic_added, "SnapshotItemEvents")["eventIds"].append(
            "fixtures.valid.m4minimal.SnapshotItemCreatedV2@2"
        )
        rules = self._rules(version_added, topic_added)
        self.assertEqual("conditional", rules["event.topic-version-added"])

        retention_lower = deepcopy(base)
        self._declaration(retention_lower, "SnapshotItemEvents")["retentionMs"] -= 1
        self.assertEqual("breaking", self._rules(base, retention_lower)["event.retention-reduced"])

        retention_higher = deepcopy(base)
        self._declaration(retention_higher, "SnapshotItemEvents")["retentionMs"] += 1
        self.assertEqual("safe", self._rules(base, retention_higher)["event.retention-increased"])

    def test_persisted_schema_add_remove_constraint_and_identity_matrix(self) -> None:
        base = self._base()

        added = deepcopy(base)
        entity = self._declaration(added, "SnapshotItem")
        extra = deepcopy(entity["fields"][2])
        extra.update({"name": "nickname", "required": False, "mutable": True})
        entity["fields"].append(extra)
        self.assertEqual("migration-required", self._rules(base, added)["entity.field-added"])

        removed = deepcopy(base)
        self._declaration(removed, "SnapshotItem")["fields"].pop()
        self.assertEqual("breaking", self._rules(base, removed)["entity.field-removed"])

        constrained_old = deepcopy(base)
        constrained_new = deepcopy(base)
        old_name = self._declaration(constrained_old, "SnapshotItem")["fields"][2]
        new_name = self._declaration(constrained_new, "SnapshotItem")["fields"][2]
        old_name["type"]["constraints"] = {"maxLength": 100}
        new_name["type"]["constraints"] = {"maxLength": 80}
        self.assertEqual(
            "migration-required",
            self._rules(constrained_old, constrained_new)["entity.constraint-changed"],
        )

        identity_changed = deepcopy(base)
        self._declaration(identity_changed, "SnapshotItem")["identityFields"] = ["name"]
        self.assertEqual("breaking", self._rules(base, identity_changed)["entity.identity-changed"])

    def test_public_client_input_matrix(self) -> None:
        base = self._base()

        required_added = deepcopy(base)
        value = self._declaration(required_added, "CreateItemInput")
        required = deepcopy(value["fields"][2])
        required["name"] = "category"
        value["fields"].append(required)
        self.assertEqual(
            "breaking",
            self._rules(base, required_added)["client.input-required-field-added"],
        )

        optional_added = deepcopy(base)
        value = self._declaration(optional_added, "CreateItemInput")
        optional = deepcopy(value["fields"][2])
        optional.update({"name": "note", "required": False})
        value["fields"].append(optional)
        self.assertEqual(
            "conditional",
            self._rules(base, optional_added)["client.input-optional-field-added"],
        )

        relaxed = deepcopy(base)
        self._declaration(relaxed, "CreateItemInput")["fields"][2]["required"] = False
        self.assertEqual("safe", self._rules(base, relaxed)["client.input-required-relaxed"])

        constrained_old = deepcopy(base)
        constrained_new = deepcopy(base)
        old_field = self._declaration(constrained_old, "CreateItemInput")["fields"][2]
        new_field = self._declaration(constrained_new, "CreateItemInput")["fields"][2]
        old_field["type"]["constraints"] = {"maxLength": 100}
        new_field["type"]["constraints"] = {"maxLength": 80}
        self.assertEqual(
            "breaking",
            self._rules(constrained_old, constrained_new)["client.input-constraint-tightened"],
        )

    def test_public_client_output_and_error_matrix(self) -> None:
        old = self._base()
        new = self._base()
        template = deepcopy(self._declaration(old, "CreateItemInput"))
        template.update(
            {
                "name": "CreateItemOutput",
                "fqn": "fixtures.valid.m4minimal.CreateItemOutput",
                "declarationId": "fixtures.valid.m4minimal.CreateItemOutput@1",
            }
        )
        old["declarations"].append(deepcopy(template))
        new["declarations"].append(deepcopy(template))
        output_ref = {
            "kind": "named",
            "declarationId": "fixtures.valid.m4minimal.CreateItemOutput@1",
            "fqn": "fixtures.valid.m4minimal.CreateItemOutput",
            "typeArguments": [],
        }
        self._declaration(old, "createItem")["output"] = deepcopy(output_ref)
        self._declaration(new, "createItem")["output"] = deepcopy(output_ref)
        extra = deepcopy(self._declaration(new, "CreateItemOutput")["fields"][2])
        extra["name"] = "status"
        self._declaration(new, "CreateItemOutput")["fields"].append(extra)
        self.assertEqual("safe", self._rules(old, new)["client.output-field-added"])

        nullable = self._base()
        operation = self._declaration(nullable, "createItem")
        operation["output"] = {"kind": "nullable", "element": deepcopy(operation["output"])}
        self.assertEqual(
            "breaking",
            self._rules(self._base(), nullable)["client.output-nullability-broadened"],
        )

        error_added = self._base()
        self._declaration(error_added, "createItem")["errorIds"].append("aidl.std.FutureError@1")
        self.assertEqual("conditional", self._rules(self._base(), error_added)["client.error-added"])

    def test_cross_surface_stricter_rule_wins_and_raw_fact_order_is_preserved(self) -> None:
        old = self._base()
        new = self._base()
        entity = self._declaration(new, "SnapshotItem")
        extra = deepcopy(entity["fields"][2])
        extra.update({"name": "nickname", "required": False})
        entity["fields"].append(extra)

        changes = diff_canonical_ir(old, new)
        raw_before = semantic_ir_diff_to_json(changes)
        classifications = classify_ir_diff(changes, old, new)
        matching = [item for item in classifications if item.path.endswith("/fields/3")]
        self.assertEqual(1, len(matching))
        self.assertEqual("migration-required", matching[0].classification)
        self.assertEqual("entity.field-added", matching[0].rule)
        self.assertEqual([item.path for item in changes], [item.path for item in classifications])
        self.assertEqual(raw_before, semantic_ir_diff_to_json(changes))

    def test_unrepresented_sync_profile_semantics_remain_conditional(self) -> None:
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
        changes, classifications = self._classes(old, new)
        self.assertTrue(changes)
        self.assertEqual({"conditional"}, {item.classification for item in classifications})
        self.assertEqual({"unmodelled.review-required"}, {item.rule for item in classifications})


if __name__ == "__main__":
    unittest.main()
