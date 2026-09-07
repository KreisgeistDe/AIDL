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

    def _analysis_sources(self, sources: dict[str, str]):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        paths = []
        for name, source in sorted(sources.items()):
            path = root / name
            path.write_text(source, encoding="utf-8")
            paths.append(path)
        return load_compiler_analysis(paths)

    @staticmethod
    def _type_diagnostics(analysis, subject: str | None = None):
        diagnostics = [
            diagnostic
            for diagnostic in analysis.diagnostics
            if diagnostic.code.value in TYPE_CODES
        ]
        if subject is not None:
            diagnostics = [
                diagnostic for diagnostic in diagnostics
                if diagnostic.subject.name == subject
            ]
        return diagnostics

    def _ir(self) -> dict:
        analysis = self._analysis(
            """

export alias SnapshotLabel = string
export opaque SnapshotToken = uuid
export alias SnapshotLabels = set<string?>
export opaque SnapshotIndex = map<string, uuid?>
export alias SnapshotProjectLabel = SnapshotLabel
export opaque SnapshotOperation = OperationId
export alias SnapshotNested = map<string, [SnapshotLabel?]>?
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

    def test_alias_opaque_preserve_project_standard_and_nested_type_refs(self) -> None:
        first = self._ir()
        second = self._ir()

        source_alias = self._declaration(first, "alias", "SnapshotLabel")
        project_alias = self._declaration(first, "alias", "SnapshotProjectLabel")
        standard_opaque = self._declaration(first, "opaque", "SnapshotOperation")
        nested_alias = self._declaration(first, "alias", "SnapshotNested")

        self.assertEqual(project_alias, self._declaration(second, "alias", "SnapshotProjectLabel"))
        self.assertEqual(standard_opaque, self._declaration(second, "opaque", "SnapshotOperation"))
        self.assertEqual(nested_alias, self._declaration(second, "alias", "SnapshotNested"))
        self.assertEqual(
            {
                "kind": "named",
                "declarationId": source_alias["declarationId"],
                "fqn": source_alias["fqn"],
                "typeArguments": [],
            },
            project_alias["target"],
        )
        self.assertEqual(
            {
                "kind": "named",
                "declarationId": "aidl.std.OperationId@1",
                "fqn": "aidl.std.OperationId",
                "typeArguments": [],
            },
            standard_opaque["representation"],
        )
        self.assertEqual(
            {
                "kind": "nullable",
                "element": {
                    "kind": "map",
                    "key": {"kind": "scalar", "name": "string"},
                    "value": {
                        "kind": "list",
                        "element": {
                            "kind": "nullable",
                            "element": {
                                "kind": "named",
                                "declarationId": source_alias["declarationId"],
                                "fqn": source_alias["fqn"],
                                "typeArguments": [],
                            },
                        },
                    },
                },
            },
            nested_alias["target"],
        )
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

    def test_missing_unresolved_and_fake_standard_targets_are_rejected_before_ir(self) -> None:
        analysis = self._analysis(
            """

export alias MissingTarget
export alias MissingNominal = ProjectTypeThatDoesNotExist
export opaque FakeStandard = other.OperationId
"""
        )
        diagnostics = self._type_diagnostics(analysis)
        self.assertEqual([diagnostic.code.value for diagnostic in diagnostics], ["AIDL-T005"] * 3)
        self.assertTrue(any("must declare '= type'" in diagnostic.message for diagnostic in diagnostics))
        self.assertTrue(any("may not fall back to a synthetic aidl.std identity" in diagnostic.message for diagnostic in diagnostics))
        self.assertTrue(all(diagnostic.location.line > 0 for diagnostic in diagnostics))
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_ambiguous_project_nominal_target_is_rejected_before_ir(self) -> None:
        analysis = self._analysis_sources(
            {
                "alpha.aidl": "module alpha\nexport alias Shared = string\n",
                "beta.aidl": "module beta\nexport alias Shared = string\n",
                "gamma.aidl": "module gamma\nimport alpha.*\nimport beta.*\nexport alias Use = Shared\n",
            }
        )
        diagnostics = self._type_diagnostics(analysis, "Use")
        self.assertEqual([diagnostic.code.value for diagnostic in diagnostics], ["AIDL-T005"])
        self.assertIn("ambiguous", diagnostics[0].message)
        self.assertGreater(diagnostics[0].location.line, 0)

    def test_wrong_kind_generic_and_inline_enum_targets_are_rejected_before_ir(self) -> None:
        wrong_kind = self._analysis(
            """

service WrongKindService {}
export alias WrongKind = WrongKindService
"""
        )
        diagnostics = self._type_diagnostics(wrong_kind, "WrongKind")
        self.assertEqual([diagnostic.code.value for diagnostic in diagnostics], ["AIDL-T005"])
        self.assertIn("unsupported declaration kind 'service'", diagnostics[0].message)

        generic_use = self._analysis(
            """

export value GenericValue<T> {
  item: T
}
export opaque GenericUse = GenericValue<string>
"""
        )
        diagnostics = self._type_diagnostics(generic_use, "GenericUse")
        self.assertEqual([diagnostic.code.value for diagnostic in diagnostics], ["AIDL-T005"])
        self.assertIn("generic project type", diagnostics[0].message)

        generic_declaration = self._analysis("\nexport alias GenericAlias<T> = string\n")
        diagnostics = self._type_diagnostics(generic_declaration, "GenericAlias")
        self.assertEqual([diagnostic.code.value for diagnostic in diagnostics], ["AIDL-T005"])

        inline_enum = self._analysis('\nexport alias InlineWire = enum("one", "two")\n')
        diagnostics = self._type_diagnostics(inline_enum, "InlineWire")
        self.assertEqual([diagnostic.code.value for diagnostic in diagnostics], ["AIDL-T005"])
        self.assertIn("inline enum target", diagnostics[0].message)

    def test_unmaterialized_constraint_forms_are_rejected_but_closed_constraints_remain_valid(self) -> None:
        rejected = self._analysis(
            """

export alias StringLiteralConstraint = string(5)
export opaque BoolConstraint = bool(true)
export alias DecimalLiteralConstraint = decimal(0.1)
"""
        )
        diagnostics = self._type_diagnostics(rejected)
        self.assertEqual([diagnostic.code.value for diagnostic in diagnostics], ["AIDL-T005"] * 3)
        self.assertTrue(all("constraint form" in diagnostic.message for diagnostic in diagnostics))

        accepted = self._analysis(
            """

export alias SizedText = string(1..80)
export opaque BoundedInt = int(min: 0, max: 100)
export alias BoundedDecimal = decimal(min: -1.5, max: 2.5)
"""
        )
        self.assertEqual([], self._type_diagnostics(accepted))
        document = build_canonical_ir(accepted)
        self.assertEqual(
            {"kind": "scalar", "name": "string", "constraints": {"minLength": 1, "maxLength": 80}},
            self._declaration(document, "alias", "SizedText")["target"],
        )
        self.assertEqual((), self._schema_errors(document))

    def test_entity_identity_target_is_rejected_when_current_ir_would_erase_identity(self) -> None:
        analysis = self._analysis("\nexport alias ItemIdentity = SnapshotItem.id\n")
        diagnostics = self._type_diagnostics(analysis, "ItemIdentity")
        self.assertEqual([diagnostic.code.value for diagnostic in diagnostics], ["AIDL-T005"])
        self.assertIn("would lose its source identity", diagnostics[0].message)

    def test_invalid_set_and_map_source_is_rejected_before_ir(self) -> None:
        analysis = self._analysis(
            """

export alias BrokenSet = set<string, int>
export alias BrokenMap = map<[string], int>
"""
        )
        type_diagnostics = self._type_diagnostics(analysis)
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
