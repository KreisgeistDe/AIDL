from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.aidl_cli import EXIT_SUCCESS, main


class AidlResolveCliTest(unittest.TestCase):
    def test_json_resolve_returns_compiler_owned_target_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "app.aidl"
            lib = root / "lib.aidl"
            app.write_text(
                "module app\nimport lib.Shared\nentity Uses {\n  value: Shared\n}\n",
                encoding="utf-8",
            )
            lib.write_text("module lib\nexport entity Shared {\n}\n", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "resolve",
                        str(root),
                        "--file",
                        str(app),
                        "--offset",
                        str(app.read_text(encoding="utf-8").rindex("Shared")),
                        "--format",
                        "json",
                    ]
                )
            self.assertEqual(EXIT_SUCCESS, exit_code)
            self.assertEqual("", stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual("resolve", payload["command"])
            self.assertTrue(payload["ok"])
            self.assertEqual("resolved", payload["result"]["status"])
            self.assertEqual("lib.Shared", payload["result"]["target"]["fullyQualifiedName"])
            self.assertEqual(str(lib), payload["result"]["target"]["location"]["file"])

    def test_unresolved_is_successful_no_target_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "app.aidl"
            app.write_text("module app\nentity Uses {\n  value: Missing\n}\n", encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "resolve",
                        str(root),
                        "--file",
                        str(app),
                        "--offset",
                        str(app.read_text(encoding="utf-8").index("Missing")),
                    ]
                )
            self.assertEqual(EXIT_SUCCESS, exit_code)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("unresolved", payload["result"]["status"])
            self.assertNotIn("target", payload["result"])


if __name__ == "__main__":
    unittest.main()
