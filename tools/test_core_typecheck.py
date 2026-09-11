from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import IrBuildError, build_canonical_ir
from tools.compiler_typecheck import TypeSyntaxError, operation_errors_evidence, parse_type

ROOT = Path(__file__).resolve().parents[1]
TYPE_CODES = {"AIDL-T001", "AIDL-T002", "AIDL-T003", "AIDL-T004", "AIDL-T005"}


class CoreTypeCheckingTests(unittest.TestCase):
    def _analysis(self, source: str):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "app.aidl"
            path.write_text(source, encoding="utf-8")
            analysis = load_compiler_analysis([path])
            return tuple(
                diagnostic
                for diagnostic in analysis.diagnostics
                if diagnostic.code.value in TYPE_CODES
            )

    def _errors_evidence(self, source: str):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "app.aidl"
            path.write_text(source, encoding="utf-8")
            analysis = load_compiler_analysis([path])
            operation = next(
                item
                for item in analysis.project.declaration_names
                if item.declaration.kind in {"query", "mutation"}
            )
            evidence = operation_errors_evidence(analysis.project, operation)
            diagnostics = tuple(
                diagnostic
                for diagnostic in analysis.diagnostics
                if diagnostic.code.value in TYPE_CODES
            )
            return evidence, diagnostics

    def test_core_type_constructors_and_int_to_decimal_default(self) -> None:
        with self.assertRaises(TypeSyntaxError):
            parse_type("set<string, int>")

        diagnostics = self._analysis(
            """module test.types
export entity Target {
  id: uuid primary
}
export value Shape {
  okSet: set<string>
  okMap: map<string, [uuid?]>
  target: ref Target
  badMap: map<[string], int>
  badRef: ref MissingEntity
}
export query convert(amount: decimal default 1, count: int default 1.5) -> string {
  errors: []
}
"""
        )
        codes = [diagnostic.code.value for diagnostic in diagnostics]
        self.assertEqual(codes.count("AIDL-T001"), 1)
        self.assertEqual(codes.count("AIDL-T002"), 1)
        self.assertNotIn("AIDL-T003", codes)
        self.assertNotIn("AIDL-T005", codes)
        self.assertTrue(all(diagnostic.phase == "type" for diagnostic in diagnostics))

    def test_operation_signature_reports_duplicate_and_default_mismatch(self) -> None:
        diagnostics = self._analysis(
            """module test.signatures
export query broken(id: uuid, id: string, count: int default 1.5) -> string {
  errors: []
}
"""
        )
        self.assertEqual(
            [diagnostic.code.value for diagnostic in diagnostics],
            ["AIDL-T002", "AIDL-T002"],
        )
        self.assertTrue(any("duplicate parameter" in diagnostic.message for diagnostic in diagnostics))
        self.assertTrue(any("not assignable" in diagnostic.message for diagnostic in diagnostics))

    def test_typed_error_contracts_and_declared_error_types(self) -> None:
        diagnostics = self._analysis(
            """module test.errors
export error Broken {
  code "BROKEN"
  httpStatus 200
  retry sometimes
  safeMessage ""
}
export value NotAnError {
  value: string
}
export query read() -> string {
  errors: [Broken, NotAnError, Broken]
}
"""
        )
        self.assertTrue(diagnostics)
        self.assertTrue(all(diagnostic.code.value == "AIDL-T003" for diagnostic in diagnostics))
        self.assertTrue(any("httpStatus" in diagnostic.message for diagnostic in diagnostics))
        self.assertTrue(any("retry" in diagnostic.message for diagnostic in diagnostics))
        self.assertTrue(any("safeMessage" in diagnostic.message for diagnostic in diagnostics))
        self.assertTrue(any("NotAnError" in diagnostic.message for diagnostic in diagnostics))
        self.assertTrue(any("duplicate declared error" in diagnostic.message for diagnostic in diagnostics))

    def test_typed_body_clause_evidence_is_stricter_than_global_diagnostics(self) -> None:
        evidence, diagnostics = self._errors_evidence(
            """module test.errors
export error KnownError {
  code "KNOWN"
  httpStatus 400
  retry never
  safeMessage "Known error"
}
export value NotAnError {
  value: string
}
export query read() -> string {
  errors: [InternalFailure, KnownError, MissingError, NotAnError]
}
"""
        )
        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            [member.source for member in evidence[0].members],
            ["InternalFailure", "KnownError", "MissingError", "NotAnError"],
        )
        self.assertEqual(
            [member.status for member in evidence[0].members],
            ["standard", "resolved", "unresolved", "wrong_kind"],
        )
        self.assertFalse(evidence[0].complete)
        self.assertFalse([d for d in diagnostics if d.code.value == "AIDL-T001"])
        self.assertTrue(any(d.code.value == "AIDL-T003" and "NotAnError" in d.message for d in diagnostics))

    def test_typed_body_clause_evidence_preserves_order_whitespace_and_qualified_resolution(self) -> None:
        evidence, _ = self._errors_evidence(
            """module test.errors
export error FirstError {
  code "FIRST"
  httpStatus 400
  retry never
  safeMessage "First"
}
export error SecondError {
  code "SECOND"
  httpStatus 400
  retry never
  safeMessage "Second"
}
export mutation write() -> string {
  errors: [ test.errors.FirstError ,   SecondError , InternalFailure ]
}
"""
        )
        self.assertEqual(len(evidence), 1)
        self.assertTrue(evidence[0].complete)
        self.assertEqual(
            [member.source for member in evidence[0].members],
            ["test.errors.FirstError", "SecondError", "InternalFailure"],
        )
        self.assertEqual(
            [member.status for member in evidence[0].members],
            ["resolved", "resolved", "standard"],
        )
        self.assertEqual(evidence[0].members[0].target, "test.errors.FirstError")

    def test_typed_body_clause_evidence_marks_ambiguous_and_malformed_incomplete(self) -> None:
        ambiguous, _ = self._errors_evidence(
            """module test.errors
export error Clash {
  code "CLASH_A"
  httpStatus 400
  retry never
  safeMessage "A"
}
export error Clash {
  code "CLASH_B"
  httpStatus 401
  retry never
  safeMessage "B"
}
export query read() -> string {
  errors: [Clash]
}
"""
        )
        self.assertEqual([member.status for member in ambiguous[0].members], ["ambiguous"])
        self.assertFalse(ambiguous[0].complete)

        malformed, diagnostics = self._errors_evidence(
            """module test.errors
export query read() -> string {
  errors: [InternalFailure,,RateLimited]
}
"""
        )
        self.assertTrue(malformed[0].malformed)
        self.assertFalse(malformed[0].complete)
        self.assertTrue(any(d.code.value == "AIDL-T003" for d in diagnostics))

    def test_public_api_rejects_owner_local_refs_and_sensitive_values(self) -> None:
        diagnostics = self._analysis(
            """module test.serialization
export entity Account {
  id: uuid primary
}
export value SecretInput {
  token: string sensitive
}
export query refLeak(account: ref Account) -> ref Account { errors: [] }
export query secretLeak(input: SecretInput) -> string { errors: [] }
export api PublicApi {
  transport rest
  version 1
  operations [query refLeak, query secretLeak]
  auth inherit
  errors problemDetails
  compatibility backward
}
"""
        )
        serialization = [d for d in diagnostics if d.code.value == "AIDL-T004"]
        self.assertEqual(len(serialization), 3)
        self.assertTrue(all(d.docs == "aidl://diagnostics/AIDL-T004" for d in serialization))

    def test_unresolved_alias_nominal_has_materialization_diagnostic(self) -> None:
        diagnostics = self._analysis("module test.materialization\nalias Broken = MissingValue\n")
        materialization = [d for d in diagnostics if d.code.value == "AIDL-T005"]
        self.assertEqual(len(materialization), 1)
        self.assertIn("may not fall back to a synthetic aidl.std identity", materialization[0].message)
        self.assertEqual(materialization[0].phase, "type")
        self.assertGreater(materialization[0].location.line, 0)

    def test_unresolved_declared_error_is_rejected_explicitly(self) -> None:
        diagnostics = self._analysis(
            """module test.errors
export query read() -> string {
  errors: [MissingProfileError]
}
"""
        )
        materialization = [d for d in diagnostics if d.code.value == "AIDL-T005"]
        self.assertEqual(len(materialization), 1)
        self.assertIn("MissingProfileError", materialization[0].message)
        self.assertEqual(materialization[0].phase, "type")
        self.assertEqual(materialization[0].docs, "aidl://diagnostics/AIDL-T005")

    def test_materialization_rejects_resolved_non_type_nominal(self) -> None:
        diagnostics = self._analysis(
            """module test.wrongkind
export resource Db sql {
  consistency strong
}
export value Broken {
  db: Db
}
"""
        )
        materialization = [d for d in diagnostics if d.code.value == "AIDL-T005"]
        self.assertEqual(len(materialization), 1)
        self.assertIn("unsupported declaration kind 'resource'", materialization[0].message)
        self.assertEqual(materialization[0].phase, "type")
        self.assertEqual(materialization[0].docs, "aidl://diagnostics/AIDL-T005")
        self.assertGreater(materialization[0].location.line, 0)
        self.assertGreater(materialization[0].location.column, 0)

    def test_materialization_rejects_entity_identity_on_non_entity(self) -> None:
        diagnostics = self._analysis(
            """module test.identity
export value NotEntity {
  id: uuid
}
export query read(id: NotEntity.id) -> string {
  errors: []
}
"""
        )
        materialization = [d for d in diagnostics if d.code.value == "AIDL-T005"]
        self.assertEqual(len(materialization), 1)
        self.assertIn("unsupported declaration kind 'value'", materialization[0].message)

    def test_materialization_rejects_generic_project_declaration_before_ir_drop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "app.aidl"
            path.write_text(
                """module test.generics
export value Box<T> {
  value: T
}
""",
                encoding="utf-8",
            )
            analysis = load_compiler_analysis([path])
        materialization = [d for d in analysis.diagnostics if d.code.value == "AIDL-T005"]
        self.assertEqual(len(materialization), 1)
        self.assertIn("type parameters are not materialized in canonical IR", materialization[0].message)
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_reference_applications_have_no_core_type_diagnostics(self) -> None:
        for relative in ("examples/petstore", "examples/calendar-offline", "examples/videohub"):
            with self.subTest(relative=relative):
                first = [
                    diagnostic.to_json()
                    for diagnostic in load_compiler_analysis([ROOT / relative]).diagnostics
                    if diagnostic.code.value in TYPE_CODES
                ]
                second = [
                    diagnostic.to_json()
                    for diagnostic in load_compiler_analysis([ROOT / relative]).diagnostics
                    if diagnostic.code.value in TYPE_CODES
                ]
                self.assertEqual(first, second)
                self.assertEqual(first, [])


if __name__ == "__main__":
    unittest.main()
