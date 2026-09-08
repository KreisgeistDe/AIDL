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
TYPE_CODE = "AIDL-T003"
MATERIALIZATION_CODE = "AIDL-T005"
_VALID_ERROR = """

export error SnapshotConflict {
  code "SNAPSHOT_CONFLICT"
  httpStatus 409
  retry never
  safeMessage "Snapshot conflict"
}
"""


class CoreErrorContractIrSemanticsTests(unittest.TestCase):
    def _project(self, suffix: str):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "app.aidl"
        source = (PROJECT / "app.aidl").read_text(encoding="utf-8") + suffix
        path.write_text(source, encoding="utf-8")
        return temporary, path

    def _analysis(self, suffix: str):
        temporary, path = self._project(suffix)
        self.addCleanup(temporary.cleanup)
        return load_compiler_analysis([path])

    def _materialization_diagnostics(self, suffix: str):
        return tuple(
            diagnostic
            for diagnostic in self._analysis(suffix).diagnostics
            if diagnostic.code.value == MATERIALIZATION_CODE
            and diagnostic.subject.kind == "error"
        )

    def _ir(self) -> dict:
        analysis = self._analysis(_VALID_ERROR)
        self.assertFalse(
            any(diagnostic.severity.value == "error" for diagnostic in analysis.diagnostics),
            [diagnostic.to_json() for diagnostic in analysis.diagnostics],
        )
        return build_canonical_ir(analysis)

    def _error(self, document: dict) -> dict:
        return next(
            declaration
            for declaration in document["declarations"]
            if declaration["kind"] == "error" and declaration["name"] == "SnapshotConflict"
        )

    def _schema_errors(self, document: dict):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        return tuple(validator.iter_errors(document))

    def test_error_contract_is_materialized_deterministically_from_explicit_source(self) -> None:
        temporary, path = self._project(_VALID_ERROR)
        self.addCleanup(temporary.cleanup)
        first_analysis = load_compiler_analysis([path])
        second_analysis = load_compiler_analysis([path])
        self.assertFalse(any(d.severity.value == "error" for d in first_analysis.diagnostics))
        self.assertFalse(any(d.severity.value == "error" for d in second_analysis.diagnostics))
        first = build_canonical_ir(first_analysis)
        second = build_canonical_ir(second_analysis)

        self.assertEqual(first, second)
        error = self._error(first)
        self.assertEqual("fixtures.valid.m4minimal.SnapshotConflict", error["fqn"])
        self.assertEqual("fixtures.valid.m4minimal.SnapshotConflict@1", error["declarationId"])
        self.assertEqual("SNAPSHOT_CONFLICT", error["code"])
        self.assertEqual("Snapshot conflict", error["safeMessage"])
        self.assertEqual("never", error["retry"])
        self.assertEqual(409, error["transportStatus"])
        source_entry = next(
            entry
            for entry in first["sourceMap"]["entries"]
            if entry["originalDeclarationId"] == error["declarationId"]
        )
        self.assertRegex(source_entry["nodePath"], r"^/declarations/\d+$")
        self.assertEqual(path.as_posix(), source_entry["span"]["file"])
        self.assertEqual((), self._schema_errors(first))

    def test_materialization_only_error_facts_are_rejected_before_ir(self) -> None:
        cases = {
            "localization key": _VALID_ERROR.replace(
                'safeMessage "Snapshot conflict"',
                'localizationKey "errors.snapshotConflict"',
            ),
            "payload field": _VALID_ERROR.replace(
                'safeMessage "Snapshot conflict"',
                'safeMessage "Snapshot conflict"\n  details: string',
            ),
            "immediate retry": _VALID_ERROR.replace("retry never", "retry immediate"),
            "backoff retry": _VALID_ERROR.replace("retry never", "retry backoff"),
            "after retry": _VALID_ERROR.replace("retry never", "retry after 5s"),
            "non-exported missing code": _VALID_ERROR.replace("export error", "error").replace(
                '  code "SNAPSHOT_CONFLICT"\n', ""
            ),
            "non-exported duplicate safeMessage": _VALID_ERROR.replace("export error", "error").replace(
                '  safeMessage "Snapshot conflict"',
                '  safeMessage "Snapshot conflict"\n  safeMessage "Again"',
            ),
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                diagnostics = self._materialization_diagnostics(source)
                self.assertGreaterEqual(len(diagnostics), 1)
                self.assertTrue(all(d.phase == "type" for d in diagnostics))
                self.assertTrue(all(d.location.line > 0 for d in diagnostics))

    def test_existing_exported_error_contract_failures_remain_owned_by_t003(self) -> None:
        cases = {
            "missing code": _VALID_ERROR.replace('  code "SNAPSHOT_CONFLICT"\n', ""),
            "duplicate code": _VALID_ERROR.replace(
                '  code "SNAPSHOT_CONFLICT"',
                '  code "SNAPSHOT_CONFLICT"\n  code "SNAPSHOT_CONFLICT_2"',
            ),
            "invalid code": _VALID_ERROR.replace('code "SNAPSHOT_CONFLICT"', 'code ""'),
            "invalid status": _VALID_ERROR.replace("httpStatus 409", "httpStatus 200"),
            "invalid retry": _VALID_ERROR.replace("retry never", "retry sometimes"),
            "invalid message": _VALID_ERROR.replace(
                'safeMessage "Snapshot conflict"', 'safeMessage ""'
            ),
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                analysis = self._analysis(source)
                t003 = [d for d in analysis.diagnostics if d.code.value == TYPE_CODE]
                t005 = [
                    d
                    for d in analysis.diagnostics
                    if d.code.value == MATERIALIZATION_CODE and d.subject.kind == "error"
                ]
                self.assertGreaterEqual(len(t003), 1)
                self.assertEqual([], t005)

    def test_ir_schema_rejects_invalid_error_contract_values(self) -> None:
        base = self._ir()
        invalid_values = {
            "code": "",
            "retry": "sometimes",
            "transportStatus": 99,
        }
        for key, value in invalid_values.items():
            with self.subTest(key=key, value=value):
                document = copy.deepcopy(base)
                self._error(document)[key] = value
                self.assertTrue(self._schema_errors(document))


if __name__ == "__main__":
    unittest.main()
