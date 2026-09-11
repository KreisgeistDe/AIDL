#!/usr/bin/env python3
"""Focused regressions for the M10.1 auth evidence and target contract."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_auth_evidence import (
    AUTH_TARGET_CONTRACT,
    operation_auth_evidence,
    operation_auth_evidence_hash,
)
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
                self.assertEqual(evidence[0].target_status, "builtin")
                self.assertTrue(evidence[0].complete)

    def test_qualified_policy_target_is_eligible_only_for_bool_no_arg_policy(self) -> None:
        analysis = self._analysis(
            """module demo
policy SignedIn() -> bool { return true }
query find() -> string { auth: SignedIn }
mutation update() -> string { auth: demo.SignedIn }
"""
        )
        for name in ("find", "update"):
            evidence = operation_auth_evidence(
                analysis.project, self._operation(analysis, name)
            )[0]
            self.assertEqual(evidence.resolution, "resolved")
            self.assertEqual(evidence.target, "demo.SignedIn")
            self.assertEqual(evidence.target_kind, "policy")
            self.assertEqual(evidence.target_status, "eligible")
            self.assertEqual(evidence.target_contract, AUTH_TARGET_CONTRACT)
            self.assertEqual(evidence.target_parameters, "()")
            self.assertEqual(evidence.target_result, "bool")
            self.assertTrue(evidence.complete)

    def test_qualified_target_states_are_explicit_and_fail_closed(self) -> None:
        analysis = self._analysis(
            """module demo
value WrongKind {}
policy Clash() -> bool { return true }
policy Clash() -> bool { return true }
policy NeedsArgument(id:uuid) -> bool { return true }
policy WrongResult() -> string { return \"no\" }
query unresolved() -> string { auth: Missing }
query ambiguous() -> string { auth: Clash }
query wrongKind() -> string { auth: WrongKind }
query incompleteArgs() -> string { auth: NeedsArgument }
mutation incompleteResult() -> string { auth: WrongResult }
"""
        )
        expected = {
            "unresolved": ("unresolved", None, None, "unresolved"),
            "ambiguous": ("ambiguous", None, None, "ambiguous"),
            "wrongKind": ("resolved", "demo.WrongKind", "value", "wrong_kind"),
            "incompleteArgs": ("resolved", "demo.NeedsArgument", "policy", "incomplete"),
            "incompleteResult": ("resolved", "demo.WrongResult", "policy", "incomplete"),
        }
        for name, (resolution, target, target_kind, status) in expected.items():
            with self.subTest(name=name):
                evidence = operation_auth_evidence(
                    analysis.project, self._operation(analysis, name)
                )[0]
                self.assertEqual(evidence.mode, "qualified_name")
                self.assertEqual(evidence.resolution, resolution)
                self.assertEqual(evidence.target, target)
                self.assertEqual(evidence.target_kind, target_kind)
                self.assertEqual(evidence.target_status, status)
                self.assertFalse(evidence.complete)

    def test_parser_preserved_identity_and_hash_are_whitespace_stable(self) -> None:
        compact = self._analysis(
            """module demo
policy SignedIn() -> bool { return true }
query find() -> string { auth: demo.SignedIn }
"""
        )
        spaced = self._analysis(
            """\nmodule   demo
policy SignedIn ( ) -> bool {
  return true
}
query find ( ) -> string {
  auth : demo . SignedIn
}
"""
        )
        compact_item = self._operation(compact, "find")
        spaced_item = self._operation(spaced, "find")
        first = operation_auth_evidence(compact.project, compact_item)
        second = operation_auth_evidence(spaced.project, spaced_item)
        self.assertEqual(first, second)
        self.assertEqual(first[0].source, "demo . SignedIn")
        self.assertEqual(first[0].target, "demo.SignedIn")
        self.assertTrue(first[0].complete)
        self.assertEqual(
            operation_auth_evidence_hash(compact.project, compact_item),
            operation_auth_evidence_hash(spaced.project, spaced_item),
        )

    def test_evidence_preserves_clause_order_and_does_not_mutate_diagnostics(self) -> None:
        analysis = self._analysis(
            """module demo
policy SignedIn() -> bool { return true }
query find() -> string {
  auth: public
  auth: SignedIn
}
"""
        )
        before = tuple(diagnostic.to_json() for diagnostic in analysis.diagnostics)
        item = self._operation(analysis, "find")
        evidence = operation_auth_evidence(analysis.project, item)
        first_hash = operation_auth_evidence_hash(analysis.project, item)
        second_hash = operation_auth_evidence_hash(analysis.project, item)
        after = tuple(diagnostic.to_json() for diagnostic in analysis.diagnostics)
        self.assertEqual([entry.mode for entry in evidence], ["builtin", "qualified_name"])
        self.assertEqual([entry.target_status for entry in evidence], ["builtin", "eligible"])
        self.assertEqual([entry.complete for entry in evidence], [True, True])
        self.assertEqual(first_hash, second_hash)
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
