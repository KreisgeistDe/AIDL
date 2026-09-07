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


class CoreDomainTypeIrSemanticsTests(unittest.TestCase):
    def _ir(self) -> dict:
        source = (PROJECT / "app.aidl").read_text(encoding="utf-8") + """

export alias SnapshotLabel = string
export opaque SnapshotToken = uuid
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
    def _declaration(document: dict, kind: str, name: str) -> dict:
        return next(
            declaration
            for declaration in document["declarations"]
            if declaration["kind"] == kind and declaration["name"] == name
        )

    @staticmethod
    def _schema_errors(document: dict):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        return tuple(validator.iter_errors(document))

    def test_alias_target_and_opaque_representation_are_materialized(self) -> None:
        first = self._ir()
        second = self._ir()

        alias = self._declaration(first, "alias", "SnapshotLabel")
        opaque = self._declaration(first, "opaque", "SnapshotToken")
        self.assertEqual(alias, self._declaration(second, "alias", "SnapshotLabel"))
        self.assertEqual(opaque, self._declaration(second, "opaque", "SnapshotToken"))
        self.assertEqual({"kind": "scalar", "name": "string"}, alias["target"])
        self.assertEqual({"kind": "scalar", "name": "uuid"}, opaque["representation"])
        self.assertEqual((), self._schema_errors(first))

    def test_closed_ir_schema_rejects_missing_or_malformed_domain_type_contracts(self) -> None:
        base = self._ir()

        missing_target = copy.deepcopy(base)
        del self._declaration(missing_target, "alias", "SnapshotLabel")["target"]
        self.assertTrue(self._schema_errors(missing_target))

        malformed_target = copy.deepcopy(base)
        self._declaration(malformed_target, "alias", "SnapshotLabel")["target"] = {"kind": "set"}
        self.assertTrue(self._schema_errors(malformed_target))

        missing_representation = copy.deepcopy(base)
        del self._declaration(missing_representation, "opaque", "SnapshotToken")["representation"]
        self.assertTrue(self._schema_errors(missing_representation))

        malformed_representation = copy.deepcopy(base)
        self._declaration(malformed_representation, "opaque", "SnapshotToken")["representation"] = {
            "kind": "map",
            "key": {"kind": "scalar", "name": "string"},
        }
        self.assertTrue(self._schema_errors(malformed_representation))


if __name__ == "__main__":
    unittest.main()
