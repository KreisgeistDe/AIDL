from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.aidl_cli import EXIT_SUCCESS, main


class AidlCompletionCliTest(unittest.TestCase):
    def _run(self, args: list[str]) -> tuple[int, dict, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue()), stderr.getvalue()

    def test_complete_json_reports_compiler_owned_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.aidl"
            source.write_text(
                "module app\n"
                "import lib.Shared\n"
                "entity Uses { target: Shared }\n",
                encoding="utf-8",
            )
            (root / "lib.aidl").write_text("module lib\nexport entity Shared {\n}\n", encoding="utf-8")
            text = source.read_text(encoding="utf-8")
            offset = text.index("Shared", text.index("target:")) + len("Sha")

            exit_code, payload, stderr = self._run(
                ["complete", str(root), "--file", str(source), "--offset", str(offset), "--format", "json"]
            )

            self.assertEqual(EXIT_SUCCESS, exit_code)
            self.assertEqual("", stderr)
            self.assertEqual("complete", payload["command"])
            self.assertTrue(payload["ok"])
            self.assertEqual("resolved", payload["result"]["status"])
            self.assertEqual("Sha", payload["result"]["prefix"])
            self.assertEqual("Shared", payload["result"]["candidates"][0]["insertText"])
            self.assertEqual("lib.Shared", payload["result"]["candidates"][0]["fullyQualifiedName"])
            self.assertEqual("exactImport:lib.Shared", payload["result"]["candidates"][0]["origin"])

    def test_complete_json_rejects_declaration_name_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.aidl"
            source.write_text(
                "module app\n"
                "entity Shared {\n}\n",
                encoding="utf-8",
            )
            text = source.read_text(encoding="utf-8")
            offset = text.index("Shared") + len("Sha")

            exit_code, payload, stderr = self._run(
                ["complete", str(root), "--file", str(source), "--offset", str(offset), "--format", "json"]
            )

            self.assertEqual(EXIT_SUCCESS, exit_code)
            self.assertEqual("", stderr)
            self.assertTrue(payload["ok"])
            self.assertEqual("invalid", payload["result"]["status"])
            self.assertEqual([], payload["result"]["candidates"])

    def test_complete_json_does_not_guess_invalid_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.aidl"
            source.write_text("module app\nentity Uses { target: @ }\n", encoding="utf-8")

            exit_code, payload, _ = self._run(
                ["complete", str(root), "--file", str(source), "--offset", str(source.read_text().index("@")), "--format", "json"]
            )

            self.assertEqual(EXIT_SUCCESS, exit_code)
            self.assertEqual("invalid", payload["result"]["status"])
            self.assertEqual([], payload["result"]["candidates"])


if __name__ == "__main__":
    unittest.main()
