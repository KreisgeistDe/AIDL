from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.core_bootstrap import (
    BootstrapSyntaxError,
    KERNEL_VERSION,
    check_projection,
    parse_source,
    parse_type_ref,
    projection_text,
)

ROOT = Path(__file__).resolve().parents[1]


class CoreBootstrapTest(unittest.TestCase):
    def test_uniform_envelope_named_args_result_and_generic_type(self) -> None:
        program = parse_source(
            'export declaration Demo(kind: "meta") -> list<ref<entity>>? {\n'
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

    def test_typeref_recursive_and_optional_binds_complete_type(self) -> None:
        type_ref = parse_type_ref("outer<left<int>, right<ref<entity>?>>?")
        self.assertEqual(type_ref.name, "outer")
        self.assertTrue(type_ref.optional)
        self.assertEqual(type_ref.arguments[1].arguments[0].name, "ref")
        self.assertTrue(type_ref.arguments[1].arguments[0].optional)

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
            ' body x: list<ref<entity>>? {\n'
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
            parse_type_ref("list<ref<entity>")

    def test_negative_multiline_modifier_block_rejects_non_modifier_tail(self) -> None:
        with self.assertRaises(BootstrapSyntaxError):
            parse_source(
                'declaration D {\n'
                ' body x: value {\n'
                '  nope\n'
                ' }\n'
                '}\n'
            )

    def test_checked_in_core_is_kernel_parsable_and_projection_is_exact(self) -> None:
        core_path = ROOT / "spec" / "core.aidl"
        projection_path = ROOT / "spec" / "core-registry-v1.json"
        check_projection(core_path, projection_path)
        program = parse_source(core_path.read_text(encoding="utf-8"))
        names = {declaration.name for declaration in program.declarations}
        self.assertTrue(
            {
                "NamePolicy",
                "Cardinality",
                "TypeRef",
                "ArgumentDefinition",
                "ModifierDefinition",
                "BodySlotDefinition",
                "DeclarationDefinition",
                "MetaCombinatorDefinition",
                "SemanticMetaModel",
                "declaration",
                "body",
            }.issubset(names)
        )
        self.assertEqual({declaration.kind for declaration in program.declarations}, {"declaration"})

    def test_kernel_contract_is_versioned_and_domain_free(self) -> None:
        contract = json.loads(
            (ROOT / "spec" / "bootstrap-kernel-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["kernelVersion"], KERNEL_VERSION)
        self.assertNotIn("domain-declaration-catalog", contract["owns"])
        self.assertIn("domain-declaration-catalog", contract["excludes"])
        self.assertEqual(
            contract["bodyForms"],
            ["inline", "multiline-v1", "multiline-v2"],
        )

    def test_revision4_is_transition_evidence_not_second_core_authority(self) -> None:
        transition = json.loads(
            (ROOT / "spec" / "core-authority-transition-v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(transition["phase"], "V1")
        self.assertEqual(transition["completedPhases"], ["D0", "I1", "I2"])
        self.assertFalse(transition["revision4"]["permanentSemanticAuthority"])
        self.assertTrue(
            transition["revision4"]["remainsProductionCompatibilityOracleUntilG1"]
        )
        self.assertFalse(transition["coreSource"]["projectWideAuthorityFlipComplete"])
        self.assertNotIn(
            "V1-independent-broad-validation",
            transition["blockedUntilSeparatePhases"],
        )
        self.assertIn(
            "G1-project-wide-authority-flip",
            transition["blockedUntilSeparatePhases"],
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
