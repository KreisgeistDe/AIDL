from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.ir_compatibility_ci import (
    EXIT_FAIL,
    EXIT_INPUT_ERROR,
    EXIT_PASS,
    EXIT_REVIEW,
    CompatibilityCiError,
    aggregate_reports,
    evaluate_authoritative_m7,
    resolve_baseline_ref,
    run_targets,
)


def _entry(classification: str, *, phases=None, preconditions=None):
    change = {"kind": "changed", "path": "/declarations/entity:example.User/fields/0/required", "oldValue": False, "newValue": True}
    classified = {"kind": change["kind"], "path": change["path"], "classification": classification, "rule": f"test.{classification}", "reason": f"{classification} reason"}
    guidance = {"kind": change["kind"], "path": change["path"], "classification": classification, "classificationRule": classified["rule"], "phases": [] if phases is None else phases, "preconditions": [] if preconditions is None else preconditions, "note": "test guidance"}
    return change, classified, guidance


def _payload(*classes: str):
    changes, classifications, guidance = [], [], []
    for classification in classes:
        phases, preconditions = [], []
        if classification == "conditional":
            preconditions = ["review"]
        elif classification == "migration-required":
            phases = [{"phase": "expand", "action": "expand", "evidence": "test"}]
        elif classification == "breaking":
            preconditions = ["approval"]
        change, classified, migration = _entry(classification, phases=phases, preconditions=preconditions)
        changes.append(change)
        classifications.append(classified)
        guidance.append(migration)
    return {"command": "diff", "diagnostics": [], "ok": True, "result": {"changes": changes, "classifications": classifications, "guidance": guidance}}


class CompatibilityCiPolicyTests(unittest.TestCase):
    def test_no_diff_is_pass(self):
        report = evaluate_authoritative_m7(_payload())
        self.assertEqual("pass", report["decision"])
        self.assertEqual(EXIT_PASS, report["exitCode"])
        self.assertEqual([], report["changes"])

    def test_safe_is_pass_and_raw_m7_output_is_preserved(self):
        payload = _payload("safe")
        report = evaluate_authoritative_m7(payload)
        self.assertEqual("pass", report["decision"])
        self.assertEqual(payload["result"]["changes"], report["changes"])
        self.assertEqual(payload["result"]["classifications"], report["classifications"])
        self.assertEqual(payload["result"]["guidance"], report["guidance"])

    def test_conditional_is_review(self):
        report = evaluate_authoritative_m7(_payload("conditional"))
        self.assertEqual("review", report["decision"])
        self.assertEqual(EXIT_REVIEW, report["exitCode"])

    def test_migration_required_is_review(self):
        report = evaluate_authoritative_m7(_payload("migration-required"))
        self.assertEqual("review", report["decision"])
        self.assertEqual(EXIT_REVIEW, report["exitCode"])

    def test_breaking_is_fail(self):
        report = evaluate_authoritative_m7(_payload("breaking"))
        self.assertEqual("fail", report["decision"])
        self.assertEqual(EXIT_FAIL, report["exitCode"])

    def test_strictest_decision_wins(self):
        report = evaluate_authoritative_m7(_payload("safe", "conditional", "migration-required", "breaking"))
        self.assertEqual("fail", report["decision"])
        self.assertEqual({"safe": 1, "conditional": 1, "migration-required": 1, "breaking": 1}, report["summary"])

    def test_failed_diff_is_tool_error_not_compatibility_failure(self):
        payload = {"command": "diff", "diagnostics": [{"code": "AIDL001"}], "ok": False, "error": {"kind": "compiler", "message": "old project has compiler errors", "side": "old"}}
        report = evaluate_authoritative_m7(payload)
        self.assertEqual("error", report["status"])
        self.assertIsNone(report["decision"])
        self.assertEqual(EXIT_INPUT_ERROR, report["exitCode"])
        self.assertEqual("compiler", report["error"]["kind"])

    def test_safe_guidance_cannot_hide_preconditions(self):
        payload = _payload("safe")
        payload["result"]["guidance"][0]["preconditions"] = ["unexpected"]
        with self.assertRaisesRegex(CompatibilityCiError, "safe guidance"):
            evaluate_authoritative_m7(payload)

    def test_classification_and_guidance_must_reference_same_change(self):
        payload = _payload("conditional")
        payload["result"]["guidance"][0]["path"] = "/different"
        with self.assertRaisesRegex(CompatibilityCiError, "same authoritative change"):
            evaluate_authoritative_m7(payload)

    def test_baseline_ref_uses_actual_pull_request_base(self):
        self.assertEqual("base-sha", resolve_baseline_ref("pull_request", pull_request_base_sha="base-sha", push_before_sha="ignored", head_sha="head-sha"))

    def test_baseline_ref_uses_previous_sha_for_main_push(self):
        self.assertEqual("before-sha", resolve_baseline_ref("push", push_before_sha="before-sha", head_sha="head-sha"))

    def test_push_cannot_diff_head_against_itself(self):
        with self.assertRaisesRegex(CompatibilityCiError, "must differ"):
            resolve_baseline_ref("push", push_before_sha="same-sha", head_sha="same-sha")

    def test_output_is_deterministic(self):
        first = evaluate_authoritative_m7(_payload("conditional", "safe"))
        second = evaluate_authoritative_m7(_payload("conditional", "safe"))
        self.assertEqual(json.dumps(first, ensure_ascii=False, separators=(",", ":"), sort_keys=True), json.dumps(second, ensure_ascii=False, separators=(",", ":"), sort_keys=True))

    def test_aggregate_reports_preserves_target_order_and_strictest_decision(self):
        reports = [{"id": "a", "status": "complete", "decision": "pass", "exitCode": EXIT_PASS}, {"id": "b", "status": "complete", "decision": "review", "exitCode": EXIT_REVIEW}]
        aggregate = aggregate_reports(reports)
        self.assertEqual("review", aggregate["decision"])
        self.assertEqual(["a", "b"], [item["id"] for item in aggregate["targets"]])

    def test_run_targets_consumes_authoritative_diff_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "targets.json"
            config.write_text(json.dumps({"version": 1, "targets": [{"id": "petstore", "path": "examples/petstore/m4-app/app.aidl"}]}), encoding="utf-8")
            with patch("tools.ir_compatibility_ci._run_authoritative_diff", return_value=(0, _payload("safe"))) as run_diff:
                report = run_targets(root / "base", root / "head", config)
            self.assertEqual("pass", report["decision"])
            old_path, new_path = run_diff.call_args.args
            self.assertEqual(root / "base" / "examples/petstore/m4-app/app.aidl", old_path)
            self.assertEqual(root / "head" / "examples/petstore/m4-app/app.aidl", new_path)


if __name__ == "__main__":
    unittest.main()
