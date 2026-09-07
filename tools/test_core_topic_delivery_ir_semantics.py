from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import build_canonical_ir


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "fixtures" / "valid" / "m4-minimal"
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))


class CoreTopicDeliveryIrSemanticsTests(unittest.TestCase):
    def _ir(self) -> dict:
        analysis = load_compiler_analysis([PROJECT])
        self.assertFalse(
            any(diagnostic.severity.value == "error" for diagnostic in analysis.diagnostics),
            [diagnostic.to_json() for diagnostic in analysis.diagnostics],
        )
        return build_canonical_ir(analysis)

    def _topic(self, document: dict) -> dict:
        return next(
            declaration
            for declaration in document["declarations"]
            if declaration["kind"] == "topic" and declaration["name"] == "SnapshotItemEvents"
        )

    def _schema_errors(self, document: dict):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        return tuple(validator.iter_errors(document))

    def test_topic_delivery_metadata_is_materialized_from_source(self) -> None:
        first = self._ir()
        second = self._ir()
        self.assertEqual(first, second)

        topic = self._topic(first)
        self.assertEqual("atLeastOnce", topic["delivery"])
        self.assertEqual("itemId", topic["partitionField"])
        self.assertEqual("perPartition", topic["ordering"])
        self.assertEqual(30 * 24 * 60 * 60 * 1000, topic["retentionMs"])
        self.assertEqual("backward", topic["compatibility"])
        self.assertEqual(8, topic["deadLetterAttempts"])
        self.assertEqual((), self._schema_errors(first))

    def test_ir_schema_rejects_invalid_topic_delivery_metadata(self) -> None:
        base = self._ir()
        invalid_values = {
            "delivery": "exactlyOnce",
            "partitionField": "",
            "ordering": "global",
            "retentionMs": 0,
            "compatibility": "rolling",
            "deadLetterAttempts": 0,
        }
        for key, value in invalid_values.items():
            with self.subTest(key=key, value=value):
                document = copy.deepcopy(base)
                self._topic(document)[key] = value
                self.assertTrue(self._schema_errors(document))


if __name__ == "__main__":
    unittest.main()
