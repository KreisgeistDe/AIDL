from __future__ import annotations

import json
import sys
import unittest
from contextlib import chdir
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
FIXTURE_ROOT = REPO_ROOT / "fixtures"
FIXTURE_ROOT_REL = Path("fixtures")
sys.path.insert(0, str(REPO_ROOT))

from tools import compiler_diagnostics  # noqa: E402
from tools.compiler_ir import build_canonical_ir  # noqa: E402
from tools.generate_m4 import generate_m4_files  # noqa: E402
from tools.ir_canonical_json import canonical_ir_json_text  # noqa: E402
from tools.ir_plan import build_plan, canonical_plan_json_text  # noqa: E402


class M5FixtureCorpusTest(unittest.TestCase):
    maxDiff = None
    _SNAPSHOT_KINDS = {"diagnostics", "ir", "plan", "generated"}

    def _manifest(self) -> list[dict[str, object]]:
        payload = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 2)
        cases = payload["cases"]
        self.assertTrue(cases)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertEqual({case["suite"] for case in cases}, {"valid", "invalid"})
        for case in cases:
            path = Path(str(case["path"]))
            self.assertEqual(path.parts[0], case["suite"])
            case_dir = FIXTURE_ROOT / path
            self.assertTrue(case_dir.is_dir(), case_dir)
            self.assertTrue(list(case_dir.rglob("*.aidl")), case_dir)
            expected = case["expectedDiagnostics"]
            snapshots = case["snapshots"]
            self.assertIsInstance(snapshots, dict)
            self.assertEqual(set(snapshots) - self._SNAPSHOT_KINDS, set())
            self.assertIn("diagnostics", snapshots)
            if case["suite"] == "valid":
                if expected:
                    self.assertEqual(
                        set(snapshots),
                        {"diagnostics"},
                        "diagnostic-only valid fixtures may document stable unsupported-profile diagnostics but cannot claim IR/plan/generated validity",
                    )
            else:
                self.assertTrue(expected)
                self.assertEqual(set(snapshots), {"diagnostics"})
            if "plan" in snapshots or "generated" in snapshots:
                self.assertIn("ir", snapshots)
            for kind, value in snapshots.items():
                snapshot_path = case_dir / str(value)
                if kind == "generated":
                    self.assertTrue(snapshot_path.is_dir(), snapshot_path)
                else:
                    self.assertTrue(snapshot_path.is_file(), snapshot_path)
        return cases

    def _snapshot_anchors(
        self, case_dir: Path, diagnostics: tuple[compiler_diagnostics.CompilerDiagnostic, ...]
    ) -> list[dict[str, object]]:
        return [
            {
                "code": diagnostic.code.value,
                "file": diagnostic.source_path.relative_to(case_dir).as_posix(),
                "line": diagnostic.location.line,
                "column": diagnostic.location.column,
            }
            for diagnostic in diagnostics
        ]

    def _analysis_pair(self, case: dict[str, object]):
        case_path = Path(str(case["path"]))
        case_dir_rel = FIXTURE_ROOT_REL / case_path
        sources_rel = [path.relative_to(REPO_ROOT) for path in sorted((FIXTURE_ROOT / case_path).rglob("*.aidl"))]
        with chdir(REPO_ROOT):
            directory_analysis = compiler_diagnostics.load_compiler_analysis([case_dir_rel])
            reversed_analysis = compiler_diagnostics.load_compiler_analysis(list(reversed(sources_rel)))
        return directory_analysis, reversed_analysis

    def _read_snapshot(self, case: dict[str, object], kind: str) -> str:
        snapshots = case["snapshots"]
        assert isinstance(snapshots, dict)
        path = FIXTURE_ROOT / str(case["path"]) / str(snapshots[kind])
        self.assertTrue(path.is_file(), f"missing {kind} snapshot for {case['id']}: {path}")
        return path.read_text(encoding="utf-8")

    def _assert_generated_snapshots(self, case: dict[str, object], files: dict[str, str]) -> None:
        snapshots = case["snapshots"]
        assert isinstance(snapshots, dict)
        root = FIXTURE_ROOT / str(case["path"]) / str(snapshots["generated"])
        expected_relpaths = {Path(path).relative_to("generated").as_posix() for path in files}
        actual_relpaths = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual_relpaths, expected_relpaths, f"missing or unexpected generated snapshots for {case['id']}")
        for generated_path, text in sorted(files.items()):
            relpath = Path(generated_path).relative_to("generated")
            snapshot_path = root / relpath
            with self.subTest(case=case["id"], kind="generated-snapshot", path=generated_path):
                self.assertEqual(snapshot_path.read_text(encoding="utf-8"), text)

    def test_manifested_projects_match_committed_snapshots(self) -> None:
        for case in self._manifest():
            case_path = Path(str(case["path"]))
            case_dir_rel = FIXTURE_ROOT_REL / case_path
            directory_analysis, reversed_analysis = self._analysis_pair(case)
            directory_diagnostics = compiler_diagnostics.compiler_diagnostics_to_json(directory_analysis.diagnostics)
            reversed_diagnostics = compiler_diagnostics.compiler_diagnostics_to_json(reversed_analysis.diagnostics)

            with self.subTest(case=case["id"], kind="diagnostics-order"):
                self.assertEqual(directory_diagnostics, reversed_diagnostics)
            with self.subTest(case=case["id"], kind="diagnostics-snapshot"):
                self.assertEqual(directory_diagnostics, self._read_snapshot(case, "diagnostics"))
            with self.subTest(case=case["id"], kind="diagnostic-anchors"):
                self.assertEqual(self._snapshot_anchors(case_dir_rel, directory_analysis.diagnostics), case["expectedDiagnostics"])

            snapshots = case["snapshots"]
            assert isinstance(snapshots, dict)
            if "ir" not in snapshots:
                continue

            directory_ir = build_canonical_ir(directory_analysis)
            reversed_ir = build_canonical_ir(reversed_analysis)
            directory_ir_text = canonical_ir_json_text(directory_ir)
            reversed_ir_text = canonical_ir_json_text(reversed_ir)
            with self.subTest(case=case["id"], kind="ir-order"):
                self.assertEqual(directory_ir_text, reversed_ir_text)
            with self.subTest(case=case["id"], kind="ir-snapshot"):
                self.assertEqual(directory_ir_text, self._read_snapshot(case, "ir"))

            if "plan" in snapshots:
                directory_plan_text = canonical_plan_json_text(build_plan(directory_ir))
                reversed_plan_text = canonical_plan_json_text(build_plan(reversed_ir))
                with self.subTest(case=case["id"], kind="plan-order"):
                    self.assertEqual(directory_plan_text, reversed_plan_text)
                with self.subTest(case=case["id"], kind="plan-snapshot"):
                    self.assertEqual(directory_plan_text, self._read_snapshot(case, "plan"))

            if "generated" in snapshots:
                directory_generated = generate_m4_files(directory_ir)
                reversed_generated = generate_m4_files(reversed_ir)
                with self.subTest(case=case["id"], kind="generated-order"):
                    self.assertEqual(directory_generated, reversed_generated)
                self._assert_generated_snapshots(case, directory_generated)


if __name__ == "__main__":
    unittest.main()