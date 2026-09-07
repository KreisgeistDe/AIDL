from __future__ import annotations

import copy
import unittest

from tools.conformance_manifest import ROOT, load_core_matrix
from tools.core_executable_evidence import load_evidence, violations


class CoreExecutableEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.core = load_core_matrix(ROOT)
        self.evidence = load_evidence(ROOT)

    def test_repository_executable_evidence_is_valid(self) -> None:
        self.assertEqual((), violations(self.evidence, self.core, root=ROOT))

    def test_implemented_cell_requires_linked_test_evidence(self) -> None:
        candidate = copy.deepcopy(self.evidence)
        del candidate["evidence"]["parse-core"]
        errors = violations(candidate, self.core, root=ROOT)
        self.assertTrue(
            any("decl.alias/parse" in error and "lacks linked executable test evidence" in error for error in errors),
            errors,
        )

    def test_documentation_only_matrix_refs_do_not_need_fake_execution(self) -> None:
        candidate = copy.deepcopy(self.core)
        row = next(item for item in candidate["features"] if item["id"] == "rule.consumer.at-least-once")
        self.assertEqual("not-applicable", row["layerStatus"]["parse"])
        self.assertEqual(["spec-core"], row["layerEvidence"]["parse"])
        self.assertEqual((), violations(self.evidence, candidate, root=ROOT))

    def test_partial_cells_are_not_promoted_by_evidence_registry(self) -> None:
        row = next(item for item in self.core["features"] if item["id"] == "decl.value")
        self.assertEqual("partial", row["layerStatus"]["ir"])
        self.assertIn("ir-core", self.evidence["evidence"])
        self.assertEqual((), violations(self.evidence, self.core, root=ROOT))

    def test_missing_test_path_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.evidence)
        candidate["evidence"]["ir-core"] = ["tools/test_missing_core_ir.py"]
        errors = violations(candidate, self.core, root=ROOT)
        self.assertIn("ir-core: missing executable evidence path tools/test_missing_core_ir.py", errors)

    def test_stale_registry_entry_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.evidence)
        candidate["evidence"]["ide-core"] = ["tools/test_core_typecheck.py"]
        errors = violations(candidate, self.core, root=ROOT)
        self.assertIn("executable evidence ids are not used by implemented cells: ['ide-core']", errors)


if __name__ == "__main__":
    unittest.main()
