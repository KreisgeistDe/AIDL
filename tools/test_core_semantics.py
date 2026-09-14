from __future__ import annotations

import unittest
from pathlib import Path

from tools.core_bootstrap import BootstrapSyntaxError
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


def unit(body: str) -> str:
    return "module test\n" + body.lstrip("\n")


class CoreSemanticsTest(unittest.TestCase):
    def registry(self):
        return load_semantic_registry(DOMAIN)

    def codes(self, source: str) -> list[str]:
        return [item.code for item in validate_source(source, self.registry())]

    def test_registry_is_direct_core_derived_and_deterministic(self) -> None:
        registry = self.registry()
        self.assertIn("declaration", registry.declarations)
        self.assertIn("type", registry.declarations)
        self.assertEqual(
            registry.declarations["declaration"].name_policy,
            registry.declarations["type"].name_policy,
        )
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
            load_semantic_registry(direct_source=DIRECT + "\n", meta_ir_text=META_IR)
        with self.assertRaisesRegex(CoreContractError, "legacy Definition-object Core"):
            load_semantic_registry(core_source="legacy", core_projection="legacy")

    def test_declaration_bearing_legacy_semantic_modules_are_not_authority(self) -> None:
        with self.assertRaisesRegex(CoreContractError, "legacy Definition-object semantic modules"):
            load_semantic_registry(unit('declaration old(kind: string = "language") {}\n'))

    def test_valid_entity_uses_named_declaration_typerefs_and_modifiers(self) -> None:
        source = unit("""
enum LocalState {
  case READY
}
entity Parent {
  field active: bool @primary
  field state: LocalState
  field declarationKind: entity
  invariant: active
}
entity Child {
  field parent: ref<Parent> @unique
  field tags: list<string>
  field parentType: Parent
}
""")
        self.assertEqual(validate_source(source, self.registry()), ())

    def test_query_args_result_and_query_identity_use_same_named_symbol_rule(self) -> None:
        source = unit("""
type LocalId {}
declaration Page {}
query MyQuery(id: LocalId) -> Page<MyQuery> {}
entity Holder {
  field queryType: MyQuery
}
""")
        self.assertEqual(validate_source(source, self.registry()), ())

    def test_type_and_declaration_surface_spellings_share_one_meta_category(self) -> None:
        source = unit("""
type AliasSpelling {}
declaration DeclarationSpelling {}
entity E {
  field left: AliasSpelling
  field right: DeclarationSpelling
  field kind: declaration
}
""")
        self.assertEqual(validate_source(source, self.registry()), ())

    def test_absent_args_are_closed_zero_and_empty_parentheses_are_rejected(self) -> None:
        absent = unit("""
enum V {
  case A
}
""")
        explicit_empty = unit("enum V() { case A }\n")
        nonempty = unit("""
enum V(value: string) {
  case A
}
""")
        self.assertEqual(validate_source(absent, self.registry()), ())
        with self.assertRaisesRegex(BootstrapSyntaxError, "empty declaration argument list"):
            validate_source(explicit_empty, self.registry())
        self.assertIn("CORE-S035", self.codes(nonempty))

    def test_specialized_result_is_required_and_unexpected_result_fails_closed(self) -> None:
        missing_result = unit("query Q {}\n")
        self.assertIn("CORE-S036", self.codes(missing_result))
        unexpected_result = unit("""
enum V -> string {
  case A
}
""")
        self.assertIn("CORE-S005", self.codes(unexpected_result))

    def test_generic_declaration_refs_fail_closed_only_when_unresolved(self) -> None:
        unresolved = unit("""
entity E {
  field parent: ref<Missing>
}
""")
        self.assertIn("CORE-S021", self.codes(unresolved))
        named_enum_target = unit("""
enum V {
  case A
}
entity E {
  field target: ref<V>
}
""")
        self.assertEqual(validate_source(named_enum_target, self.registry()), ())

    def test_ambiguous_typeref_bases_fail_closed_for_nullable_generic_and_ref_paths(self) -> None:
        source = unit("""
entity Duplicate {}
enum Duplicate {
  case A
}
entity Holder {
  field direct: Duplicate?
  field generic: list<Duplicate?>
  field reference: ref<Duplicate>
}
""")
        diagnostics = validate_source(source, self.registry())
        ambiguous = [item for item in diagnostics if item.code == "CORE-S023"]
        self.assertEqual(len(ambiguous), 3)
        self.assertTrue(
            all("ambiguous declaration symbol 'Duplicate'" in item.message for item in ambiguous)
        )
        self.assertNotIn("CORE-S021", [item.code for item in diagnostics])
        self.assertNotIn("CORE-S022", [item.code for item in diagnostics])

    def test_ambiguous_result_typeref_is_order_independent(self) -> None:
        first = unit("""
entity Duplicate {}
enum Duplicate {
  case A
}
query Q -> Duplicate? {}
""")
        second = unit("""
enum Duplicate {
  case A
}
entity Duplicate {}
query Q -> Duplicate? {}
""")
        for source in (first, second):
            ambiguity = [
                item for item in validate_source(source, self.registry())
                if item.code == "CORE-S023"
            ]
            self.assertEqual(len(ambiguity), 1)
            self.assertIn("result of declaration query", ambiguity[0].message)

    def test_unknown_symbol_modifier_duplicate_name_and_order_fail(self) -> None:
        source = unit("""
entity E {
  invariant first: true
  field id: MissingType @primary @primary
  field id: string @missing
}
""")
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
        source = unit("""
entity E {
  invariant count: 1
}
""")
        self.assertIn("CORE-S015", self.codes(source))


if __name__ == "__main__":
    unittest.main()
