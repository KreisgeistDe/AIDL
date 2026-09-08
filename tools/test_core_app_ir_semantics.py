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

    def _line_of(self, text: str, needle: str, occurrence: int = 1) -> int:
        seen = 0
        for line, value in enumerate(text.splitlines(), start=1):
            if needle in value:
                seen += 1
                if seen == occurrence:
                    return line
        self.fail(f"missing expected source line containing {needle!r}")

    def _multi_api_text(self) -> str:
        text = SOURCE.read_text(encoding="utf-8")
        text = text.replace(
            "  api PetstoreApi\n",
            "  api PetstoreApi\n  api PetstoreAdminApi\n",
            1,
        )
        second_api = """export api PetstoreAdminApi {
  transport rpc
  version 1
  operations [mutation createPet]
  auth inherit
  errors problemDetails
  compatibility backward
}

"""
        text = text.replace(
            "export resource PetstoreDb sql {\n",
            second_api + "export resource PetstoreDb sql {\n",
            1,
        )
        text = text.replace(
            "  apis [PetstoreApi]\n",
            "  apis [PetstoreApi, PetstoreAdminApi]\n",
            1,
        )
        return text

    def _assert_single_app_diagnostic(
        self,
        text: str,
        *,
        line: int,
        message_fragment: str,
        subject_name: str = "PetstoreApp",
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
            {"kind": "app", "name": subject_name},
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
        text = self._multi_api_text()
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
            ["petstore.m4.PetstoreApi@1", "petstore.m4.PetstoreAdminApi@1"],
            first["app"]["apiIds"],
        )
        self.assertEqual("petstore.m4.PetstoreSystem@1", first["app"]["systemId"])
        self.assertEqual("petstore.m4.local@1", first["app"]["defaultDeploymentId"])
        self.assertEqual(
            [
                {"id": "core", "major": 1},
                {"id": "distributed", "major": 1},
                {"id": "cloud", "major": 1},
            ],
            first["profiles"],
        )

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
        self.assertEqual("petstore.m4.PetstoreApp@1", app_entry["originalDeclarationId"])
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
  system ExampleSystem
  system exampleSystem
  defaultDeployment local
}
system ExampleSystem {}
deployment local for ExampleSystem {}
""",
                5,
                "clause is not a normative app clause",
            ),
        }
        for name, (text, line, message_fragment) in cases.items():
            with self.subTest(name=name):
                self._assert_single_app_diagnostic(
                    text,
                    line=line,
                    message_fragment=message_fragment,
                    subject_name="ExampleApp",
                )

    def test_structural_app_materialization_failures_are_diagnosed_before_ir(self) -> None:
        base = self._multi_api_text()
        cases = {}

        changed = base.replace("app PetstoreApp {", "app PetstoreApp version 2 {", 1)
        cases["parser-only header version"] = (
            changed,
            self._line_of(changed, "app PetstoreApp version 2"),
            "header version is parser-only",
        )

        changed = base.replace(
            "  profile core version 1\n",
            "  profile core version 1\n  profile core version 1\n",
            1,
        )
        cases["duplicate profile"] = (
            changed,
            self._line_of(changed, "profile core version 1", 2),
            "repeats profile 'core@1'",
        )

        changed = base.replace("  system PetstoreSystem\n", "", 1)
        cases["missing system"] = (
            changed,
            self._line_of(changed, "app PetstoreApp"),
            "must declare exactly one system clause; found 0",
        )

        changed = base.replace(
            "  system PetstoreSystem\n",
            "  system PetstoreSystem\n  system PetstoreSystem\n",
            1,
        )
        cases["repeated system"] = (
            changed,
            self._line_of(changed, "system PetstoreSystem", 2),
            "must declare exactly one system clause; found 2",
        )

        changed = base.replace("  defaultDeployment local\n", "", 1)
        cases["missing default deployment"] = (
            changed,
            self._line_of(changed, "app PetstoreApp"),
            "must declare exactly one defaultDeployment clause; found 0",
        )

        changed = base.replace(
            "  defaultDeployment local\n",
            "  defaultDeployment local\n  defaultDeployment local\n",
            1,
        )
        cases["repeated default deployment"] = (
            changed,
            self._line_of(changed, "defaultDeployment local", 2),
            "must declare exactly one defaultDeployment clause; found 2",
        )

        changed = base.replace(
            "  api PetstoreAdminApi\n",
            "  api PetstoreApi\n  api PetstoreAdminApi\n",
            1,
        )
        cases["duplicate api"] = (
            changed,
            self._line_of(changed, "api PetstoreApi", 2),
            "repeats api reference 'PetstoreApi'",
        )

        for name, (text, line, message_fragment) in cases.items():
            with self.subTest(name=name):
                self._assert_single_app_diagnostic(
                    text,
                    line=line,
                    message_fragment=message_fragment,
                )

    def test_app_references_reject_unresolved_and_wrong_kind_before_ir(self) -> None:
        base = self._multi_api_text()
        cases = {}

        changed = base.replace("  system PetstoreSystem\n", "  system MissingSystem\n", 1)
        cases["unresolved system"] = (
            changed,
            self._line_of(changed, "system MissingSystem"),
            "system reference 'MissingSystem' is unresolved",
        )

        changed = base.replace("  api PetstoreApi\n", "  api MissingApi\n", 1)
        cases["unresolved api"] = (
            changed,
            self._line_of(changed, "api MissingApi"),
            "api reference 'MissingApi' is unresolved",
        )

        changed = base.replace("  defaultDeployment local\n", "  defaultDeployment missing\n", 1)
        cases["unresolved deployment"] = (
            changed,
            self._line_of(changed, "defaultDeployment missing"),
            "defaultDeployment reference 'missing' is unresolved",
        )

        changed = base.replace("  system PetstoreSystem\n", "  system PetstoreApi\n", 1)
        cases["wrong-kind system"] = (
            changed,
            self._line_of(changed, "system PetstoreApi"),
            "system reference 'PetstoreApi' must target system; found api",
        )

        changed = base.replace("  api PetstoreApi\n", "  api PetstoreSystem\n", 1)
        cases["wrong-kind api"] = (
            changed,
            self._line_of(changed, "api PetstoreSystem"),
            "api reference 'PetstoreSystem' must target api; found system",
        )

        changed = base.replace("  defaultDeployment local\n", "  defaultDeployment PetstoreApi\n", 1)
        cases["wrong-kind deployment"] = (
            changed,
            self._line_of(changed, "defaultDeployment PetstoreApi"),
            "defaultDeployment reference 'PetstoreApi' must target deployment; found api",
        )

        for name, (text, line, message_fragment) in cases.items():
            with self.subTest(name=name):
                self._assert_single_app_diagnostic(
                    text,
                    line=line,
                    message_fragment=message_fragment,
                )

    def test_ambiguous_imported_app_reference_is_diagnosed_at_clause(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        app_text = base.replace(
            "module petstore.m4\n",
            "module petstore.m4\nimport first.system.*\nimport second.system.*\n",
            1,
        ).replace(
            "  system PetstoreSystem\n",
            "  system SharedSystem\n",
            1,
        )
        app_text = app_text.replace(
            "export system PetstoreSystem {\n",
            "export system PetstoreSystemOriginal {\n",
            1,
        )
        analysis = self._analysis_sources(
            {
                "app.aidl": app_text,
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
        self.assertEqual(
            self._line_of(app_text, "system SharedSystem"),
            diagnostics[0].location.line,
        )
        self.assertIn(
            "system reference 'SharedSystem' must resolve uniquely to system; found 2 matching declarations",
            diagnostics[0].message,
        )
        with self.assertRaises(IrBuildError):
            build_canonical_ir(analysis)

    def test_partial_auth_remains_open_and_app_claims_remain_partial(self) -> None:
        text = self._multi_api_text().replace(
            "auth {\n  provider oidc config(\"ISSUER\")\n  subject claim \"sub\" as SubjectId\n  roles [user]\n  scopes [pets.write]\n  serviceIdentities required\n}\n",
            "auth {\n  provider oidc\n}\n",
            1,
        )
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
