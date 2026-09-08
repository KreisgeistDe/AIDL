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
AUTH_BLOCK = """auth {
  provider oidc
  subject claim \"sub\"
  roles [user]
  scopes [pets.write]
  serviceIdentities required
}
"""


class CoreAppProjectLosslessnessTest(unittest.TestCase):
    def _write_project(self, directory: Path, files: dict[str, str]) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for name, text in files.items():
            path = directory / name
            path.write_text(text, encoding="utf-8")
            paths[name] = path
        return paths

    def _dist414(self, paths: list[Path]):
        return tuple(
            diagnostic
            for diagnostic in load_compiler_analysis(paths).diagnostics
            if diagnostic.code.value == "AIDL-DIST414"
        )

    def test_single_app_multifile_project_is_order_independent_and_schema_valid(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._write_project(
                root,
                {
                    "app.aidl": base,
                    "extra.aidl": "module petstore.extra\n",
                },
            )
            first_analysis = load_compiler_analysis([paths["app.aidl"], paths["extra.aidl"]])
            second_analysis = load_compiler_analysis([paths["extra.aidl"], paths["app.aidl"]])
            self.assertEqual((), first_analysis.diagnostics)
            self.assertEqual((), second_analysis.diagnostics)
            first = build_canonical_ir(first_analysis)
            second = build_canonical_ir(second_analysis)
            self.assertEqual(first, second)
            self.assertEqual([], list(VALIDATOR.iter_errors(first)))
            self.assertEqual("petstore.m4.PetstoreApp@1", first["app"]["declarationId"])
            app_entry = next(
                entry for entry in first["sourceMap"]["entries"] if entry["nodePath"] == "/app"
            )
            self.assertEqual(str(paths["app.aidl"]), app_entry["span"]["file"])

    def test_zero_app_is_rejected_before_ir_with_stable_project_diagnostic(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        start = base.index("app PetstoreApp {")
        end = base.index("\n\nauth {", start)
        without_app = base[:start] + base[end + 2 :]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._write_project(root, {"project.aidl": without_app})
            analysis = load_compiler_analysis([paths["project.aidl"]])
            diagnostics = tuple(
                item for item in analysis.diagnostics if item.code.value == "AIDL-DIST414"
            )
            self.assertEqual(1, len(diagnostics))
            self.assertEqual("project.aidl", diagnostics[0].source_path.name)
            self.assertEqual("project must declare exactly one app; found 0", diagnostics[0].message)
            self.assertEqual({"kind": "app", "name": "<missing>"}, diagnostics[0].subject.to_json())
            with self.assertRaises(IrBuildError):
                build_canonical_ir(analysis)

    def test_multiple_apps_are_rejected_before_ir_independent_of_source_order(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        app_start = base.index("app PetstoreApp {")
        app_end = base.index("\n\nauth {", app_start)
        app_block = base[app_start:app_end]
        second = app_block.replace("app PetstoreApp", "app SecondApp", 1)
        first_text = base
        second_text = "module petstore.m4\n\n" + second + "\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._write_project(
                root,
                {"a-main.aidl": first_text, "z-second.aidl": second_text},
            )
            forward = self._dist414([paths["a-main.aidl"], paths["z-second.aidl"]])
            reverse = self._dist414([paths["z-second.aidl"], paths["a-main.aidl"]])
            self.assertEqual(1, len(forward))
            self.assertEqual(1, len(reverse))
            self.assertEqual(forward[0].to_json(), reverse[0].to_json())
            self.assertEqual("z-second.aidl", forward[0].source_path.name)
            self.assertEqual("project must declare exactly one app; found 2", forward[0].message)

    def test_cross_file_auth_is_rejected_source_locally_independent_of_source_order(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        app_text = base.replace("\n\n" + AUTH_BLOCK, "\n", 1)
        auth_text = "module petstore.m4\n\n" + AUTH_BLOCK
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._write_project(
                root,
                {"app.aidl": app_text, "auth.aidl": auth_text},
            )
            forward = self._dist414([paths["app.aidl"], paths["auth.aidl"]])
            reverse = self._dist414([paths["auth.aidl"], paths["app.aidl"]])
            self.assertEqual(1, len(forward))
            self.assertEqual(1, len(reverse))
            self.assertEqual(forward[0].to_json(), reverse[0].to_json())
            self.assertEqual("auth.aidl", forward[0].source_path.name)
            self.assertIn("cross-file auth association is not represented", forward[0].message)
            self.assertEqual(
                next(
                    line
                    for line, value in enumerate(auth_text.splitlines(), start=1)
                    if value.strip() == "auth {"
                ),
                forward[0].location.line,
            )

    def test_multiple_project_auth_blocks_are_rejected_before_ir(self) -> None:
        base = SOURCE.read_text(encoding="utf-8")
        second_auth = "module petstore.m4\n\n" + AUTH_BLOCK
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._write_project(
                root,
                {"app.aidl": base, "z-auth.aidl": second_auth},
            )
            diagnostics = self._dist414([paths["z-auth.aidl"], paths["app.aidl"]])
            self.assertEqual(1, len(diagnostics))
            self.assertEqual("z-auth.aidl", diagnostics[0].source_path.name)
            self.assertIn("must declare at most one project auth block; found 2", diagnostics[0].message)

    def test_unknown_colocated_auth_clause_is_rejected_before_ir(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").replace(
            "  serviceIdentities required\n",
            "  serviceIdentities required\n  audience pets\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(text, encoding="utf-8")
            diagnostics = self._dist414([source])
            self.assertEqual(1, len(diagnostics))
            self.assertIn("auth clause is not a normative auth clause: 'audience pets'", diagnostics[0].message)

    def test_decl_app_validate_and_ir_are_promoted_only_with_project_closure_evidence(self) -> None:
        row = next(item for item in CONFORMANCE["features"] if item["id"] == "decl.app")
        self.assertEqual("implemented", row["layerStatus"]["validate"])
        self.assertEqual("implemented", row["layerStatus"]["ir"])


if __name__ == "__main__":
    unittest.main()
