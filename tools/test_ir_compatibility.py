from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.ir_version import (
    IrCompatibilityError,
    IrConsumerCapabilities,
    require_compatible_ir,
)


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "tools" / "ir_compatibility_contract" / "matrix.json"
SCHEMA_PATH = ROOT / "spec" / "ir.schema.json"
CORE_FIXTURE_PATH = ROOT / "tools" / "ir_schema_contract" / "valid_core.json"


class IrCompatibilityMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(schema, format_checker=FormatChecker())
        cls.valid_core = json.loads(CORE_FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_version_compatibility_matrix(self) -> None:
        for case in self.matrix["versionCases"]:
            with self.subTest(case=case["id"]):
                consumer = IrConsumerCapabilities.create(
                    case["consumer"],
                    profile_majors=[tuple(profile) for profile in case["profiles"]],
                    tolerated_additive_fields=case["toleratedAdditiveFields"],
                )
                document = {
                    "irVersion": case["producer"],
                    "profiles": case["documentProfiles"],
                }
                if case["compatible"]:
                    require_compatible_ir(
                        document,
                        consumer,
                        additive_fields=case["additiveFields"],
                    )
                else:
                    with self.assertRaisesRegex(
                        IrCompatibilityError,
                        case["error"],
                    ):
                        require_compatible_ir(
                            document,
                            consumer,
                            additive_fields=case["additiveFields"],
                        )

    def test_schema_compatibility_matrix(self) -> None:
        mutations = {
            "none": lambda document: None,
            "unknownTopLevelField": lambda document: document.__setitem__(
                "futureCore", {}
            ),
            "invalidSemanticHashType": lambda document: document.__setitem__(
                "semanticHash", 7
            ),
            "unknownDeclarationField": lambda document: document["declarations"][0].__setitem__(
                "futureCore", True
            ),
        }
        self.assertEqual(
            set(mutations),
            {case["mutation"] for case in self.matrix["schemaCases"]},
        )
        for case in self.matrix["schemaCases"]:
            with self.subTest(case=case["id"]):
                document = copy.deepcopy(self.valid_core)
                mutations[case["mutation"]](document)
                self.assertEqual(case["valid"], self.validator.is_valid(document))

    def test_current_schema_and_version_gate_have_distinct_evolution_roles(self) -> None:
        consumer = IrConsumerCapabilities.create(
            "0.3.0",
            profile_majors=[
                (profile["id"], profile["major"])
                for profile in self.valid_core["profiles"]
            ],
            tolerated_additive_fields=["/futureCore"],
        )

        older = copy.deepcopy(self.valid_core)
        older["irVersion"] = "0.2.9"
        require_compatible_ir(older, consumer)
        self.assertFalse(self.validator.is_valid(older))

        newer = copy.deepcopy(self.valid_core)
        newer["irVersion"] = "0.4.0"
        require_compatible_ir(newer, consumer, additive_fields=["/futureCore"])
        self.assertFalse(self.validator.is_valid(newer))

        self.assertTrue(self.validator.is_valid(self.valid_core))


if __name__ == "__main__":
    unittest.main()
