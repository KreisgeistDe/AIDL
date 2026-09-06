from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.aidl_cli import main
from tools.test_aidl_ir import _MINIMAL_PROJECT


class AidlJsonCliTest(unittest.TestCase):
    def _write_project(self, root: Path, text: str = _MINIMAL_PROJECT) -> Path:
        path = root / "app.aidl"
        path.write_text(text, encoding="utf-8")
        return path

    def _run(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(args)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_check_json_success_is_stable_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            first = self._run(["check", "--format", "json", str(source)])
            second = self._run(["check", "--format", "json", str(source)])

        self.assertEqual(first, second)
        self.assertEqual(0, first[0])
        self.assertEqual("", first[2])
        self.assertEqual(
            {"command": "check", "diagnostics": [], "ok": True},
            json.loads(first[1]),
        )
        self.assertTrue(first[1].endswith("\n"))
        self.assertFalse(first[1].endswith("\n\n"))

    def test_check_json_failure_carries_existing_diagnostics(self) -> None:
        invalid = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory), invalid)
            exit_code, stdout, stderr = self._run(["check", "--format", "json", str(source)])

        payload = json.loads(stdout)
        self.assertEqual(1, exit_code)
        self.assertEqual("", stderr)
        self.assertFalse(payload["ok"])
        self.assertEqual("check", payload["command"])
        self.assertEqual("AIDL-R001", payload["diagnostics"][0]["code"])
        self.assertEqual(str(source), payload["diagnostics"][0]["location"]["file"])

    def test_ir_json_wraps_canonical_ir_without_changing_default_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            exit_code, stdout, stderr = self._run(["ir", "--format", "json", str(source)])

        payload = json.loads(stdout)
        self.assertEqual(0, exit_code)
        self.assertEqual("", stderr)
        self.assertTrue(payload["ok"])
        self.assertEqual("ir", payload["command"])
        self.assertEqual([], payload["diagnostics"])
        self.assertEqual("0.3.0", payload["result"]["irVersion"])
        self.assertIn("semanticHash", payload["result"])

    def test_ir_json_failure_is_machine_readable(self) -> None:
        invalid = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory), invalid)
            exit_code, stdout, stderr = self._run(["ir", "--format", "json", str(source)])

        payload = json.loads(stdout)
        self.assertEqual(1, exit_code)
        self.assertEqual("", stderr)
        self.assertFalse(payload["ok"])
        self.assertEqual("AIDL-R001", payload["diagnostics"][0]["code"])
        self.assertNotIn("result", payload)

    def test_plan_json_wraps_existing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            exit_code, stdout, stderr = self._run(["plan", "--format", "json", str(source)])

        payload = json.loads(stdout)
        self.assertEqual(0, exit_code)
        self.assertEqual("", stderr)
        self.assertTrue(payload["ok"])
        self.assertEqual("plan", payload["command"])
        self.assertEqual([], payload["diagnostics"])
        self.assertEqual("0.1.0", payload["result"]["planVersion"])
        self.assertIn("sourceSemanticHash", payload["result"])

    def test_plan_selection_failure_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            exit_code, stdout, stderr = self._run(
                ["plan", "--format", "json", "--deployment", "missing", str(source)]
            )

        payload = json.loads(stdout)
        self.assertEqual(1, exit_code)
        self.assertEqual("", stderr)
        self.assertFalse(payload["ok"])
        self.assertEqual("planBuild", payload["error"]["kind"])
        self.assertEqual([], payload["diagnostics"])


if __name__ == "__main__":
    unittest.main()
