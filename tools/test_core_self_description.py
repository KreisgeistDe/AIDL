from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.core_self_description import (
    CoreSelfDescriptionError,
    check_semantic_meta_ir,
    compile_self_described_core,
    load_self_described_core,
    semantic_meta_ir_text,
)

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "spec" / "core-self-description-v1.aidl"
META_IR_PATH = ROOT / "spec" / "core-meta-ir-v1.json"
CORE = CORE_PATH.read_text(encoding="utf-8")


class CoreSelfDescriptionTest(unittest.TestCase):
    def test_checked_in_self_description_and_meta_ir_are_deterministic(self) -> None:
        first = load_self_described_core()
        second = load_self_described_core()
        self.assertEqual(first, second)
        checked = META_IR_PATH.read_text(encoding="utf-8")
        self.assertEqual(checked, semantic_meta_ir_text(CORE))
        check_semantic_meta_ir(CORE, checked)
        payload = json.loads(checked)
        self.assertEqual(payload["schemaVersion"], 2)
        self.assertFalse(payload["authorityInput"])
        self.assertEqual(payload["role"], "derived-non-authoritative-runtime-meta-ir")
        self.assertNotIn("typeCarriers", payload)
        self.assertIn("predeclaredTypeSymbols", payload)

    def test_corrected_direct_contracts_cover_args_return_and_symbol_identity(self) -> None:
        model = load_self_described_core()
        for kind in ("declaration", "type", "enum", "entity", "query", "compatibilityProjection"):
            self.assertIn(kind, model.contracts)
        for symbol in ("string", "bool", "int", "NamePolicy", "CardinalityLabel", "myQuery"):
            self.assertIn(symbol, model.symbols)
        base = model.contracts["declaration"]
        enum = model.contracts["enum"]
        query = model.contracts["query"]
        entity = model.contracts["entity"]
        self.assertIsNotNone(base.arguments)
        self.assertEqual(base.result.name, "any")
        self.assertIsNone(enum.arguments)
        self.assertIsNone(enum.result)
        self.assertEqual(query.arguments.value_type.name, "type")
        self.assertEqual(query.result.name, "type")
        field = next(item for item in entity.body if item.body_type == "field")
        self.assertEqual(field.expected_type.name, "type")

    def test_required_acceptance_examples_compile_without_kind_specific_host_rules(self) -> None:
        self.assertNotIn("produces(", CORE)
        self.assertNotIn("type-position", CORE)
        self.assertIn("declaration declaration", CORE)
        self.assertIn("-> any", CORE)
        self.assertIn("declaration enum", CORE)
        self.assertIn("declaration query", CORE)
        self.assertIn("-> type", CORE)
        self.assertIn("type string {}", CORE)
        self.assertIn("type bool {}", CORE)
        self.assertIn("type int {}", CORE)
        self.assertIn("enum NamePolicy", CORE)
        self.assertIn("field state: NamePolicy", CORE)
        self.assertIn("query myQuery(id: Id) -> Page<myQuery>", CORE)
        load_self_described_core()

    def test_void_args_and_return_fail_closed(self) -> None:
        with self.assertRaisesRegex(CoreSelfDescriptionError, "Args=void"):
            compile_self_described_core(CORE.replace("enum NamePolicy {", "enum NamePolicy() {"))
        with self.assertRaisesRegex(CoreSelfDescriptionError, "Return=void"):
            compile_self_described_core(CORE.replace("enum NamePolicy {", "enum NamePolicy -> string {"))

    def test_named_symbol_typeref_resolution_is_generic_and_fails_closed(self) -> None:
        extended = CORE + """

declaration widget(name: name(required)) {
  body value: body(type, name(required), cardinal(1, 1))
}
widget Demo {
  value item: NamePolicy
}
"""
        model = compile_self_described_core(extended)
        self.assertIn("widget", model.contracts)
        self.assertIn("Demo", model.symbols)
        broken = CORE.replace("field state: NamePolicy", "field state: MissingType")
        with self.assertRaisesRegex(CoreSelfDescriptionError, "unresolved type symbol"):
            compile_self_described_core(broken)

    def test_no_definition_object_or_obsolete_carrier_meta_model_is_normative(self) -> None:
        for fragment in (
            "ArgumentDefinition",
            "ModifierDefinition",
            "BodySlotDefinition",
            "DeclarationDefinition",
            "MetaCombinatorDefinition",
            "SemanticMetaModel",
            "produces(type)",
            "type-position",
        ):
            self.assertNotIn(fragment, CORE)

    def test_meta_ir_drift_fails_closed(self) -> None:
        drifted = META_IR_PATH.read_text(encoding="utf-8").replace(
            '"authorityInput": false', '"authorityInput": true', 1
        )
        with self.assertRaisesRegex(CoreSelfDescriptionError, "meta-IR drift"):
            check_semantic_meta_ir(CORE, drifted)


if __name__ == "__main__":
    unittest.main()
