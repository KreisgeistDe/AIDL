from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.aidl_cli import EXIT_SUCCESS, main


class AidlDocumentationCliTest(unittest.TestCase):
    def _run(self, args: list[str]) -> tuple[int, dict, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue()), stderr.getvalue()

    def test_document_json_reports_compiler_owned_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.aidl"
            source.write_text(
                "module app\n"
                "import lib.Shared\n"
                "entity Uses { target: Shared }\n",
                encoding="utf-8",
            )
            target = root / "lib.aidl"
            target.write_text("module lib\nexport entity Shared {\n}\n", encoding="utf-8")
            text = source.read_text(encoding="utf-8")
            offset = text.index("Shared", text.index("target:"))

            exit_code, payload, stderr = self._run(
                ["document", str(root), "--file", str(source), "--offset", str(offset), "--format", "json"]
            )

            self.assertEqual(EXIT_SUCCESS, exit_code)
            self.assertEqual("", stderr)
            self.assertEqual("document", payload["command"])
            self.assertTrue(payload["ok"])
            self.assertEqual("resolved", payload["result"]["status"])
            declaration = payload["result"]["declaration"]
            self.assertEqual("lib.Shared", declaration["fullyQualifiedName"])
            self.assertEqual("entity", declaration["kind"])
            self.assertEqual(str(target), declaration["location"]["file"])
            self.assertEqual("entity Shared", declaration["representation"])

    def test_document_json_does_not_guess_unresolved_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.aidl"
            source.write_text("module app\nentity Uses { target: Missing }\n", encoding="utf-8")
            offset = source.read_text(encoding="utf-8").index("Missing")

            exit_code, payload, stderr = self._run(
                ["document", str(root), "--file", str(source), "--offset", str(offset), "--format", "json"]
            )

            self.assertEqual(EXIT_SUCCESS, exit_code)
            self.assertEqual("", stderr)
            self.assertEqual("unresolved", payload["result"]["status"])
            self.assertNotIn("declaration", payload["result"])
            self.assertEqual([], payload["result"]["diagnostics"])

    def test_document_json_preserves_diagnostic_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "app.aidl"
            source.write_text(
                "module app\nentity Shared {\n}\nentity Shared {\n}\n",
                encoding="utf-8",
            )
            # Duplicate-declaration diagnostics anchor at the second declaration start.
            offset = source.read_text(encoding="utf-8").rindex("entity")

            exit_code, payload, _ = self._run(
                ["document", str(root), "--file", str(source), "--offset", str(offset), "--format", "json"]
            )

            self.assertEqual(EXIT_SUCCESS, exit_code)
            self.assertEqual("resolved", payload["result"]["status"])
            diagnostic = next(item for item in payload["result"]["diagnostics"] if item["code"] == "AIDL-R002")
            for field in ("code", "phase", "severity", "message", "location"):
                self.assertIn(field, diagnostic)


if __name__ == "__main__":
    unittest.main()
