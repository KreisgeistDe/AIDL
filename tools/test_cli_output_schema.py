from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from tools.aidl_cli import main
from tools.cli_output_schema import (
    CLI_OUTPUT_SCHEMA_ID,
    CLI_OUTPUT_SCHEMA_PATH,
    CLI_OUTPUT_SCHEMA_V1_ID,
    CLI_OUTPUT_SCHEMA_V1_PATH,
    CLI_OUTPUT_SCHEMA_V2_ID,
    CLI_OUTPUT_SCHEMA_V2_PATH,
    CLI_OUTPUT_SCHEMA_V3_ID,
    CLI_OUTPUT_SCHEMA_V3_PATH,
    CLI_OUTPUT_SCHEMA_V4_ID,
    CLI_OUTPUT_SCHEMA_V4_PATH,
    CLI_OUTPUT_SCHEMA_V5_ID,
    CLI_OUTPUT_SCHEMA_V5_PATH,
    CLI_OUTPUT_SCHEMA_V6_ID,
    CLI_OUTPUT_SCHEMA_V6_PATH,
    CLI_OUTPUT_SCHEMA_VERSION,
)
from tools.test_aidl_ir import _MINIMAL_PROJECT


ROOT = Path(__file__).resolve().parents[1]
CLI_SCHEMA_PATH = ROOT / CLI_OUTPUT_SCHEMA_PATH
CLI_SCHEMA_V1_PATH = ROOT / CLI_OUTPUT_SCHEMA_V1_PATH
CLI_SCHEMA_V2_PATH = ROOT / CLI_OUTPUT_SCHEMA_V2_PATH
CLI_SCHEMA_V3_PATH = ROOT / CLI_OUTPUT_SCHEMA_V3_PATH
CLI_SCHEMA_V4_PATH = ROOT / CLI_OUTPUT_SCHEMA_V4_PATH
CLI_SCHEMA_V5_PATH = ROOT / CLI_OUTPUT_SCHEMA_V5_PATH
CLI_SCHEMA_V6_PATH = ROOT / CLI_OUTPUT_SCHEMA_V6_PATH
IR_SCHEMA_PATH = ROOT / "spec" / "ir.schema.json"


class CliOutputSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(CLI_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.v1_schema = json.loads(CLI_SCHEMA_V1_PATH.read_text(encoding="utf-8"))
        cls.v2_schema = json.loads(CLI_SCHEMA_V2_PATH.read_text(encoding="utf-8"))
        cls.v3_schema = json.loads(CLI_SCHEMA_V3_PATH.read_text(encoding="utf-8"))
        cls.v4_schema = json.loads(CLI_SCHEMA_V4_PATH.read_text(encoding="utf-8"))
        cls.v5_schema = json.loads(CLI_SCHEMA_V5_PATH.read_text(encoding="utf-8"))
        cls.v6_schema = json.loads(CLI_SCHEMA_V6_PATH.read_text(encoding="utf-8"))
        cls.ir_schema = json.loads(IR_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        Draft202012Validator.check_schema(cls.v1_schema)
        Draft202012Validator.check_schema(cls.v2_schema)
        Draft202012Validator.check_schema(cls.v3_schema)
        Draft202012Validator.check_schema(cls.v4_schema)
        Draft202012Validator.check_schema(cls.v5_schema)
        Draft202012Validator.check_schema(cls.v6_schema)
        ir_resource = Resource.from_contents(cls.ir_schema)
        registry = (
            Registry()
            .with_resource(CLI_OUTPUT_SCHEMA_V1_ID, Resource.from_contents(cls.v1_schema))
            .with_resource(CLI_OUTPUT_SCHEMA_V2_ID, Resource.from_contents(cls.v2_schema))
            .with_resource(CLI_OUTPUT_SCHEMA_V3_ID, Resource.from_contents(cls.v3_schema))
            .with_resource(CLI_OUTPUT_SCHEMA_V4_ID, Resource.from_contents(cls.v4_schema))
            .with_resource(CLI_OUTPUT_SCHEMA_V5_ID, Resource.from_contents(cls.v5_schema))
            .with_resource(CLI_OUTPUT_SCHEMA_V6_ID, Resource.from_contents(cls.v6_schema))
            .with_resource("https://aidl.example/spec/cli/1/ir.schema.json", ir_resource)
            .with_resource(cls.ir_schema["$id"], ir_resource)
        )
        cls.validator = Draft202012Validator(cls.schema, registry=registry)
        cls.v5_validator = Draft202012Validator(cls.v5_schema, registry=registry)
        cls.v6_validator = Draft202012Validator(cls.v6_schema, registry=registry)

    def _run(self, args: list[str]) -> tuple[int, dict[str, object], str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(args)
        payload = json.loads(stdout.getvalue())
        self.validator.validate(payload)
        return exit_code, payload, stdout.getvalue(), stderr.getvalue()

    def test_schema_identity_versions_transitive_dependencies_without_invalidating_v1_through_v6(self) -> None:
        self.assertEqual(CLI_OUTPUT_SCHEMA_ID, self.schema["$id"])
        self.assertEqual("7.0.0", CLI_OUTPUT_SCHEMA_VERSION)
        self.assertEqual(CLI_OUTPUT_SCHEMA_V6_ID, self.v6_schema["$id"])
        self.assertEqual(CLI_OUTPUT_SCHEMA_V5_ID, self.v5_schema["$id"])
        self.assertEqual(CLI_OUTPUT_SCHEMA_V4_ID, self.v4_schema["$id"])
        self.assertEqual(CLI_OUTPUT_SCHEMA_V3_ID, self.v3_schema["$id"])
        self.assertEqual(CLI_OUTPUT_SCHEMA_V2_ID, self.v2_schema["$id"])
        self.assertEqual(CLI_OUTPUT_SCHEMA_V1_ID, self.v1_schema["$id"])
        legacy_success = {"command": "check", "diagnostics": [], "ok": True}
        self.validator.validate(legacy_success)
        self.validator.validate(
            {
                "command": "inspect",
                "diagnostics": [],
                "ok": False,
                "result": {"status": "unknown", "query": "demo.Missing"},
                "error": {"kind": "unknownFqn", "message": "missing"},
            }
        )
        self.validator.validate(
            {
                "command": "dependencies",
                "diagnostics": [],
                "ok": False,
                "result": {"status": "unknown", "query": "demo.Missing"},
                "error": {"kind": "unknownFqn", "message": "missing"},
            }
        )
        with self.assertRaises(Exception):
            self.v5_validator.validate(
                {
                    "command": "impact",
                    "diagnostics": [],
                    "ok": False,
                    "result": {"status": "unknown", "query": "demo.Missing"},
                    "error": {"kind": "unknownFqn", "message": "missing"},
                }
            )
        with self.assertRaises(Exception):
            self.v6_validator.validate(
                {
                    "command": "dependencies",
                    "diagnostics": [],
                    "ok": True,
                    "result": {
                        "status": "resolved",
                        "query": "demo.getPet",
                        "declaration": {
                            "declarationId": "demo.getPet@1",
                            "fullyQualifiedName": "demo.getPet",
                            "kind": "query",
                        },
                        "dependencies": [],
                        "transitiveDependencies": [],
                        "totals": {"directDependencies": 0, "transitiveDependencies": 0},
                        "truncated": {"directDependencies": False, "transitiveDependencies": False},
                    },
                }
            )

    def test_current_check_ir_plan_and_diff_outputs_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            check = self._run(["check", "--format", "json", str(source)])
            ir = self._run(["ir", "--format", "json", str(source)])
            plan = self._run(["plan", "--format", "json", str(source)])
            diff = self._run(
                ["diff", "--old", str(source), "--new", str(source), "--format", "json"]
            )

        self.assertEqual(0, check[0])
        self.assertEqual(0, ir[0])
        self.assertEqual(0, plan[0])
        self.assertEqual(0, diff[0])
        self.assertEqual([], diff[1]["result"]["changes"])
        self.assertEqual("", check[3] + ir[3] + plan[3] + diff[3])

    def test_current_inspect_success_and_failures_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            success = self._run(["inspect", "demo.Pet", str(source), "--format", "json"])
            unknown = self._run(["inspect", "demo.Missing", str(source), "--format", "json"])
            invalid = self._run(["inspect", "not a fqn", str(source), "--format", "json"])

        self.assertEqual(0, success[0])
        self.assertTrue(success[1]["ok"])
        declaration = success[1]["result"]["declaration"]
        self.assertEqual("demo.Pet", declaration["fullyQualifiedName"])
        self.assertEqual("entity", declaration["kind"])
        self.assertEqual("demo.Pet@1", declaration["canonical"]["declarationId"])
        self.assertEqual(1, unknown[0])
        self.assertEqual("unknown", unknown[1]["result"]["status"])
        self.assertEqual("unknownFqn", unknown[1]["error"]["kind"])
        self.assertEqual(1, invalid[0])
        self.assertEqual("invalid", invalid[1]["result"]["status"])
        self.assertEqual("invalidFqn", invalid[1]["error"]["kind"])
        self.assertEqual("", success[3] + unknown[3] + invalid[3])

    def test_dependencies_success_and_failures_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            success = self._run(["dependencies", "demo.getPet", str(source), "--format", "json"])
            unknown = self._run(["dependencies", "demo.Missing", str(source), "--format", "json"])
            invalid = self._run(["dependencies", "not a fqn", str(source), "--format", "json"])

        self.assertEqual(0, success[0])
        self.assertTrue(success[1]["ok"])
        result = success[1]["result"]
        self.assertEqual("resolved", result["status"])
        self.assertEqual("demo.getPet", result["declaration"]["fullyQualifiedName"])
        self.assertEqual(
            ["demo.Pet"],
            [item["fullyQualifiedName"] for item in result["dependencies"]],
        )
        self.assertEqual(
            ["demo.Species"],
            [item["fullyQualifiedName"] for item in result["transitiveDependencies"]],
        )
        self.assertEqual(
            {"directDependencies": 1, "transitiveDependencies": 1},
            result["totals"],
        )
        self.assertEqual(
            {"directDependencies": False, "transitiveDependencies": False},
            result["truncated"],
        )
        self.assertEqual(1, unknown[0])
        self.assertEqual("unknown", unknown[1]["result"]["status"])
        self.assertEqual("unknownFqn", unknown[1]["error"]["kind"])
        self.assertEqual(1, invalid[0])
        self.assertEqual("invalid", invalid[1]["result"]["status"])
        self.assertEqual("invalidFqn", invalid[1]["error"]["kind"])
        self.assertEqual("", success[3] + unknown[3] + invalid[3])

    def test_explain_success_and_failures_validate(self) -> None:
        project = (
            "module example.orders\n"
            "consumer ApplyOrder {\n"
            "  call: refreshOrder(event.id)\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(project, encoding="utf-8")
            success = self._run(["explain", "example.orders.ApplyOrder", str(source), "--format", "json"])
            unknown = self._run(["explain", "example.orders.Missing", str(source), "--format", "json"])
            invalid = self._run(["explain", "not a fqn", str(source), "--format", "json"])

        self.assertEqual(0, success[0])
        self.assertTrue(success[1]["ok"])
        result = success[1]["result"]
        self.assertEqual("resolved", result["status"])
        self.assertEqual("AIDL-DIST411", result["explanations"][0]["rule"]["code"])
        self.assertEqual(
            [{"kind": "insertClause", "text": "idempotency: event.eventId retain 30d"}],
            result["explanations"][0]["remediation"],
        )
        self.assertEqual(1, unknown[0])
        self.assertEqual("unknown", unknown[1]["result"]["status"])
        self.assertEqual("unknownFqn", unknown[1]["error"]["kind"])
        self.assertEqual(1, invalid[0])
        self.assertEqual("invalid", invalid[1]["result"]["status"])
        self.assertEqual("invalidFqn", invalid[1]["error"]["kind"])
        self.assertEqual("", success[3] + unknown[3] + invalid[3])

    def test_summary_success_and_failure_validate(self) -> None:
        invalid_project = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            success = self._run(["summary", str(source), "--format", "json"])
            source.write_text(invalid_project, encoding="utf-8")
            failure = self._run(["summary", str(source), "--format", "json"])

        self.assertEqual(0, success[0])
        self.assertTrue(success[1]["ok"])
        self.assertEqual(1, success[1]["result"]["moduleCount"])
        self.assertIn("demo.Pet", [item["fullyQualifiedName"] for item in success[1]["result"]["declarations"]])
        self.assertEqual(1, failure[0])
        self.assertFalse(failure[1]["ok"])
        self.assertEqual("compiler", failure[1]["error"]["kind"])
        self.assertTrue(failure[1]["diagnostics"])
        self.assertEqual("", success[3] + failure[3])

    def test_impact_success_and_failures_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            success = self._run(["impact", "demo.Pet", str(source), "--format", "json"])
            unknown = self._run(["impact", "demo.Missing", str(source), "--format", "json"])
            invalid = self._run(["impact", "not a fqn", str(source), "--format", "json"])

        self.assertEqual(0, success[0])
        self.assertTrue(success[1]["ok"])
        result = success[1]["result"]
        self.assertEqual("resolved", result["status"])
        self.assertEqual("demo.Pet", result["declaration"]["fullyQualifiedName"])
        self.assertEqual("unknown", result["generatedArtifacts"]["status"])
        self.assertEqual(1, unknown[0])
        self.assertEqual("unknown", unknown[1]["result"]["status"])
        self.assertEqual("unknownFqn", unknown[1]["error"]["kind"])
        self.assertEqual(1, invalid[0])
        self.assertEqual("invalid", invalid[1]["result"]["status"])
        self.assertEqual("invalidFqn", invalid[1]["error"]["kind"])
        self.assertEqual("", success[3] + unknown[3] + invalid[3])

    def test_inspect_is_deterministic_and_human_output_is_compact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            first = self._run(["inspect", "demo.Pet", str(source), "--format", "json"])
            second = self._run(["inspect", "demo.Pet", str(source), "--format", "json"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                human_code = main(["inspect", "demo.Pet", str(source)])

        self.assertEqual(first[2], second[2])
        self.assertEqual(0, human_code)
        self.assertIn("demo.Pet (entity)\n", stdout.getvalue())
        self.assertIn("canonical: {", stdout.getvalue())
        self.assertEqual("", stderr.getvalue())

    def test_dependencies_are_deterministic_and_human_output_is_compact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            first = self._run(["dependencies", "demo.getPet", str(source), "--format", "json"])
            second = self._run(["dependencies", "demo.getPet", str(source), "--format", "json"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                human_code = main(["dependencies", "demo.getPet", str(source)])

        self.assertEqual(first[2], second[2])
        self.assertEqual(0, human_code)
        self.assertEqual(
            "demo.getPet (query): 1 direct dependencies\n- demo.Pet (entity) [demo.Pet@1]\n",
            stdout.getvalue(),
        )
        self.assertEqual("", stderr.getvalue())

    def test_explain_is_deterministic_and_human_output_is_compact(self) -> None:
        project = (
            "module example.orders\n"
            "consumer ApplyOrder {\n"
            "  call: refreshOrder(event.id)\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(project, encoding="utf-8")
            first = self._run(["explain", "example.orders.ApplyOrder", str(source), "--format", "json"])
            second = self._run(["explain", "example.orders.ApplyOrder", str(source), "--format", "json"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                human_code = main(["explain", "example.orders.ApplyOrder", str(source)])

        self.assertEqual(first[2], second[2])
        self.assertEqual(0, human_code)
        self.assertIn("example.orders.ApplyOrder (consumer): 1 diagnostics\n", stdout.getvalue())
        self.assertIn("- AIDL-DIST411:", stdout.getvalue())
        self.assertIn("fix: insertClause", stdout.getvalue())
        self.assertEqual("", stderr.getvalue())

    def test_impact_is_deterministic_and_human_output_is_compact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(_MINIMAL_PROJECT, encoding="utf-8")
            first = self._run(["impact", "demo.Pet", str(source), "--format", "json"])
            second = self._run(["impact", "demo.Pet", str(source), "--format", "json"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                human_code = main(["impact", "demo.Pet", str(source)])

        self.assertEqual(first[2], second[2])
        self.assertEqual(0, human_code)
        self.assertIn("demo.Pet (entity)\n", stdout.getvalue())
        self.assertIn("generated artifacts: unknown:", stdout.getvalue())
        self.assertEqual("", stderr.getvalue())

    def test_inspect_rejects_project_with_compiler_errors(self) -> None:
        invalid_project = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(invalid_project, encoding="utf-8")
            result = self._run(["inspect", "demo.Pet", str(source), "--format", "json"])

        self.assertEqual(1, result[0])
        self.assertFalse(result[1]["ok"])
        self.assertEqual("compiler", result[1]["error"]["kind"])
        self.assertTrue(result[1]["diagnostics"])

    def test_dependencies_reject_project_with_compiler_errors(self) -> None:
        invalid_project = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(invalid_project, encoding="utf-8")
            result = self._run(["dependencies", "demo.Pet", str(source), "--format", "json"])

        self.assertEqual(1, result[0])
        self.assertFalse(result[1]["ok"])
        self.assertEqual("compiler", result[1]["error"]["kind"])
        self.assertTrue(result[1]["diagnostics"])

    def test_impact_rejects_project_with_compiler_errors(self) -> None:
        invalid_project = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(invalid_project, encoding="utf-8")
            result = self._run(["impact", "demo.Pet", str(source), "--format", "json"])

        self.assertEqual(1, result[0])
        self.assertFalse(result[1]["ok"])
        self.assertEqual("compiler", result[1]["error"]["kind"])
        self.assertTrue(result[1]["diagnostics"])

    def test_current_failure_envelopes_validate(self) -> None:
        invalid = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "app.aidl"
            source.write_text(invalid, encoding="utf-8")
            check = self._run(["check", "--format", "json", str(source)])
            ir = self._run(["ir", "--format", "json", str(source)])

        self.assertEqual(1, check[0])
        self.assertEqual(1, ir[0])
        self.assertFalse(check[1]["ok"])
        self.assertFalse(ir[1]["ok"])

    def test_editor_and_refactoring_result_shapes_validate(self) -> None:
        location = {"file": "/tmp/app.aidl", "line": 2, "column": 7, "offset": 18}
        target = {"fullyQualifiedName": "demo.Pet", "kind": "entity", "location": location}
        payloads = [
            {
                "command": "resolve",
                "diagnostics": [],
                "ok": True,
                "result": {"status": "resolved", "reference": "Pet", "target": target},
            },
            {
                "command": "complete",
                "diagnostics": [],
                "ok": True,
                "result": {
                    "status": "resolved",
                    "prefix": "Pe",
                    "candidates": [
                        {
                            "insertText": "Pet",
                            "displayText": "Pet",
                            "fullyQualifiedName": "demo.Pet",
                            "kind": "entity",
                            "origin": "local:demo",
                            "location": {"file": "/tmp/app.aidl", "offset": 18},
                        }
                    ],
                },
            },
            {
                "command": "document",
                "diagnostics": [],
                "ok": True,
                "result": {
                    "status": "resolved",
                    "diagnostics": [],
                    "declaration": {
                        "fullyQualifiedName": "demo.Pet",
                        "kind": "entity",
                        "location": location,
                        "representation": "entity Pet",
                    },
                },
            },
            {
                "command": "usages",
                "diagnostics": [],
                "ok": True,
                "result": {
                    "status": "resolved",
                    "target": target,
                    "usages": [
                        {"file": "/tmp/app.aidl", "line": 4, "column": 3, "offset": 44, "length": 3}
                    ],
                },
            },
            {
                "command": "rename",
                "diagnostics": [],
                "ok": True,
                "result": {
                    "status": "ready",
                    "applied": False,
                    "target": target,
                    "newFullyQualifiedName": "demo.Animal",
                    "edits": [
                        {
                            "file": "/tmp/app.aidl",
                            "line": 2,
                            "column": 7,
                            "offset": 18,
                            "length": 3,
                            "replacement": "Animal",
                        }
                    ],
                },
            },
        ]
        for payload in payloads:
            with self.subTest(command=payload["command"]):
                self.validator.validate(payload)

    def test_schema_rejects_unknown_command_and_top_level_expansion(self) -> None:
        with self.assertRaises(Exception):
            self.validator.validate(
                {"command": "check", "diagnostics": [], "ok": True, "unexpected": True}
            )
        with self.assertRaises(Exception):
            self.validator.validate({"command": "agent-workflow", "diagnostics": [], "ok": True})


if __name__ == "__main__":
    unittest.main()