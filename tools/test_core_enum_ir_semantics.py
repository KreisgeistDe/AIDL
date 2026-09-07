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
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))


class CoreEnumIrSemanticsTests(unittest.TestCase):
    def _ir(self) -> dict:
        source = (PROJECT / "app.aidl").read_text(encoding="utf-8") + """

export enum SnapshotState {
  Draft
  Published
  Archived
}
"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "app.aidl"
            path.write_text(source, encoding="utf-8")
            analysis = load_compiler_analysis([path])
            self.assertFalse(
                any(diagnostic.severity.value == "error" for diagnostic in analysis.diagnostics),
                [diagnostic.to_json() for diagnostic in analysis.diagnostics],
            )
            return build_canonical_ir(analysis)

    @staticmethod
    def _enum(document: dict) -> dict:
        return next(
            declaration
            for declaration in document["declarations"]
            if declaration["kind"] == "enum" and declaration["name"] == "SnapshotState"
        )

    @staticmethod
    def _schema_errors(document: dict):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        return tuple(validator.iter_errors(document))

    def test_enum_identity_and_cases_are_preserved_deterministically(self) -> None:
        first = self._ir()
        second = self._ir()

        enum = self._enum(first)
        self.assertEqual(enum, self._enum(second))
        self.assertEqual("SnapshotState", enum["name"])
        self.assertEqual("enum", enum["kind"])
        self.assertEqual(["Draft", "Published", "Archived"], enum["values"])
        self.assertEqual((), self._schema_errors(first))

    def test_closed_ir_schema_rejects_invalid_enum_case_contracts(self) -> None:
        base = self._ir()

        empty = copy.deepcopy(base)
        self._enum(empty)["values"] = []
        self.assertTrue(self._schema_errors(empty))

        duplicate = copy.deepcopy(base)
        self._enum(duplicate)["values"] = ["Draft", "Draft"]
        self.assertTrue(self._schema_errors(duplicate))

        missing = copy.deepcopy(base)
        del self._enum(missing)["values"]
        self.assertTrue(self._schema_errors(missing))


if __name__ == "__main__":
    unittest.main()
