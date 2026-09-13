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

    def test_revision4_is_core_authorized_compatibility_not_semantic_authority(self) -> None:
        transition = json.loads(
            (ROOT / "spec" / "core-authority-transition-v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(transition["phase"], "complete")
        self.assertEqual(
            transition["completedPhases"], ["D0", "I1", "I2", "V1", "G1"]
        )
        self.assertFalse(transition["revision4"]["permanentSemanticAuthority"])
        self.assertFalse(
            transition["revision4"]["remainsProductionCompatibilityOracleUntilG1"]
        )
        self.assertTrue(transition["revision4"]["productionUseRequiresCoreAuthorization"])
        self.assertTrue(transition["coreSource"]["projectWideAuthorityFlipComplete"])
        self.assertTrue(transition["integrationState"]["g1IntegratedOnMain"])
        self.assertEqual(
            transition["integrationState"]["mainCommit"],
            "b90c44912d7f82450c2190473035bce14bef828d",
        )
        self.assertEqual(transition["nextGate"]["id"], "M10.5-01")
        self.assertEqual(transition["nextGate"]["status"], "complete")
        self.assertFalse(transition["nextGate"]["requiresPostG1CurrentMainRefreshRevalidation"])
        self.assertFalse(transition["nextGate"]["laterSemanticKotlinBlockedUntilComplete"])
        evidence = transition["nextGate"]["historicalMergedEvidence"]
        self.assertEqual(evidence["pr"], 77)
        self.assertEqual(
            evidence["mergeCommit"],
            "1574963eed95a2f80c1cdc47f48a3eaa39df4a4b",
        )
        self.assertEqual(evidence["role"], "historical-provisional-parity-evidence")
        self.assertFalse(evidence["pendingIntegrationTarget"])
        accepted = transition["nextGate"]["postG1CurrentMainRefresh"]
        self.assertEqual(
            accepted["baselineBaseCommit"],
            "f471fd9c1ee808ff9557d4a9f6bdf8b092d9c2c5",
        )
        self.assertEqual(accepted["manifest"], "spec/m10-5-parity-manifest.json")
        self.assertEqual(accepted["implementationPr"], 94)
        self.assertEqual(
            accepted["implementationHead"],
            "9228f94302c1fbbc6cd5fc0b5fc7af9231071d76",
        )
        self.assertTrue(accepted["independentlyValidated"])
        self.assertTrue(accepted["integratedOnMain"])
        self.assertEqual(
            accepted["mainCommit"],
            "fcfc3fc92e6577270dbf89be22c4ddfac5c187a9",
        )
        reconciliation = transition["nextGate"]["statusReconciliation"]
        self.assertEqual(reconciliation["implementationPr"], 95)
        self.assertEqual(
            reconciliation["implementationHead"],
            "2a26b1deff1baa5504e5e714222e8726181c7d5a",
        )
        self.assertTrue(reconciliation["independentlyValidated"])
        self.assertTrue(reconciliation["integratedOnMain"])
        self.assertEqual(
            reconciliation["mainCommit"],
            "3fa5c969338d1f0dc6b9bc573e70c7004f53aceb",
        )
        self.assertEqual(transition["nextAction"]["id"], "M10.5-02")
        self.assertEqual(transition["nextAction"]["status"], "dependency-ready")

    def test_post_g1_durable_status_is_consistent_across_authority_sources(self) -> None:
        transition = json.loads(
            (ROOT / "spec" / "core-authority-transition-v1.json").read_text(
                encoding="utf-8"
            )
        )
        todo = (ROOT / "TODO.md").read_text(encoding="utf-8")
        authority_doc = (ROOT / "docs" / "core-language-authority-gate.md").read_text(
            encoding="utf-8"
        )
        parity_doc = (ROOT / "docs" / "m10-5-parity-evidence.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("G1", transition["completedPhases"])
        self.assertTrue(transition["integrationState"]["g1IntegratedOnMain"])
        self.assertNotIn("candidateState", transition)
        self.assertIn("- [x] **G1 — Core authority integration/flip.**", todo)
        self.assertNotIn("G1 remains unchecked", todo)
        self.assertIn("- [x] **M10.5-01 — Refresh the Python parity baseline", todo)
        self.assertIn("PR #94", todo)
        self.assertIn("9228f94302c1fbbc6cd5fc0b5fc7af9231071d76", todo)
        self.assertIn("fcfc3fc92e6577270dbf89be22c4ddfac5c187a9", todo)
        self.assertIn("PR #77 remains already-merged historical/provisional evidence", todo)
        self.assertIn("PR #95", todo)
        self.assertIn("2a26b1deff1baa5504e5e714222e8726181c7d5a", todo)
        self.assertIn("3fa5c969338d1f0dc6b9bc573e70c7004f53aceb", todo)
        self.assertIn("- [x] **M10.5-02 — Kotlin Multiplatform compiler skeleton / Gate 02.**", todo)
        self.assertIn("dfb3af756f2c726f925ee16bddecebe004e5c781", todo)
        self.assertIn("5ca01218246982e4b21701254bf3f1844b103014", todo)
        self.assertIn("- [ ] **M10.5-03 and later Kotlin semantic work.**", todo)
        self.assertIn("Gate 03 remains incomplete", todo)
        self.assertNotIn("Dependency-ready next roadmap action", todo)
        self.assertNotIn("blocked until this durable-state correction", todo.lower())
        self.assertNotIn("PR #77 remains candidate compatibility evidence only and is not validated or integrated", authority_doc)
        self.assertIn("D0, I1, I2, V1 and G1 are complete and integrated.", authority_doc)
        self.assertIn("PR #77 remains already-merged historical/provisional M10.5-01 parity evidence", authority_doc)
        self.assertIn("not a pending integration target", authority_doc)
        self.assertIn("M10.5-01 refresh is complete", authority_doc)
        self.assertIn("3fa5c969338d1f0dc6b9bc573e70c7004f53aceb", authority_doc)
        self.assertIn("durable-state reconciliation is complete", parity_doc)
        self.assertIn("M10.5-02 and is dependency-ready", parity_doc)
        self.assertNotIn("requires fresh independent validation and later integration before Gate 01 is complete", authority_doc)
        self.assertNotIn("M10.5-01 remains incomplete until this new candidate", parity_doc)
        self.assertNotIn("This branch implements G1", authority_doc)

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
