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


class CoreEnumIrSemanticsTests(unittest.TestCase):
    def _analysis(self, enum_source: str):
        source = (PROJECT / "app.aidl").read_text(encoding="utf-8") + "\n\n" + enum_source + "\n"
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "app.aidl"
        path.write_text(source, encoding="utf-8")
        return path, load_compiler_analysis([path])

    def _valid_path(self) -> Path:
        source = (PROJECT / "app.aidl").read_text(encoding="utf-8") + """

export enum SnapshotState { Draft, Published, Archived }
"""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "app.aidl"
        path.write_text(source, encoding="utf-8")
        return path

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

    def test_enum_identity_and_unassigned_cases_are_preserved_deterministically(self) -> None:
        path = self._valid_path()
        first_analysis = load_compiler_analysis([path])
        second_analysis = load_compiler_analysis([path])
        self.assertFalse(
            any(diagnostic.severity.value == "error" for diagnostic in first_analysis.diagnostics),
            [diagnostic.to_json() for diagnostic in first_analysis.diagnostics],
        )
        self.assertFalse(
            any(diagnostic.severity.value == "error" for diagnostic in second_analysis.diagnostics),
            [diagnostic.to_json() for diagnostic in second_analysis.diagnostics],
        )

        first = build_canonical_ir(first_analysis)
        second = build_canonical_ir(second_analysis)
        self.assertEqual(first, second)

        enum = self._enum(first)
        self.assertEqual("SnapshotState", enum["name"])
        self.assertEqual("enum", enum["kind"])
        self.assertEqual("fixtures.valid.m4minimal.SnapshotState", enum["fqn"])
        self.assertEqual("fixtures.valid.m4minimal.SnapshotState@1", enum["declarationId"])
        self.assertEqual(["Draft", "Published", "Archived"], enum["values"])
        self.assertEqual((), self._schema_errors(first))

    def test_unmaterializable_enum_source_forms_are_rejected_before_ir(self) -> None:
        cases = (
            (
                "empty",
                "export enum SnapshotState {}",
                "enum must contain at least one case",
            ),
            (
                "duplicate",
                "export enum SnapshotState { Draft, Draft }",
                "duplicate case identity 'Draft'",
            ),
            (
                "assigned-wire-value",
                'export enum SnapshotState { Draft = "draft", Published }',
                "declares wire value",
            ),
            (
                "malformed-number-assignment",
                "export enum SnapshotState { Draft = 7, Published }",
                "is malformed",
            ),
            (
                "malformed-extra-token",
                "export enum SnapshotState { Draft Published }",
                "is malformed",
            ),
            (
                "malformed-trailing-comma",
                "export enum SnapshotState { Draft, }",
                "is malformed",
            ),
        )
        for name, enum_source, expected_message in cases:
            with self.subTest(name=name):
                _, analysis = self._analysis(enum_source)
                diagnostics = [
                    diagnostic
                    for diagnostic in analysis.diagnostics
                    if diagnostic.code.value == "AIDL-T005"
                    and diagnostic.subject.kind == "enum"
                    and diagnostic.subject.name == "SnapshotState"
                ]
                self.assertTrue(diagnostics, [diagnostic.to_json() for diagnostic in analysis.diagnostics])
                self.assertTrue(
                    any(expected_message in diagnostic.message for diagnostic in diagnostics),
                    [diagnostic.to_json() for diagnostic in diagnostics],
                )
                with self.assertRaises(IrBuildError):
                    build_canonical_ir(analysis)

    def test_closed_ir_schema_rejects_invalid_enum_case_contracts(self) -> None:
        path = self._valid_path()
        analysis = load_compiler_analysis([path])
        self.assertFalse(
            any(diagnostic.severity.value == "error" for diagnostic in analysis.diagnostics),
            [diagnostic.to_json() for diagnostic in analysis.diagnostics],
        )
        base = build_canonical_ir(analysis)

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
