from __future__ import annotations

import copy
import json
import unittest

try:
    from .compiler_declaration_family_parity import (
        DECLARATION_FAMILY_PARITY_VERSION,
        _build_dispositions,
        declaration_family_dispositions,
        declaration_family_dispositions_json,
    )
    from .compiler_language_surface import LanguageSurfaceBridge
    from .compiler_language_surface_integration import (
        _ALWAYS_INTEGRATED,
        _LOSSLESS_CANDIDATES,
    )
except ImportError:  # pragma: no cover
    from compiler_declaration_family_parity import (
        DECLARATION_FAMILY_PARITY_VERSION,
        _build_dispositions,
        declaration_family_dispositions,
        declaration_family_dispositions_json,
    )
    from compiler_language_surface import LanguageSurfaceBridge
    from compiler_language_surface_integration import (
        _ALWAYS_INTEGRATED,
        _LOSSLESS_CANDIDATES,
    )


class DeclarationFamilyParityTest(unittest.TestCase):
    def test_inventory_matches_frozen_contract_exactly(self) -> None:
        contract = LanguageSurfaceBridge().contract
        contract_kinds = [item["kind"] for item in contract["declaration_kinds"]]
        data = declaration_family_dispositions()
        audit_kinds = [item["declaration_kind"] for item in data["declarations"]]

        self.assertEqual(data["schema_version"], DECLARATION_FAMILY_PARITY_VERSION)
        self.assertEqual(data["contract_revision"], 4)
        self.assertEqual(data["inventory_count"], 48)
        self.assertEqual(audit_kinds, contract_kinds)
        self.assertEqual(set(audit_kinds), set(contract_kinds))
        self.assertEqual(len(audit_kinds), len(set(audit_kinds)))
        self.assertIn("alias", audit_kinds)
        self.assertNotIn("opaque", audit_kinds)
        self.assertNotIn("module", audit_kinds)
        self.assertNotIn("import", audit_kinds)

    def test_production_admission_is_projected_from_existing_compiler_gates(self) -> None:
        data = declaration_family_dispositions()
        items = {item["declaration_kind"]: item for item in data["declarations"]}
        gate_kinds = {
            "alias" if kind == "opaque" else kind
            for kind in (_ALWAYS_INTEGRATED | _LOSSLESS_CANDIDATES)
        }
        audited_admitted = {
            kind for kind, item in items.items() if item["disposition"] == "production_parity"
        }

        self.assertEqual(audited_admitted, gate_kinds)
        self.assertEqual(
            audited_admitted,
            {
                "alias",
                "entity",
                "enum",
                "migration",
                "client",
                "consumer",
                "projection",
                "app",
                "query",
                "mutation",
            },
        )
        self.assertEqual(data["production_parity_count"], 10)
        self.assertEqual(data["intentionally_excluded_count"], 38)
        for kind in ("app", "query", "mutation"):
            self.assertEqual(items[kind]["production_admission"], "conditional_lossless")
        for kind in ("alias", "entity", "enum", "migration", "client", "consumer", "projection"):
            self.assertEqual(items[kind]["production_admission"], "always_lossless")

    def test_non_admitted_families_remain_explicitly_fail_closed(self) -> None:
        items = {
            item["declaration_kind"]: item
            for item in declaration_family_dispositions()["declarations"]
        }
        for kind in ("auth", "policy", "event", "workflow", "frontend", "test", "scenario"):
            with self.subTest(kind=kind):
                self.assertNotIn(kind, _ALWAYS_INTEGRATED | _LOSSLESS_CANDIDATES)
                self.assertEqual(items[kind]["disposition"], "intentionally_excluded")
                self.assertEqual(items[kind]["production_admission"], "non_admitted")
                self.assertIn("Production Normalization", items[kind]["reason"])

    def test_audit_json_is_byte_stable(self) -> None:
        first = declaration_family_dispositions_json()
        second = declaration_family_dispositions_json()
        self.assertEqual(first, second)
        parsed = json.loads(first)
        self.assertEqual(parsed["inventory_count"], 48)
        self.assertEqual(
            first,
            json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )

    def test_contract_inventory_drift_is_derived_not_hidden_by_a_parallel_table(self) -> None:
        contract = copy.deepcopy(LanguageSurfaceBridge().contract)
        contract["declaration_kinds"].append(
            {
                "kind": "futureKind",
                "disposition": "canonical",
                "name_policy": "required",
                "export_allowed": True,
                "header_args_occurrence": {"min": 0, "max": 1},
                "header_args": [],
                "result_type": False,
                "body_slots": [],
                "legacy_forms": [],
            }
        )
        data = _build_dispositions(contract, _ALWAYS_INTEGRATED, _LOSSLESS_CANDIDATES)
        items = {item["declaration_kind"]: item for item in data["declarations"]}
        self.assertEqual(data["inventory_count"], 49)
        self.assertEqual(items["futureKind"]["disposition"], "intentionally_excluded")
        self.assertEqual(items["futureKind"]["production_admission"], "non_admitted")


if __name__ == "__main__":
    unittest.main()
