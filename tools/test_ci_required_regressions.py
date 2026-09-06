from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.ci_required_regressions import (
    CONFIG_ERROR_EXIT,
    CertificationError,
    certify_repository,
    load_inventory,
    main,
)


_AREAS = (
    ("completion", "tools.compiler_completion", "complete"),
    ("documentation", "tools.compiler_documentation", "document"),
    ("refactoring", "tools.compiler_refactoring", "rename"),
    ("resolution", "tools.compiler_resolution", "resolve"),
)


class RequiredRegressionCertificationTest(unittest.TestCase):
    def _write(self, root: Path, relative: str, text: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _inventory(self) -> dict[str, object]:
        suites = []
        cli_tests = []
        for area, module, command in _AREAS:
            compiler_test = f"tools/test_compiler_{area}.py"
            cli_test = f"tools/test_aidl_{area}_cli.py"
            cli_tests.append(cli_test)
            suites.append(
                {
                    "area": area,
                    "module": module,
                    "source": module.replace(".", "/") + ".py",
                    "compilerTests": [compiler_test],
                    "cliCommands": [command],
                    "cliTests": [cli_test],
                }
            )
        return {
            "version": 1,
            "gate": "Compiler / Python",
            "workflow": ".github/workflows/python-validation.yml",
            "workflowJob": "compiler-python",
            "selectionPolicy": ".github/python-test-selection.json",
            "cliSource": "tools/aidl_cli.py",
            "compilerSuites": suites,
            "cliRegressionModules": sorted(cli_tests),
        }

    def _fixture(self, root: Path) -> Path:
        self._write(
            root,
            ".github/python-test-selection.json",
            json.dumps({"version": 1, "roots": ["tools"], "pattern": "test_*.py", "exclusions": []}),
        )
        self._write(
            root,
            ".github/workflows/python-validation.yml",
            "name: Validation\n"
            "jobs:\n"
            "  compiler-python:\n"
            "    name: Compiler / Python\n"
            "    steps:\n"
            "      - name: Certify\n"
            "        run: python3 -m tools.ci_required_regressions validate\n"
            "      - name: Run\n"
            "        run: python3 -m tools.ci_test_selection run\n",
        )
        commands = []
        for area, module, command in _AREAS:
            self._write(root, module.replace(".", "/") + ".py", "VALUE = 1\n")
            self._write(root, f"tools/test_compiler_{area}.py", f"import {module}\n")
            self._write(root, f"tools/test_aidl_{area}_cli.py", "import tools.aidl_cli\n")
            commands.append(f'subcommands.add_parser("{command}")')
        self._write(
            root,
            "tools/aidl_cli.py",
            "def register(subcommands):\n    " + "\n    ".join(commands) + "\n",
        )
        inventory_path = self._write(
            root,
            ".github/compiler-required-regressions.json",
            json.dumps(self._inventory(), indent=2) + "\n",
        )
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        return inventory_path

    def _rewrite_json(self, root: Path, relative: str, payload: object) -> None:
        self._write(root, relative, json.dumps(payload, indent=2) + "\n")
        subprocess.run(["git", "add", relative], cwd=root, check=True)

    def test_complete_inventory_certifies_all_pairs_in_required_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._fixture(root)
            result = certify_repository(root, inventory)
        self.assertEqual(4, result.suites)
        self.assertEqual(4, result.compiler_regressions)
        self.assertEqual(4, result.cli_regressions)

    def test_missing_required_module_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._fixture(root)
            (root / "tools/compiler_completion.py").unlink()
            subprocess.run(["git", "add", "-u"], cwd=root, check=True)
            with self.assertRaisesRegex(CertificationError, "not committed"):
                certify_repository(root, inventory)

    def test_required_exclusion_from_compiler_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._fixture(root)
            policy = {
                "version": 1,
                "roots": ["tools"],
                "pattern": "test_*.py",
                "exclusions": [
                    {
                        "path": "tools/test_compiler_completion.py",
                        "ciJob": "Other Gate",
                        "command": "python3 -m unittest tools/test_compiler_completion.py",
                        "reason": "Fixture exclusion used to prove required-gate rejection."
                    }
                ],
            }
            self._rewrite_json(root, ".github/python-test-selection.json", policy)
            with self.assertRaisesRegex(CertificationError, "excluded from Compiler / Python"):
                certify_repository(root, inventory)

    def test_new_critical_importer_not_in_inventory_fails_drift_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._fixture(root)
            self._write(root, "tools/test_unexpected_name.py", "import tools.compiler_completion\n")
            subprocess.run(["git", "add", "tools/test_unexpected_name.py"], cwd=root, check=True)
            with self.assertRaisesRegex(CertificationError, "selected but not inventoried"):
                certify_repository(root, inventory)

    def test_new_cli_regression_not_in_inventory_fails_drift_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._fixture(root)
            self._write(root, "tools/test_unexpected_cli_surface.py", "import tools.aidl_cli\n")
            subprocess.run(["git", "add", "tools/test_unexpected_cli_surface.py"], cwd=root, check=True)
            with self.assertRaisesRegex(CertificationError, "CLI regressions are selected but not inventoried"):
                certify_repository(root, inventory)

    def test_inventory_requires_deterministic_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._fixture(root)
            payload = self._inventory()
            payload["cliRegressionModules"] = list(reversed(payload["cliRegressionModules"]))
            self._rewrite_json(root, ".github/compiler-required-regressions.json", payload)
            with self.assertRaisesRegex(CertificationError, "unique and sorted"):
                load_inventory(inventory)

    def test_each_compiler_suite_requires_cli_pair_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._fixture(root)
            payload = self._inventory()
            payload["compilerSuites"][0]["cliTests"] = []
            self._rewrite_json(root, ".github/compiler-required-regressions.json", payload)
            with self.assertRaisesRegex(CertificationError, "must be a non-empty array"):
                load_inventory(inventory)

    def test_cli_has_stable_success_and_configuration_error_exits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory = self._fixture(root)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                success = main(["validate", "--repo-root", str(root), "--inventory", str(inventory)])
            self.assertEqual(0, success)
            self.assertIn("required regressions:", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())

            payload = self._inventory()
            payload["version"] = 2
            self._rewrite_json(root, ".github/compiler-required-regressions.json", payload)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                failure = main(["validate", "--repo-root", str(root), "--inventory", str(inventory)])
            self.assertEqual(CONFIG_ERROR_EXIT, failure)
            self.assertIn("unsupported required-regression inventory version", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
