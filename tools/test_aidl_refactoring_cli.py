from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.aidl_cli import EXIT_SUCCESS, EXIT_VALIDATION_FAILURE, main
from tools.test_aidl_ir import _MINIMAL_PROJECT


class AidlRefactoringCliTest(unittest.TestCase):
    def _write_project(self, root: Path) -> Path:
        path = root / "app.aidl"
        path.write_text(_MINIMAL_PROJECT, encoding="utf-8")
        return path

    def _run(self, args: list[str]) -> tuple[int, dict, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue()), stderr.getvalue()

    def test_usages_json_reports_compiler_owned_locations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write_project(root)
            offset = source.read_text(encoding="utf-8").index("Species")

            exit_code, payload, stderr = self._run(
                ["usages", str(root), "--file", str(source), "--offset", str(offset), "--format", "json"]
            )

            self.assertEqual(EXIT_SUCCESS, exit_code)
            self.assertEqual("", stderr)
            self.assertEqual("usages", payload["command"])
            self.assertTrue(payload["ok"])
            self.assertEqual("resolved", payload["result"]["status"])
            self.assertEqual("demo.Species", payload["result"]["target"]["fullyQualifiedName"])
            self.assertEqual(1, len(payload["result"]["usages"]))

    def test_rename_json_supports_plan_and_apply_and_rejects_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write_project(root)
            offset = source.read_text(encoding="utf-8").index("Species")

            plan_code, plan, _ = self._run(
                ["rename", str(root), "--file", str(source), "--offset", str(offset), "--new-name", "AnimalKind", "--format", "json"]
            )
            self.assertEqual(EXIT_SUCCESS, plan_code)
            self.assertTrue(plan["ok"])
            self.assertEqual("ready", plan["result"]["status"])
            self.assertFalse(plan["result"]["applied"])

            apply_code, applied, _ = self._run(
                ["rename", str(root), "--file", str(source), "--offset", str(offset), "--new-name", "AnimalKind", "--apply", "--format", "json"]
            )
            self.assertEqual(EXIT_SUCCESS, apply_code)
            self.assertTrue(applied["ok"])
            self.assertEqual("applied", applied["result"]["status"])
            self.assertTrue(applied["result"]["applied"])

            new_offset = source.read_text(encoding="utf-8").index("AnimalKind")
            rejected_code, rejected, _ = self._run(
                ["rename", str(root), "--file", str(source), "--offset", str(new_offset), "--new-name", "entity", "--apply", "--format", "json"]
            )
            self.assertEqual(EXIT_VALIDATION_FAILURE, rejected_code)
            self.assertFalse(rejected["ok"])
            self.assertEqual("invalidName", rejected["result"]["status"])


if __name__ == "__main__":
    unittest.main()
