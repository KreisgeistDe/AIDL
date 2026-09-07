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


class CoreValueIrSemanticsTests(unittest.TestCase):
    def _analysis(self, additions: str):
        source = (PROJECT / "app.aidl").read_text(encoding="utf-8") + additions
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "app.aidl"
        path.write_text(source, encoding="utf-8")
        return load_compiler_analysis([path])

    def _ir(self) -> dict:
        analysis = self._analysis(
            """

export value SnapshotValueContract {
  label: string required
  optionalSecret: string? sensitive
  mutableCount: int mutable
  generatedToken: uuid generated
  labels: set<string> required
  lookup: map<string, uuid?> required
}
"""
        )
        self.assertFalse(
            any(diagnostic.severity.value == "error" for diagnostic in analysis.diagnostics),
            [diagnostic.to_json() for diagnostic in analysis.diagnostics],
        )
        return build_canonical_ir(analysis)

    @staticmethod
    def _declaration(document: dict, name: str) -> dict:
        return next(
            declaration
            for declaration in document["declarations"]
            if declaration["kind"] == "value" and declaration["name"] == name
        )

    @staticmethod
    def _schema_errors(document: dict):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        return tuple(validator.iter_errors(document))

    def test_value_fields_preserve_order_types_and_core_metadata(self) -> None:
        first = self._ir()
        second = self._ir()
        value = self._declaration(first, "SnapshotValueContract")
        second_value = self._declaration(second, "SnapshotValueContract")

        self.assertEqual(value, second_value)
        self.assertEqual(
            ["label", "optionalSecret", "mutableCount", "generatedToken", "labels", "lookup"],
            [field["name"] for field in value["fields"]],
        )

        label = value["fields"][0]
        self.assertEqual({"kind": "scalar", "name": "string"}, label["type"])
        self.assertTrue(label["required"])
        self.assertFalse(label["mutable"])
        self.assertFalse(label["sensitive"])
        self.assertFalse(label["generated"])

        optional_secret = value["fields"][1]
        self.assertEqual(
            {"kind": "nullable", "element": {"kind": "scalar", "name": "string"}},
            optional_secret["type"],
        )
        self.assertFalse(optional_secret["required"])
        self.assertFalse(optional_secret["mutable"])
        self.assertTrue(optional_secret["sensitive"])
        self.assertFalse(optional_secret["generated"])

        self.assertTrue(value["fields"][2]["mutable"])
        self.assertTrue(value["fields"][3]["generated"])
        self.assertEqual(
            {"kind": "set", "element": {"kind": "scalar", "name": "string"}},
            value["fields"][4]["type"],
        )
        self.assertEqual(
            {
                "kind": "map",
                "key": {"kind": "scalar", "name": "string"},
                "value": {"kind": "nullable", "element": {"kind": "scalar", "name": "uuid"}},
            },
            value["fields"][5]["type"],
        )
        self.assertEqual((), self._schema_errors(first))

    def test_closed_ir_schema_rejects_missing_or_malformed_value_field_contract(self) -> None:
        base = self._ir()

        missing_required = copy.deepcopy(base)
        del self._declaration(missing_required, "SnapshotValueContract")["fields"][0]["required"]
        self.assertTrue(self._schema_errors(missing_required))

        malformed_sensitive = copy.deepcopy(base)
        self._declaration(malformed_sensitive, "SnapshotValueContract")["fields"][1]["sensitive"] = "yes"
        self.assertTrue(self._schema_errors(malformed_sensitive))

        missing_type = copy.deepcopy(base)
        del self._declaration(missing_type, "SnapshotValueContract")["fields"][2]["type"]
        self.assertTrue(self._schema_errors(missing_type))

        malformed_type = copy.deepcopy(base)
        self._declaration(malformed_type, "SnapshotValueContract")["fields"][4]["type"] = {"kind": "set"}
        self.assertTrue(self._schema_errors(malformed_type))


if __name__ == "__main__":
    unittest.main()
