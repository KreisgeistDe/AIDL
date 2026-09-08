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

export value SnapshotReferenceTarget {
  id: uuid
}

export value SnapshotValueContract {
  label: string required
  optionalLabel: string?
  sensitiveLabel: string sensitive
  mutableCount: int mutable
  generatedToken: uuid generated
  constrainedLabel: string(1..80) required mutable
  labels: set<string>
  lookup: map<string, uuid?>
  optionalSecret: string? sensitive
  requiredLabels: set<string> required
  nestedLookup: map<string, set<uuid?>?>? generated
  related: SnapshotReferenceTarget
  primaryLike: uuid primary
  revisionToken: revision concurrencyToken
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

    def test_value_fields_preserve_order_types_and_independent_core_metadata(self) -> None:
        first = self._ir()
        second = self._ir()
        value = self._declaration(first, "SnapshotValueContract")
        second_value = self._declaration(second, "SnapshotValueContract")

        self.assertEqual(value, second_value)
        self.assertEqual(
            [
                "label",
                "optionalLabel",
                "sensitiveLabel",
                "mutableCount",
                "generatedToken",
                "constrainedLabel",
                "labels",
                "lookup",
                "optionalSecret",
                "requiredLabels",
                "nestedLookup",
                "related",
                "primaryLike",
                "revisionToken",
            ],
            [field["name"] for field in value["fields"]],
        )

        fields = {field["name"]: field for field in value["fields"]}
        label = fields["label"]
        self.assertEqual({"kind": "scalar", "name": "string"}, label["type"])
        self.assertTrue(label["required"])

        optional_label = fields["optionalLabel"]
        self.assertEqual(
            {"kind": "nullable", "element": {"kind": "scalar", "name": "string"}},
            optional_label["type"],
        )
        self.assertFalse(optional_label["required"])

        self.assertTrue(fields["sensitiveLabel"]["sensitive"])
        self.assertTrue(fields["mutableCount"]["mutable"])
        self.assertTrue(fields["generatedToken"]["generated"])
        self.assertEqual(
            {
                "kind": "scalar",
                "name": "string",
                "constraints": {"minLength": 1, "maxLength": 80},
            },
            fields["constrainedLabel"]["type"],
        )
        self.assertTrue(fields["constrainedLabel"]["required"])
        self.assertTrue(fields["constrainedLabel"]["mutable"])
        self.assertEqual(
            {"kind": "set", "element": {"kind": "scalar", "name": "string"}},
            fields["labels"]["type"],
        )
        self.assertTrue(fields["labels"]["required"])
        self.assertEqual(
            {
                "kind": "map",
                "key": {"kind": "scalar", "name": "string"},
                "value": {"kind": "nullable", "element": {"kind": "scalar", "name": "uuid"}},
            },
            fields["lookup"]["type"],
        )
        self.assertTrue(fields["lookup"]["required"])
        self.assertEqual(
            {
                "kind": "named",
                "declarationId": "fixtures.valid.m4minimal.SnapshotReferenceTarget@1",
                "fqn": "fixtures.valid.m4minimal.SnapshotReferenceTarget",
                "typeArguments": [],
            },
            fields["related"]["type"],
        )
        self.assertTrue(fields["primaryLike"]["primary"])
        self.assertTrue(fields["revisionToken"]["concurrencyToken"])
        self.assertEqual((), self._schema_errors(first))

    def test_value_type_and_modifier_combinations_are_split_without_losing_semantics(self) -> None:
        value = self._declaration(self._ir(), "SnapshotValueContract")
        fields = {field["name"]: field for field in value["fields"]}

        optional_secret = fields["optionalSecret"]
        self.assertEqual(
            {"kind": "nullable", "element": {"kind": "scalar", "name": "string"}},
            optional_secret["type"],
        )
        self.assertFalse(optional_secret["required"])
        self.assertTrue(optional_secret["sensitive"])

        required_labels = fields["requiredLabels"]
        self.assertEqual(
            {"kind": "set", "element": {"kind": "scalar", "name": "string"}},
            required_labels["type"],
        )
        self.assertTrue(required_labels["required"])

        nested_lookup = fields["nestedLookup"]
        self.assertEqual(
            {
                "kind": "nullable",
                "element": {
                    "kind": "map",
                    "key": {"kind": "scalar", "name": "string"},
                    "value": {
                        "kind": "nullable",
                        "element": {
                            "kind": "set",
                            "element": {
                                "kind": "nullable",
                                "element": {"kind": "scalar", "name": "uuid"},
                            },
                        },
                    },
                },
            },
            nested_lookup["type"],
        )
        self.assertFalse(nested_lookup["required"])
        self.assertTrue(nested_lookup["generated"])

    def test_value_rejects_every_non_materialized_body_fact_before_ir(self) -> None:
        cases = {
            "invariant": "invariant NonEmpty: label != \"\"",
            "non-field": "notAField",
            "duplicate": "label: string\n  label: string",
            "nullable-required": "label: string? required",
            "clientGenerated": "label: string clientGenerated",
            "immutable": "label: string immutable",
            "unique": "label: string unique",
            "default": "label: string default \"x\"",
            "onDelete": "label: string onDelete restrict",
            "via": "label: string via codec",
            "repeated-modifier": "label: string mutable mutable",
        }
        for name, body in cases.items():
            with self.subTest(name=name):
                analysis = self._analysis(
                    f"""

export value BrokenValue {{
  {body}
}}
"""
                )
                diagnostics = [
                    diagnostic
                    for diagnostic in analysis.diagnostics
                    if diagnostic.code.value == "AIDL-T005"
                    and diagnostic.subject is not None
                    and diagnostic.subject.kind == "value"
                    and diagnostic.subject.name == "BrokenValue"
                ]
                self.assertTrue(diagnostics, [d.to_json() for d in analysis.diagnostics])
                self.assertTrue(all(d.phase == "type" for d in diagnostics))
                self.assertTrue(all(d.location.line > 0 and d.location.column > 0 for d in diagnostics))
                with self.assertRaises(IrBuildError):
                    build_canonical_ir(analysis)

    def test_unowned_malformed_value_type_is_rejected_before_ir(self) -> None:
        analysis = self._analysis(
            """

export value BrokenValue {
  labels: map<string
}
"""
        )
        diagnostics = [
            diagnostic
            for diagnostic in analysis.diagnostics
            if diagnostic.code.value == "AIDL-T005"
            and diagnostic.subject is not None
            and diagnostic.subject.kind == "value"
            and diagnostic.subject.name == "BrokenValue"
        ]
        self.assertEqual(len(diagnostics), 1, [d.to_json() for d in analysis.diagnostics])
        self.assertIn("not losslessly materialized", diagnostics[0].message)
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_existing_generic_materialization_boundary_is_not_duplicated(self) -> None:
        analysis = self._analysis(
            """

export value GenericValue<T> {
  value: T
}
"""
        )
        diagnostics = [
            diagnostic
            for diagnostic in analysis.diagnostics
            if diagnostic.code.value == "AIDL-T005"
            and diagnostic.subject is not None
            and diagnostic.subject.kind == "value"
            and diagnostic.subject.name == "GenericValue"
        ]
        self.assertEqual(len(diagnostics), 1, [d.to_json() for d in analysis.diagnostics])
        self.assertIn("type parameters are not materialized", diagnostics[0].message)
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_closed_ir_schema_rejects_missing_or_malformed_value_field_contract(self) -> None:
        base = self._ir()
        fields = {field["name"]: field for field in self._declaration(base, "SnapshotValueContract")["fields"]}

        missing_required = copy.deepcopy(base)
        missing_fields = {field["name"]: field for field in self._declaration(missing_required, "SnapshotValueContract")["fields"]}
        del missing_fields["label"]["required"]
        self.assertTrue(self._schema_errors(missing_required))

        malformed_sensitive = copy.deepcopy(base)
        malformed_fields = {field["name"]: field for field in self._declaration(malformed_sensitive, "SnapshotValueContract")["fields"]}
        malformed_fields["optionalSecret"]["sensitive"] = "yes"
        self.assertTrue(self._schema_errors(malformed_sensitive))

        missing_type = copy.deepcopy(base)
        missing_type_fields = {field["name"]: field for field in self._declaration(missing_type, "SnapshotValueContract")["fields"]}
        del missing_type_fields["requiredLabels"]["type"]
        self.assertTrue(self._schema_errors(missing_type))

        malformed_type = copy.deepcopy(base)
        malformed_type_fields = {field["name"]: field for field in self._declaration(malformed_type, "SnapshotValueContract")["fields"]}
        malformed_type_fields["nestedLookup"]["type"] = {"kind": "map"}
        self.assertTrue(self._schema_errors(malformed_type))

        self.assertIn("constrainedLabel", fields)


if __name__ == "__main__":
    unittest.main()
