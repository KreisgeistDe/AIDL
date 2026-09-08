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
CONFORMANCE = json.loads(
    (ROOT / "spec" / "core-conformance.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


_MINIMAL_MULTI_API = """module example.app

app ExampleApp {
  profile core version 1
  system ExampleSystem
  api FirstApi
  api SecondApi
  defaultDeployment local
}

export api FirstApi {
  transport rest
  version 1
  operations []
  auth inherit
  errors problemDetails
  compatibility backward
}

export api SecondApi {
  transport rpc
  version 1
  operations []
  auth inherit
  errors problemDetails
  compatibility backward
}

export system ExampleSystem {
  services []
  resources []
  apis [FirstApi, SecondApi]
}

export deployment local for ExampleSystem {
  environment test
  target process
}
"""


class CoreAppIrSemanticsTest(unittest.TestCase):
    def _analysis(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(text, encoding="utf-8")
            return load_compiler_analysis([source])

    def _analysis_sources(self, sources: dict[str, str]):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in sources.items():
                (root / name).write_text(text, encoding="utf-8")
            return load_compiler_analysis([root])

    def _build(self, text: str) -> dict:
        return build_canonical_ir(self._analysis(text))

    def _app_contract_diagnostics(self, text: str):
        return tuple(
            diagnostic
            for diagnostic in self._analysis(text).diagnostics
            if diagnostic.code.value == "AIDL-DIST414"
        )

    def _assert_single_app_diagnostic(
        self,
        text: str,
        *,
        line: int,
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
        self.assertEqual(line, diagnostic.location.line)
        self.assertEqual("policy", diagnostic.phase)
        self.assertEqual("error", diagnostic.severity.value)
        self.assertIn(message_fragment, diagnostic.message)
        self.assertEqual(
            {"kind": "app", "name": "ExampleApp"},
            diagnostic.subject.to_json(),
        )
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

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

    def test_multi_api_app_projection_is_deterministic_schema_valid_and_source_mapped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_MULTI_API, encoding="utf-8")
            first_analysis = load_compiler_analysis([source])
            second_analysis = load_compiler_analysis([source])
            first = build_canonical_ir(first_analysis)
            second = build_canonical_ir(second_analysis)

        self.assertEqual(first, second)
        self.assertEqual([], list(VALIDATOR.iter_errors(first)))
        self.assertEqual(
            ["example.app.FirstApi@1", "example.app.SecondApi@1"],
            first["app"]["apiIds"],
        )
        self.assertEqual("example.app.ExampleSystem@1", first["app"]["systemId"])
        self.assertEqual("example.app.local@1", first["app"]["defaultDeploymentId"])
        self.assertEqual([{"id": "core", "major": 1}], first["profiles"])

        app_item = next(
            item
            for item in first_analysis.project.declaration_names
            if item.declaration.kind == "app"
        )
        app_entry = next(
            entry
            for entry in first["sourceMap"]["entries"]
            if entry["nodePath"] == "/app"
        )
        self.assertEqual("example.app.ExampleApp@1", app_entry["originalDeclarationId"])
        self.assertEqual(str(source), app_entry["span"]["file"])
        self.assertEqual(app_item.declaration.span.line, app_entry["span"]["startLine"])
        self.assertEqual(app_item.declaration.span.column, app_entry["span"]["startColumn"])
        self.assertEqual(app_item.declaration.end.line, app_entry["span"]["endLine"])
        self.assertEqual(app_item.declaration.end.column, app_entry["span"]["endColumn"])

    def test_normative_app_profile_contract_has_stable_source_diagnostics(self) -> None:
        cases = {
            "missing profile": (
                """module example.app
app ExampleApp {
  compatibility stable
  system ExampleSystem
  defaultDeployment local
}
system ExampleSystem {}
deployment local for ExampleSystem {}
""",
                2,
                "must select at least one explicit profile",
            ),
            "malformed profile": (
                """module example.app
app ExampleApp {
  profile Core version 1
  system ExampleSystem
  defaultDeployment local
}
system ExampleSystem {}
deployment local for ExampleSystem {}
""",
                3,
                "profile clause must be 'profile ID version POSITIVE_MAJOR'",
            ),
            "unregistered profile version": (
                """module example.app
app ExampleApp {
  profile core version 2
  system ExampleSystem
  defaultDeployment local
}
system ExampleSystem {}
deployment local for ExampleSystem {}
""",
                3,
                "selects unregistered profile 'core@2'",
            ),
            "missing profile dependency": (
                """module example.app
app ExampleApp {
  profile distributed version 1
  system ExampleSystem
  defaultDeployment local
}
system ExampleSystem {}
deployment local for ExampleSystem {}
""",
                3,
                "requires explicit profile 'core@1'",
            ),
            "malformed app clause": (
                """module example.app
app ExampleApp {
  profile core version 1
  system exampleSystem
  defaultDeployment local
}
system ExampleSystem {}
deployment local for ExampleSystem {}
""",
                4,
                "clause is not a normative app clause",
            ),
        }
        for name, (text, line, message_fragment) in cases.items():
            with self.subTest(name=name):
                self._assert_single_app_diagnostic(
                    text,
                    line=line,
                    message_fragment=message_fragment,
                )

    def test_structural_app_materialization_failures_are_diagnosed_before_ir(self) -> None:
        cases = {
            "parser-only header version": (
                _MINIMAL_MULTI_API.replace("app ExampleApp {", "app ExampleApp version 2 {", 1),
                3,
                "header version is parser-only",
            ),
            "duplicate profile": (
                _MINIMAL_MULTI_API.replace(
                    "  profile core version 1\n",
                    "  profile core version 1\n  profile core version 1\n",
                    1,
                ),
                5,
                "repeats profile 'core@1'",
            ),
            "missing system": (
                _MINIMAL_MULTI_API.replace("  system ExampleSystem\n", "", 1),
                3,
                "must declare exactly one system clause; found 0",
            ),
            "repeated system": (
                _MINIMAL_MULTI_API.replace(
                    "  system ExampleSystem\n",
                    "  system ExampleSystem\n  system ExampleSystem\n",
                    1,
                ),
                6,
                "must declare exactly one system clause; found 2",
            ),
            "missing default deployment": (
                _MINIMAL_MULTI_API.replace("  defaultDeployment local\n", "", 1),
                3,
                "must declare exactly one defaultDeployment clause; found 0",
            ),
            "repeated default deployment": (
                _MINIMAL_MULTI_API.replace(
                    "  defaultDeployment local\n",
                    "  defaultDeployment local\n  defaultDeployment local\n",
                    1,
                ),
                9,
                "must declare exactly one defaultDeployment clause; found 2",
            ),
            "duplicate api": (
                _MINIMAL_MULTI_API.replace(
                    "  api SecondApi\n",
                    "  api FirstApi\n  api SecondApi\n",
                    1,
                ),
                7,
                "repeats api reference 'FirstApi'",
            ),
        }
        for name, (text, line, message_fragment) in cases.items():
            with self.subTest(name=name):
                self._assert_single_app_diagnostic(
                    text,
                    line=line,
                    message_fragment=message_fragment,
                )

    def test_app_references_reject_unresolved_and_wrong_kind_before_ir(self) -> None:
        cases = {
            "unresolved system": (
                _MINIMAL_MULTI_API.replace("  system ExampleSystem\n", "  system MissingSystem\n", 1),
                5,
                "system reference 'MissingSystem' is unresolved",
            ),
            "unresolved api": (
                _MINIMAL_MULTI_API.replace("  api FirstApi\n", "  api MissingApi\n", 1),
                6,
                "api reference 'MissingApi' is unresolved",
            ),
            "unresolved deployment": (
                _MINIMAL_MULTI_API.replace("  defaultDeployment local\n", "  defaultDeployment missing\n", 1),
                8,
                "defaultDeployment reference 'missing' is unresolved",
            ),
            "wrong-kind system": (
                _MINIMAL_MULTI_API.replace("  system ExampleSystem\n", "  system FirstApi\n", 1),
                5,
                "system reference 'FirstApi' must target system; found api",
            ),
            "wrong-kind api": (
                _MINIMAL_MULTI_API.replace("  api FirstApi\n", "  api ExampleSystem\n", 1),
                6,
                "api reference 'ExampleSystem' must target api; found system",
            ),
            "wrong-kind deployment": (
                _MINIMAL_MULTI_API.replace("  defaultDeployment local\n", "  defaultDeployment FirstApi\n", 1),
                8,
                "defaultDeployment reference 'FirstApi' must target deployment; found api",
            ),
        }
        for name, (text, line, message_fragment) in cases.items():
            with self.subTest(name=name):
                self._assert_single_app_diagnostic(
                    text,
                    line=line,
                    message_fragment=message_fragment,
                )

    def test_ambiguous_imported_app_reference_is_diagnosed_at_clause(self) -> None:
        analysis = self._analysis_sources(
            {
                "app.aidl": """module example.app
import first.system.*
import second.system.*
app ExampleApp {
  profile core version 1
  system SharedSystem
  api LocalApi
  defaultDeployment local
}
export api LocalApi {}
deployment local for SharedSystem {}
""",
                "first.aidl": """module first.system
export system SharedSystem {}
""",
                "second.aidl": """module second.system
export system SharedSystem {}
""",
            }
        )
        diagnostics = tuple(
            diagnostic
            for diagnostic in analysis.diagnostics
            if diagnostic.code.value == "AIDL-DIST414"
        )
        self.assertEqual(1, len(diagnostics))
        self.assertEqual(6, diagnostics[0].location.line)
        self.assertIn(
            "system reference 'SharedSystem' must resolve uniquely to system; found 2 matching declarations",
            diagnostics[0].message,
        )
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_partial_auth_remains_open_and_app_claims_remain_partial(self) -> None:
        text = _MINIMAL_MULTI_API + """
auth {
  provider oidc
}
"""
        self.assertEqual((), self._app_contract_diagnostics(text))
        app_row = next(
            feature
            for feature in CONFORMANCE["features"]
            if feature["id"] == "decl.app"
        )
        self.assertEqual("partial", app_row["layerStatus"]["validate"])
        self.assertEqual("partial", app_row["layerStatus"]["ir"])

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
