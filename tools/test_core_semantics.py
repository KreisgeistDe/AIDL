from __future__ import annotations

import unittest
from pathlib import Path

from tools.core_bootstrap import TypeRef
from tools.core_semantics import (
    CoreContractError,
    infer_expression_type,
    load_semantic_registry,
    registry_digest,
    validate_source,
)


ROOT = Path(__file__).resolve().parents[1]
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

        undeclared = DOMAIN.replace(
            '      ordered: true,\n      uniqueByName: true,',
            '      order: 0,\n      ordered: true,\n      uniqueByName: true,',
            1,
        )
        with self.assertRaisesRegex(CoreContractError, "undeclared metadata: order"):
            load_semantic_registry(undeclared)

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
