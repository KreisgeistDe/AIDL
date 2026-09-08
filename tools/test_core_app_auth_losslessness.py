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

    def _ir(self, text: str):
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
            return first, str(source)

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

    def test_provider_block_clause_is_rejected_before_ir(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        text = base.replace(
            "  provider oidc\n",
            '  provider oidc {\n    issuer "x"\n  }\n',
            1,
        )
        self._assert_single_app_diagnostic(
            text,
            needle="provider oidc {",
            message_fragment="auth provider must be a leaf clause",
        )

    def test_unrepresented_auth_value_forms_are_rejected_before_ir(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        cases = (
            (
                base.replace('  subject claim "sub"\n', "  subject principal\n", 1),
                "subject principal",
                "auth subject must be exactly",
            ),
            (
                base.replace('  subject claim "sub"\n', '  subject claim "sub" trailing\n', 1),
                'subject claim "sub" trailing',
                "auth subject must be exactly",
            ),
            (
                base.replace("  roles [user]\n", "  roles user\n", 1),
                "roles user",
                "auth roles must be an explicit bracket list",
            ),
            (
                base.replace("  scopes [pets.write]\n", "  scopes pets.write\n", 1),
                "scopes pets.write",
                "auth scopes must be an explicit bracket list",
            ),
            (
                base.replace("  roles [user]\n", "  roles [user, admin, user]\n", 1),
                "roles [user, admin, user]",
                "auth roles must not repeat list elements",
            ),
            (
                base.replace("  scopes [pets.write]\n", "  scopes [pets.read, pets.write, pets.read]\n", 1),
                "scopes [pets.read, pets.write, pets.read]",
                "auth scopes must not repeat list elements",
            ),
            (
                base.replace("  serviceIdentities required\n", "  serviceIdentities inherited\n", 1),
                "serviceIdentities inherited",
                "auth serviceIdentities must be one of required, optional, or disabled",
            ),
        )
        for text, needle, message_fragment in cases:
            with self.subTest(needle=needle):
                self._assert_single_app_diagnostic(
                    text,
                    needle=needle,
                    message_fragment=message_fragment,
                )

    def test_auth_projection_preserves_order_empty_lists_enum_and_source_map(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        variants = (
            (
                base.replace("  roles [user]\n", "  roles [admin, user]\n", 1)
                .replace("  scopes [pets.write]\n", "  scopes [pets.read, pets.write]\n", 1),
                ["admin", "user"],
                ["pets.read", "pets.write"],
                "required",
            ),
            (
                base.replace("  roles [user]\n", "  roles []\n", 1)
                .replace("  scopes [pets.write]\n", "  scopes []\n", 1)
                .replace("  serviceIdentities required\n", "  serviceIdentities optional\n", 1),
                [],
                [],
                "optional",
            ),
            (
                base.replace("  serviceIdentities required\n", "  serviceIdentities disabled\n", 1),
                ["user"],
                ["pets.write"],
                "disabled",
            ),
        )
        for text, roles, scopes, service_identities in variants:
            with self.subTest(serviceIdentities=service_identities, roles=roles, scopes=scopes):
                ir, source_path = self._ir(text)
                self.assertEqual([], list(VALIDATOR.iter_errors(ir)))
                self.assertEqual("oidc", ir["app"]["auth"]["provider"])
                self.assertEqual("sub", ir["app"]["auth"]["subjectClaim"])
                self.assertEqual(roles, ir["app"]["auth"]["roles"])
                self.assertEqual(scopes, ir["app"]["auth"]["scopes"])
                self.assertEqual(
                    service_identities,
                    ir["app"]["auth"]["serviceIdentities"],
                )
                app_entry = next(
                    entry
                    for entry in ir["sourceMap"]["entries"]
                    if entry["nodePath"] == "/app"
                )
                self.assertEqual("petstore.m4.PetstoreApp@1", app_entry["originalDeclarationId"])
                self.assertEqual(source_path, app_entry["span"]["file"])

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

    def test_partial_auth_is_rejected_and_app_claims_are_closed(self) -> None:
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
        self.assertEqual(4, len(diagnostics))
        self.assertEqual(
            {
                "subject",
                "roles",
                "scopes",
                "serviceIdentities",
            },
            {
                clause
                for clause in ("subject", "roles", "scopes", "serviceIdentities")
                if any(f"exactly one {clause} clause; found 0" in item.message for item in diagnostics)
            },
        )
        app_row = next(
            feature
            for feature in CONFORMANCE["features"]
            if feature["id"] == "decl.app"
        )
        self.assertEqual("implemented", app_row["layerStatus"]["validate"])
        self.assertEqual("implemented", app_row["layerStatus"]["ir"])


if __name__ == "__main__":
    unittest.main()
