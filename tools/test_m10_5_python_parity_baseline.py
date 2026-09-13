from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.m10_5_python_parity_baseline import (
    BASELINE_BASE_COMMIT,
    CORE_AUTHORITY_BINDINGS,
    RUNNER_INPUTS,
    SEMANTIC_AUTHORITY,
    SEMANTIC_DIMENSIONS,
    assert_fingerprint,
    build_input_identity,
    build_parity_evidence,
    compare_results,
    validate_input_identity,
    validate_manifest,
)


class M105PythonParityBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.manifest = json.loads(
            (cls.root / "spec/m10-5-parity-manifest.json").read_text(encoding="utf-8")
        )

    def test_manifest_is_post_g1_current_main_python_reference(self) -> None:
        manifest = validate_manifest()
        self.assertEqual(manifest["reference_implementation"], "python")
        self.assertFalse(manifest["normative_language_source"])
        self.assertEqual(manifest["status"], "post-g1-current-main-candidate")
        self.assertEqual(manifest["baseline_base_commit"], BASELINE_BASE_COMMIT)
        self.assertEqual(manifest["semantic_authority"], SEMANTIC_AUTHORITY)
        self.assertEqual(set(manifest["core_authority_bindings"]), CORE_AUTHORITY_BINDINGS)
        self.assertEqual(manifest["runner_inputs"], ["source", "config", "profile"])
        self.assertEqual(tuple(manifest["runner_inputs"]), RUNNER_INPUTS)
        self.assertEqual(manifest["comparison_contract"]["semantic_allowlists"], [])
        self.assertEqual(
            tuple(manifest["comparison_contract"]["semantic_dimensions"]),
            SEMANTIC_DIMENSIONS,
        )

    def test_core_authority_schema_profile_and_closure_inputs_are_fingerprint_bound(self) -> None:
        evidence = build_parity_evidence()
        core_bound = {row["path"] for row in evidence["core_authority_bindings"]}
        self.assertEqual(core_bound, CORE_AUTHORITY_BINDINGS)
        bound = {row["path"] for row in evidence["normative_bindings"]}
        self.assertIn("spec/language-surface-v1.json", bound)
        self.assertIn("spec/ir.schema.json", bound)
        self.assertIn("spec/profile-registry.json", bound)
        self.assertIn("spec/m10-2-language-surface-classification.json", bound)
        self.assertIn("spec/m10-3-closure-certification.json", bound)
        self.assertEqual(evidence["semantic_authority"], SEMANTIC_AUTHORITY)
        self.assertTrue(evidence["fingerprint"].startswith("sha256:"))
        self.assertEqual(build_parity_evidence(), build_parity_evidence())

    def test_runner_input_identity_requires_exact_source_config_profile_set(self) -> None:
        identity = build_input_identity(source=b"s", config=b"c", profile=b"p")
        self.assertEqual(set(identity), {"source", "config", "profile"})
        self.assertEqual(validate_input_identity(identity), identity)

        missing = dict(identity)
        missing.pop("profile")
        with self.assertRaisesRegex(ValueError, "exactly source, config, profile"):
            validate_input_identity(missing)

        extra = dict(identity)
        extra["workspace"] = identity["source"]
        with self.assertRaisesRegex(ValueError, "exactly source, config, profile"):
            validate_input_identity(extra)

    def test_manifest_runner_input_and_authority_drift_fail_closed(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["runner_inputs"] = ["source", "profile"]
        with self.assertRaisesRegex(ValueError, "runner_inputs must be exactly"):
            validate_manifest(manifest=manifest)

        manifest = copy.deepcopy(self.manifest)
        manifest["baseline_base_commit"] = "cbe34ce18dfa696c3bcbf30b6b37af53989112d6"
        with self.assertRaisesRegex(ValueError, "post-G1 baseline base commit drift"):
            validate_manifest(manifest=manifest)

        manifest = copy.deepcopy(self.manifest)
        manifest["semantic_authority"]["revision4_role"] = "semantic-authority"
        with self.assertRaisesRegex(ValueError, "Core semantic authority boundary drift"):
            validate_manifest(manifest=manifest)

        manifest = copy.deepcopy(self.manifest)
        manifest["core_authority_bindings"].pop()
        with self.assertRaisesRegex(ValueError, "Core authority binding inventory drift"):
            validate_manifest(manifest=manifest)

    def _copy_bound_repository(self, root: Path) -> None:
        paths = {
            "spec/m10-5-parity-manifest.json",
            *self.manifest["core_authority_bindings"],
            *self.manifest["normative_bindings"],
        }
        for surface in self.manifest["parity_inventory"]:
            paths.update(surface["evidence"])
        for values in self.manifest["parity_corpus"].values():
            paths.update(values)
        for relative in paths:
            source = self.root / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def _assert_bound_file_drift_changes_fingerprint(self, relative: str) -> None:
        baseline = build_parity_evidence()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._copy_bound_repository(root)
            target = root / relative
            target.write_bytes(target.read_bytes() + b"\n")
            changed = build_parity_evidence(repo_root=root)
            self.assertNotEqual(changed["fingerprint"], baseline["fingerprint"])
            with self.assertRaisesRegex(ValueError, "parity fingerprint drift detected"):
                assert_fingerprint(baseline["fingerprint"], changed["fingerprint"])

    def test_fingerprint_fails_closed_on_core_authority_compatibility_drift(self) -> None:
        for relative in (
            "spec/core.aidl",
            "spec/core.authority.aidl",
            "spec/core.compatibility.aidl",
        ):
            with self.subTest(relative=relative):
                self._assert_bound_file_drift_changes_fingerprint(relative)

    def test_fingerprint_drift_fails_closed_when_ir_or_profile_changes(self) -> None:
        for relative in ("spec/ir.schema.json", "spec/profile-registry.json"):
            with self.subTest(relative=relative):
                self._assert_bound_file_drift_changes_fingerprint(relative)

    def test_structured_mismatch_reporting_has_no_semantic_allowlist(self) -> None:
        fingerprint = build_parity_evidence()["fingerprint"]
        identity = build_input_identity(source=b"source", config=b"{}", profile=b"core@1")
        reference = {"input_identity": identity}
        candidate = {"input_identity": identity}
        for dimension in SEMANTIC_DIMENSIONS:
            reference[dimension] = {"value": dimension}
            candidate[dimension] = {"value": dimension}
        candidate["diagnostics"] = [{"code": "AIDL-X999"}]

        result = compare_results(
            reference=reference,
            candidate=candidate,
            expected_fingerprint=fingerprint,
            actual_fingerprint=fingerprint,
        )
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["mismatches"], [
            {
                "dimension": "diagnostics",
                "kind": "semantic_mismatch",
                "reference": {"value": "diagnostics"},
                "candidate": [{"code": "AIDL-X999"}],
            }
        ])

    def test_comparison_rejects_input_identity_and_fingerprint_drift(self) -> None:
        fingerprint = build_parity_evidence()["fingerprint"]
        first = build_input_identity(source=b"same", config=b"{}", profile=b"core@1")
        second = build_input_identity(source=b"different", config=b"{}", profile=b"core@1")
        reference = {"input_identity": first}
        candidate = {"input_identity": second}
        for dimension in SEMANTIC_DIMENSIONS:
            reference[dimension] = []
            candidate[dimension] = []

        with self.assertRaisesRegex(ValueError, "runner input identity drift"):
            compare_results(
                reference=reference,
                candidate=candidate,
                expected_fingerprint=fingerprint,
                actual_fingerprint=fingerprint,
            )
        with self.assertRaisesRegex(ValueError, "parity fingerprint drift"):
            compare_results(
                reference=reference,
                candidate=reference,
                expected_fingerprint=fingerprint,
                actual_fingerprint="sha256:" + "0" * 64,
            )

    def test_todo_records_integrated_gate01_and_dependency_ready_m10_5_02(self) -> None:
        todo = (self.root / "TODO.md").read_text(encoding="utf-8")
        self.assertIn("PR #77 remains already-merged historical/provisional evidence", todo)
        self.assertIn("- [x] **M10.5-01 — Refresh the Python parity baseline", todo)
        self.assertIn("9228f94302c1fbbc6cd5fc0b5fc7af9231071d76", todo)
        self.assertIn("fcfc3fc92e6577270dbf89be22c4ddfac5c187a9", todo)
        self.assertIn("PR #95", todo)
        self.assertIn("2a26b1deff1baa5504e5e714222e8726181c7d5a", todo)
        self.assertIn("3fa5c969338d1f0dc6b9bc573e70c7004f53aceb", todo)
        self.assertIn("M10.5-02 and later Kotlin work", todo)
        self.assertIn("Dependency-ready next roadmap action", todo)
        self.assertNotIn("blocked until this durable-state correction", todo.lower())
        self.assertNotIn("Current post-G1 candidate", todo)
        self.assertNotIn("requires fresh independent validation and integration before Gate 01", todo)


if __name__ == "__main__":
    unittest.main()
