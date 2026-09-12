from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.compiler_declaration_family_parity import declaration_family_dispositions
from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_language_surface import (
    BodySlot,
    Declaration,
    HeaderArg,
    LanguageSurfaceBridge,
    ModifierCall,
    OperationParameter,
    TypeRef,
)
from tools.compiler_language_surface_body_parity import ContractBodyParityBridge
from tools.compiler_language_surface_coverage import (
    LANGUAGE_SURFACE_COVERAGE_VERSION,
    _build_coverage,
    _contract_leaves,
    _semantic_contract,
    language_surface_coverage,
    language_surface_coverage_json,
)
from tools.compiler_language_surface_integration import normalize_compiler_analysis
from tools.compiler_operation_execution_parity import operation_execution_dispositions
from tools.compiler_operation_policy_parity import operation_policy_dispositions


class M101LanguageSurfaceCoverageTest(unittest.TestCase):
    def _analysis(self, source_text: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "model.aidl"
        source.write_text(source_text, encoding="utf-8")
        return load_compiler_analysis([source])

    def test_inventory_accounts_for_every_non_example_contract_leaf(self) -> None:
        contract = LanguageSurfaceBridge().contract
        expected = list(_contract_leaves(_semantic_contract(contract)))
        data = language_surface_coverage()
        facts = {item["path"]: item for item in data["contract_facts"]}

        self.assertEqual(data["schema_version"], LANGUAGE_SURFACE_COVERAGE_VERSION)
        self.assertEqual(data["contract_revision"], 4)
        self.assertEqual(data["contract_leaf_count"], len(expected))
        self.assertEqual(
            [item["path"] for item in data["contract_facts"]],
            [path for path, _ in expected],
        )
        self.assertEqual(len(data["declaration_dispositions"]), 48)

        self.assertEqual(
            facts[
                "/declaration_kinds/query/header_args/parameters/parameter/modifiers/0"
            ]["value"],
            "default",
        )
        self.assertEqual(
            facts[
                "/declaration_kinds/query/body_slots/errors/item/reference_kinds/0"
            ]["value"],
            "error",
        )
        self.assertEqual(
            facts["/declaration_kinds/query/body_slots/errors/order"]["value"],
            "canonical",
        )
        self.assertEqual(
            facts[
                "/declaration_kinds/app/body_slots/profile/nested_slots/version/occurrence/min"
            ]["value"],
            1,
        )
        self.assertEqual(facts["/modifiers/default/arity/min"]["value"], 1)
        self.assertEqual(
            facts["/modifiers/default/argument_mode"]["value"], "expression"
        )

    def test_dispositions_are_correlated_from_existing_compiler_evidence(self) -> None:
        data = language_surface_coverage()
        declaration_items = {
            item["declaration_kind"]: item
            for item in data["declaration_dispositions"]
        }
        self.assertEqual(
            data["declaration_dispositions"],
            declaration_family_dispositions()["declarations"],
        )
        self.assertEqual(declaration_items["entity"]["production_admission"], "always_lossless")
        self.assertEqual(declaration_items["query"]["production_admission"], "conditional_lossless")
        self.assertEqual(declaration_items["workflow"]["production_admission"], "non_admitted")

        modifiers = {item["name"]: item for item in data["modifier_dispositions"]}
        default_targets = {
            item["target"]: item["production_admission"]
            for item in modifiers["default"]["targets"]
        }
        self.assertEqual(default_targets["entity.field"], "always_lossless")
        self.assertEqual(default_targets["value.field"], "non_admitted")
        self.assertEqual(default_targets["query.parameter"], "conditional_lossless")
        self.assertEqual(default_targets["mutation.parameter"], "conditional_lossless")

        self.assertEqual(
            data["operation_policy_dispositions"],
            operation_policy_dispositions()["declarations"],
        )
        self.assertEqual(
            data["operation_execution_dispositions"],
            operation_execution_dispositions()["declarations"],
        )

    def test_typeref_and_reference_projection_shapes_come_from_executable_bridge(self) -> None:
        shapes = language_surface_coverage()["bridge_semantic_shapes"]
        self.assertEqual(
            shapes["type_ref_optional"],
            {"kind": "scalar", "optional": True, "name": "string"},
        )
        self.assertEqual(
            shapes["type_ref_range"],
            {
                "kind": "scalar",
                "optional": False,
                "name": "string",
                "range": {"min": 1, "max": 80},
            },
        )
        self.assertEqual(
            shapes["reference_projection"],
            {
                "kind": "reference",
                "optional": False,
                "target": "Pet",
                "projection": "id",
                "resolved_type": "uuid",
            },
        )

    def test_legacy_entity_facts_match_independent_canonical_semantics(self) -> None:
        bridge = LanguageSurfaceBridge(
            reference_projections={"Pet.id": ("Pet", "id", "uuid")}
        )
        result = bridge.normalize_text(
            """entity Adoption {
  name: string required
  petId: ref Pet.id required
}
"""
        )
        self.assertTrue(result.ok, result.diagnostics)
        actual = result.document.declarations[0]
        canonical = Declaration(
            kind="entity",
            name="Adoption",
            name_policy="required",
            exported=False,
            body_slots=(
                BodySlot(
                    "field",
                    "name",
                    "type_ref",
                    TypeRef("scalar", name="string"),
                    modifiers=(ModifierCall("required", "entity.field", "none"),),
                ),
                BodySlot(
                    "field",
                    "petId",
                    "type_ref",
                    TypeRef(
                        "reference",
                        target="Pet",
                        projection="id",
                        resolved_type="uuid",
                    ),
                    modifiers=(ModifierCall("required", "entity.field", "none"),),
                ),
            ),
        )
        self.assertEqual(canonical.semantic(), actual.semantic())
        self.assertEqual(canonical.semantic_hash(), actual.semantic_hash())

    def test_legacy_operation_facts_match_independent_canonical_semantics(self) -> None:
        bridge = ContractBodyParityBridge()
        result = bridge.normalize_text(
            """query find(limit: int? default 10) -> string {
  timeout: 5s
  allow: principal
  read: value
}
"""
        )
        self.assertTrue(result.ok, result.diagnostics)
        actual = result.document.declarations[0]
        canonical = Declaration(
            kind="query",
            name="find",
            name_policy="required",
            exported=False,
            header_args=(
                HeaderArg(
                    "parameters",
                    "parameter_list",
                    (
                        OperationParameter(
                            "limit",
                            TypeRef("scalar", optional=True, name="int"),
                            modifiers=(
                                ModifierCall(
                                    "default",
                                    "query.parameter",
                                    "expression",
                                    ("10",),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            result_type=TypeRef("scalar", name="string"),
            body_slots=(
                BodySlot("read", None, "expression", "value"),
                BodySlot("allow", None, "expression", "principal"),
                BodySlot("timeout", None, "literal", "5s"),
            ),
        )
        self.assertEqual(canonical.semantic(), actual.semantic())
        self.assertEqual(canonical.semantic_hash(), actual.semantic_hash())

    def test_production_normalization_is_differentially_stable(self) -> None:
        first = normalize_compiler_analysis(
            self._analysis(
                """module demo
query find(limit: int? default 10) -> string {
  read: value
  allow: principal
  timeout: 5s
}
"""
            )
        )
        second = normalize_compiler_analysis(
            self._analysis(
                """\nmodule demo
query find( limit : int? default 10 ) -> string {
  timeout : 5s
  allow : principal
  read : value
}
"""
            )
        )
        self.assertTrue(first.ok, (first.diagnostics, first.type_issues))
        self.assertTrue(second.ok, (second.diagnostics, second.type_issues))
        self.assertEqual(first.semantic_json(), second.semantic_json())
        self.assertEqual(first.semantic_hash(), second.semantic_hash())

    def test_unsupported_and_incomplete_shapes_remain_fail_closed(self) -> None:
        cases = (
            "query find(page: Page<string>) -> string {\n  read: value\n}\n",
            "query find(broken) -> string {\n  read: value\n}\n",
            "mutation update() -> string {\n  idempotency: key retain 5s\n}\n",
        )
        for source in cases:
            with self.subTest(source=source.splitlines()[0]):
                normalized = normalize_compiler_analysis(self._analysis(source))
                self.assertFalse(normalized.ok)
                self.assertIn("AIDL-N013", [item.code for item in normalized.diagnostics])
                self.assertEqual(normalized.declarations, ())

    def test_audit_json_is_byte_stable_and_contract_drift_fails_closed(self) -> None:
        first = language_surface_coverage_json()
        second = language_surface_coverage_json()
        self.assertEqual(first, second)
        parsed = json.loads(first)
        self.assertEqual(
            first,
            json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )

        surface = LanguageSurfaceBridge()
        body = ContractBodyParityBridge()
        drifted = copy.deepcopy(surface.contract)
        drifted["declaration_kinds"][0]["name_policy"] = "optional"
        with self.assertRaisesRegex(ValueError, "contract drift"):
            _build_coverage(
                drifted,
                surface.contract,
                body.contract,
                declaration_family_dispositions(),
                operation_policy_dispositions(),
                operation_execution_dispositions(),
            )


if __name__ == "__main__":
    unittest.main()
