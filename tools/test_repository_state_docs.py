from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from tools.aidl_cli import _parser
from tools.cli_output_schema import CLI_OUTPUT_SCHEMA_ID, CLI_OUTPUT_SCHEMA_VERSION
from tools.ir_version import CURRENT_IR_VERSION, IrVersion
from tools.validate_repository_state import violations as repository_state_violations


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
AGENT_DOC = ROOT / "docs" / "04-agent-tooling.md"
COVERAGE_DOC = ROOT / "docs" / "12-coverage-and-limits.md"
M8_WORKFLOW_DOC = ROOT / "docs" / "m8-coding-agent-workflow.md"
M8_SCHEMA_DOC = ROOT / "docs" / "m8-cli-json-schemas.md"
IR_SCHEMA = ROOT / "spec" / "ir.schema.json"
PROFILE_REGISTRY = ROOT / "spec" / "profile-registry.json"


def _registered_commands() -> tuple[str, ...]:
    parser = _parser()
    action = next(
        item
        for item in parser._actions
        if isinstance(item, argparse._SubParsersAction)
    )
    return tuple(action.choices)


def _table_commands(text: str, pattern: str) -> tuple[str, ...]:
    return tuple(re.findall(pattern, text, flags=re.MULTILINE))


class RepositoryStateDocumentationTest(unittest.TestCase):
    def test_readme_and_agent_command_tables_match_registered_cli(self) -> None:
        registered = _registered_commands()
        readme_commands = _table_commands(
            README.read_text(encoding="utf-8"),
            r"^\| `([a-z]+)` \|",
        )
        agent_commands = _table_commands(
            AGENT_DOC.read_text(encoding="utf-8"),
            r"^\| `aidl ([a-z]+)(?: <FQN>)?` \|",
        )
        self.assertEqual(registered, readme_commands)
        self.assertEqual(registered, agent_commands)

        completed = subprocess.run(
            [sys.executable, "-m", "tools.aidl_cli", "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        for command in registered:
            with self.subTest(command=command):
                self.assertRegex(completed.stdout, rf"\b{re.escape(command)}\b")

    def test_current_ir_schema_identity_matches_ir_version_contract(self) -> None:
        schema = json.loads(IR_SCHEMA.read_text(encoding="utf-8"))
        version = IrVersion.parse(CURRENT_IR_VERSION)
        self.assertEqual(CURRENT_IR_VERSION, schema["properties"]["irVersion"]["const"])
        self.assertEqual(
            f"https://aidl.example/spec/{version.major}.{version.minor}/ir.schema.json",
            schema["$id"],
        )

    def test_cli_schema_generation_identifiers_are_complete_and_current(self) -> None:
        current_major = int(CLI_OUTPUT_SCHEMA_VERSION.split(".", 1)[0])
        self.assertEqual(7, current_major)
        expected_current = f"https://aidl.example/spec/cli/{current_major}/cli-output.schema.json"
        self.assertEqual(expected_current, CLI_OUTPUT_SCHEMA_ID)

        for major in range(1, current_major + 1):
            path = ROOT / "spec" / (
                "cli-output.schema.json" if major == 1 else f"cli-output-v{major}.schema.json"
            )
            with self.subTest(major=major):
                schema = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    f"https://aidl.example/spec/cli/{major}/cli-output.schema.json",
                    schema["$id"],
                )

        schema_doc = M8_SCHEMA_DOC.read_text(encoding="utf-8")
        self.assertIn(f"schema artifact version: `{CLI_OUTPUT_SCHEMA_VERSION}`", schema_doc)
        self.assertIn(f"`$id`: `{CLI_OUTPUT_SCHEMA_ID}`", schema_doc)

    def test_profile_registry_version_is_explicit_semver_and_documented_as_independent(self) -> None:
        registry = json.loads(PROFILE_REGISTRY.read_text(encoding="utf-8"))
        registry_version = registry["registryVersion"]
        parsed = IrVersion.parse(registry_version)
        self.assertEqual(registry_version, str(parsed))

        profiles = registry["profiles"]
        identities = [(item["id"], item["major"]) for item in profiles]
        self.assertEqual(len(identities), len(set(identities)))
        for profile_id, major in identities:
            with self.subTest(profile=profile_id):
                self.assertRegex(profile_id, r"^[a-z][a-z0-9-]*$")
                self.assertIsInstance(major, int)
                self.assertGreaterEqual(major, 1)

        marker = f"`registryVersion` `{registry_version}`"
        for path in (README, AGENT_DOC, COVERAGE_DOC):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn(marker, text)
                self.assertRegex(text, r"(?i)unabhängig|independent")

    def test_agent_and_coverage_docs_do_not_restore_known_stale_state_claims(self) -> None:
        workflow = M8_WORKFLOW_DOC.read_text(encoding="utf-8")
        self.assertIn("`transitiveDependencies`", workflow)
        self.assertIn("M8-08 transitive closure", workflow)
        self.assertNotIn("transitive dependency discovery remains open", workflow)
        self.assertNotIn("direct and transitive dependencies remains open", workflow)

        readme = README.read_text(encoding="utf-8")
        coverage = COVERAGE_DOC.read_text(encoding="utf-8")
        self.assertNotIn("noch keinen vollständigen Compiler oder eine Runtime", readme)
        self.assertNotIn("- Parser, Resolver und vollständige Typprüfung,", coverage)
        self.assertNotIn("- Codegeneratoren,", coverage)
        self.assertIn("## Installation aus einem Checkout", readme)
        self.assertIn("| Installierbares CLI-/Compiler-Artefakt |", coverage)
        self.assertNotIn("- installierbares CLI-/Compiler-Artefakt und Clean-Machine-Installation;", coverage)

    def test_roadmap_and_agent_state_authority_is_offline_valid(self) -> None:
        self.assertEqual(repository_state_violations(ROOT), ())

    def test_repository_state_validator_rejects_project_ai_paths(self) -> None:
        errors = repository_state_violations(ROOT, paths=("README.md", ".ai/TASK.md"))
        self.assertEqual(len(errors), 1)
        self.assertIn("project must not track .ai/** paths", errors[0])


if __name__ == "__main__":
    unittest.main()
