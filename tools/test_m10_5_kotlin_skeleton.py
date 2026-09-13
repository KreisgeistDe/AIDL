from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


class M105KotlinSkeletonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.kotlin_root = cls.root / "compiler" / "kotlin"
        cls.manifest = json.loads(
            (cls.root / "spec" / "m10-5-parity-manifest.json").read_text(encoding="utf-8")
        )
        cls.contract = (
            cls.kotlin_root
            / "src/commonMain/kotlin/de/kreisgeist/aidl/compiler/contract/ParityContract.kt"
        ).read_text(encoding="utf-8")
        cls.build = (cls.kotlin_root / "build.gradle.kts").read_text(encoding="utf-8")

    def test_kmp_targets_share_one_common_contract_boundary(self) -> None:
        self.assertIn('kotlin("multiplatform") version "2.3.0"', self.build)
        self.assertRegex(self.build, r"\bjvm\(\)")
        self.assertRegex(self.build, r"\blinuxX64\s*\{")
        self.assertTrue((self.kotlin_root / "src/commonMain").is_dir())
        self.assertTrue((self.kotlin_root / "src/jvmMain").is_dir())
        self.assertTrue((self.kotlin_root / "src/linuxX64Main").is_dir())

    def test_coverage_gate_requires_line_and_branch_at_95_percent(self) -> None:
        self.assertIn("minBound(95, CoverageUnit.LINE)", self.build)
        self.assertIn("minBound(95, CoverageUnit.BRANCH)", self.build)

    def test_integrated_runner_inputs_are_inherited_exactly(self) -> None:
        self.assertEqual(self.manifest["runner_inputs"], ["source", "config", "profile"])
        match = re.search(r"runnerInputs: List<String> = listOf\(([^)]*)\)", self.contract)
        self.assertIsNotNone(match)
        values = re.findall(r'"([^"]+)"', match.group(1))
        self.assertEqual(values, self.manifest["runner_inputs"])

    def test_all_six_normative_bindings_are_inherited_exactly(self) -> None:
        block = re.search(
            r"normativeBindings: List<String> = listOf\((.*?)\n\s*\)",
            self.contract,
            re.DOTALL,
        )
        self.assertIsNotNone(block)
        values = re.findall(r'"([^"]+)"', block.group(1))
        self.assertEqual(values, self.manifest["normative_bindings"])
        self.assertEqual(len(values), 6)

    def test_python_authority_and_empty_semantic_allowlist_are_explicit(self) -> None:
        self.assertEqual(self.manifest["reference_implementation"], "python")
        self.assertEqual(self.manifest["comparison_contract"]["semantic_allowlists"], [])
        self.assertIn('const val referenceImplementation = "python"', self.contract)
        self.assertIn("val semanticAllowlists: List<String> = emptyList()", self.contract)

    def test_common_code_has_no_platform_integration_imports(self) -> None:
        common_files = list((self.kotlin_root / "src/commonMain").rglob("*.kt"))
        self.assertGreaterEqual(len(common_files), 2)
        forbidden = ("java.", "javax.", "kotlinx.cinterop", "platform.")
        for path in common_files:
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text, f"{path}: platform dependency {marker}")

    def test_adapters_depend_on_common_contract_and_do_not_duplicate_contract_tables(self) -> None:
        adapter_files = [
            *self.kotlin_root.joinpath("src/jvmMain").rglob("*.kt"),
            *self.kotlin_root.joinpath("src/linuxX64Main").rglob("*.kt"),
        ]
        self.assertEqual(len(adapter_files), 2)
        for path in adapter_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("ParityContract", text)
            self.assertNotIn("normativeBindings", text)
            self.assertNotIn("runnerInputs =", text)


if __name__ == "__main__":
    unittest.main()
