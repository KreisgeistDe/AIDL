#!/usr/bin/env python3
"""Focused regressions for the M10.1 auth evidence prerequisite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_auth_evidence import operation_auth_evidence
from tools.compiler_diagnostics import load_compiler_analysis


class M101AuthEvidenceTest(unittest.TestCase):
    def _analysis(self, source_text: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "model.aidl"
        source.write_text(source_text, encoding="utf-8")
        return load_compiler_analysis([source])

    @staticmethod
    def _operation(analysis, name: str):
        return next(
            item
            for item in analysis.project.declaration_names
            if item.declaration.kind in {"query", "mutation"}
            and item.declaration.name == name
        )

    def test_query_and_mutation_builtin_modes_are_explicit_and_complete(self) -> None:
        analysis = self._analysis(
            """module demo
query qPublic() -> string { auth: public }
query qAuthenticated() -> string { auth: authenticated }
query qService() -> string { auth: service }
mutation mPublic() -> string { auth: public }
mutation mAuthenticated() -> string { auth: authenticated }
mutation mService() -> string { auth: service }
"""
        )
        for name, expected in (
            ("qPublic", "public"),
            ("qAuthenticated", "authenticated"),
            ("qService", "service"),
            ("mPublic", "public"),
            ("mAuthenticated", "authenticated"),
            ("mService", "service"),
        ):
            with self.subTest(name=name):
                evidence = operation_auth_evidence(
                    analysis.project, self._operation(analysis, name)
                )
                self.assertEqual(len(evidence), 1)
                self.assertEqual(evidence[0].source, expected)
                self.assertEqual(evidence[0].mode, "builtin")
                self.assertEqual(evidence[0].resolution, "builtin")
                self.assertIsNone(evidence[0].target)
                self.assertIsNone(evidence[0].target_kind)
                self.assertTrue(evidence[0].complete)

    def test_qualified_names_report_existing_resolution_states_but_remain_incomplete(self) -> None:
        analysis = self._analysis(
            """module demo
value Profile {}
value Clash {}
value Clash {}
query resolved() -> string { auth: Profile }
query unresolved() -> string { auth: MissingProfile }
mutation ambiguous() -> string { auth: Clash }
mutation qualified() -> string { auth: demo.Profile }
"""
        )
        expected = {
            "resolved": ("resolved", "demo.Profile", "value"),
            "unresolved": ("unresolved", None, None),
            "ambiguous": ("ambiguous", None, None),
            "qualified": ("resolved", "demo.Profile", "value"),
        }
        for name, (resolution, target, target_kind) in expected.items():
            with self.subTest(name=name):
                evidence = operation_auth_evidence(
                    analysis.project, self._operation(analysis, name)
                )
                self.assertEqual(len(evidence), 1)
                self.assertEqual(evidence[0].mode, "qualified_name")
                self.assertEqual(evidence[0].resolution, resolution)
                self.assertEqual(evidence[0].target, target)
                self.assertEqual(evidence[0].target_kind, target_kind)
                self.assertFalse(evidence[0].complete)

    def test_parser_preserved_identity_and_resolution_are_whitespace_stable(self) -> None:
        compact = self._analysis(
            """module demo
value Profile {}
query find() -> string { auth: demo.Profile }
"""
        )
        spaced = self._analysis(
            """\nmodule   demo
value Profile { }
query find ( ) -> string {
  auth : demo . Profile
}
"""
        )
        first = operation_auth_evidence(
            compact.project, self._operation(compact, "find")
        )
        second = operation_auth_evidence(
            spaced.project, self._operation(spaced, "find")
        )
        self.assertEqual(first, second)
        self.assertEqual(first[0].source, "demo . Profile")
        self.assertEqual(first[0].target, "demo.Profile")
        self.assertFalse(first[0].complete)

    def test_evidence_preserves_clause_order_and_does_not_mutate_diagnostics(self) -> None:
        analysis = self._analysis(
            """module demo
value Profile {}
query find() -> string {
  auth: public
  auth: Profile
}
"""
        )
        before = tuple(diagnostic.to_json() for diagnostic in analysis.diagnostics)
        evidence = operation_auth_evidence(
            analysis.project, self._operation(analysis, "find")
        )
        after = tuple(diagnostic.to_json() for diagnostic in analysis.diagnostics)
        self.assertEqual([item.mode for item in evidence], ["builtin", "qualified_name"])
        self.assertEqual([item.resolution for item in evidence], ["builtin", "resolved"])
        self.assertEqual([item.complete for item in evidence], [True, False])
        self.assertEqual(before, after)

    def test_non_operation_declarations_have_no_auth_evidence(self) -> None:
        analysis = self._analysis(
            """module demo
value Profile {}
"""
        )
        item = next(iter(analysis.project.declaration_names))
        self.assertEqual(operation_auth_evidence(analysis.project, item), ())


if __name__ == "__main__":
    unittest.main()
