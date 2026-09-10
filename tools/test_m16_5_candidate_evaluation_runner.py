from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from dataclasses import replace

from tools import m16_5_candidate_projection as projection
from tools import m16_5_e5_migration as e5
from tools import m16_evaluation_runner as current
from tools import m16_5_candidate_evaluation_runner as runner

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "fixtures/m16-5/evaluation-candidate-projection-cases.json").read_text(
        encoding="utf-8"
    )
)


def git_blob_sha(path: pathlib.Path) -> str:
    payload = path.read_bytes()
    digest = hashlib.sha1()
    digest.update(f"blob {len(payload)}\0".encode("ascii"))
    digest.update(payload)
    return digest.hexdigest()


class CandidateEvaluationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m16-candidate-runner-test-")
        self.root = pathlib.Path(self.temp.name)
        self.executor = self.root / "fake_executor.py"
        self.executor.write_text(
            """#!/usr/bin/env python3
import json, pathlib, sys
request = json.load(sys.stdin)
source = next(iter(sorted(pathlib.Path(request['attempt']['worktreePath']).rglob('*.aidl'))), None)
raw = '' if source is None else source.read_text(encoding='utf-8')
response = {
  'schemaVersion': request['schemaVersion'],
  'protocolId': request['protocolId'],
  'surface': request['surface'],
  'taskId': request['task']['id'],
  'attemptNumber': request['attempt']['number'],
  'corpusFingerprint': request['corpusFingerprint'],
  'baselineFingerprint': request['baselineFingerprint'],
  'acceptedExecutionContract': request['frozenExecutionContract'],
  'identity': {
    'provider': 'fake-provider', 'model': 'fake-model', 'modelVersion': '1',
    'executor': 'fake-executor', 'executorVersion': '1',
    'executorBuild': 'build-fixed', 'invocationId': 'invocation-fixed'
  },
  'networkPolicy': 'disabled by deterministic fake executor',
  'seed': {'supported': True, 'used': request['frozenExecutionContract']['seedPolicy']['seed'], 'unavailableReason': None},
  'tokenCost': {'available': True, 'inputTokens': 1, 'outputTokens': 1, 'totalTokens': 2, 'unavailableReason': None},
  'rawModelOutput': raw,
  'assessment': {
    'observedSemanticFacts': ['fact:ok'], 'falseAssumptions': [],
    'invalidCombinations': [], 'errors': [], 'inventedSyntax': [],
    'wrongPlacement': [], 'regressions': 0, 'unnecessaryEdits': 0,
    'humanRewrite': 'not-reviewed'
  },
  'retryRequested': False
}
print(json.dumps(response, sort_keys=True, separators=(',', ':')))
""",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def fixture():
        contract = {
            "contextBudgetTokens": 32000,
            "retryLimit": 2,
            "seedPolicy": {
                "kind": "fixed-when-supported",
                "seed": 1605008,
                "unsupportedBehavior": "record-unavailable",
            },
            "taskOrder": "ascending-task-id",
            "networkAccess": "executor-defined-but-recorded",
            "acceptanceChecks": list(current.EXPECTED_ACCEPTANCE_CHECKS),
            "recordRawFailures": True,
            "humanRewriteScale": [
                "none",
                "minor",
                "substantial",
                "rejected",
                "not-reviewed",
            ],
            "tokenCostPolicy": "record provider-reported input/output totals when available; otherwise record explicit unavailable reason",
        }
        corpus = {
            "corpusId": "urn:test:candidate-corpus",
            "fingerprint": "sha256:test-corpus",
            "tasks": [
                {
                    "id": "m16-001",
                    "mode": "construct",
                    "family": "Core",
                    "requirement": "Keep the valid module unchanged.",
                    "initialProject": {"kind": "emptyModule", "value": "eval.test"},
                    "expectedSemanticFacts": ["fact:ok"],
                    "requiredSurfaces": ["entity"],
                }
            ],
        }
        baseline = {
            "baselineId": "urn:test:before",
            "fingerprint": "sha256:test-baseline",
            "projectBase": "test-authority",
            "corpusFingerprint": corpus["fingerprint"],
            "surface": "current",
            "surfaceAuthority": {
                "kind": "accepted-project-main",
                "commit": "test-authority",
                "candidateSyntaxAuthorized": False,
            },
            "executionContract": contract,
        }
        return corpus, baseline

    def test_candidate_request_preserves_current_external_contract(self):
        corpus, baseline = self.fixture()
        task = corpus["tasks"][0]
        worktree = self.root / "worktree"
        worktree.mkdir()
        candidate = runner._external_request(task, baseline, 1, worktree)
        current_request = current._external_request(task, baseline, 1, worktree)
        self.assertEqual(candidate["surface"], "candidate")
        candidate_normalized = copy.deepcopy(candidate)
        candidate_normalized["surface"] = current.CURRENT_SURFACE
        self.assertEqual(candidate_normalized, current_request)
        self.assertEqual(candidate["protocolId"], current.PROTOCOL_ID)
        self.assertEqual(candidate["frozenExecutionContract"], baseline["executionContract"])

    def test_response_validation_is_the_frozen_contract_with_candidate_surface(self):
        corpus, baseline = self.fixture()
        request = runner._external_request(corpus["tasks"][0], baseline, 1, self.root)
        response = {
            "schemaVersion": request["schemaVersion"],
            "protocolId": request["protocolId"],
            "surface": "candidate",
            "taskId": "m16-001",
            "attemptNumber": 1,
            "corpusFingerprint": request["corpusFingerprint"],
            "baselineFingerprint": request["baselineFingerprint"],
            "acceptedExecutionContract": copy.deepcopy(request["frozenExecutionContract"]),
            "identity": {
                "provider": "p", "model": "m", "modelVersion": "1",
                "executor": "e", "executorVersion": "1",
                "executorBuild": "b", "invocationId": "i",
            },
            "networkPolicy": "disabled",
            "seed": {"supported": True, "used": 1605008, "unavailableReason": None},
            "tokenCost": {"available": False, "inputTokens": None, "outputTokens": None, "totalTokens": None, "unavailableReason": "not reported"},
            "rawModelOutput": "",
            "assessment": {
                "observedSemanticFacts": [], "falseAssumptions": [],
                "invalidCombinations": [], "errors": [], "inventedSyntax": [],
                "wrongPlacement": [], "regressions": 0, "unnecessaryEdits": 0,
                "humanRewrite": "not-reviewed",
            },
            "retryRequested": False,
        }
        validated = runner._validate_response(response, request, baseline)
        self.assertEqual(validated["identity"]["executorBuild"], "b")
        bad = copy.deepcopy(response)
        bad["surface"] = "current"
        with self.assertRaisesRegex(runner.EvaluationRunnerError, "surface mismatch"):
            runner._validate_response(bad, request, baseline)

    def test_exact_integrated_projection_identity_is_required(self):
        context = runner._projection_context()
        self.assertEqual(
            context.projection_ref.content_fingerprint,
            runner.REQUIRED_PROJECTION_FINGERPRINT,
        )
        stale = replace(
            context,
            projection_ref=replace(context.projection_ref, content_fingerprint="sha256:stale"),
        )
        original = projection.exact_context
        try:
            projection.exact_context = lambda: stale
            with self.assertRaisesRegex(runner.EvaluationRunnerError, "identity/fingerprint mismatch"):
                runner._projection_context()
        finally:
            projection.exact_context = original

    def test_candidate_initialization_uses_e5_and_preserves_repeated_order(self):
        current_source = CASES["reordered_repeated"]["current"]
        candidate = runner._candidateize_source(current_source, runner._projection_context())
        self.assertEqual(
            e5.extract_facts(candidate, source_version=e5.TARGET_VERSION),
            e5.extract_facts(current_source, source_version=e5.OLD_VERSION),
        )
        fact = e5.extract_facts(candidate, source_version=e5.TARGET_VERSION)[0]
        self.assertEqual(dict(fact.facts)["sources"], tuple(CASES["reordered_repeated"]["sources"]))

    def test_supported_candidate_output_reaches_unchanged_compiler_acceptance(self):
        candidate = self.root / "candidate-positive"
        projected = self.root / "projected-positive"
        candidate.mkdir()
        (candidate / "main.aidl").write_text(
            CASES["accepted_project"]["candidate"], encoding="utf-8"
        )
        compiler, evidence = runner._project_candidate_attempt(
            candidate, projected, runner._projection_context()
        )
        self.assertTrue(evidence["accepted"])
        self.assertTrue(compiler["parseSuccess"])
        self.assertTrue(compiler["semanticValidationSuccess"])
        self.assertTrue(compiler["compileSuccess"])
        self.assertTrue(compiler["check"]["ok"])
        self.assertTrue(compiler["ir"]["ok"])
        self.assertTrue(projected.is_dir())

    def test_missing_ambiguous_and_unmodeled_candidate_outputs_stay_unavailable(self):
        cases = (
            ("missing_fact", "incomplete-candidate-anchor"),
            ("ambiguous_fact", "ambiguous-inverse-fact"),
            ("unsupported_e3", "unsupported-candidate-construct"),
        )
        for key, reason in cases:
            with self.subTest(key=key):
                candidate = self.root / f"candidate-{key}"
                projected = self.root / f"projected-{key}"
                candidate.mkdir()
                (candidate / "main.aidl").write_text(
                    CASES["fail_closed"][key], encoding="utf-8"
                )
                compiler, evidence = runner._project_candidate_attempt(
                    candidate, projected, runner._projection_context()
                )
                self.assertFalse(evidence["accepted"])
                self.assertEqual(evidence["reason"], reason)
                self.assertFalse(compiler["parseSuccess"])
                self.assertFalse(compiler["semanticValidationSuccess"])
                self.assertFalse(compiler["compileSuccess"])
                self.assertFalse(projected.exists())

    def test_production_compiler_rejection_remains_rejection(self):
        candidate = self.root / "candidate-rejected"
        projected = self.root / "projected-rejected"
        candidate.mkdir()
        (candidate / "main.aidl").write_text(
            CASES["compiler_rejection_project"]["candidate"], encoding="utf-8"
        )
        compiler, evidence = runner._project_candidate_attempt(
            candidate, projected, runner._projection_context()
        )
        self.assertFalse(evidence["accepted"])
        self.assertEqual(evidence["reason"], "compiler-rejected")
        self.assertFalse(compiler["semanticValidationSuccess"])
        self.assertFalse(compiler["compileSuccess"])
        self.assertFalse(projected.exists())

    def test_full_adapter_with_fake_executor_keeps_protocol_and_candidate_surface(self):
        corpus, baseline = self.fixture()
        output = self.root / "candidate-run.json"
        evidence_root = self.root / "candidate-run.evidence"
        record = runner.execute_run(
            corpus=corpus,
            baseline=baseline,
            executor_argv=[sys.executable, str(self.executor)],
            run_id="candidate-fake-run",
            output_path=output,
            evidence_root=evidence_root,
            repo_root=ROOT,
        )
        self.assertTrue(output.exists())
        self.assertEqual(record["surface"], "candidate")
        self.assertEqual(record["executionContract"], baseline["executionContract"])
        self.assertEqual(record["runner"]["protocolId"], current.PROTOCOL_ID)
        self.assertEqual(
            record["runner"]["candidateProjection"]["content_fingerprint"],
            runner.REQUIRED_PROJECTION_FINGERPRINT,
        )
        attempt = record["tasks"][0]["attempts"][0]
        self.assertTrue(attempt["compileSuccess"])
        self.assertEqual(attempt["evidence"]["request"]["surface"], "candidate")
        self.assertTrue(attempt["evidence"]["candidateProjection"]["accepted"])
        self.assertTrue((evidence_root / "m16-001/attempt-1/candidate-projection.json").exists())

    def test_frozen_authority_files_are_byte_identical(self):
        expected = {
            "fixtures/m16-5/m16-agent-task-corpus.json": "c8dae3b9babf0c89bcd942a7d0c94a70dc537f82",
            "fixtures/m16-5/m16-before-baseline.json": "5ee06d6537ce5457c73bbf571fb72ca17188a2c5",
            "tools/m16_evaluation_runner.py": "692e3cf1c36c98952786472828934f62a46f30d5",
        }
        for relative, blob in expected.items():
            with self.subTest(path=relative):
                self.assertEqual(git_blob_sha(ROOT / relative), blob)

    def test_candidate_runner_has_no_second_language_authority_table(self):
        source = (ROOT / "tools/m16_5_candidate_evaluation_runner.py").read_text(encoding="utf-8")
        self.assertNotIn("ROW_IDS =", source)
        self.assertNotIn("RULES =", source)
        self.assertNotIn("expectedSemanticFacts", source)
        self.assertIn("projection.project_worktree", source)
        self.assertIn("e5.migrate", source)
        self.assertIn("current._external_request", source)
        self.assertIn("current._validate_response", source)


if __name__ == "__main__":
    unittest.main()
