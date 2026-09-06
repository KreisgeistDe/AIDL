from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from tools.aidl_cli import EXIT_INTERNAL_ERROR, EXIT_SUCCESS, EXIT_VALIDATION_FAILURE, main
from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_explanation import explain_project_declaration


ROOT = Path(__file__).resolve().parents[1]


class CompilerExplanationTest(unittest.TestCase):
    def _write(self, root: Path, text: str) -> Path:
        source = root / "app.aidl"
        source.write_text(text, encoding="utf-8")
        return source

    def _run(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_explains_only_existing_compiler_rule_evidence_and_authorized_fix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "module example.orders\n"
                "consumer ApplyOrder {\n"
                "  call: refreshOrder(event.id)\n"
                "}\n",
            )
            analysis = load_compiler_analysis([source])
            result = explain_project_declaration(analysis, "example.orders.ApplyOrder")

        payload = result.to_json()
        self.assertEqual("resolved", payload["status"])
        self.assertEqual(1, payload["totalDiagnosticCount"])
        self.assertFalse(payload["truncated"])
        explanation = payload["explanations"][0]
        diagnostic = analysis.diagnostics[0].to_json()
        self.assertEqual(diagnostic["code"], explanation["rule"]["code"])
        self.assertEqual(diagnostic["message"], explanation["rule"]["message"])
        self.assertEqual(diagnostic["expected"], explanation["rule"]["expected"])
        self.assertEqual(diagnostic["docs"], explanation["rule"]["docs"])
        self.assertEqual(diagnostic["location"], explanation["evidence"]["location"])
        self.assertEqual(diagnostic["subject"], explanation["evidence"]["subject"])
        self.assertEqual(diagnostic["allowedFixes"], explanation["remediation"])
        self.assertEqual(
            [{"kind": "insertClause", "text": "idempotency: event.eventId retain 30d"}],
            explanation["remediation"],
        )

    def test_clean_declaration_has_bounded_empty_explanation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write(
                Path(directory),
                "module example.orders\n"
                "consumer ObserveOrder {\n"
                "  retry: exponential (attempts:3)\n"
                "}\n",
            )
            analysis = load_compiler_analysis([source])
            first = explain_project_declaration(analysis, "example.orders.ObserveOrder").to_json()
            second = explain_project_declaration(analysis, "example.orders.ObserveOrder").to_json()

        self.assertEqual(first, second)
        self.assertEqual([], first["explanations"])
        self.assertEqual(0, first["totalDiagnosticCount"])
        self.assertFalse(first["truncated"])

    def test_cli_json_and_human_output_are_deterministic_and_successful_with_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write(
                Path(directory),
                "module example.orders\n"
                "consumer ApplyOrder {\n"
                "  call: refreshOrder(event.id)\n"
                "}\n",
            )
            first = self._run(["explain", "example.orders.ApplyOrder", str(source), "--format", "json"])
            second = self._run(["explain", "example.orders.ApplyOrder", str(source), "--format", "json"])
            human = self._run(["explain", "example.orders.ApplyOrder", str(source)])

        self.assertEqual(EXIT_SUCCESS, first[0])
        self.assertEqual(first[1], second[1])
        payload = json.loads(first[1])
        self.assertTrue(payload["ok"])
        self.assertEqual("AIDL-DIST411", payload["result"]["explanations"][0]["rule"]["code"])
        self.assertEqual(EXIT_SUCCESS, human[0])
        self.assertIn("example.orders.ApplyOrder (consumer): 1 diagnostics\n", human[1])
        self.assertIn("fix: insertClause", human[1])
        self.assertEqual("", first[2] + second[2] + human[2])

    def test_invalid_and_unknown_fqn_use_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write(
                Path(directory),
                "module example.orders\nconsumer ObserveOrder {\n}\n",
            )
            for fqn, status, kind in (
                ("not a fqn", "invalid", "invalidFqn"),
                ("example.orders.Missing", "unknown", "unknownFqn"),
            ):
                with self.subTest(fqn=fqn):
                    code, stdout, stderr = self._run(
                        ["explain", fqn, str(source), "--format", "json"]
                    )
                    self.assertEqual(EXIT_VALIDATION_FAILURE, code)
                    payload = json.loads(stdout)
                    self.assertFalse(payload["ok"])
                    self.assertEqual(status, payload["result"]["status"])
                    self.assertEqual(kind, payload["error"]["kind"])
                    self.assertEqual("", stderr)

    def test_unexpected_cli_failure_uses_internal_error(self) -> None:
        with patch("tools.aidl_cli.load_compiler_analysis", side_effect=RuntimeError("boom")):
            code, stdout, stderr = self._run(
                ["explain", "example.orders.ApplyOrder", ".", "--format", "json"]
            )
        self.assertEqual(EXIT_INTERNAL_ERROR, code)
        self.assertEqual("", stderr)
        self.assertEqual("internal", json.loads(stdout)["error"]["kind"])

    def test_v4_schema_accepts_explain_and_frozen_prior_envelopes(self) -> None:
        schemas = {}
        for version, name in (
            (1, "cli-output.schema.json"),
            (2, "cli-output-v2.schema.json"),
            (3, "cli-output-v3.schema.json"),
            (4, "cli-output-v4.schema.json"),
        ):
            schemas[version] = json.loads((ROOT / "spec" / name).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schemas[version])
        ir_schema = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))
        ir_resource = Resource.from_contents(ir_schema)
        registry = Registry()
        for version in (1, 2, 3):
            registry = registry.with_resource(schemas[version]["$id"], Resource.from_contents(schemas[version]))
        registry = registry.with_resource("https://aidl.example/spec/cli/1/ir.schema.json", ir_resource)
        registry = registry.with_resource(ir_schema["$id"], ir_resource)
        validator = Draft202012Validator(schemas[4], registry=registry)

        with tempfile.TemporaryDirectory() as directory:
            source = self._write(
                Path(directory),
                "module example.orders\n"
                "consumer ApplyOrder {\n"
                "  call: refreshOrder(event.id)\n"
                "}\n",
            )
            code, stdout, _ = self._run(
                ["explain", "example.orders.ApplyOrder", str(source), "--format", "json"]
            )
        self.assertEqual(EXIT_SUCCESS, code)
        validator.validate(json.loads(stdout))
        validator.validate({"command": "check", "diagnostics": [], "ok": True})
        self.assertEqual("https://aidl.example/spec/cli/4/cli-output.schema.json", schemas[4]["$id"])


if __name__ == "__main__":
    unittest.main()
