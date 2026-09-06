from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m8-coding-agent-workflow.md"
FIXTURE = ROOT / "fixtures" / "valid" / "m4-minimal"
FQN = "fixtures.valid.m4minimal.SnapshotItem"


class M8AgentWorkflowTest(unittest.TestCase):
    def _aidl(self, *args: str) -> tuple[int, dict[str, object], str]:
        completed = subprocess.run(
            [sys.executable, "-m", "tools.aidl_cli", *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        return completed.returncode, payload, completed.stderr

    def _assert_success(self, command: str, result: tuple[int, dict[str, object], str]) -> None:
        exit_code, payload, stderr = result
        self.assertEqual(0, exit_code)
        self.assertEqual(command, payload["command"])
        self.assertTrue(payload["ok"])
        self.assertEqual("", stderr)

    def test_documented_workflow_runs_before_and_after_supported_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "m4-minimal"
            shutil.copytree(FIXTURE, project)

            self._assert_success(
                "check",
                self._aidl("check", "--format", "json", str(project)),
            )
            self._assert_success(
                "plan",
                self._aidl("plan", str(project), "--format", "json"),
            )
            before_inspect = self._aidl(
                "inspect", FQN, str(project), "--format", "json"
            )
            self._assert_success("inspect", before_inspect)
            self.assertEqual("resolved", before_inspect[1]["result"]["status"])

            source = project / "app.aidl"
            text = source.read_text(encoding="utf-8")
            old = (
                "export entity SnapshotItem {\n"
                "  id: uuid primary immutable\n"
                "  revision: revision generated concurrencyToken\n"
                "  name: string(1..80) required mutable\n"
                "}"
            )
            new = old.replace("string(1..80)", "string(1..81)")
            self.assertIn(old, text)
            source.write_text(text.replace(old, new, 1), encoding="utf-8")
            self.assertIn(new, source.read_text(encoding="utf-8"))

            self._assert_success(
                "check",
                self._aidl("check", "--format", "json", str(project)),
            )
            self._assert_success(
                "plan",
                self._aidl("plan", str(project), "--format", "json"),
            )
            after_inspect = self._aidl(
                "inspect", FQN, str(project), "--format", "json"
            )
            self._assert_success("inspect", after_inspect)
            self.assertEqual("resolved", after_inspect[1]["result"]["status"])

    def test_documentation_spells_only_existing_workflow_surfaces(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        required = (
            "./aidl check --format json fixtures/valid/m4-minimal",
            "./aidl plan fixtures/valid/m4-minimal --format json",
            "./aidl inspect fixtures.valid.m4minimal.SnapshotItem fixtures/valid/m4-minimal --format json",
            "python3 -m unittest tools/test_m8_agent_workflow.py tools/test_aidl_check.py tools/test_aidl_plan.py tools/test_cli_output_schema.py",
            "there is no `aidl discover` command",
            "no synthetic `aidl edit` command exists",
            "`transitiveDependencies`",
            "M8-08 transitive closure",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

        self.assertNotIn("transitive dependency discovery remains open", text)
        self.assertNotIn("direct and transitive dependencies remains open", text)

        for path in (
            ROOT / "tools" / "test_aidl_check.py",
            ROOT / "tools" / "test_aidl_plan.py",
            ROOT / "tools" / "test_cli_output_schema.py",
        ):
            self.assertTrue(path.is_file(), path)


if __name__ == "__main__":
    unittest.main()
