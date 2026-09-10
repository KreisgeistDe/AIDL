from __future__ import annotations

import copy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import m16_evaluation_harness as e8


class HarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.corpus = e8.load_corpus(cls.repo_root)
        cls.baseline = e8.load_baseline(cls.repo_root)

    def _all_success_record(self, *, surface: str = "current") -> dict:
        tasks = []
        for task in self.corpus["tasks"]:
            attempts = [{
                "parseSuccess": True,
                "semanticValidationSuccess": True,
                "compileSuccess": True,
                "observedSemanticFacts": list(task["expectedSemanticFacts"]),
                "falseAssumptions": [],
                "invalidCombinations": [],
                "errors": [],
                "inventedSyntax": [],
                "wrongPlacement": [],
                "diagnostics": [],
                "sourceLines": 20,
                "regressions": 0,
                "tokenCost": {
                    "available": True,
                    "inputTokens": 100,
                    "outputTokens": 40,
                    "totalTokens": 140,
                    "unavailableReason": None,
                },
                "patch": {
                    "filesTouched": 1,
                    "linesAdded": 4,
                    "linesDeleted": 1,
                    "unnecessaryEdits": 0,
                },
                "humanRewrite": "none",
            }]
            tasks.append({"taskId": task["id"], "attempts": attempts})
        record = {
            "schemaVersion": 1,
            "runId": f"test-{surface}",
            "surface": surface,
            "corpusId": self.corpus["corpusId"],
            "corpusFingerprint": self.corpus["fingerprint"],
            "baselineId": self.baseline["baselineId"],
            "baselineFingerprint": self.baseline["fingerprint"],
            "executionContract": copy.deepcopy(self.baseline["executionContract"]),
            "tasks": tasks,
        }
        return e8.fingerprint_run_record(record)

    def _stub_modules(self, *, e4_fingerprint: str = e8.E4_SCHEMA_FINGERPRINT):
        ref = types.SimpleNamespace(
            schema_id=e8.E4_SCHEMA_ID,
            semantic_version=e8.E4_SCHEMA_VERSION,
            content_fingerprint=e4_fingerprint,
        )
        e4 = types.ModuleType("tools.m16_5_e4_introspection")
        e4.build_catalog = lambda: types.SimpleNamespace(schema_ref=ref)
        e5 = types.ModuleType("tools.m16_5_e5_migration")
        e5.OLD_SCHEMA_ID = e8.E5_OLD_SCHEMA_ID
        e5.OLD_VERSION = e8.E5_OLD_VERSION
        e5.OLD_SCHEMA_FINGERPRINT = e8.E5_OLD_FINGERPRINT
        e5.TARGET_SCHEMA_ID = e8.E5_TARGET_SCHEMA_ID
        e5.TARGET_VERSION = e8.E5_TARGET_VERSION
        e5.TARGET_SCHEMA_FINGERPRINT = e8.E5_TARGET_FINGERPRINT
        return {
            "tools.m16_5_e4_introspection": e4,
            "tools.m16_5_e5_migration": e5,
        }

    def test_frozen_corpus_and_baseline_fingerprints(self):
        e8.validate_corpus(self.corpus)
        self.assertEqual(50, self.corpus["taskCount"])
        self.assertEqual(
            "sha256:e47b399c2460f576a2f68023af039412f02395de67f8204f3785bf9d7d8dfcef",
            self.corpus["fingerprint"],
        )
        self.assertEqual(
            "sha256:d5c7e9cd2003cfa970707e11d8cb130c80aac056028630aa3b7679e2790b7110",
            self.baseline["fingerprint"],
        )

    def test_corpus_task_ids_and_wording_are_surface_neutral(self):
        e8.validate_corpus(self.corpus)
        self.assertEqual(
            [f"m16-{index:03d}" for index in range(1, 51)],
            [task["id"] for task in self.corpus["tasks"]],
        )
        requirements = "\n".join(task["requirement"] for task in self.corpus["tasks"])
        for marker in e8.CANDIDATE_NEUTRALITY_PATTERNS:
            self.assertNotIn(marker.lower(), requirements.lower())

    def test_corpus_tamper_fails_closed(self):
        changed = copy.deepcopy(self.corpus)
        changed["tasks"][0]["requirement"] += " Please guess."
        with self.assertRaisesRegex(e8.EvaluationContractError, "fingerprint"):
            e8.validate_corpus(changed)

    def test_baseline_pins_equal_context_and_current_authority(self):
        self.assertEqual(e8.PROJECT_BASE, self.baseline["projectBase"])
        self.assertEqual(self.corpus["fingerprint"], self.baseline["corpusFingerprint"])
        self.assertFalse(self.baseline["surfaceAuthority"]["candidateSyntaxAuthorized"])
        self.assertEqual(2, self.baseline["executionContract"]["retryLimit"])
        self.assertEqual(32000, self.baseline["executionContract"]["contextBudgetTokens"])

    def test_all_success_run_aggregates_deterministically(self):
        record = self._all_success_record()
        first = e8.summarize_run(record, self.corpus, self.baseline)
        second = e8.summarize_run(record, self.corpus, self.baseline)
        self.assertEqual(first, second)
        self.assertEqual(50, first["raw"]["outputCorrectTasks"])
        self.assertEqual(1.0, first["rates"]["outputCorrectness"])
        self.assertEqual(1.0, first["rates"]["firstPassSuccess"])
        self.assertEqual(1.0, first["rates"]["semanticFactRecall"])
        self.assertEqual(7000, first["tokenCost"]["totalTokens"])
        self.assertEqual(0, first["raw"]["unnecessaryEdits"])
        self.assertEqual([], first["rawFailures"])

    def test_missing_fact_and_raw_failures_are_not_normalized_away(self):
        record = self._all_success_record()
        record.pop("fingerprint")
        first_task = record["tasks"][0]["attempts"][0]
        first_task["observedSemanticFacts"].pop()
        first_task["falseAssumptions"] = ["assumed unrelated declaration rename"]
        first_task["invalidCombinations"] = ["required+optional"]
        first_task["errors"] = ["compiler rejected output"]
        first_task["regressions"] = 1
        record = e8.fingerprint_run_record(record)
        summary = e8.summarize_run(record, self.corpus, self.baseline)
        self.assertEqual(49, summary["raw"]["outputCorrectTasks"])
        self.assertEqual(1, summary["raw"]["missingFacts"])
        self.assertEqual(1, summary["raw"]["falseAssumptions"])
        self.assertEqual(1, summary["raw"]["invalidCombinations"])
        self.assertEqual(1, summary["raw"]["errors"])
        self.assertEqual(1, summary["raw"]["regressions"])
        self.assertEqual("m16-001", summary["rawFailures"][0]["taskId"])

    def test_retry_and_patch_churn_are_raw_counts(self):
        record = self._all_success_record()
        record.pop("fingerprint")
        original = record["tasks"][1]["attempts"][0]
        failed = copy.deepcopy(original)
        failed["parseSuccess"] = False
        failed["compileSuccess"] = False
        failed["errors"] = ["parse failure"]
        failed["patch"]["unnecessaryEdits"] = 3
        record["tasks"][1]["attempts"] = [failed, original]
        record = e8.fingerprint_run_record(record)
        summary = e8.summarize_run(record, self.corpus, self.baseline)
        self.assertEqual(1, summary["raw"]["retries"])
        self.assertEqual(49, summary["raw"]["firstPassSuccessTasks"])
        self.assertEqual(0, summary["raw"]["unnecessaryEdits"])

    def test_unavailable_token_cost_requires_reason_and_is_counted(self):
        record = self._all_success_record()
        record.pop("fingerprint")
        cost = record["tasks"][2]["attempts"][0]["tokenCost"]
        cost.update({
            "available": False,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "unavailableReason": "executor did not expose token accounting",
        })
        record = e8.fingerprint_run_record(record)
        summary = e8.summarize_run(record, self.corpus, self.baseline)
        self.assertEqual(49, summary["tokenCost"]["availableTasks"])
        self.assertEqual(1, summary["tokenCost"]["unavailableTasks"])

    def test_retry_limit_fails_closed(self):
        record = self._all_success_record()
        record.pop("fingerprint")
        attempt = record["tasks"][0]["attempts"][0]
        record["tasks"][0]["attempts"] = [copy.deepcopy(attempt) for _ in range(4)]
        record = e8.fingerprint_run_record(record)
        with self.assertRaisesRegex(e8.EvaluationContractError, "retry limit"):
            e8.validate_run_record(record, self.corpus, self.baseline)

    def test_context_mismatch_fails_closed(self):
        record = self._all_success_record()
        record.pop("fingerprint")
        record["executionContract"]["contextBudgetTokens"] += 1
        record = e8.fingerprint_run_record(record)
        with self.assertRaisesRegex(e8.EvaluationContractError, "executionContract"):
            e8.validate_run_record(record, self.corpus, self.baseline)

    def test_run_fingerprint_tamper_fails_closed(self):
        record = self._all_success_record()
        record["tasks"][0]["attempts"][0]["sourceLines"] += 1
        with self.assertRaisesRegex(e8.EvaluationContractError, "fingerprint"):
            e8.validate_run_record(record, self.corpus, self.baseline)

    def test_candidate_status_reads_exact_prototype_identities_and_reports_gaps(self):
        with patch.dict(sys.modules, self._stub_modules()):
            status = e8.prototype_candidate_status(self.corpus)
        self.assertFalse(status["ready"])
        self.assertGreater(status["unavailableTaskCount"], 0)
        self.assertIn("m16-048", status["unavailableTasks"])
        self.assertIn("m16-029", status["unavailableTasks"])
        self.assertIn("m16-045", status["unavailableTasks"])
        self.assertEqual(e8.E4_SCHEMA_FINGERPRINT, status["e4Schema"]["fingerprint"])

    def test_candidate_status_rejects_stale_e4_tuple(self):
        with patch.dict(sys.modules, self._stub_modules(e4_fingerprint="sha256:stale")):
            with self.assertRaisesRegex(e8.EvaluationContractError, "E4 exact schema tuple"):
                e8.prototype_candidate_status(self.corpus)

    def test_compare_refuses_candidate_while_prototype_coverage_incomplete(self):
        before = self._all_success_record(surface="current")
        candidate = self._all_success_record(surface="candidate")
        with patch.dict(sys.modules, self._stub_modules()):
            with self.assertRaisesRegex(e8.EvaluationContractError, "candidate comparison unavailable"):
                e8.compare_runs(before, candidate, self.corpus, self.baseline)

    def test_human_rewrite_classification_is_machine_counted(self):
        record = self._all_success_record()
        record.pop("fingerprint")
        record["tasks"][3]["attempts"][0]["humanRewrite"] = "minor"
        record["tasks"][4]["attempts"][0]["humanRewrite"] = "substantial"
        record = e8.fingerprint_run_record(record)
        summary = e8.summarize_run(record, self.corpus, self.baseline)
        self.assertEqual(48, summary["humanRewrite"]["none"])
        self.assertEqual(1, summary["humanRewrite"]["minor"])
        self.assertEqual(1, summary["humanRewrite"]["substantial"])

    def test_integrated_prototype_status_when_present(self):
        if not (self.repo_root / "tools/m16_5_e4_introspection.py").exists():
            self.skipTest("isolated workspace does not include integrated E4/E5 modules")
        status = e8.prototype_candidate_status(self.corpus)
        self.assertFalse(status["ready"])
        self.assertEqual(e8.E4_SCHEMA_FINGERPRINT, status["e4Schema"]["fingerprint"])

    def test_full_fixture_verification_when_project_paths_present(self):
        if not (self.repo_root / "examples/petstore").exists():
            self.skipTest("isolated workspace does not include full project examples")
        corpus, baseline = e8.validate_frozen_prerequisite(self.repo_root)
        self.assertEqual(self.corpus["fingerprint"], corpus["fingerprint"])
        self.assertEqual(self.baseline["fingerprint"], baseline["fingerprint"])


if __name__ == "__main__":
    unittest.main()
