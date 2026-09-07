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


class CoreErrorContractIrSemanticsTests(unittest.TestCase):
    def _ir(self) -> dict:
        source = (PROJECT / "app.aidl").read_text(encoding="utf-8") + """

export error SnapshotConflict {
  code "SNAPSHOT_CONFLICT"
  httpStatus 409
  retry never
  safeMessage "Snapshot conflict"
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

    def _error(self, document: dict) -> dict:
        return next(
            declaration
            for declaration in document["declarations"]
            if declaration["kind"] == "error" and declaration["name"] == "SnapshotConflict"
        )

    def _schema_errors(self, document: dict):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        return tuple(validator.iter_errors(document))

    def test_error_contract_is_materialized_from_source(self) -> None:
        first = self._ir()
        second = self._ir()
        self.assertEqual(self._error(first), self._error(second))

        error = self._error(first)
        self.assertEqual("SNAPSHOT_CONFLICT", error["code"])
        self.assertEqual("Snapshot conflict", error["safeMessage"])
        self.assertEqual("never", error["retry"])
        self.assertEqual(409, error["transportStatus"])
        self.assertEqual((), self._schema_errors(first))

    def test_invalid_exported_error_contract_has_stable_type_diagnostics(self) -> None:
        source = """module test.error
export error Broken {
  code ""
  httpStatus 200
  retry sometimes
  safeMessage ""
}
"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "app.aidl"
            path.write_text(source, encoding="utf-8")
            diagnostics = [
                diagnostic
                for diagnostic in load_compiler_analysis([path]).diagnostics
                if diagnostic.code.value == TYPE_CODE
            ]
        self.assertGreaterEqual(len(diagnostics), 4)
        messages = "\n".join(diagnostic.message for diagnostic in diagnostics)
        self.assertIn("error code must be a non-empty string", messages)
        self.assertIn("invalid public error httpStatus", messages)
        self.assertIn("invalid error retry class", messages)
        self.assertIn("safeMessage", messages)
        self.assertTrue(all(diagnostic.phase == "type" for diagnostic in diagnostics))

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
