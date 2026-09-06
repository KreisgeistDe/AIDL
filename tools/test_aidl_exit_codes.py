from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools.aidl_cli import (
    EXIT_INTERNAL_ERROR,
    EXIT_SUCCESS,
    EXIT_VALIDATION_FAILURE,
    main,
)
from tools.test_aidl_ir import _MINIMAL_PROJECT


class AidlExitCodeTest(unittest.TestCase):
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

    def test_all_commands_use_zero_for_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            for args in (
                ["check", str(source)],
                ["check", "--format", "json", str(source)],
                ["ir", str(source)],
                ["ir", "--format", "json", str(source)],
                ["plan", str(source)],
                ["plan", "--format", "json", str(source)],
                ["dependencies", "demo.getPet", str(source)],
                ["dependencies", "demo.getPet", str(source), "--format", "json"],
                ["summary", str(source)],
                ["summary", str(source), "--format", "json"],
                ["impact", "demo.Pet", str(source)],
                ["impact", "demo.Pet", str(source), "--format", "json"],
            ):
                with self.subTest(args=args):
                    exit_code, _, _ = self._run(args)
                    self.assertEqual(EXIT_SUCCESS, exit_code)

    def test_compiler_errors_use_validation_failure_for_all_commands(self) -> None:
        invalid = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory), invalid)
            for command in ("check", "ir", "plan", "summary"):
                for json_mode in (False, True):
                    args = [command]
                    if json_mode:
                        args += ["--format", "json"]
                    args.append(str(source))
                    with self.subTest(command=command, json_mode=json_mode):
                        exit_code, _, _ = self._run(args)
                        self.assertEqual(EXIT_VALIDATION_FAILURE, exit_code)
            for command in ("dependencies", "impact"):
                for json_mode in (False, True):
                    args = [command, "demo.Pet", str(source)]
                    if json_mode:
                        args += ["--format", "json"]
                    with self.subTest(command=command, json_mode=json_mode):
                        exit_code, _, _ = self._run(args)
                        self.assertEqual(EXIT_VALIDATION_FAILURE, exit_code)

    def test_fqn_commands_invalid_and_unknown_use_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            for command in ("dependencies", "impact"):
                for fqn in ("not a fqn", "demo.Missing"):
                    for json_mode in (False, True):
                        args = [command, fqn, str(source)]
                        if json_mode:
                            args += ["--format", "json"]
                        with self.subTest(command=command, fqn=fqn, json_mode=json_mode):
                            exit_code, _, _ = self._run(args)
                            self.assertEqual(EXIT_VALIDATION_FAILURE, exit_code)

    def test_plan_selection_failure_uses_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            for json_mode in (False, True):
                args = ["plan"]
                if json_mode:
                    args += ["--format", "json"]
                args += ["--deployment", "missing", str(source)]
                with self.subTest(json_mode=json_mode):
                    exit_code, _, _ = self._run(args)
                    self.assertEqual(EXIT_VALIDATION_FAILURE, exit_code)

    def test_unexpected_error_uses_internal_error_and_human_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            for command, args in (
                ("check", ["check", str(source)]),
                ("ir", ["ir", str(source)]),
                ("plan", ["plan", str(source)]),
                ("dependencies", ["dependencies", "demo.getPet", str(source)]),
                ("summary", ["summary", str(source)]),
                ("impact", ["impact", "demo.Pet", str(source)]),
            ):
                with self.subTest(command=command):
                    with patch("tools.aidl_cli.load_compiler_analysis", side_effect=RuntimeError("boom")):
                        exit_code, stdout, stderr = self._run(args)
                    self.assertEqual(EXIT_INTERNAL_ERROR, exit_code)
                    self.assertEqual("", stdout)
                    self.assertEqual(
                        f"aidl {command}: internal error: RuntimeError: boom\n",
                        stderr,
                    )

    def test_unexpected_error_uses_internal_error_json_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            for command, args in (
                ("check", ["check", "--format", "json", str(source)]),
                ("ir", ["ir", "--format", "json", str(source)]),
                ("plan", ["plan", "--format", "json", str(source)]),
                ("dependencies", ["dependencies", "demo.getPet", str(source), "--format", "json"]),
                ("summary", ["summary", str(source), "--format", "json"]),
                ("impact", ["impact", "demo.Pet", str(source), "--format", "json"]),
            ):
                with self.subTest(command=command):
                    with patch("tools.aidl_cli.load_compiler_analysis", side_effect=RuntimeError("boom")):
                        exit_code, stdout, stderr = self._run(args)
                    self.assertEqual(EXIT_INTERNAL_ERROR, exit_code)
                    self.assertEqual("", stderr)
                    self.assertEqual(
                        {
                            "command": command,
                            "diagnostics": [],
                            "error": {"kind": "internal", "message": "RuntimeError: boom"},
                            "ok": False,
                        },
                        json.loads(stdout),
                    )
                    self.assertTrue(stdout.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
