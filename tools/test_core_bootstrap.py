from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.core_bootstrap import (
    BootstrapSyntaxError,
    KERNEL_META_COMBINATORS,
    KERNEL_VERSION,
    check_projection,
    generate_projection,
    parse_bootstrap_source,
    parse_meta_combinator,
    parse_source,
    parse_type_ref,
    projection_text,
)

ROOT = Path(__file__).resolve().parents[1]


class CoreBootstrapTest(unittest.TestCase):
    def test_uniform_envelope_named_args_result_and_generic_type(self) -> None:
        program = parse_source(
            'export declaration Demo(kind: "meta") -> list<ref<sample>>? {\n'
            ' body x: string\n'
            '}\n'
        )
        declaration = program.declarations[0]
        self.assertTrue(declaration.exported)
        self.assertEqual(declaration.kind, "declaration")
        self.assertEqual(declaration.name, "Demo")
        self.assertEqual(dict(declaration.arguments)["kind"].value, "meta")
        self.assertEqual(declaration.result.name, "list")
        self.assertTrue(declaration.result.optional)
        self.assertEqual(declaration.result.arguments[0].name, "ref")

    def test_generic_envelope_does_not_require_host_known_declaration_kind(self) -> None:
        source = (
            'module example.foundation\n\n'
            'futurekind Example {\n'
            ' slot value: string\n'
            '}\n'
        )
        program = parse_bootstrap_source(source)
        self.assertEqual(program.declarations[0].kind, "futurekind")
        projection = generate_projection(source)
        self.assertEqual(projection["declarations"][0]["kind"], "futurekind")

    def test_typeref_recursive_and_optional_binds_complete_type(self) -> None:
        type_ref = parse_type_ref("outer<left<int>, right<ref<sample>?>>?")
        self.assertEqual(type_ref.name, "outer")
        self.assertTrue(type_ref.optional)
        self.assertEqual(type_ref.arguments[1].arguments[0].name, "ref")
        self.assertTrue(type_ref.arguments[1].arguments[0].optional)

    def test_finite_structural_meta_combinators_parse_deterministically(self) -> None:
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
        for source, expected_name in samples.items():
            with self.subTest(source=source):
                first = parse_meta_combinator(source)
                second = parse_meta_combinator(source)
                self.assertEqual(first, second)
                self.assertEqual(first.name, expected_name)

    def test_unknown_or_malformed_meta_combinators_fail_closed(self) -> None:
        for source in (
            "entity(required)",
            "name(",
            "type-position(extra)",
            "produces(type",
            "produces(type) trailing",
        ):
            with self.subTest(source=source):
                with self.assertRaises(BootstrapSyntaxError):
                    parse_meta_combinator(source)

    def test_duplicate_bootstrap_bindings_fail_closed_without_changing_ordinary_parse(self) -> None:
        duplicate_names = "first Same {}\nsecond Same {}\n"
        self.assertEqual(len(parse_source(duplicate_names).declarations), 2)
        with self.assertRaisesRegex(BootstrapSyntaxError, "duplicate or ambiguous bootstrap binding"):
            parse_bootstrap_source(duplicate_names)

        duplicate_imports = "module demo\nimport shared\nimport shared\n"
        self.assertEqual(parse_source(duplicate_imports).imports, ("shared", "shared"))
        with self.assertRaisesRegex(BootstrapSyntaxError, "duplicate or ambiguous bootstrap import binding"):
            parse_bootstrap_source(duplicate_imports)

    def test_inline_modifier_boundary_ignores_quoted_and_nested_at(self) -> None:
        program = parse_source(
            'declaration D {\n'
            ' body x: ["@inside", {text: "@nested"}] @tag(reason: "ok")\n'
            '}\n'
        )
        entry = program.declarations[0].body[0]
        self.assertEqual(entry.form, "inline")
        self.assertEqual(entry.value.to_json(), ["@inside", {"text": "@nested"}])
        self.assertEqual(entry.modifiers[0].name, "tag")
        self.assertEqual(dict(entry.modifiers[0].arguments)["reason"].value, "ok")

    def test_multiline_v1_balanced_value_then_modifiers(self) -> None:
        source = (
            'declaration D {\n'
            ' body x: {\n'
            '  [\n'
            '    "@value",\n'
            '    {nested: [1, 2]}\n'
            '  ]\n'
            '  @ordered\n'
            ' }\n'
            '}\n'
        )
        entry = parse_source(source).declarations[0].body[0]
        self.assertEqual(entry.form, "multiline-v1")
        self.assertEqual(entry.value.to_json()[0], "@value")
        self.assertEqual(entry.modifiers[0].name, "ordered")

    def test_multiline_v2_value_then_modifier_block(self) -> None:
        source = (
            'declaration D {\n'
            ' body x: list<ref<sample>>? {\n'
            '  @required\n'
            ' }\n'
            '}\n'
        )
        entry = parse_source(source).declarations[0].body[0]
        self.assertEqual(entry.form, "multiline-v2")
        self.assertEqual(entry.value.kind, "typeRef")
        self.assertEqual(entry.modifiers[0].name, "required")

    def test_negative_positional_modifier_argument_rejected(self) -> None:
        with self.assertRaises(BootstrapSyntaxError):
            parse_source(
                'declaration D {\n'
                ' body x: string @tag("bad")\n'
                '}\n'
            )

    def test_negative_unbalanced_generic_rejected(self) -> None:
        with self.assertRaises(BootstrapSyntaxError):
            parse_type_ref("list<ref<sample>")

    def test_negative_multiline_modifier_block_rejects_non_modifier_tail(self) -> None:
        with self.assertRaises(BootstrapSyntaxError):
            parse_source(
                'declaration D {\n'
                ' body x: value {\n'
                '  nope\n'
                ' }\n'
                '}\n'
            )

    def test_checked_in_legacy_runtime_core_is_kernel_parsable_and_projection_is_exact(self) -> None:
        core_path = ROOT / "spec" / "core.aidl"
        projection_path = ROOT / "spec" / "core-registry-v1.json"
        check_projection(core_path, projection_path)
        program = parse_bootstrap_source(core_path.read_text(encoding="utf-8"))
        names = {declaration.name for declaration in program.declarations}
        self.assertIn("DeclarationDefinition", names)
        self.assertIn("SemanticMetaModel", names)
        self.assertEqual({declaration.kind for declaration in program.declarations}, {"declaration"})

    def test_parsing_current_runtime_core_does_not_require_generated_registry(self) -> None:
        source = (ROOT / "spec" / "core.aidl").read_text(encoding="utf-8")
        first = parse_bootstrap_source(source)
        second = parse_bootstrap_source(source)
        self.assertEqual(first, second)
        self.assertGreater(len(first.declarations), 0)

    def test_kernel_contract_is_versioned_finite_and_domain_free(self) -> None:
        contract = json.loads(
            (ROOT / "spec" / "bootstrap-kernel-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["kernelVersion"], KERNEL_VERSION)
        self.assertEqual(
            tuple(item["name"] for item in contract["metaCombinators"]),
            KERNEL_META_COMBINATORS,
        )
        self.assertTrue(contract["authorityFirewall"]["directAidlDeclarationKindContractsAreNormative"])
        self.assertFalse(contract["authorityFirewall"]["generatedMetaIrOrRegistryIsAuthorityInput"])
        self.assertFalse(contract["authorityFirewall"]["concreteProducerKindCatalogOwnedByHost"])
        self.assertIn("concrete-declaration-kind-catalog", contract["excludes"])
        self.assertIn("concrete-category-to-schema-map", contract["excludes"])
        self.assertIn("name-policy-values", contract["excludes"])
        self.assertEqual(contract["directives"]["module"], "compilation-unit-identity-only")
        self.assertEqual(
            contract["bodyForms"],
            ["inline", "multiline-v1", "multiline-v2"],
        )
        carrier = contract["typeCarrierRule"]
        self.assertEqual(carrier["producer"], "produces(type)")
        self.assertFalse(carrier["hostKnowsConcreteProducerKinds"])
        self.assertTrue(carrier["recursiveGenericArgumentsUseSameRule"])

    def test_host_source_has_no_concrete_kind_or_category_semantic_table(self) -> None:
        source = (ROOT / "tools" / "core_bootstrap.py").read_text(encoding="utf-8")
        forbidden_fragments = (
            'declaration.kind == "entity"',
            'declaration.kind == "query"',
            'declaration.kind == "enum"',
            '"language": DeclarationDefinition',
            '"meta-combinator": MetaCombinatorDefinition',
            '"required", "optional", "forbidden"',
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)
        self.assertNotIn("core source may only contain declaration meta-definitions", source)

    def test_revision4_stays_compatibility_only_while_authority_correction_is_open(self) -> None:
        transition = json.loads(
            (ROOT / "spec" / "core-authority-transition-v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(transition["phase"], "self-description-correction-in-progress")
        self.assertEqual(
            transition["completedPhases"], ["D0", "I1", "I2", "V1", "G1"]
        )
        self.assertFalse(transition["revision4"]["permanentSemanticAuthority"])
        self.assertTrue(transition["revision4"]["productionUseRequiresCoreAuthorization"])
        self.assertTrue(transition["coreSource"]["projectWideAuthorityFlipComplete"])
        self.assertFalse(transition["coreSource"]["permanentAuthorityAfterCorrection"])
        self.assertEqual(
            transition["coreSelfDescription"]["path"],
            "spec/core-self-description-v1.aidl",
        )
        self.assertFalse(
            transition["coreSelfDescription"]["permanentDefinitionObjectAuthority"]
        )
        correction = transition["authorityCorrection"]
        self.assertTrue(correction["supersedesPermanentDefinitionObjectAuthorityDesign"])
        self.assertEqual(correction["p1"]["status"], "integrated")
        self.assertEqual(
            correction["p1"]["mainCommit"],
            "755b38f6edd4ebb2ad4a9be5da0195082b0a3cb9",
        )
        self.assertEqual(correction["p2"]["status"], "implemented")
        self.assertFalse(correction["p2"]["permanentDefinitionObjectAuthority"])
        self.assertTrue(correction["p2"]["enumInstancesValidAtTypePositions"])
        self.assertEqual(correction["p3"]["status"], "pending")
        self.assertEqual(correction["p4"]["status"], "pending")
        self.assertTrue(correction["semanticsDependentKotlinFrozen"])
        self.assertIn("PR-99", correction["frozenKotlinWorkIncludes"])
        self.assertFalse(transition["generatedProjection"]["authorityInput"])
        self.assertEqual(
            transition["nextAction"]["id"],
            "CORE-SELF-DESCRIPTION-P2-VALIDATION",
        )
        self.assertEqual(
            transition["nextAction"]["status"],
            "pending-independent-validation",
        )

    def test_projection_drift_fails_deterministically(self) -> None:
        source = (
            'module aidl.core\n\n'
            'declaration D(kind: "meta") {\n'
            ' body namePolicy: NamePolicy @required\n'
            '}\n'
        )
        expected = projection_text(source)
        self.assertEqual(expected, projection_text(source))
        with tempfile.TemporaryDirectory() as temp_dir:
            core_path = Path(temp_dir) / "core.aidl"
            projection_path = Path(temp_dir) / "core-registry-v1.json"
            core_path.write_text(source, encoding="utf-8")
            projection_path.write_text(expected, encoding="utf-8")
            check_projection(core_path, projection_path)
            projection_path.write_text(
                expected.replace('"kernelVersion": 1', '"kernelVersion": 2'),
                encoding="utf-8",
            )
            with self.assertRaises(BootstrapSyntaxError):
                check_projection(core_path, projection_path)


if __name__ == "__main__":
    unittest.main()
