#!/usr/bin/env python3
"""Regression checks for the normative M10.1 language-surface freeze."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "spec" / "language-surface-v1.json"
SCHEMA_PATH = ROOT / "spec" / "language-surface-v1.schema.json"


class LanguageSurfaceV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.by_kind = {item["kind"]: item for item in cls.contract["declaration_kinds"]}
        cls.modifiers = {item["name"]: item for item in cls.contract["modifiers"]}
        cls.examples = {item["id"]: item for item in cls.contract["examples"]}

    def test_contract_validates_against_schema(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        Draft202012Validator(self.schema).validate(self.contract)

    def test_inventory_matches_normative_grammar_declaration_surface(self) -> None:
        expected = {
            "app", "auth", "a11y", "privacy", "enum", "alias", "value", "union",
            "error", "entity", "view", "api", "policy", "query", "mutation", "event",
            "topic", "queue", "consumer", "projection", "workflow", "saga", "task",
            "schedule", "system", "service", "client", "tenant", "channel", "resource",
            "media", "rendition", "sync", "migration", "deployment", "frontend", "theme",
            "component", "page", "form", "action", "syncStatus", "seo", "nativeFunction",
            "nativeComponent", "fixture", "test", "scenario",
        }
        self.assertEqual(expected, set(self.by_kind))
        self.assertEqual(len(expected), len(self.contract["declaration_kinds"]))

    def test_name_policy_required_optional_none_are_closed_enum(self) -> None:
        self.assertEqual("required", self.by_kind["entity"]["name_policy"])
        self.assertEqual("none", self.by_kind["auth"]["name_policy"])
        allowed = {"required", "optional", "none"}
        self.assertTrue({item["name_policy"] for item in self.by_kind.values()} <= allowed)
        self.assertIn("optional", self.schema["$defs"]["declarationKind"]["properties"]["name_policy"]["enum"])

    def test_cardinality_notation_is_explicit_min_max(self) -> None:
        field = self.by_kind["entity"]["body_slots"][0]
        self.assertEqual({"min": 0, "max": None}, field["occurrence"])  # A*
        read = self.by_kind["query"]["body_slots"][0]
        self.assertEqual({"min": 0, "max": 1}, read["occurrence"])  # R?
        self.assertEqual({"min": 0, "max": 1}, self.by_kind["query"]["header_args_occurrence"])  # args?

    def test_type_optionality_is_separate_from_slot_cardinality(self) -> None:
        field_type = self.by_kind["entity"]["body_slots"][0]["type"]
        self.assertIs(field_type["optional"], False)
        self.assertIn("optional", self.schema["$defs"]["typeRef"]["required"])

    def test_modifier_target_and_arity_contracts(self) -> None:
        public_reason = self.modifiers["publicReason"]
        self.assertEqual(["query", "mutation"], public_reason["targets"])
        self.assertEqual({"min": 1, "max": 1}, public_reason["arity"])
        self.assertEqual("literal", public_reason["argument_mode"])
        required = self.modifiers["required"]
        self.assertEqual({"min": 0, "max": 0}, required["arity"])
        self.assertNotIn("query", required["targets"])

    def test_enum_is_first_class_body_slot(self) -> None:
        slot = self.by_kind["enum"]["body_slots"][0]
        self.assertEqual("enum_case", slot["value_mode"])
        self.assertEqual("required", slot["name_policy"])
        self.assertTrue(slot["unique"])

    def test_reference_projection_pet_id_is_resolved_fact(self) -> None:
        projection = self.examples["reference-projection-pet-id"]["facts"]["type"]
        self.assertEqual("reference", projection["kind"])
        self.assertEqual("Pet", projection["target"])
        self.assertEqual("id", projection["projection"])
        self.assertEqual("uuid", projection["resolved_type"])

    def test_literal_and_expression_modes_remain_distinct(self) -> None:
        migration = self.by_kind["migration"]
        self.assertEqual(["literal", "literal"], [arg["value_mode"] for arg in migration["header_args"]])
        self.assertEqual("expression", self.by_kind["query"]["body_slots"][0]["value_mode"])
        self.assertEqual("negative", self.examples["expression-in-literal-slot"]["classification"])

    def test_representative_golden_and_negative_cases_are_frozen(self) -> None:
        for fixture_id in ("user-entity", "migration", "public-reason-get-pet", "app-profile", "reference-projection-pet-id"):
            self.assertEqual("golden", self.examples[fixture_id]["classification"])
        for fixture_id in ("expression-in-literal-slot", "modifier-wrong-target", "duplicate-unique-slot"):
            self.assertEqual("negative", self.examples[fixture_id]["classification"])

    def test_legacy_relationship_forms_normalize_to_named_facts(self) -> None:
        self.assertTrue(self.by_kind["migration"]["legacy_forms"])
        self.assertEqual(["fromVersion", "toVersion"], [arg["name"] for arg in self.by_kind["migration"]["header_args"]])
        self.assertEqual(["service"], [arg["name"] for arg in self.by_kind["client"]["header_args"]])
        self.assertEqual(["topic", "messageType"], [arg["name"] for arg in self.by_kind["consumer"]["header_args"]])
        self.assertEqual(["sources", "target"], [arg["name"] for arg in self.by_kind["projection"]["header_args"]])


if __name__ == "__main__":
    unittest.main()
