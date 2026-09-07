from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import build_canonical_ir


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "fixtures" / "valid" / "m4-minimal"
SOURCE = (PROJECT / "app.aidl").read_text(encoding="utf-8")
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))


class CoreEventIrSemanticsTests(unittest.TestCase):
    def _analysis_for_source(self, source: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        project = Path(temporary.name)
        (project / "app.aidl").write_text(source, encoding="utf-8")
        return load_compiler_analysis([project])

    def _ir(self, source: str = SOURCE) -> dict:
        analysis = self._analysis_for_source(source)
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

    def _materialization_errors(self, source: str) -> list[dict]:
        analysis = self._analysis_for_source(source)
        return [
            diagnostic.to_json()
            for diagnostic in analysis.diagnostics
            if diagnostic.code.value == "AIDL-T005"
            and diagnostic.subject.kind == "event"
        ]

    def test_event_version_identity_and_schema_are_materialized_from_source(self) -> None:
        source = SOURCE.replace(
            "export event SnapshotItemCreated version 1 {",
            "export event SnapshotItemCreated version 2 {",
        )
        first = self._ir(source)
        second = self._ir(source)
        self.assertEqual(first, second)

        event = self._event(first)
        self.assertEqual(2, event["majorVersion"])
        self.assertEqual("fixtures.valid.m4minimal.SnapshotItemCreated", event["fqn"])
        self.assertEqual("fixtures.valid.m4minimal.SnapshotItemCreated@2", event["declarationId"])
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

    def test_event_materialization_rejects_non_lossless_source_before_ir(self) -> None:
        variants = {
            "missing-version": SOURCE.replace(
                "export event SnapshotItemCreated version 1 {",
                "export event SnapshotItemCreated {",
            ),
            "zero-version": SOURCE.replace(
                "export event SnapshotItemCreated version 1 {",
                "export event SnapshotItemCreated version 0 {",
            ),
            "malformed-version": SOURCE.replace(
                "export event SnapshotItemCreated version 1 {",
                "export event SnapshotItemCreated version nope {",
            ),
            "evolves": SOURCE.replace(
                "export event SnapshotItemCreated version 1 {",
                "export event SnapshotItemCreated version 1 evolves PreviousSnapshotItemCreated {",
            ),
            "malformed-body": SOURCE.replace(
                "  eventId: OperationId required\n",
                "  eventId OperationId required\n",
            ),
            "dropped-modifier": SOURCE.replace(
                "  itemId: uuid required\n",
                "  itemId: uuid required immutable\n",
            ),
        }
        for name, source in variants.items():
            with self.subTest(name=name):
                errors = self._materialization_errors(source)
                self.assertTrue(errors, name)
                self.assertTrue(all(error["code"] == "AIDL-T005" for error in errors))

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
