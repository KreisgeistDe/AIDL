from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import IrBuildError, build_canonical_ir


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples" / "petstore" / "m4-app" / "app.aidl"
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))
CONFORMANCE = json.loads((ROOT / "spec" / "core-conformance.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
AUTH_BLOCK = """auth {
  provider oidc
  subject claim \"sub\"
  roles [user]
  scopes [pets.write]
  serviceIdentities required
}
"""


class CoreAppAuthCardinalityTest(unittest.TestCase):
    def _analysis(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(text, encoding="utf-8")
            return load_compiler_analysis([source])

    def _dist414(self, text: str):
        return tuple(
            diagnostic
            for diagnostic in self._analysis(text).diagnostics
            if diagnostic.code.value == "AIDL-DIST414"
        )

    def _line_of_occurrence(self, text: str, needle: str, occurrence: int = 1) -> int:
        seen = 0
        for line, value in enumerate(text.splitlines(), start=1):
            if needle in value:
                seen += 1
                if seen == occurrence:
                    return line
        self.fail(f"missing occurrence {occurrence} of {needle!r}")

    def _assert_one_rejection(self, text: str, line: int, fragment: str) -> None:
        analysis = self._analysis(text)
        diagnostics = tuple(d for d in analysis.diagnostics if d.code.value == "AIDL-DIST414")
        self.assertEqual(1, len(diagnostics))
        diagnostic = diagnostics[0]
        self.assertEqual(line, diagnostic.location.line)
        self.assertEqual("policy", diagnostic.phase)
        self.assertEqual("error", diagnostic.severity.value)
        self.assertEqual({"kind": "app", "name": "PetstoreApp"}, diagnostic.subject.to_json())
        self.assertIn(fragment, diagnostic.message)
        self.assertEqual([], [d.code.value for d in analysis.diagnostics if d.severity.value == "error" and d.code.value != "AIDL-DIST414"])
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_all_eleven_cardinality_and_completeness_failures_are_rejected(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        cases: list[tuple[str, int, str]] = []
        doubled = base.replace(AUTH_BLOCK, AUTH_BLOCK + "\n" + AUTH_BLOCK, 1)
        cases.append((doubled, self._line_of_occurrence(doubled, "auth {", 2), "must declare at most one auth block; found 2"))

        required = (
            ("provider", "  provider oidc\n"),
            ("subject", "  subject claim \"sub\"\n"),
            ("roles", "  roles [user]\n"),
            ("scopes", "  scopes [pets.write]\n"),
            ("serviceIdentities", "  serviceIdentities required\n"),
        )
        auth_line = self._line_of_occurrence(base, "auth {")
        for key, line_text in required:
            missing = base.replace(line_text, "", 1)
            cases.append((missing, auth_line, f"exactly one {key} clause; found 0"))
            duplicate = base.replace(line_text, line_text + line_text, 1)
            cases.append((duplicate, self._line_of_occurrence(duplicate, line_text.strip(), 2), f"exactly one {key} clause; found 2"))

        self.assertEqual(11, len(cases))
        for text, line, fragment in cases:
            with self.subTest(fragment=fragment):
                self._assert_one_rejection(text, line, fragment)

    def test_zero_auth_is_valid_and_omits_app_auth(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").replace(AUTH_BLOCK, "", 1)
        analysis = self._analysis(text)
        self.assertEqual((), analysis.diagnostics)
        ir = build_canonical_ir(analysis)
        self.assertNotIn("auth", ir["app"])
        self.assertEqual([], list(VALIDATOR.iter_errors(ir)))

    def test_complete_and_explicit_empty_auth_are_deterministic_schema_valid_and_source_mapped(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        for text, expected_roles, expected_scopes in (
            (base, ["user"], ["pets.write"]),
            (base.replace("  roles [user]\n", "  roles []\n", 1).replace("  scopes [pets.write]\n", "  scopes []\n", 1), [], []),
        ):
            with self.subTest(roles=expected_roles, scopes=expected_scopes):
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "app.aidl"
                    source.write_text(text, encoding="utf-8")
                    first_analysis = load_compiler_analysis([source])
                    second_analysis = load_compiler_analysis([source])
                    self.assertEqual((), first_analysis.diagnostics)
                    self.assertEqual((), second_analysis.diagnostics)
                    first = build_canonical_ir(first_analysis)
                    second = build_canonical_ir(second_analysis)
                self.assertEqual(first, second)
                self.assertEqual([], list(VALIDATOR.iter_errors(first)))
                self.assertEqual(expected_roles, first["app"]["auth"]["roles"])
                self.assertEqual(expected_scopes, first["app"]["auth"]["scopes"])
                self.assertEqual("oidc", first["app"]["auth"]["provider"])
                self.assertEqual("sub", first["app"]["auth"]["subjectClaim"])
                self.assertEqual("required", first["app"]["auth"]["serviceIdentities"])
                app_entry = next(entry for entry in first["sourceMap"]["entries"] if entry["nodePath"] == "/app")
                self.assertEqual("petstore.m4.PetstoreApp@1", app_entry["originalDeclarationId"])

    def test_existing_provider_config_and_subject_alias_rejections_remain_single_and_local(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        cases = (
            (base.replace("  provider oidc\n", "  provider oidc config(\"ISSUER\")\n", 1), "provider oidc config(\"ISSUER\")", "provider configuration"),
            (base.replace("  subject claim \"sub\"\n", "  subject claim \"sub\" as SubjectId\n", 1), "subject claim \"sub\" as SubjectId", "subject alias/type"),
        )
        for text, needle, fragment in cases:
            with self.subTest(needle=needle):
                self._assert_one_rejection(text, self._line_of_occurrence(text, needle), fragment)

    def test_decl_app_claim_remains_partial_until_non_cardinality_auth_value_forms_are_closed(self) -> None:
        row = next(feature for feature in CONFORMANCE["features"] if feature["id"] == "decl.app")
        self.assertEqual("partial", row["layerStatus"]["validate"])
        self.assertEqual("partial", row["layerStatus"]["ir"])


if __name__ == "__main__":
    unittest.main()
