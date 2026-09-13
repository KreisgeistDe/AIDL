from __future__ import annotations

import unittest
from pathlib import Path

from tools.core_bootstrap import TypeRef, projection_text
from tools.core_semantics import (
    CoreContractError,
    infer_expression_type,
    load_semantic_registry,
    registry_digest,
    validate_source,
)


ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "spec" / "core.aidl").read_text(encoding="utf-8")
PROJECTION = (ROOT / "spec" / "core-registry-v1.json").read_text(encoding="utf-8")
DOMAIN = (ROOT / "spec" / "core.domain.aidl").read_text(encoding="utf-8")


EXTRA_CONTRACTS = """
module aidl.test.contracts
import aidl.core

declaration view(kind: "language") {
  body namePolicy: "required"
  body arguments: []
  body result: null
  body slots: []
  body modifiers: []
}

declaration sample(kind: "language") {
  body namePolicy: "required"
  body arguments: [
    {name: "tag", type: string, cardinality: {min: 0, max: 1}},
    {name: "item", type: int, cardinality: {min: 1, max: null}}
  ]
  body result: null
  body slots: [
    {
      bodyType: "value",
      namePolicy: "forbidden",
      valueType: int,
      cardinality: {min: 1, max: 1},
      ordered: true,
      uniqueByName: false,
      modifiers: []
    }
  ]
  body modifiers: []
}
"""


class CoreSemanticsTest(unittest.TestCase):
    def registry(self):
        return load_semantic_registry(DOMAIN, EXTRA_CONTRACTS)

    def codes(self, source: str) -> list[str]:
        return [item.code for item in validate_source(source, self.registry())]

    def test_domain_contracts_are_aidl_owned_and_digest_is_deterministic(self) -> None:
        registry = self.registry()
        self.assertIn("entity", registry.declarations)
        self.assertEqual(registry.combinators["choice"].behavior, "choice")
        self.assertEqual(registry.combinators["ref"].behavior, "declaration-ref-kind")
        self.assertIn("primary", registry.modifiers)
        self.assertEqual(registry_digest(registry), registry_digest(self.registry()))

    def test_loader_requires_exact_core_projection(self) -> None:
        self.assertEqual(PROJECTION, projection_text(CORE))
        with self.assertRaisesRegex(CoreContractError, "Core projection drift"):
            load_semantic_registry(
                DOMAIN,
                core_source=CORE,
                core_projection=PROJECTION + " ",
            )

    def test_core_owned_required_and_optional_meta_fields_drive_loading(self) -> None:
        sparse = """
module aidl.test.sparse
import aidl.core

declaration sparseModifier(kind: "modifier") {
  body targets: ["field"]
  body cardinality: {min: 0}
}

declaration sparseLanguage(kind: "language") {
  body namePolicy: "required"
}
"""
        registry = load_semantic_registry(sparse)
        self.assertEqual(registry.modifiers["sparseModifier"].arguments, ())
        self.assertIsNone(registry.modifiers["sparseModifier"].cardinality.maximum)
        self.assertEqual(registry.declarations["sparseLanguage"].slots, ())

        missing = sparse.replace("  body cardinality: {min: 0}\n", "")
        with self.assertRaisesRegex(
            CoreContractError,
            "ModifierDefinition missing required metadata: cardinality",
        ):
            load_semantic_registry(missing)

    def test_semantic_category_mapping_is_core_owned(self) -> None:
        changed_core = CORE.replace(
            '"modifier": ModifierDefinition',
            '"modifier": MetaCombinatorDefinition',
        )
        changed_projection = projection_text(changed_core)
        with self.assertRaisesRegex(
            CoreContractError,
            "MetaCombinatorDefinition contains undeclared metadata: cardinality, targets",
        ):
            load_semantic_registry(
                DOMAIN,
                core_source=changed_core,
                core_projection=changed_projection,
            )

    def test_undeclared_argument_definition_metadata_fails_closed(self) -> None:
        invalid = EXTRA_CONTRACTS.replace(
            '{name: "tag", type: string, cardinality: {min: 0, max: 1}}',
            '{name: "tag", type: string, cardinality: {min: 0, max: 1}, extra: true}',
        )
        with self.assertRaisesRegex(
            CoreContractError,
            "ArgumentDefinition contains undeclared metadata: extra",
        ):
            load_semantic_registry(invalid)

    def test_undeclared_modifier_definition_metadata_fails_closed(self) -> None:
        invalid = DOMAIN.replace(
            '  body cardinality: {min: 0, max: 1}\n}',
            '  body cardinality: {min: 0, max: 1}\n  body extra: true\n}',
            1,
        )
        with self.assertRaisesRegex(
            CoreContractError,
            "ModifierDefinition contains undeclared metadata: extra",
        ):
            load_semantic_registry(invalid)

    def test_undeclared_body_slot_definition_metadata_fails_closed(self) -> None:
        invalid = DOMAIN.replace(
            '      ordered: true,\n      uniqueByName: true,',
            '      order: 0,\n      ordered: true,\n      uniqueByName: true,',
            1,
        )
        with self.assertRaisesRegex(
            CoreContractError,
            "BodySlotDefinition contains undeclared metadata: order",
        ):
            load_semantic_registry(invalid)

    def test_undeclared_declaration_definition_metadata_fails_closed(self) -> None:
        invalid = EXTRA_CONTRACTS.replace(
            '  body modifiers: []\n}',
            '  body modifiers: []\n  body extra: true\n}',
            1,
        )
        with self.assertRaisesRegex(
            CoreContractError,
            "DeclarationDefinition contains undeclared metadata: extra",
        ):
            load_semantic_registry(invalid)

    def test_undeclared_meta_combinator_metadata_fails_closed(self) -> None:
        invalid = DOMAIN.replace(
            '  body arguments: {min: 2, max: null}\n}',
            '  body arguments: {min: 2, max: null}\n  body extra: true\n}',
            1,
        )
        with self.assertRaisesRegex(
            CoreContractError,
            "MetaCombinatorDefinition contains undeclared metadata: extra",
        ):
            load_semantic_registry(invalid)

    def test_valid_entity_field_modifiers_ref_and_invariant(self) -> None:
        source = """
entity Parent {
  field active: bool @primary
  invariant: active
}

entity Child {
  field parent: ref<Parent> @unique
}
"""
        self.assertEqual(validate_source(source, self.registry()), ())

    def test_name_policy_cardinality_variadic_and_forbidden_slot_name(self) -> None:
        valid = """
sample S(tag: "x", item: 1, item: 2) {
  value: 7
}
"""
        self.assertEqual(validate_source(valid, self.registry()), ())

        invalid = """
sample S {
  value named: 7
}
"""
        diagnostics = validate_source(invalid, self.registry())
        self.assertIn("CORE-S004", [item.code for item in diagnostics])
        self.assertIn("CORE-S002", [item.code for item in diagnostics])
        self.assertTrue(all(item.line >= 1 and item.column >= 1 for item in diagnostics))

    def test_unknown_slot_duplicate_unique_name_and_order_violation(self) -> None:
        source = """
entity E {
  invariant first: true
  field id: uuid
  field id: string
  nope x: int
}
"""
        diagnostics = validate_source(source, self.registry())
        codes = [item.code for item in diagnostics]
        self.assertIn("CORE-S007", codes)
        self.assertIn("CORE-S008", codes)
        self.assertIn("CORE-S006", codes)
        ordering = next(item for item in diagnostics if item.code == "CORE-S007")
        self.assertEqual(ordering.line, 4)
        self.assertGreaterEqual(ordering.column, 1)
        self.assertEqual(
            ordering.expected,
            "ordered BodySlot sequence: field before invariant",
        )

    def test_body_slot_order_comes_from_normative_sequence_not_host_order_key(self) -> None:
        self.assertNotIn("order:", DOMAIN)
        reversed_source = """
entity E {
  invariant first: true
  field id: uuid
}
"""
        self.assertIn("CORE-S007", self.codes(reversed_source))

    def test_modifier_allowlist_targets_and_cardinality(self) -> None:
        source = """
entity E {
  field id: uuid @primary @primary
  field name: string @missing
}
"""
        codes = self.codes(source)
        self.assertIn("CORE-S033", codes)
        self.assertIn("CORE-S030", codes)

    def test_ref_resolution_unresolved_and_wrong_kind(self) -> None:
        unresolved = """
entity E {
  field parent: ref<Missing>
}
"""
        self.assertIn("CORE-S012", self.codes(unresolved))

        wrong_kind = """
view V {}
entity E {
  field target: ref<V>
}
"""
        self.assertIn("CORE-S013", self.codes(wrong_kind))

    def test_recursive_generic_typeref_validation(self) -> None:
        source = """
entity E {
  field good: list<uuid>?
  field bad: list<Missing>
}
"""
        diagnostics = validate_source(source, self.registry())
        self.assertIn("CORE-S022", [item.code for item in diagnostics])
        self.assertTrue(any("Missing" in item.message for item in diagnostics))

    def test_expression_inference_and_assignability(self) -> None:
        env = {"active": TypeRef("bool"), "deleted": TypeRef("bool")}
        inferred, error = infer_expression_type("active && !deleted", env)
        self.assertEqual((inferred, error), ("bool", None))

        inferred, error = infer_expression_type("active == 1", env)
        self.assertIsNone(inferred)
        self.assertIn("incompatible", error or "")

        source = """
entity E {
  invariant count: 1
}
"""
        self.assertIn("CORE-S015", self.codes(source))

    def test_diagnostics_include_expected_contract(self) -> None:
        diagnostics = validate_source("entity {}\n", self.registry())
        self.assertEqual(diagnostics[0].code, "CORE-S001")
        self.assertEqual(diagnostics[0].expected, "NamePolicy required")
        self.assertEqual(diagnostics[0].line, 1)


if __name__ == "__main__":
    unittest.main()
