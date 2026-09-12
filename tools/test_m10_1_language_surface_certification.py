from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

import tools.compiler_language_surface_certification as certification
from tools.compiler_language_surface_certification import (
    CLOSURE_CERTIFICATION_VERSION,
    closure_certification,
    closure_certification_json,
)


class M101LanguageSurfaceCertificationTest(unittest.TestCase):
    def test_certification_closes_every_acceptance_criterion(self) -> None:
        data = closure_certification()

        self.assertEqual(data["schema_version"], CLOSURE_CERTIFICATION_VERSION)
        self.assertEqual(data["contract_revision"], 4)
        self.assertEqual(data["state"], "certified")
        self.assertEqual(data["unresolved_language_decisions"], [])
        self.assertTrue(data["m10_5_03"]["unblocked"])
        self.assertEqual(len(data["acceptance_criteria"]), 7)
        self.assertTrue(all(item["status"] == "pass" for item in data["acceptance_criteria"]))
        self.assertEqual(
            [item["id"] for item in data["acceptance_criteria"]],
            [
                "frozen-facts-lossless-or-fail-closed",
                "legacy-canonical-semantic-convergence",
                "contract-derived-production-normalization",
                "formatter-migration-separation",
                "complete-production-dispositions",
                "deterministic-coverage-and-differential-ci",
                "m10.5-03-language-decision-readiness",
            ],
        )

    def test_production_semantic_envelope_is_complete_and_explicit(self) -> None:
        envelope = closure_certification()["production_semantic_envelope"]

        self.assertEqual(
            envelope["admitted_declaration_families"],
            [
                "app",
                "enum",
                "alias",
                "entity",
                "query",
                "mutation",
                "consumer",
                "projection",
                "client",
                "migration",
            ],
        )
        self.assertEqual(len(envelope["intentionally_non_admitted_declaration_families"]), 38)
        self.assertNotIn("query", envelope["intentionally_non_admitted_declaration_families"])
        self.assertNotIn("mutation", envelope["intentionally_non_admitted_declaration_families"])

        policy = envelope["operation_policy_dispositions"]
        for kind in ("query", "mutation"):
            by_concept = {
                item["concept"]: item
                for item in policy
                if item["operation_kind"] == kind
            }
            self.assertEqual(by_concept["authorize"]["disposition"], "production_parity")
            self.assertIsNone(by_concept["authorize"]["diagnostic_boundary"])
            for concept in ("auth", "cache", "consistency"):
                self.assertEqual(by_concept[concept]["disposition"], "excluded")
                self.assertEqual(
                    by_concept[concept]["diagnostic_boundary"],
                    "AIDL-N010 -> AIDL-N013",
                )

        execution = envelope["operation_execution_dispositions"]
        excluded = [item for item in execution if item["disposition"] == "excluded"]
        self.assertTrue(excluded)
        self.assertTrue(all(item["diagnostic_boundary"] for item in excluded))

    def test_policy_exclusion_without_boundary_fails_closed(self) -> None:
        policy = copy.deepcopy(certification.operation_policy_dispositions())
        self.assertEqual(policy["contract_revision"], 4)
        del policy["declarations"]["query"][0]["diagnostic_boundary"]

        with patch.object(certification, "operation_policy_dispositions", return_value=policy):
            with self.assertRaisesRegex(ValueError, "lacks fail-closed diagnostic boundary"):
                closure_certification()

    def test_non_coverage_audit_schema_version_drift_fails_closed(self) -> None:
        cases = (
            (
                "declaration-family",
                "declaration_family_dispositions",
                certification.declaration_family_dispositions,
            ),
            (
                "operation-policy",
                "operation_policy_dispositions",
                certification.operation_policy_dispositions,
            ),
            (
                "operation-execution",
                "operation_execution_dispositions",
                certification.operation_execution_dispositions,
            ),
        )
        for audit_name, function_name, factory in cases:
            with self.subTest(audit=audit_name):
                data = copy.deepcopy(factory())
                self.assertEqual(data["contract_revision"], 4)
                data["schema_version"] = "aidl.test-schema-drift/v999"
                with patch.object(certification, function_name, return_value=data):
                    with self.assertRaisesRegex(
                        ValueError,
                        f"{audit_name} audit version drift detected",
                    ):
                        closure_certification()

    def test_formatter_and_explicit_migration_remain_separate(self) -> None:
        data = closure_certification()["formatter_migration_separation"]
        self.assertEqual(
            data,
            {
                "same_version_formatter": "LanguageSurfaceBridge.format_legacy",
                "language_version_migration": "LanguageSurfaceBridge.migrate_to_canonical_preview",
            },
        )

    def test_m10_5_03_unblock_is_bounded_to_frozen_revision(self) -> None:
        data = closure_certification()
        condition = data["m10_5_03"]["condition"]
        self.assertIn("frozen-v1 revision 4", condition)
        self.assertIn("Python-versus-Kotlin differential parity", condition)
        self.assertIn("separately versioned language decision", condition)
        self.assertEqual(
            data["roadmap_packages"],
            [f"M10.1-{index:02d}" for index in range(1, 11)],
        )

    def test_certification_json_is_byte_stable(self) -> None:
        first = closure_certification_json()
        second = closure_certification_json()
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            json.dumps(
                json.loads(first),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        )


if __name__ == "__main__":
    unittest.main()
