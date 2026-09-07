from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import IrBuildError, build_canonical_ir
from tools.m4_petstore import SOURCE


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


class CoreAppIrSemanticsTest(unittest.TestCase):
    def _analysis(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(text, encoding="utf-8")
            return load_compiler_analysis([source])

    def _build(self, text: str) -> dict:
        return build_canonical_ir(self._analysis(text))

    def _app_contract_diagnostics(self, text: str):
        return tuple(
            diagnostic
            for diagnostic in self._analysis(text).diagnostics
            if diagnostic.code.value == "AIDL-DIST414"
        )

    def test_app_identity_references_profiles_and_auth_are_deterministic(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        first = self._build(text)
        second = self._build(text)

        self.assertEqual(first["app"], second["app"])
        self.assertEqual(first["profiles"], second["profiles"])
        self.assertEqual([], list(VALIDATOR.iter_errors(first)))

        app = first["app"]
        self.assertEqual("petstore.m4.PetstoreApp@1", app["declarationId"])
        self.assertEqual("petstore.m4.PetstoreApp", app["fqn"])
        self.assertEqual("PetstoreApp", app["name"])
        self.assertEqual("petstore.m4", app["ownerModule"])
        self.assertRegex(app["semanticHash"], r"^sha256:[a-f0-9]{64}$")
        self.assertEqual("petstore.m4.PetstoreSystem@1", app["systemId"])
        self.assertEqual(["petstore.m4.PetstoreApi@1"], app["apiIds"])
        self.assertEqual("petstore.m4.local@1", app["defaultDeploymentId"])
        self.assertEqual(
            [
                {"id": "core", "major": 1},
                {"id": "distributed", "major": 1},
                {"id": "cloud", "major": 1},
            ],
            first["profiles"],
        )
        self.assertEqual(
            {
                "provider": "oidc",
                "subjectClaim": "sub",
                "roles": ["user"],
                "scopes": ["pets.write"],
                "serviceIdentities": "required",
            },
            app["auth"],
        )
        self.assertEqual((), self._app_contract_diagnostics(text))

    def test_normative_app_profile_contract_has_stable_source_diagnostics(self) -> None:
        cases = {
            "missing profile": (
                """module example.app
app ExampleApp {
  compatibility stable
}
""",
                2,
                "app 'example.app.ExampleApp' must select at least one explicit profile",
            ),
            "malformed profile": (
                """module example.app
app ExampleApp {
  profile Core version 1
}
""",
                3,
                "app 'example.app.ExampleApp' profile clause must be 'profile ID version POSITIVE_MAJOR'; found 'profile Core version 1'",
            ),
            "unregistered profile version": (
                """module example.app
app ExampleApp {
  profile core version 2
}
""",
                3,
                "app 'example.app.ExampleApp' selects unregistered profile 'core@2'",
            ),
            "missing profile dependency": (
                """module example.app
app ExampleApp {
  profile distributed version 1
}
""",
                3,
                "app 'example.app.ExampleApp' profile 'distributed@1' requires explicit profile 'core@1'",
            ),
            "malformed app clause": (
                """module example.app
app ExampleApp {
  profile core version 1
  system exampleSystem
}
""",
                4,
                "app 'example.app.ExampleApp' clause is not a normative app clause: 'system exampleSystem'",
            ),
        }
        for name, (text, line, message) in cases.items():
            with self.subTest(name=name):
                diagnostics = self._app_contract_diagnostics(text)
                self.assertEqual(1, len(diagnostics))
                self.assertEqual(message, diagnostics[0].message)
                self.assertEqual(line, diagnostics[0].location.line)
                self.assertEqual("policy", diagnostics[0].phase)
                self.assertEqual("error", diagnostics[0].severity.value)
                self.assertEqual(
                    {"kind": "app", "name": "ExampleApp"},
                    diagnostics[0].subject.to_json(),
                )

    def test_unproven_duplicate_and_partial_auth_rules_remain_open(self) -> None:
        text = """module example.app
app ExampleApp {
  profile core version 1
  profile core version 1
}
auth {
  provider oidc
}
"""
        self.assertEqual((), self._app_contract_diagnostics(text))

    def test_missing_or_unresolved_required_app_references_fail_ir(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        cases = {
            "missing system": ("  system PetstoreSystem\n", "app must declare system and defaultDeployment"),
            "missing deployment": ("  defaultDeployment local\n", "app must declare system and defaultDeployment"),
            "unknown system": ("  system PetstoreSystem\n", "  system MissingSystem\n"),
            "unknown api": ("  api PetstoreApi\n", "  api MissingApi\n"),
            "unknown deployment": ("  defaultDeployment local\n", "  defaultDeployment missing\n"),
        }
        for name, (needle, replacement) in cases.items():
            with self.subTest(name=name):
                changed = text.replace(needle, replacement, 1)
                with self.assertRaises(IrBuildError):
                    self._build(changed)

    def test_closed_schema_rejects_malformed_app_profiles_and_auth(self) -> None:
        document = self._build(SOURCE.read_text(encoding="utf-8"))
        mutations = []

        missing_system = copy.deepcopy(document)
        del missing_system["app"]["systemId"]
        mutations.append(missing_system)

        unknown_app_field = copy.deepcopy(document)
        unknown_app_field["app"]["sourceContract"] = "syntax"
        mutations.append(unknown_app_field)

        malformed_api_id = copy.deepcopy(document)
        malformed_api_id["app"]["apiIds"] = ["not a declaration id"]
        mutations.append(malformed_api_id)

        invalid_profile = copy.deepcopy(document)
        invalid_profile["profiles"][0]["major"] = 0
        mutations.append(invalid_profile)

        unknown_profile_field = copy.deepcopy(document)
        unknown_profile_field["profiles"][0]["status"] = "implemented"
        mutations.append(unknown_profile_field)

        invalid_auth = copy.deepcopy(document)
        invalid_auth["app"]["auth"]["serviceIdentities"] = "sometimes"
        mutations.append(invalid_auth)

        unknown_auth_field = copy.deepcopy(document)
        unknown_auth_field["app"]["auth"]["tokenSource"] = "header"
        mutations.append(unknown_auth_field)

        for malformed in mutations:
            self.assertFalse(VALIDATOR.is_valid(malformed))


if __name__ == "__main__":
    unittest.main()
