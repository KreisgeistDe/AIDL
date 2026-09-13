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
        self.assertEqual(program.declarations[0].kind, "futurekind")
        type_ref = parse_type_ref("outer<left<int>, right<ref<sample>?>>?")
        self.assertEqual(type_ref.name, "outer")
        self.assertTrue(type_ref.optional)

    def test_finite_structural_meta_combinators_parse_and_unknown_fails(self) -> None:
        samples = {
            "name(required)": "name",
            "args(cardinal(optional))": "args",
            "body(type-position, cardinal(many))": "body",
            "cardinal(optional)": "cardinal",
            "modifier(cardinal(optional))": "modifier",
            "type-position": "type-position",
            "produces(type)": "produces",
        }
        self.assertEqual(tuple(samples.values()), KERNEL_META_COMBINATORS)
        for source, expected in samples.items():
            self.assertEqual(parse_meta_combinator(source).name, expected)
        with self.assertRaises(BootstrapSyntaxError):
            parse_meta_combinator("entity(required)")

    def test_duplicate_bindings_fail_only_bootstrap_parse(self) -> None:
        duplicate = "first Same {}\nsecond Same {}\n"
        self.assertEqual(len(parse_source(duplicate).declarations), 2)
        with self.assertRaisesRegex(BootstrapSyntaxError, "duplicate or ambiguous bootstrap binding"):
            parse_bootstrap_source(duplicate)

    def test_kernel_contract_remains_finite_and_has_no_concrete_kind_catalog(self) -> None:
        contract = json.loads((ROOT / "spec" / "bootstrap-kernel-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["kernelVersion"], KERNEL_VERSION)
        self.assertEqual(tuple(item["name"] for item in contract["metaCombinators"]), KERNEL_META_COMBINATORS)
        self.assertTrue(contract["authorityFirewall"]["directAidlDeclarationKindContractsAreNormative"])
        self.assertFalse(contract["authorityFirewall"]["generatedMetaIrOrRegistryIsAuthorityInput"])
        self.assertFalse(contract["authorityFirewall"]["concreteProducerKindCatalogOwnedByHost"])
        self.assertIn("concrete-declaration-kind-catalog", contract["excludes"])

    def test_p3_transition_reconciles_integrated_p2_and_freezes_p4_kotlin(self) -> None:
        transition = json.loads((ROOT / "spec" / "core-authority-transition-v1.json").read_text(encoding="utf-8"))
        correction = transition["authorityCorrection"]
        self.assertEqual(correction["p2"]["status"], "integrated")
        self.assertEqual(correction["p2"]["mainCommit"], "7280f01a2c97b004c79cd0a2e598513bfa183ac0")
        self.assertEqual(correction["p3"]["status"], "implemented")
        self.assertFalse(correction["p3"]["legacyDefinitionObjectRuntimeAuthority"])
        self.assertEqual(correction["p4"]["status"], "pending")
        self.assertTrue(correction["semanticsDependentKotlinFrozen"])
        self.assertIn("PR-99", correction["frozenKotlinWorkIncludes"])
        self.assertFalse(transition["coreMetaIr"]["authorityInput"])
        self.assertEqual(transition["nextAction"]["id"], "CORE-SELF-DESCRIPTION-P3-VALIDATION")
        self.assertEqual(transition["nextAction"]["status"], "pending-independent-validation")


if __name__ == "__main__":
    unittest.main()
