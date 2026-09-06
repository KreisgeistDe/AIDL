from __future__ import annotations

import importlib.resources
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


class PackagingContractTests(unittest.TestCase):
    def _project(self) -> dict:
        return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    def test_console_entry_point_and_supported_python_are_explicit(self) -> None:
        document = self._project()
        project = document["project"]
        self.assertEqual(project["scripts"]["aidl"], "tools.aidl_cli:main")
        self.assertEqual(project["requires-python"], ">=3.12,<3.13")
        self.assertEqual(project["name"], "aidl-toolchain")

    def test_runtime_dependencies_are_exactly_pinned(self) -> None:
        dependencies = self._project()["project"]["dependencies"]
        self.assertTrue(dependencies)
        self.assertTrue(all("==" in dependency for dependency in dependencies))
        self.assertIn("jsonschema==4.25.1", dependencies)
        self.assertEqual(len(dependencies), len(set(dependencies)))

    def test_build_backend_is_pinned(self) -> None:
        build_requires = self._project()["build-system"]["requires"]
        self.assertEqual(build_requires, ["setuptools==80.9.0", "wheel==0.45.1"])

    def test_machine_contracts_are_declared_as_package_data(self) -> None:
        document = self._project()
        self.assertEqual(document["tool"]["setuptools"]["packages"], ["tools", "spec"])
        self.assertEqual(document["tool"]["setuptools"]["package-data"]["spec"], ["*.json"])
        schema = importlib.resources.files("spec").joinpath("ir.schema.json")
        self.assertTrue(schema.is_file())
        self.assertIn('"irVersion"', schema.read_text(encoding="utf-8"))

    def test_repository_launcher_targets_same_production_entry_point(self) -> None:
        launcher = (ROOT / "aidl").read_text(encoding="utf-8")
        self.assertIn("from tools.aidl_cli import main", launcher)
        self.assertIn('raise SystemExit(main())', launcher)


if __name__ == "__main__":
    unittest.main()
