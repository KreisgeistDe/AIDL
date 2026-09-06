import copy
import itertools
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.ir_canonical_json import canonical_ir_json_bytes, canonical_ir_json_text


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "spec" / "ir.schema.json"
FIXTURE_PATH = ROOT / "tools" / "ir_schema_contract" / "valid_core.json"


def _reverse_mapping_insertion_order(value):
    if isinstance(value, dict):
        return {
            key: _reverse_mapping_insertion_order(value[key])
            for key in reversed(tuple(value))
        }
    if isinstance(value, list):
        return [_reverse_mapping_insertion_order(item) for item in value]
    return value


class CanonicalIrJsonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.valid_document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _declaration(document: dict, name: str) -> dict:
        return next(item for item in document["declarations"] if item["name"] == name)

    def test_text_and_byte_contract_is_compact_sorted_utf8_with_one_lf(self) -> None:
        document = {"z": "Grüße", "a": {"y": 2, "x": 1}}
        text = canonical_ir_json_text(document)
        self.assertEqual('{"a":{"x":1,"y":2},"z":"Grüße"}\n', text)
        self.assertEqual(text.encode("utf-8"), canonical_ir_json_bytes(document))
        self.assertFalse(canonical_ir_json_bytes(document).startswith(b"\xef\xbb\xbf"))

    def test_mapping_insertion_order_does_not_change_bytes(self) -> None:
        reordered = _reverse_mapping_insertion_order(self.valid_document)
        self.assertEqual(
            canonical_ir_json_bytes(self.valid_document),
            canonical_ir_json_bytes(reordered),
        )

    def test_semantic_set_permutations_do_not_change_bytes(self) -> None:
        expected = canonical_ir_json_bytes(self.valid_document)
        document = copy.deepcopy(self.valid_document)
        document["profiles"].reverse()
        document["app"]["auth"]["roles"].reverse()
        document["app"]["auth"]["scopes"].reverse()

        service = document["system"]["services"][0]
        for key in ("owns", "uses", "exposes", "runs"):
            service[key].reverse()
        document["system"]["resources"][0]["transactionIsolation"].reverse()
        document["system"]["topicIds"].reverse()
        document["system"]["apiIds"].reverse()
        document["system"]["consumerGroups"][0]["consumerIds"].reverse()

        self.assertEqual(expected, canonical_ir_json_bytes(document))

    def test_profile_permutations_and_repeated_calls_are_byte_identical(self) -> None:
        expected = canonical_ir_json_bytes(self.valid_document)
        for profiles in itertools.permutations(self.valid_document["profiles"]):
            document = _reverse_mapping_insertion_order(self.valid_document)
            document["profiles"] = list(profiles)
            for _ in range(5):
                self.assertEqual(expected, canonical_ir_json_bytes(document))

    def test_ordered_transaction_steps_remain_positional(self) -> None:
        original = canonical_ir_json_bytes(self.valid_document)
        reordered = copy.deepcopy(self.valid_document)
        mutation = self._declaration(reordered, "renamePet")
        mutation["rootEffect"]["steps"].reverse()

        reordered_bytes = canonical_ir_json_bytes(reordered)
        self.assertNotEqual(original, reordered_bytes)
        canonical_document = json.loads(reordered_bytes)
        canonical_mutation = self._declaration(canonical_document, "renamePet")
        self.assertEqual(
            ["publish", "write", "read"],
            [step["kind"] for step in canonical_mutation["rootEffect"]["steps"]],
        )

    def test_canonicalized_m3_01_fixture_remains_draft_2020_12_valid(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        validator = Draft202012Validator(
            self.schema,
            format_checker=FormatChecker(),
        )
        canonical_document = json.loads(canonical_ir_json_bytes(self.valid_document))
        errors = sorted(
            validator.iter_errors(canonical_document),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        self.assertEqual([], errors, "\n".join(error.message for error in errors))

    def test_serialization_does_not_mutate_input(self) -> None:
        document = copy.deepcopy(self.valid_document)
        before = copy.deepcopy(document)
        canonical_ir_json_bytes(document)
        self.assertEqual(before, document)


if __name__ == "__main__":
    unittest.main()
