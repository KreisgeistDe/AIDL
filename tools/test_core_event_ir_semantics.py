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


class CoreEventIrSemanticsTests(unittest.TestCase):
    def _ir(self) -> dict:
        analysis = load_compiler_analysis([PROJECT])
        self.assertFalse(
            any(diagnostic.severity.value == "error" for diagnostic in analysis.diagnostics),
            [diagnostic.to_json() for diagnostic in analysis.diagnostics],
        )
        return build_canonical_ir(analysis)

    def _event(self, document: dict) -> dict:
        return next(
            declaration
            for declaration in document["declarations"]
            if declaration["kind"] == "event" and declaration["name"] == "SnapshotItemCreated"
        )

    def _schema_errors(self, document: dict):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        return tuple(validator.iter_errors(document))

    def test_event_version_and_schema_are_materialized_from_source(self) -> None:
        first = self._ir()
        second = self._ir()
        self.assertEqual(first, second)

        event = self._event(first)
        self.assertEqual(1, event["majorVersion"])
        self.assertEqual(
            ["eventId", "itemId", "occurredAt"],
            [field["name"] for field in event["fields"]],
        )
        self.assertEqual(
            ["named", "scalar", "scalar"],
            [field["type"]["kind"] for field in event["fields"]],
        )
        self.assertEqual("uuid", event["fields"][1]["type"]["name"])
        self.assertEqual("datetime", event["fields"][2]["type"]["name"])
        self.assertTrue(all(field["required"] for field in event["fields"]))
        self.assertEqual((), self._schema_errors(first))

    def test_ir_schema_rejects_invalid_event_version_and_schema(self) -> None:
        base = self._ir()
        invalid_mutations = (
            lambda event: event.__setitem__("majorVersion", 0),
            lambda event: event.__setitem__("fields", []),
            lambda event: event["fields"][0].__setitem__("name", ""),
        )
        for index, mutate in enumerate(invalid_mutations):
            with self.subTest(index=index):
                document = copy.deepcopy(base)
                mutate(self._event(document))
                self.assertTrue(self._schema_errors(document))


if __name__ == "__main__":
    unittest.main()
