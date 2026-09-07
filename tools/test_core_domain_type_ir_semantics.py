from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import IrBuildError, build_canonical_ir


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "fixtures" / "valid" / "m4-minimal"
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))
TYPE_CODES = {"AIDL-T001", "AIDL-T002", "AIDL-T003", "AIDL-T004", "AIDL-T005"}


class CoreDomainTypeIrSemanticsTests(unittest.TestCase):
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

export alias SnapshotLabel = string
export opaque SnapshotToken = uuid
export alias SnapshotLabels = set<string?>
export opaque SnapshotIndex = map<string, uuid?>
export value SnapshotCollections {
  nested: map<string, set<uuid?>>?
}
"""
        )
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
    def _field(document: dict, declaration_name: str, field_name: str) -> dict:
        declaration = CoreDomainTypeIrSemanticsTests._declaration(document, "value", declaration_name)
        return next(field for field in declaration["fields"] if field["name"] == field_name)

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

    def test_set_and_map_type_constructors_preserve_nested_nullable_shape(self) -> None:
        first = self._ir()
        second = self._ir()

        labels = self._declaration(first, "alias", "SnapshotLabels")
        index = self._declaration(first, "opaque", "SnapshotIndex")
        nested = self._field(first, "SnapshotCollections", "nested")

        self.assertEqual(labels, self._declaration(second, "alias", "SnapshotLabels"))
        self.assertEqual(index, self._declaration(second, "opaque", "SnapshotIndex"))
        self.assertEqual(nested, self._field(second, "SnapshotCollections", "nested"))
        self.assertEqual(
            {
                "kind": "set",
                "element": {"kind": "nullable", "element": {"kind": "scalar", "name": "string"}},
            },
            labels["target"],
        )
        self.assertEqual(
            {
                "kind": "map",
                "key": {"kind": "scalar", "name": "string"},
                "value": {"kind": "nullable", "element": {"kind": "scalar", "name": "uuid"}},
            },
            index["representation"],
        )
        self.assertEqual(
            {
                "kind": "nullable",
                "element": {
                    "kind": "map",
                    "key": {"kind": "scalar", "name": "string"},
                    "value": {
                        "kind": "set",
                        "element": {
                            "kind": "nullable",
                            "element": {"kind": "scalar", "name": "uuid"},
                        },
                    },
                },
            },
            nested["type"],
        )
        self.assertFalse(nested["required"])
        self.assertEqual((), self._schema_errors(first))

    def test_invalid_set_and_map_source_is_rejected_before_ir(self) -> None:
        analysis = self._analysis(
            """

export value BrokenCollections {
  badSet: set<string, int>
  badMap: map<[string], int>
}
"""
        )
        type_diagnostics = [
            diagnostic
            for diagnostic in analysis.diagnostics
            if diagnostic.code.value in TYPE_CODES
        ]
        self.assertEqual([diagnostic.code.value for diagnostic in type_diagnostics], ["AIDL-T001", "AIDL-T001"])
        self.assertTrue(any("set requires one type argument" in diagnostic.message for diagnostic in type_diagnostics))
        self.assertTrue(any("map key" in diagnostic.message for diagnostic in type_diagnostics))
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_closed_ir_schema_rejects_missing_or_malformed_domain_type_contracts(self) -> None:
        base = self._ir()

        missing_target = copy.deepcopy(base)
        del self._declaration(missing_target, "alias", "SnapshotLabel")["target"]
        self.assertTrue(self._schema_errors(missing_target))

        malformed_target = copy.deepcopy(base)
        self._declaration(malformed_target, "alias", "SnapshotLabels")["target"] = {"kind": "set"}
        self.assertTrue(self._schema_errors(malformed_target))

        missing_representation = copy.deepcopy(base)
        del self._declaration(missing_representation, "opaque", "SnapshotToken")["representation"]
        self.assertTrue(self._schema_errors(missing_representation))

        malformed_representation = copy.deepcopy(base)
        self._declaration(malformed_representation, "opaque", "SnapshotIndex")["representation"] = {
            "kind": "map",
            "key": {"kind": "scalar", "name": "string"},
        }
        self.assertTrue(self._schema_errors(malformed_representation))


if __name__ == "__main__":
    unittest.main()
