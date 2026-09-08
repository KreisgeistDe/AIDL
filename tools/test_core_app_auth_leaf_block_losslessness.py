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
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


class CoreAppAuthLeafBlockLosslessnessTest(unittest.TestCase):
    def _analysis(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(text, encoding="utf-8")
            return load_compiler_analysis([source])

    def _assert_single_leaf_shape_diagnostic(
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
        expected_line = next(
            line
            for line, value in enumerate(text.splitlines(), start=1)
            if needle in value
        )
        self.assertEqual(expected_line, diagnostic.location.line)
        self.assertEqual("policy", diagnostic.phase)
        self.assertEqual("error", diagnostic.severity.value)
        self.assertIn(message_fragment, diagnostic.message)
        self.assertEqual(
            {"kind": "app", "name": "PetstoreApp"},
            diagnostic.subject.to_json(),
        )
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_represented_app_and_auth_leaf_block_forms_are_rejected_before_ir(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        cases = (
            (
                base.replace(
                    "  profile core version 1\n",
                    "  profile core version 1 {\n    ignored true\n  }\n",
                    1,
                ),
                "profile core version 1 {",
                "profile must be a leaf clause",
            ),
            (
                base.replace(
                    "  system PetstoreSystem\n",
                    "  system PetstoreSystem {\n    ignored true\n  }\n",
                    1,
                ),
                "system PetstoreSystem {",
                "system must be a leaf clause",
            ),
            (
                base.replace(
                    "  api PetstoreApi\n",
                    "  api PetstoreApi {\n    ignored true\n  }\n",
                    1,
                ),
                "api PetstoreApi {",
                "api must be a leaf clause",
            ),
            (
                base.replace(
                    "  defaultDeployment local\n",
                    "  defaultDeployment local {\n    ignored true\n  }\n",
                    1,
                ),
                "defaultDeployment local {",
                "defaultDeployment must be a leaf clause",
            ),
            (
                base.replace(
                    '  subject claim "sub"\n',
                    '  subject claim "sub" {\n    ignored true\n  }\n',
                    1,
                ),
                'subject claim "sub" {',
                "auth subject must be a leaf clause",
            ),
            (
                base.replace(
                    "  roles [user]\n",
                    "  roles [user] {\n    ignored true\n  }\n",
                    1,
                ),
                "roles [user] {",
                "auth roles must be a leaf clause",
            ),
            (
                base.replace(
                    "  scopes [pets.write]\n",
                    "  scopes [pets.write] {\n    ignored true\n  }\n",
                    1,
                ),
                "scopes [pets.write] {",
                "auth scopes must be a leaf clause",
            ),
            (
                base.replace(
                    "  serviceIdentities required\n",
                    "  serviceIdentities required {\n    ignored true\n  }\n",
                    1,
                ),
                "serviceIdentities required {",
                "auth serviceIdentities must be a leaf clause",
            ),
        )
        for text, needle, message_fragment in cases:
            with self.subTest(needle=needle):
                self._assert_single_leaf_shape_diagnostic(
                    text,
                    needle=needle,
                    message_fragment=message_fragment,
                )

    def test_valid_leaf_app_auth_projection_remains_deterministic_schema_valid_and_source_mapped(self) -> None:
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
            self.assertEqual(
                "petstore.m4.PetstoreApp@1",
                app_entry["originalDeclarationId"],
            )
            self.assertEqual(str(source), app_entry["span"]["file"])


if __name__ == "__main__":
    unittest.main()
