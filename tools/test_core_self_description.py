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
        self.assertFalse(payload["authorityInput"])
        self.assertEqual(payload["role"], "derived-non-authoritative-runtime-meta-ir")

    def test_direct_contracts_and_aidl_type_carriers_drive_semantics(self) -> None:
        model = load_self_described_core()
        for kind in ("declaration", "type", "enum", "entity", "compatibilityProjection"):
            self.assertIn(kind, model.contracts)
        for carrier in ("string", "bool", "int", "NamePolicy", "CardinalityLabel"):
            self.assertIn(carrier, model.type_carriers)
        entity = model.contracts["entity"]
        field = next(item for item in entity.body if item.body_type == "field")
        invariant = next(item for item in entity.body if item.body_type == "invariant")
        self.assertEqual(field.expected_type.name, "choice")
        self.assertEqual(invariant.expected_type.name, "expression")

    def test_no_definition_object_meta_model_is_normative_in_direct_source(self) -> None:
        for fragment in (
            "ArgumentDefinition",
            "ModifierDefinition",
            "BodySlotDefinition",
            "DeclarationDefinition",
            "MetaCombinatorDefinition",
            "SemanticMetaModel",
        ):
            self.assertNotIn(fragment, CORE)

    def test_new_kind_needs_no_host_catalog_and_invalid_carrier_fails_closed(self) -> None:
        extended = CORE + """

declaration widget(name: name(required)) {
  body value: body(type-position, name(required), cardinal(1, 1))
}
widget Demo {
  value item: string
}
"""
        model = compile_self_described_core(extended)
        self.assertIn("widget", model.contracts)
        broken = CORE.replace("field state: NamePolicy", "field state: MissingType")
        with self.assertRaisesRegex(CoreSelfDescriptionError, "unresolved type carrier"):
            compile_self_described_core(broken)

    def test_meta_ir_drift_fails_closed(self) -> None:
        drifted = META_IR_PATH.read_text(encoding="utf-8").replace(
            '"authorityInput": false', '"authorityInput": true', 1
        )
        with self.assertRaisesRegex(CoreSelfDescriptionError, "meta-IR drift"):
            check_semantic_meta_ir(CORE, drifted)


if __name__ == "__main__":
    unittest.main()
