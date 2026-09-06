from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.aidl_cli import main
from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.ir_plan import PlanBuildError, build_plan, canonical_plan_json_text
from tools.test_aidl_ir import _MINIMAL_PROJECT


class AidlPlanTest(unittest.TestCase):
    def _write_project(self, root: Path, text: str = _MINIMAL_PROJECT) -> Path:
        path = root / "app.aidl"
        path.write_text(text, encoding="utf-8")
        return path

    def test_plan_is_deterministic_and_derived_only_from_ir(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            document = build_canonical_ir(load_compiler_analysis([source]))

        first = build_plan(document)
        second = build_plan(json.loads(json.dumps(document)))
        self.assertEqual(first, second)
        self.assertEqual("0.1.0", first["planVersion"])
        self.assertEqual(document["semanticHash"], first["sourceSemanticHash"])
        self.assertEqual(document["app"]["declarationId"], first["appId"])
        self.assertEqual(document["system"]["declarationId"], first["systemId"])
        self.assertEqual(document["app"]["defaultDeploymentId"], first["deployment"]["declarationId"])
        self.assertEqual(
            sorted(first["actions"], key=lambda item: (item["kind"], item["targetId"], item.get("adapter", ""))),
            first["actions"],
        )
        self.assertEqual(canonical_plan_json_text(first), canonical_plan_json_text(second))

    def test_plan_cli_emits_only_canonical_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["plan", str(source), "--deployment", "local"])

        self.assertEqual(0, exit_code)
        self.assertEqual("", stderr.getvalue())
        plan = json.loads(stdout.getvalue())
        self.assertEqual(stdout.getvalue(), canonical_plan_json_text(plan))
        self.assertEqual("local", plan["deployment"]["name"])
        self.assertTrue(any(action["kind"] == "deployService" for action in plan["actions"]))
        self.assertTrue(any(action["kind"] == "bindResource" for action in plan["actions"]))
        self.assertTrue(any(action["kind"] == "exposeApi" for action in plan["actions"]))

    def test_plan_cli_reuses_compiler_error_gate(self) -> None:
        invalid = _MINIMAL_PROJECT.replace("module demo\n", "module demo\nimport missing.Type\n", 1)
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory), invalid)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["plan", str(source)])

        self.assertEqual(1, exit_code)
        self.assertEqual("", stdout.getvalue())
        self.assertIn("AIDL-R001", stderr.getvalue())

    def test_unknown_deployment_fails_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["plan", str(source), "--deployment", "missing"])

        self.assertEqual(1, exit_code)
        self.assertEqual("", stdout.getvalue())
        self.assertIn("matched 0 deployments", stderr.getvalue())

    def test_plan_rejects_ir_without_stable_identity(self) -> None:
        with self.assertRaises(PlanBuildError):
            build_plan({"irVersion": "0.3.0", "semanticHash": "sha256:x", "app": {}, "system": {}, "deployments": []})


if __name__ == "__main__":
    unittest.main()
