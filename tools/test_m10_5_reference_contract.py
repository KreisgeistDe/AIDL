from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.m10_5_reference_contract import (
    REQUIRED_DIMENSIONS,
    REQUIRED_SURFACES,
    build_reference_contract,
    reference_contract_json,
)


class M105ReferenceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.manifest = json.loads((cls.root / "tools/m10_5_reference_contract.json").read_text(encoding="utf-8"))

    def test_inventory_is_complete_non_normative_and_deterministic(self) -> None:
        data = build_reference_contract()
        self.assertEqual(data["authority"], "M10.5-01")
        self.assertEqual(data["reference_implementation"], "python")
        self.assertEqual(tuple(data["observable_surfaces"]), tuple(sorted(REQUIRED_SURFACES)))
        self.assertEqual(data["frozen_contract"]["authority"], "M10.1")
        self.assertEqual(data["frozen_contract"]["status"], "frozen")
        self.assertEqual(data["frozen_contract"]["contract_revision"], 4)
        self.assertTrue(data["fingerprint"].startswith("sha256:"))
        self.assertEqual(reference_contract_json(), reference_contract_json())
        self.assertEqual(
            reference_contract_json(),
            json.dumps(json.loads(reference_contract_json()), sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )

    def test_evidence_is_existing_project_owned_files(self) -> None:
        data = build_reference_contract()
        self.assertTrue(data["evidence"])
        for row in data["evidence"]:
            self.assertFalse(row["path"].startswith(".ai/"))
            self.assertTrue((self.root / row["path"]).is_file(), row["path"])
            self.assertTrue(row["sha256"].startswith("sha256:"))

    def test_differential_contract_is_exact_and_future_kotlin_is_not_required(self) -> None:
        contract = build_reference_contract()["differential_contract"]
        self.assertEqual(contract["comparison"], "exact_canonical_json")
        self.assertEqual(tuple(contract["semantic_dimensions"]), REQUIRED_DIMENSIONS)
        self.assertEqual(contract["transport_only_differences"], [])
        self.assertEqual(contract["runner_implementations"], ["python", "kotlin"])
        self.assertFalse(contract["kotlin_required_for_m10_5_01"])

    def test_schema_normative_and_surface_drift_fail_closed(self) -> None:
        cases = []
        schema = copy.deepcopy(self.manifest)
        schema["schema_version"] = "aidl.test/v999"
        cases.append((schema, "schema version drift"))
        normative = copy.deepcopy(self.manifest)
        normative["normative_language_source"] = True
        cases.append((normative, "normative language source"))
        missing = copy.deepcopy(self.manifest)
        missing["observable_surfaces"] = missing["observable_surfaces"][:-1]
        cases.append((missing, "surface inventory drift"))
        duplicate = copy.deepcopy(self.manifest)
        duplicate["observable_surfaces"].append(copy.deepcopy(duplicate["observable_surfaces"][0]))
        cases.append((duplicate, "surface ids must be unique"))
        for manifest, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    build_reference_contract(manifest=manifest)

    def test_frozen_contract_and_differential_drift_fail_closed(self) -> None:
        revision = copy.deepcopy(self.manifest)
        revision["frozen_language_contract"]["contract_revision"] = 5
        with self.assertRaisesRegex(ValueError, "frozen language contract identity drift"):
            build_reference_contract(manifest=revision)

        dimensions = copy.deepcopy(self.manifest)
        dimensions["differential_contract"]["semantic_dimensions"] = list(REQUIRED_DIMENSIONS[:-1])
        with self.assertRaisesRegex(ValueError, "semantic dimensions drift"):
            build_reference_contract(manifest=dimensions)

        transport = copy.deepcopy(self.manifest)
        transport["differential_contract"]["transport_only_differences"] = ["implementation"]
        with self.assertRaisesRegex(ValueError, "separately reviewed contract change"):
            build_reference_contract(manifest=transport)

    def test_missing_and_project_ai_evidence_fail_closed(self) -> None:
        missing = copy.deepcopy(self.manifest)
        missing["observable_surfaces"][0]["evidence"][0] = "tools/does-not-exist.py"
        with self.assertRaisesRegex(ValueError, "missing evidence path"):
            build_reference_contract(manifest=missing)

        project_ai = copy.deepcopy(self.manifest)
        project_ai["observable_surfaces"][0]["evidence"][0] = ".ai/forbidden.json"
        with self.assertRaisesRegex(ValueError, "project-.ai evidence path"):
            build_reference_contract(manifest=project_ai)


if __name__ == "__main__":
    unittest.main()
