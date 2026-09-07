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
    def _build(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(text, encoding="utf-8")
            return build_canonical_ir(load_compiler_analysis([source]))

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
