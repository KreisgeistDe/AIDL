from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.core_bootstrap import (
    BootstrapSyntaxError,
    KERNEL_META_COMBINATORS,
    KERNEL_VERSION,
    parse_bootstrap_source,
    parse_meta_combinator,
    parse_source,
    parse_type_ref,
)

ROOT = Path(__file__).resolve().parents[1]


class CoreBootstrapTest(unittest.TestCase):
    def test_generic_envelope_and_recursive_typeref_are_domain_free(self) -> None:
        program = parse_bootstrap_source("futurekind Example {\n slot value: string\n}\n")
        declaration = program.declarations[0]
        self.assertEqual(declaration.kind, "futurekind")
        self.assertFalse(declaration.arguments_present)
        present_empty = parse_source("futurekind Example() {}\n").declarations[0]
        self.assertTrue(present_empty.arguments_present)
        self.assertEqual(present_empty.arguments, ())
        type_ref = parse_type_ref("outer<left<int>, right<ref<sample>?>>?")
        self.assertEqual(type_ref.name, "outer")
        self.assertTrue(type_ref.optional)

    def test_finite_structural_meta_combinators_parse_and_obsolete_markers_fail(self) -> None:
        samples = {
            "name(required)": "name",
            "args(type, cardinal(optional))": "args",
            "body(type, name(required), cardinal(many))": "body",
            "cardinal(optional)": "cardinal",
            "modifier(primary, cardinal(optional))": "modifier",
        }
        self.assertEqual(tuple(samples.values()), KERNEL_META_COMBINATORS)
        for source, expected in samples.items():
            self.assertEqual(parse_meta_combinator(source).name, expected)
        for obsolete in ("produces(type)", "type-position"):
            with self.assertRaises(BootstrapSyntaxError):
                parse_meta_combinator(obsolete)
        with self.assertRaises(BootstrapSyntaxError):
            parse_meta_combinator("entity(required)")

    def test_duplicate_bindings_fail_only_bootstrap_parse(self) -> None:
        duplicate = "first Same {}\nsecond Same {}\n"
        self.assertEqual(len(parse_source(duplicate).declarations), 2)
        with self.assertRaisesRegex(BootstrapSyntaxError, "duplicate or ambiguous bootstrap binding"):
            parse_bootstrap_source(duplicate)

    def test_kernel_contract_is_finite_and_has_no_kind_or_producer_catalog(self) -> None:
        contract = json.loads((ROOT / "spec" / "bootstrap-kernel-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["kernelVersion"], KERNEL_VERSION)
        self.assertEqual(tuple(item["name"] for item in contract["metaCombinators"]), KERNEL_META_COMBINATORS)
        self.assertTrue(contract["authorityFirewall"]["directAidlDeclarationKindContractsAreNormative"])
        self.assertFalse(contract["authorityFirewall"]["generatedMetaIrOrRegistryIsAuthorityInput"])
        self.assertFalse(contract["authorityFirewall"]["concreteDeclarationKindCatalogOwnedByHost"])
        self.assertFalse(contract["authorityFirewall"]["producerCapabilitySystemOwnedByHost"])
        self.assertEqual(contract["typeRef"]["carrierIdentity"], "generic-visible-named-declaration-symbol")
        self.assertIn("producer-carrier-capability-system", contract["excludes"])
        self.assertIn("type-position-marker", contract["excludes"])

    def test_transition_freezes_p4_while_semantic_correction_is_validated(self) -> None:
        transition = json.loads((ROOT / "spec" / "core-authority-transition-v1.json").read_text(encoding="utf-8"))
        correction = transition["authorityCorrection"]
        self.assertEqual(correction["durableStateReconciliation"]["mainCommit"], "bb8fb6ff9eb18429c94e9982a9e8d3e03a7ef48d")
        self.assertTrue(correction["semanticCorrection"]["producesRemoved"])
        self.assertTrue(correction["semanticCorrection"]["typePositionRemoved"])
        self.assertEqual(correction["semanticCorrection"]["typeRefCarrierIdentity"], "generic-visible-named-declaration-symbol")
        self.assertEqual(correction["p4"]["status"], "frozen")
        self.assertTrue(correction["semanticsDependentKotlinFrozen"])
        self.assertIn("PR-99", correction["frozenKotlinWorkIncludes"])
        self.assertFalse(transition["coreMetaIr"]["authorityInput"])
        self.assertEqual(transition["nextAction"]["id"], "CORE-SELF-DESCRIPTION-CORRECTION-VALIDATION")
        self.assertEqual(transition["nextAction"]["status"], "pending-independent-exact-head-validation")


if __name__ == "__main__":
    unittest.main()
