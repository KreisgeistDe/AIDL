from __future__ import annotations

import unittest
from pathlib import Path

from tools.core_semantics import (
    CoreContractError,
    infer_expression_type,
    load_semantic_registry,
    registry_digest,
    validate_source,
)

ROOT = Path(__file__).resolve().parents[1]
DIRECT = (ROOT / "spec" / "core-self-description-v1.aidl").read_text(encoding="utf-8")
META_IR = (ROOT / "spec" / "core-meta-ir-v1.json").read_text(encoding="utf-8")
DOMAIN = (ROOT / "spec" / "core.domain.aidl").read_text(encoding="utf-8")


class CoreSemanticsTest(unittest.TestCase):
    def registry(self):
        return load_semantic_registry(DOMAIN)

    def codes(self, source: str) -> list[str]:
        return [item.code for item in validate_source(source, self.registry())]

    def test_registry_is_direct_core_derived_and_deterministic(self) -> None:
        registry = self.registry()
        self.assertIn("entity", registry.declarations)
        self.assertIn("enum", registry.declarations)
        self.assertIn("query", registry.declarations)
        self.assertIn("compatibilityProjection", registry.declarations)
        self.assertEqual(registry.combinators["choice"].behavior, "choice")
        self.assertEqual(registry.combinators["ref"].behavior, "declaration-ref-kind")
        self.assertIn("primary", registry.modifiers)
        self.assertEqual(registry_digest(registry), registry_digest(self.registry()))

    def test_meta_ir_and_direct_source_drift_fail_closed(self) -> None:
        with self.assertRaisesRegex(CoreContractError, "meta-IR drift"):
            load_semantic_registry(
                direct_source=DIRECT + "\n",
                meta_ir_text=META_IR,
            )
        with self.assertRaisesRegex(CoreContractError, "legacy Definition-object Core"):
            load_semantic_registry(core_source="legacy", core_projection="legacy")

    def test_declaration_bearing_legacy_semantic_modules_are_not_authority(self) -> None:
        with self.assertRaisesRegex(CoreContractError, "legacy Definition-object semantic modules"):
            load_semantic_registry('declaration old(kind: "language") {}\n')

    def test_valid_entity_uses_named_symbol_typerefs_and_modifiers(self) -> None:
        source = """
enum LocalState {
  case READY:
}
entity Parent {
  field active: bool @primary
  field state: LocalState
  invariant: active
}

entity Child {
  field parent: ref<Parent> @unique
  field tags: list<string>
}
"""
        self.assertEqual(validate_source(source, self.registry()), ())

    def test_query_args_and_result_use_same_generic_named_symbol_rule(self) -> None:
        source = """
type LocalId {}
type Page {}
query MyQuery(id: LocalId) -> Page<MyQuery> {
}
"""
        self.assertEqual(validate_source(source, self.registry()), ())

    def test_void_args_and_result_fail_closed(self) -> None:
        explicit_empty_args = """
enum V() {
  case A:
}
"""
        self.assertIn("CORE-S035", self.codes(explicit_empty_args))
        unexpected_result = """
enum V -> string {
  case A:
}
"""
        self.assertIn("CORE-S005", self.codes(unexpected_result))

    def test_generic_declaration_refs_fail_closed_only_when_unresolved(self) -> None:
        unresolved = """
entity E {
  field parent: ref<Missing>
}
"""
        self.assertIn("CORE-S021", self.codes(unresolved))

        named_enum_target = """
enum V {
  case A:
}
entity E {
  field target: ref<V>
}
"""
        self.assertEqual(validate_source(named_enum_target, self.registry()), ())

    def test_unknown_symbol_modifier_duplicate_name_and_order_fail(self) -> None:
        source = """
entity E {
  invariant first: true
  field id: MissingType @primary @primary
  field id: string @missing
}
"""
        codes = self.codes(source)
        self.assertIn("CORE-S007", codes)
        self.assertIn("CORE-S008", codes)
        self.assertIn("CORE-S022", codes)
        self.assertIn("CORE-S033", codes)
        self.assertIn("CORE-S030", codes)

    def test_expression_inference_is_preserved(self) -> None:
        inferred, error = infer_expression_type("active && !deleted", {})
        self.assertIsNone(inferred)
        self.assertIsNotNone(error)
        source = """
entity E {
  invariant count: 1
}
"""
        self.assertIn("CORE-S015", self.codes(source))


if __name__ == "__main__":
    unittest.main()
