from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.aidl_cli import EXIT_SUCCESS, EXIT_VALIDATION_FAILURE, main
from tools.compiler_change_impact import MAX_IMPACT_DECLARATIONS, analyze_change_impact
from tools.compiler_diagnostics import load_compiler_analysis
from tools.test_aidl_ir import _MINIMAL_PROJECT


class CompilerChangeImpactTest(unittest.TestCase):
    def _run(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(args)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_entity_impact_projects_direct_ir_evidence_conservatively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            result = analyze_change_impact(load_compiler_analysis([source]), "demo.Pet").to_json()

        self.assertEqual("resolved", result["status"])
        self.assertEqual("demo.Pet@1", result["declaration"]["declarationId"])
        self.assertIn(
            "demo.getPet",
            [item["declaration"]["fullyQualifiedName"] for item in result["affectedDeclarations"]],
        )
        self.assertIn(
            "demo.Pet",
            [item["declaration"]["fullyQualifiedName"] for item in result["persistedState"]],
        )
        self.assertEqual("unknown", result["generatedArtifacts"]["status"])
        self.assertEqual([], result["generatedArtifacts"]["artifacts"])
        self.assertTrue(result["generatedArtifacts"]["reason"])

    def test_public_operation_impact_is_evidence_backed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            result = analyze_change_impact(load_compiler_analysis([source]), "demo.getPet").to_json()

        contracts = result["publicContracts"]
        self.assertTrue(
            any(
                item["declaration"]["fullyQualifiedName"] == "demo.getPet"
                and item["category"] == "publicOperation"
                for item in contracts
            )
        )
        self.assertTrue(any(item["surface"] == "apiClient" for item in result["compatibilityChecks"]))
        self.assertTrue(all(item["status"] == "requiresComparison" for item in result["compatibilityChecks"]))

    def test_impact_is_deterministic_and_cli_is_compact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            first = self._run(["impact", "demo.Pet", str(source), "--format", "json"])
            second = self._run(["impact", "demo.Pet", str(source), "--format", "json"])
            human = self._run(["impact", "demo.Pet", str(source)])

        self.assertEqual(EXIT_SUCCESS, first[0])
        self.assertEqual(first[1], second[1])
        self.assertEqual("", first[2] + second[2])
        self.assertTrue(json.loads(first[1])["ok"])
        self.assertEqual(EXIT_SUCCESS, human[0])
        self.assertIn("demo.Pet (entity)\n", human[1])
        self.assertIn("generated artifacts: unknown:", human[1])
        self.assertEqual("", human[2])

    def test_impact_bounds_affected_declarations(self) -> None:
        anchor = """export query getPet(id: Pet.id) -> Pet? {
  auth: authenticated
  read: Pet.byId(id)
  consistency: strong
  errors: []
  timeout: 2s
}
"""
        extra_queries = "\n".join(
            f"""export query get{index:03d}(id: Pet.id) -> Pet? {{
  auth: authenticated
  read: Pet.byId(id)
  consistency: strong
  errors: []
  timeout: 2s
}}"""
            for index in range(MAX_IMPACT_DECLARATIONS + 2)
        )
        project = _MINIMAL_PROJECT.replace(anchor, anchor + "\n" + extra_queries + "\n", 1)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "many.aidl"
            source.write_text(project, encoding="utf-8")
            analysis = load_compiler_analysis([source])
            self.assertFalse([item for item in analysis.diagnostics if item.severity.value == "error"])
            result = analyze_change_impact(analysis, "demo.Pet").to_json()

        self.assertGreater(result["totals"]["affectedDeclarations"], MAX_IMPACT_DECLARATIONS)
        self.assertEqual(MAX_IMPACT_DECLARATIONS, len(result["affectedDeclarations"]))
        self.assertTrue(result["truncated"]["affectedDeclarations"])

    def test_invalid_unknown_and_compiler_error_use_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            for fqn in ("not a fqn", "demo.Missing"):
                code, stdout, stderr = self._run(["impact", fqn, str(source), "--format", "json"])
                self.assertEqual(EXIT_VALIDATION_FAILURE, code)
                self.assertFalse(json.loads(stdout)["ok"])
                self.assertEqual("", stderr)

            source.write_text(
                _MINIMAL_PROJECT.replace("module demo\n", "module demo\nimport missing.Type\n", 1),
                encoding="utf-8",
            )
            code, stdout, stderr = self._run(["impact", "demo.Pet", str(source), "--format", "json"])
            self.assertEqual(EXIT_VALIDATION_FAILURE, code)
            self.assertEqual("compiler", json.loads(stdout)["error"]["kind"])
            self.assertEqual("", stderr)


if __name__ == "__main__":
    unittest.main()
