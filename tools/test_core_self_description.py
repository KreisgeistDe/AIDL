from __future__ import annotations

import unittest
from pathlib import Path

from tools.core_self_description import (
    CoreSelfDescriptionError,
    compile_self_described_core,
    load_self_described_core,
)


ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "spec" / "core-self-description-v1.aidl"
CORE = CORE_PATH.read_text(encoding="utf-8")


class CoreSelfDescriptionTest(unittest.TestCase):
    def test_checked_in_self_description_compiles_deterministically(self) -> None:
        first = load_self_described_core()
        second = load_self_described_core()
        self.assertEqual(first, second)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertIn("declaration", first.contracts)
        self.assertIn("type", first.contracts)
        self.assertIn("enum", first.contracts)
        self.assertIn("entity", first.contracts)

    def test_no_permanent_definition_object_meta_model_remains_in_p2_source(self) -> None:
        forbidden = (
            "NamePolicy(kind:",
            "Cardinality(kind:",
            "ArgumentDefinition",
            "ModifierDefinition",
            "BodySlotDefinition",
            "DeclarationDefinition",
            "MetaCombinatorDefinition",
            "SemanticMetaModel",
        )
        for fragment in forbidden:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, CORE)

    def test_type_is_a_declaration_kind_and_base_types_are_aidl_defined(self) -> None:
        model = load_self_described_core()
        self.assertEqual(model.contracts["type"].produces, ("type",))
        declarations = {(item.kind, item.name) for item in model.declarations}
        for name in ("string", "bool", "int"):
            with self.subTest(name=name):
                self.assertIn(("type", name), declarations)
                self.assertIn(name, model.type_carriers)

    def test_enum_uses_same_general_produces_type_carrier_rule(self) -> None:
        model = load_self_described_core()
        self.assertEqual(model.contracts["enum"].produces, ("type",))
        self.assertIn("NamePolicy", model.type_carriers)
        example = next(item for item in model.declarations if item.name == "CoreEntityExample")
        state = next(item for item in example.body if item.name == "state")
        self.assertEqual(state.value.value.name, "NamePolicy")

    def test_entity_is_directly_self_described_without_host_kind_knowledge(self) -> None:
        model = load_self_described_core()
        entity = model.contracts["entity"]
        field = next(item for item in entity.body if item.body_type == "field")
        self.assertTrue(field.type_position)
        self.assertEqual(field.name_policy, "required")
        self.assertEqual({item.name for item in field.modifiers}, {"primary", "unique"})

        bootstrap_source = (ROOT / "tools" / "core_bootstrap.py").read_text(encoding="utf-8")
        compiler_source = (ROOT / "tools" / "core_self_description.py").read_text(encoding="utf-8")
        self.assertNotIn('declaration.kind == "entity"', bootstrap_source)
        self.assertNotIn('declaration.kind == "entity"', compiler_source)
        self.assertNotIn('declaration.kind == "enum"', compiler_source)

    def test_new_declaration_kind_needs_no_host_catalog_change(self) -> None:
        extended = CORE + """

declaration widget {
  body value: body(type-position, name(required), cardinal(1, 1))
}

widget Demo {
  value item: string
}
"""
        model = compile_self_described_core(extended)
        self.assertIn("widget", model.contracts)
        demo = next(item for item in model.declarations if item.name == "Demo")
        self.assertEqual(demo.kind, "widget")

    def test_undefined_kind_and_unresolved_type_carrier_fail_closed(self) -> None:
        with self.assertRaisesRegex(CoreSelfDescriptionError, "undefined declaration-kind"):
            compile_self_described_core(CORE + "\nmystery M {}\n")

        broken = CORE.replace("field state: NamePolicy", "field state: MissingType")
        with self.assertRaisesRegex(CoreSelfDescriptionError, "unresolved type carrier 'MissingType'"):
            compile_self_described_core(broken)

    def test_structural_cardinality_and_modifier_rules_fail_closed(self) -> None:
        no_case = CORE.replace(
            "enum NamePolicy {\n  case REQUIRED:\n  case OPTIONAL:\n  case FORBIDDEN:\n}",
            "enum NamePolicy {\n}",
        )
        with self.assertRaisesRegex(CoreSelfDescriptionError, "body-entry count violates cardinality"):
            compile_self_described_core(no_case)

        unknown_modifier = CORE.replace("field id: string @primary", "field id: string @unknown")
        with self.assertRaisesRegex(CoreSelfDescriptionError, "modifier 'unknown' is not declared"):
            compile_self_described_core(unknown_modifier)

    def test_duplicate_named_body_binding_fails_closed(self) -> None:
        duplicate = CORE.replace(
            "case REQUIRED:\n  case OPTIONAL:",
            "case REQUIRED:\n  case REQUIRED:",
        )
        with self.assertRaisesRegex(CoreSelfDescriptionError, "duplicate name 'REQUIRED'"):
            compile_self_described_core(duplicate)


if __name__ == "__main__":
    unittest.main()
