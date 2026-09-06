from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.aidl_cli import EXIT_SUCCESS, EXIT_VALIDATION_FAILURE, main
from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_summary import MAX_SUMMARY_DECLARATIONS, summarize_project
from tools.test_aidl_ir import _MINIMAL_PROJECT


class CompilerProjectSummaryTest(unittest.TestCase):
    def _run(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(args)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_summary_projects_existing_compiler_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            summary = summarize_project(load_compiler_analysis([source])).to_json()

        self.assertEqual(1, summary["moduleCount"])
        self.assertEqual(1, summary["documentCount"])
        self.assertEqual("demo", summary["modules"][0]["name"])
        self.assertEqual(len(summary["declarations"]), summary["totals"]["declarations"])
        self.assertGreaterEqual(summary["declarationCount"], summary["totals"]["declarations"])
        self.assertEqual(
            sorted(item["fullyQualifiedName"] for item in summary["declarations"]),
            [item["fullyQualifiedName"] for item in summary["declarations"]],
        )
        self.assertIn("demo.Pet", [item["fullyQualifiedName"] for item in summary["declarations"]])
        self.assertEqual(
            sorted(item["kind"] for item in summary["declarationKinds"]),
            [item["kind"] for item in summary["declarationKinds"]],
        )
        self.assertEqual(
            {"declarations": False, "moduleDependencies": False, "modules": False},
            summary["truncated"],
        )

    def test_summary_is_deterministic_and_cli_is_compact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            first = self._run(["summary", str(source), "--format", "json"])
            second = self._run(["summary", str(source), "--format", "json"])
            human = self._run(["summary", str(source)])

        self.assertEqual(EXIT_SUCCESS, first[0])
        self.assertEqual(first[1], second[1])
        self.assertEqual("", first[2] + second[2])
        payload = json.loads(first[1])
        self.assertTrue(payload["ok"])
        self.assertEqual("summary", payload["command"])
        self.assertEqual(1, payload["result"]["moduleCount"])
        self.assertEqual(EXIT_SUCCESS, human[0])
        self.assertIn("project: 1 modules", human[1])
        self.assertIn("declarations:", human[1])
        self.assertEqual("", human[2])

    def test_summary_bounds_declaration_listing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "many.aidl"
            declarations = "".join(
                f"export enum E{index:03d} {{ value }}\n" for index in range(MAX_SUMMARY_DECLARATIONS + 2)
            )
            source.write_text("module demo\n" + declarations, encoding="utf-8")
            summary = summarize_project(load_compiler_analysis([source])).to_json()

        self.assertEqual(MAX_SUMMARY_DECLARATIONS + 2, summary["totals"]["declarations"])
        self.assertEqual(MAX_SUMMARY_DECLARATIONS, len(summary["declarations"]))
        self.assertTrue(summary["truncated"]["declarations"])
        self.assertEqual("demo.E000", summary["declarations"][0]["fullyQualifiedName"])

    def test_summary_rejects_project_with_compiler_errors(self) -> None:
        invalid = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(invalid, encoding="utf-8")
            exit_code, stdout, stderr = self._run(["summary", str(source), "--format", "json"])

        self.assertEqual(EXIT_VALIDATION_FAILURE, exit_code)
        self.assertEqual("", stderr)
        payload = json.loads(stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual("compiler", payload["error"]["kind"])
        self.assertTrue(payload["diagnostics"])


if __name__ == "__main__":
    unittest.main()
