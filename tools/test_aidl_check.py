from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.aidl_cli import EXIT_INTERNAL_ERROR, main
from tools.test_aidl_ir import _MINIMAL_PROJECT


class AidlCheckTest(unittest.TestCase):
    def _write_project(self, root: Path, text: str = _MINIMAL_PROJECT) -> Path:
        path = root / "app.aidl"
        path.write_text(text, encoding="utf-8")
        return path

    def _run(self, source: Path) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["check", str(source)])
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def _run_json(self, source: Path) -> tuple[int, dict[str, object], str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["check", str(source), "--format", "json"])
        return exit_code, json.loads(stdout.getvalue()), stderr.getvalue()

    def test_valid_supported_project_succeeds_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            exit_code, stdout, stderr = self._run(source)

        self.assertEqual(0, exit_code)
        self.assertEqual("", stdout)
        self.assertEqual("", stderr)

    def test_petstore_project_check_does_not_crash(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["check", "examples/petstore"])

        self.assertNotEqual(EXIT_INTERNAL_ERROR, exit_code)

    def test_invalid_project_emits_human_readable_source_located_diagnostic(self) -> None:
        invalid = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory), invalid)
            exit_code, stdout, stderr = self._run(source)

        self.assertEqual(1, exit_code)
        self.assertEqual("", stdout)
        self.assertIn(f"{source}:2:1: error AIDL-R001:", stderr)
        self.assertTrue(stderr.endswith("\n"))

    def test_unresolved_named_type_has_stable_source_located_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(
                Path(directory),
                "module demo\nalias Broken = MissingType\n",
            )
            exit_code, payload, stderr = self._run_json(source)

        self.assertEqual(1, exit_code)
        self.assertEqual("", stderr)
        self.assertFalse(payload["ok"])
        diagnostics = payload["diagnostics"]
        self.assertEqual([diagnostic["code"] for diagnostic in diagnostics], ["AIDL-R003", "AIDL-T005"])
        resolver, materialization = diagnostics
        self.assertEqual("resolve", resolver["phase"])
        self.assertEqual("error", resolver["severity"])
        self.assertEqual("unresolved name 'MissingType'", resolver["message"])
        self.assertEqual(str(source), resolver["location"]["file"])
        self.assertEqual(2, resolver["location"]["line"])
        self.assertEqual("type", materialization["phase"])
        self.assertIn("may not fall back to a synthetic aidl.std identity", materialization["message"])
        self.assertEqual(str(source), materialization["location"]["file"])
        self.assertEqual(2, materialization["location"]["line"])

    def test_cyclic_module_dependency_has_stable_source_located_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.aidl"
            second = root / "b.aidl"
            first.write_text(
                "module example.a\n"
                "import example.b.B\n"
                "export value A {\n}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.b\n"
                "import example.a.A\n"
                "export value B {\n}\n",
                encoding="utf-8",
            )
            exit_code, payload, stderr = self._run_json(root)

        self.assertEqual(1, exit_code)
        self.assertEqual("", stderr)
        cycle_diagnostics = [
            diagnostic
            for diagnostic in payload["diagnostics"]
            if diagnostic["code"] == "AIDL-R004"
        ]
        self.assertEqual(1, len(cycle_diagnostics))
        diagnostic = cycle_diagnostics[0]
        self.assertEqual("resolve", diagnostic["phase"])
        self.assertEqual("error", diagnostic["severity"])
        self.assertEqual(
            "cyclic module dependency: example.a -> example.b -> example.a",
            diagnostic["message"],
        )
        self.assertEqual(str(first), diagnostic["location"]["file"])
        self.assertEqual(1, diagnostic["location"]["line"])

    def test_human_readable_diagnostics_are_deterministic(self) -> None:
        invalid = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory), invalid)
            first = self._run(source)
            second = self._run(source)

        self.assertEqual(first, second)
        self.assertEqual(1, first[0])
        self.assertEqual("", first[1])


if __name__ == "__main__":
    unittest.main()
