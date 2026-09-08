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
CONFORMANCE = json.loads(
    (ROOT / "spec" / "core-conformance.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


class CoreAppAuthLosslessnessTest(unittest.TestCase):
    def _analysis(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(text, encoding="utf-8")
            return load_compiler_analysis([source])

    def _line_of(self, text: str, needle: str) -> int:
        for line, value in enumerate(text.splitlines(), start=1):
            if needle in value:
                return line
        self.fail(f"missing expected source line containing {needle!r}")

    def _assert_single_app_diagnostic(
        self,
        text: str,
        *,
        needle: str,
        message_fragment: str,
    ) -> None:
        analysis = self._analysis(text)
        diagnostics = tuple(
            diagnostic
            for diagnostic in analysis.diagnostics
            if diagnostic.code.value == "AIDL-DIST414"
        )
        self.assertEqual(1, len(diagnostics))
        diagnostic = diagnostics[0]
        self.assertEqual(self._line_of(text, needle), diagnostic.location.line)
        self.assertEqual("policy", diagnostic.phase)
        self.assertEqual("error", diagnostic.severity.value)
        self.assertIn(message_fragment, diagnostic.message)
        self.assertEqual(
            {"kind": "app", "name": "PetstoreApp"},
            diagnostic.subject.to_json(),
        )
        self.assertEqual(
            [],
            [
                item.code.value
                for item in analysis.diagnostics
                if item.severity.value == "error" and item.code.value != "AIDL-DIST414"
            ],
        )
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_unrepresented_provider_configuration_and_subject_alias_are_rejected_before_ir(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        cases = (
            (
                base.replace("  provider oidc\n", "  provider oidc config(\"ISSUER\")\n", 1),
                "provider oidc config(\"ISSUER\")",
                "auth provider configuration is not represented by the current Canonical IR app.auth contract",
            ),
            (
                base.replace("  subject claim \"sub\"\n", "  subject claim \"sub\" as SubjectId\n", 1),
                "subject claim \"sub\" as SubjectId",
                "auth subject alias/type is not represented by the current Canonical IR app.auth contract",
            ),
        )
        for text, needle, message_fragment in cases:
            with self.subTest(needle=needle):
                self._assert_single_app_diagnostic(
                    text,
                    needle=needle,
                    message_fragment=message_fragment,
                )

    def test_reduced_auth_projection_is_deterministic_schema_valid_and_source_mapped(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
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
        self.assertEqual(
            {
                "provider": "oidc",
                "subjectClaim": "sub",
                "roles": ["user"],
                "scopes": ["pets.write"],
                "serviceIdentities": "required",
            },
            first["app"]["auth"],
        )
        app_entry = next(
            entry
            for entry in first["sourceMap"]["entries"]
            if entry["nodePath"] == "/app"
        )
        self.assertEqual("petstore.m4.PetstoreApp@1", app_entry["originalDeclarationId"])
        self.assertEqual(str(source), app_entry["span"]["file"])

    def test_partial_auth_and_app_claims_remain_open(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").replace(
            "auth {\n  provider oidc\n  subject claim \"sub\"\n  roles [user]\n  scopes [pets.write]\n  serviceIdentities required\n}\n",
            "auth {\n  provider oidc\n}\n",
            1,
        )
        diagnostics = tuple(
            diagnostic
            for diagnostic in self._analysis(text).diagnostics
            if diagnostic.code.value == "AIDL-DIST414"
        )
        self.assertEqual((), diagnostics)
        app_row = next(
            feature
            for feature in CONFORMANCE["features"]
            if feature["id"] == "decl.app"
        )
        self.assertEqual("partial", app_row["layerStatus"]["validate"])
        self.assertEqual("partial", app_row["layerStatus"]["ir"])


if __name__ == "__main__":
    unittest.main()
