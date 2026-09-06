import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "spec" / "ir.schema.json"
FIXTURE_PATH = ROOT / "tools" / "ir_schema_contract" / "valid_core.json"


class CanonicalIrSchemaContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(
            cls.schema,
            format_checker=FormatChecker(),
        )
        cls.valid_document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _declaration(document: dict, name: str) -> dict:
        return next(item for item in document["declarations"] if item["name"] == name)

    def test_representative_core_document_is_valid(self) -> None:
        errors = sorted(
            self.validator.iter_errors(self.valid_document),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        self.assertEqual([], errors, "\n".join(error.message for error in errors))

    def test_type_ref_is_closed_and_discriminated(self) -> None:
        variants = {
            variant["properties"]["kind"]["const"]: variant
            for variant in self.schema["$defs"]["typeRef"]["oneOf"]
        }
        self.assertEqual(
            {"scalar", "named", "list", "set", "map", "nullable", "ref", "record"},
            set(variants),
        )
        for variant in variants.values():
            self.assertFalse(variant["additionalProperties"])

    def test_domain_declarations_require_kind_specific_semantics(self) -> None:
        document = copy.deepcopy(self.valid_document)
        species = self._declaration(document, "Species")
        del species["values"]
        self.assertFalse(self.validator.is_valid(document))

    def test_unknown_core_property_is_rejected(self) -> None:
        document = copy.deepcopy(self.valid_document)
        document["mystery"] = {}
        self.assertFalse(self.validator.is_valid(document))

    def test_generic_operation_contract_is_rejected(self) -> None:
        document = copy.deepcopy(self.valid_document)
        self._declaration(document, "renamePet")["contract"] = {}
        self.assertFalse(self.validator.is_valid(document))

    def test_incomplete_map_type_is_rejected(self) -> None:
        document = copy.deepcopy(self.valid_document)
        showcase = self._declaration(document, "TypeShowcase")
        payload = showcase["fields"][0]["type"]
        map_field = next(field for field in payload["fields"] if field["name"] == "map")
        del map_field["type"]["value"]
        self.assertFalse(self.validator.is_valid(document))

    def test_exactly_once_topic_is_rejected(self) -> None:
        document = copy.deepcopy(self.valid_document)
        self._declaration(document, "PetEvents")["delivery"] = "exactlyOnce"
        self.assertFalse(self.validator.is_valid(document))

    def test_transaction_publish_requires_outbox(self) -> None:
        document = copy.deepcopy(self.valid_document)
        mutation = self._declaration(document, "renamePet")
        publish = next(
            step for step in mutation["rootEffect"]["steps"] if step["kind"] == "publish"
        )
        publish["via"] = "direct"
        self.assertFalse(self.validator.is_valid(document))

    def test_profile_extension_namespace_must_be_versioned(self) -> None:
        document = copy.deepcopy(self.valid_document)
        document["profileExtensions"] = {
            "cloud": [
                {
                    "target": "/deployments/0",
                    "schema": "https://aidl.example/profiles/cloud/1/deployment.schema.json",
                    "value": {},
                }
            ]
        }
        self.assertFalse(self.validator.is_valid(document))


if __name__ == "__main__":
    unittest.main()
