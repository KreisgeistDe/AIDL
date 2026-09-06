from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools.aidl_cli import EXIT_INTERNAL_ERROR, EXIT_SUCCESS, EXIT_VALIDATION_FAILURE, main
from tools.compiler_ir import IrBuildError
from tools.ir_diff import IrDiffError
from tools.test_aidl_ir import _MINIMAL_PROJECT


_ADDED_DECLARATION = """export enum Color { red, blue }

"""


def _changed_project() -> str:
    return _MINIMAL_PROJECT.replace(
        "export enum Species { dog, cat }\n\n",
        _ADDED_DECLARATION + "export enum Species { dog, cat }\n\n",
        1,
    ).replace("timeout: 2s", "timeout: 3s", 1)


class AidlDiffCliTest(unittest.TestCase):
    def _write_project(self, root: Path, name: str, text: str = _MINIMAL_PROJECT) -> Path:
        project = root / name
        project.mkdir()
        source = project / "app.aidl"
        source.write_text(text, encoding="utf-8")
        return source

    def _run(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(args)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def _args(self, old: Path, new: Path, *, output_format: str = "human") -> list[str]:
        args = ["diff", "--old", str(old), "--new", str(new)]
        if output_format != "human":
            args += ["--format", output_format]
        return args

    def test_no_diff_is_success_and_stable_json_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self._write_project(root, "old")
            new = self._write_project(root, "new")
            first = self._run(self._args(old, new, output_format="json"))
            second = self._run(self._args(old, new, output_format="json"))

        self.assertEqual(first, second)
        self.assertEqual(EXIT_SUCCESS, first[0])
        self.assertEqual("", first[2])
        self.assertEqual(
            {
                "command": "diff",
                "diagnostics": [],
                "ok": True,
                "result": {"changes": [], "classifications": [], "guidance": []},
            },
            json.loads(first[1]),
        )
        self.assertTrue(first[1].endswith("\n"))

    def test_add_remove_and_change_are_successful_semantic_diff_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self._write_project(root, "old")
            new = self._write_project(root, "new", _changed_project())

            forward_code, forward_stdout, forward_stderr = self._run(
                self._args(old, new, output_format="json")
            )
            reverse_code, reverse_stdout, reverse_stderr = self._run(
                self._args(new, old, output_format="json")
            )

        forward = json.loads(forward_stdout)
        reverse = json.loads(reverse_stdout)
        self.assertEqual(EXIT_SUCCESS, forward_code)
        self.assertEqual(EXIT_SUCCESS, reverse_code)
        self.assertEqual("", forward_stderr)
        self.assertEqual("", reverse_stderr)
        self.assertTrue(forward["ok"])
        self.assertTrue(reverse["ok"])
        self.assertIn("added", {item["kind"] for item in forward["result"]["changes"]})
        self.assertIn("changed", {item["kind"] for item in forward["result"]["changes"]})
        self.assertIn("removed", {item["kind"] for item in reverse["result"]["changes"]})
        self.assertIn("changed", {item["kind"] for item in reverse["result"]["changes"]})
        raw_keys = [(item["kind"], item["path"]) for item in forward["result"]["changes"]]
        self.assertEqual(
            raw_keys,
            [(item["kind"], item["path"]) for item in forward["result"]["classifications"]],
        )
        self.assertEqual(
            raw_keys,
            [(item["kind"], item["path"]) for item in forward["result"]["guidance"]],
        )
        self.assertIn("safe", {item["classification"] for item in forward["result"]["classifications"]})
        self.assertIn("conditional", {item["classification"] for item in forward["result"]["classifications"]})
        self.assertIn("breaking", {item["classification"] for item in reverse["result"]["classifications"]})
        self.assertTrue(
            any(
                item["path"].startswith("/declarations/enum:demo.Color@1")
                and item["newValue"]["name"] == "Color"
                for item in forward["result"]["changes"]
                if item["kind"] == "added"
            )
        )
        self.assertTrue(
            any(
                item["oldValue"] is not None and item["newValue"] is not None
                for item in forward["result"]["changes"]
                if item["kind"] == "changed"
            )
        )

    def test_human_output_is_deterministic_projection_of_same_facts_classifications_and_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self._write_project(root, "old")
            new = self._write_project(root, "new", _changed_project())
            json_code, json_stdout, json_stderr = self._run(
                self._args(old, new, output_format="json")
            )
            human_first = self._run(self._args(old, new))
            human_second = self._run(self._args(old, new))

        self.assertEqual(EXIT_SUCCESS, json_code)
        self.assertEqual("", json_stderr)
        self.assertEqual(human_first, human_second)
        self.assertEqual(EXIT_SUCCESS, human_first[0])
        self.assertEqual("", human_first[2])
        result = json.loads(json_stdout)["result"]
        expected = "".join(
            f"{change['kind']} {change['path']} "
            f"old={json.dumps(change['oldValue'], ensure_ascii=False, separators=(',', ':'), sort_keys=True)} "
            f"new={json.dumps(change['newValue'], ensure_ascii=False, separators=(',', ':'), sort_keys=True)} "
            f"classification={classification['classification']} "
            f"rule={classification['rule']} "
            f"reason={json.dumps(classification['reason'], ensure_ascii=False, separators=(',', ':'), sort_keys=True)} "
            f"guidance={json.dumps(guidance, ensure_ascii=False, separators=(',', ':'), sort_keys=True)}\n"
            for change, classification, guidance in zip(
                result["changes"], result["classifications"], result["guidance"], strict=True
            )
        )
        self.assertEqual(expected, human_first[1])

    def test_invalid_old_and_new_compiler_inputs_are_side_specific_exit_one(self) -> None:
        invalid = _MINIMAL_PROJECT.replace(
            "module demo\n",
            "module demo\nimport missing.Type\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid_old = self._write_project(root, "invalid-old", invalid)
            valid_new = self._write_project(root, "valid-new")
            old_code, old_stdout, old_stderr = self._run(
                self._args(invalid_old, valid_new, output_format="json")
            )

            valid_old = self._write_project(root, "valid-old")
            invalid_new = self._write_project(root, "invalid-new", invalid)
            new_code, new_stdout, new_stderr = self._run(
                self._args(valid_old, invalid_new)
            )

        old_payload = json.loads(old_stdout)
        self.assertEqual(EXIT_VALIDATION_FAILURE, old_code)
        self.assertEqual("", old_stderr)
        self.assertFalse(old_payload["ok"])
        self.assertEqual("compiler", old_payload["error"]["kind"])
        self.assertEqual("old", old_payload["error"]["side"])
        self.assertEqual("AIDL-R001", old_payload["diagnostics"][0]["code"])

        self.assertEqual(EXIT_VALIDATION_FAILURE, new_code)
        self.assertEqual("", new_stdout)
        self.assertIn("aidl diff new:", new_stderr)
        self.assertIn("AIDL-R001", new_stderr)

    def test_ir_and_diff_input_errors_are_expected_side_specific_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self._write_project(root, "old")
            new = self._write_project(root, "new")

            with patch("tools.aidl_cli.build_canonical_ir", side_effect=IrBuildError("unsupported IR input")):
                ir_code, ir_stdout, ir_stderr = self._run(
                    self._args(old, new, output_format="json")
                )

            with patch(
                "tools.aidl_cli.diff_canonical_ir",
                side_effect=IrDiffError("new: schema-invalid at /app: bad input"),
            ):
                diff_code, diff_stdout, diff_stderr = self._run(
                    self._args(old, new, output_format="json")
                )

        self.assertEqual(EXIT_VALIDATION_FAILURE, ir_code)
        self.assertEqual("", ir_stderr)
        ir_payload = json.loads(ir_stdout)
        self.assertEqual(
            {"kind": "irBuild", "message": "unsupported IR input", "side": "old"},
            ir_payload["error"],
        )

        self.assertEqual(EXIT_VALIDATION_FAILURE, diff_code)
        self.assertEqual("", diff_stderr)
        diff_payload = json.loads(diff_stdout)
        self.assertEqual(
            {"kind": "diffInput", "message": "schema-invalid at /app: bad input", "side": "new"},
            diff_payload["error"],
        )

    def test_semantic_differences_are_exit_zero_and_unexpected_errors_are_exit_seventy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = self._write_project(root, "old")
            new = self._write_project(root, "new", _changed_project())
            diff_code, _, _ = self._run(self._args(old, new))

            with patch("tools.aidl_cli.load_compiler_analysis", side_effect=RuntimeError("boom")):
                internal_code, internal_stdout, internal_stderr = self._run(
                    self._args(old, new, output_format="json")
                )

        self.assertEqual(EXIT_SUCCESS, diff_code)
        self.assertEqual(EXIT_INTERNAL_ERROR, internal_code)
        self.assertEqual("", internal_stderr)
        self.assertEqual(
            {
                "command": "diff",
                "diagnostics": [],
                "error": {"kind": "internal", "message": "RuntimeError: boom"},
                "ok": False,
            },
            json.loads(internal_stdout),
        )


if __name__ == "__main__":
    unittest.main()
