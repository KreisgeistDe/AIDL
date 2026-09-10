from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import m16_evaluation_runner as runner


class EvaluationRunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m16-runner-test-")
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "M16 Test"],
            check=True,
        )
        (self.repo / "sample/project").mkdir(parents=True)
        (self.repo / "sample/project/base.aidl").write_text(
            "module sample.base\n", encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "-m", "base"], check=True
        )
        self.authority = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True
        ).strip()
        self._write_fake_aidl()
        self.executor = self._write_executor()
        self.path_env = str(self.bin) + os.pathsep + os.environ.get("PATH", "")

    def tearDown(self):
        self.temp.cleanup()

    def _write_executable(self, path: Path, text: str) -> Path:
        path.write_text(text, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def _write_fake_aidl(self):
        self._write_executable(
            self.bin / "aidl",
            """#!/usr/bin/env python3
import json, os, pathlib, sys
command = sys.argv[1]
root = pathlib.Path(sys.argv[2])
if os.environ.get('AIDL_FAKE_MALFORMED') == '1':
    print('not-json')
    raise SystemExit(0)
text = '\\n'.join(p.read_text(encoding='utf-8') for p in root.rglob('*.aidl'))
broken = 'BROKEN' in text
diagnostics = []
if broken:
    diagnostics = [{'phase':'parse','severity':'error','code':'AIDL-P001','message':'broken','location':{'file':'main.aidl','line':1,'column':1,'offset':0}}]
payload = {'command': command, 'diagnostics': diagnostics, 'ok': not broken}
if command == 'ir' and not broken:
    payload['result'] = {'schemaVersion': 1, 'declarations': []}
print(json.dumps(payload, sort_keys=True, separators=(',', ':')))
raise SystemExit(1 if broken else 0)
""",
        )

    def _write_executor(self) -> Path:
        return self._write_executable(
            self.root / "mock_executor.py",
            """#!/usr/bin/env python3
import json, pathlib, sys
mode = sys.argv[1] if len(sys.argv) > 1 else 'valid'
request = json.load(sys.stdin)
worktree = pathlib.Path(request['attempt']['worktreePath'])
attempt = request['attempt']['number']
source = next(iter(sorted(worktree.rglob('*.aidl'))), None)
if source is None:
    source = worktree / 'main.aidl'
    source.write_text('module generated\\\\n', encoding='utf-8')
if mode == 'retry':
    text = source.read_text(encoding='utf-8')
    if attempt == 1:
        source.write_text(text + 'BROKEN\\\\n', encoding='utf-8')
    else:
        source.write_text(text.replace('BROKEN\\\\n', '') + '// repaired\\\\n', encoding='utf-8')
elif mode == 'valid':
    source.write_text(source.read_text(encoding='utf-8') + '// changed\\\\n', encoding='utf-8')
elif mode == 'echo-source':
    pass
elif mode == 'exit':
    print('executor failure', file=sys.stderr)
    raise SystemExit(9)
identity = {
    'provider':'mock-provider',
    'model':'mock-model',
    'modelVersion':'1',
    'executor':'mock-executor',
    'executorVersion':'1',
    'executorBuild':'build-abc',
    'invocationId':'invocation-' + str(request['attempt']['number']),
}
seed = {'supported': True, 'used': request['frozenExecutionContract']['seedPolicy']['seed'], 'unavailableReason': None}
token = {'available': True, 'inputTokens': 10, 'outputTokens': 5, 'totalTokens': 15, 'unavailableReason': None}
if mode == 'unavailable':
    seed = {'supported': False, 'used': None, 'unavailableReason': 'mock executor has no seed control'}
    token = {'available': False, 'inputTokens': None, 'outputTokens': None, 'totalTokens': None, 'unavailableReason': 'mock executor has no token counters'}
raw = source.read_text(encoding='utf-8') if source.exists() else ''
response = {
    'schemaVersion': request['schemaVersion'],
    'protocolId': request['protocolId'],
    'surface': request['surface'],
    'taskId': request['task']['id'],
    'attemptNumber': attempt,
    'corpusFingerprint': request['corpusFingerprint'],
    'baselineFingerprint': request['baselineFingerprint'],
    'acceptedExecutionContract': request['frozenExecutionContract'],
    'identity': identity,
    'networkPolicy':'network disabled by mock executor',
    'seed':seed,
    'tokenCost':token,
    'rawModelOutput':raw,
    'assessment':{
        'observedSemanticFacts':['fact:ok'],
        'falseAssumptions':[],
        'invalidCombinations':[],
        'errors':[],
        'inventedSyntax':[],
        'wrongPlacement':[],
        'regressions':0,
        'unnecessaryEdits':0,
        'humanRewrite':'not-reviewed',
    },
    'retryRequested':False,
}
if mode == 'mismatch':
    response['taskId'] = 'm16-wrong'
if mode == 'missing-identity':
    response['identity'].pop('invocationId')
print(json.dumps(response, sort_keys=True, separators=(',', ':')))
""",
        )

    def _fixture(self, *, kind="emptyModule", value="eval.test"):
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
            "acceptanceChecks": list(runner.EXPECTED_ACCEPTANCE_CHECKS),
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
            "corpusId": "urn:test:corpus",
            "fingerprint": "sha256:corpus",
            "tasks": [
                {
                    "id": "m16-001",
                    "mode": "construct" if kind == "emptyModule" else "change",
                    "family": "Core",
                    "requirement": "Make the requested semantic change.",
                    "initialProject": {"kind": kind, "value": value},
                    "expectedSemanticFacts": ["fact:ok"],
                    "requiredSurfaces": ["entity"],
                }
            ],
        }
        baseline = {
            "baselineId": "urn:test:baseline",
            "fingerprint": "sha256:baseline",
            "projectBase": self.authority,
            "corpusFingerprint": corpus["fingerprint"],
            "surface": "current",
            "surfaceAuthority": {
                "kind": "accepted-project-main",
                "commit": self.authority,
                "candidateSyntaxAuthorized": False,
            },
            "executionContract": contract,
        }
        return corpus, baseline

    def _execute(self, mode="valid", *, corpus=None, baseline=None, run_id="run-1"):
        if corpus is None or baseline is None:
            corpus, baseline = self._fixture()
        output = self.root / f"{mode}-{run_id}.json"
        evidence = self.root / f"{mode}-{run_id}.evidence"
        with patch.dict(os.environ, {"PATH": self.path_env}):
            record = runner.execute_run(
                corpus=corpus,
                baseline=baseline,
                executor_argv=[sys.executable, str(self.executor), mode],
                run_id=run_id,
                output_path=output,
                evidence_root=evidence,
                repo_root=self.repo,
            )
        return record, output, evidence

    def test_protocol_compiler_plumbing_and_provenance(self):
        record, output, evidence = self._execute("valid")
        self.assertTrue(output.exists())
        attempt = record["tasks"][0]["attempts"][0]
        self.assertTrue(attempt["parseSuccess"])
        self.assertTrue(attempt["semanticValidationSuccess"])
        self.assertTrue(attempt["compileSuccess"])
        self.assertEqual(runner.PROTOCOL_ID, attempt["evidence"]["protocolId"])
        self.assertEqual("build-abc", attempt["evidence"]["identity"]["executorBuild"])
        self.assertEqual("invocation-1", attempt["evidence"]["identity"]["invocationId"])
        self.assertEqual(
            list(runner.EXPECTED_ACCEPTANCE_CHECKS),
            attempt["evidence"]["compiler"]["acceptanceChecks"],
        )
        self.assertTrue((evidence / "m16-001/attempt-1/executor-stdout.txt").exists())
        self.assertTrue((evidence / "m16-001/attempt-1/aidl-check-stdout.json").exists())

    def test_retry_uses_isolated_snapshot_and_compiler_failure(self):
        record, _, _ = self._execute("retry")
        attempts = record["tasks"][0]["attempts"]
        self.assertEqual(2, len(attempts))
        self.assertFalse(attempts[0]["parseSuccess"])
        self.assertTrue(attempts[1]["parseSuccess"])
        self.assertNotEqual(
            attempts[0]["evidence"]["worktreeAfter"],
            attempts[1]["evidence"]["worktreeAfter"],
        )

    def test_unavailable_seed_and_token_accounting_are_explicit(self):
        record, _, _ = self._execute("unavailable")
        attempt = record["tasks"][0]["attempts"][0]
        self.assertFalse(attempt["evidence"]["seed"]["supported"])
        self.assertIsNone(attempt["evidence"]["seed"]["used"])
        self.assertFalse(attempt["tokenCost"]["available"])
        self.assertIn("no token", attempt["tokenCost"]["unavailableReason"])

    def test_request_uses_exact_frozen_controls_without_temperature(self):
        record, _, _ = self._execute("valid")
        request = record["tasks"][0]["attempts"][0]["evidence"]["request"]
        self.assertEqual(32000, request["frozenExecutionContract"]["contextBudgetTokens"])
        self.assertEqual(2, request["frozenExecutionContract"]["retryLimit"])
        self.assertNotIn("temperature", request["frozenExecutionContract"])
        self.assertEqual("<task-worktree>", request["attempt"]["worktreePath"])

    def test_mismatched_task_identity_fails_closed_and_keeps_raw_evidence(self):
        corpus, baseline = self._fixture()
        output = self.root / "mismatch.json"
        evidence = self.root / "mismatch.evidence"
        with patch.dict(os.environ, {"PATH": self.path_env}):
            with self.assertRaisesRegex(runner.EvaluationRunnerError, "taskId mismatch"):
                runner.execute_run(
                    corpus=corpus,
                    baseline=baseline,
                    executor_argv=[sys.executable, str(self.executor), "mismatch"],
                    run_id="mismatch",
                    output_path=output,
                    evidence_root=evidence,
                    repo_root=self.repo,
                )
        self.assertFalse(output.exists())
        self.assertTrue((evidence / "m16-001/attempt-1/executor-stdout.txt").exists())

    def test_external_process_failure_fails_closed(self):
        corpus, baseline = self._fixture()
        with patch.dict(os.environ, {"PATH": self.path_env}):
            with self.assertRaisesRegex(runner.EvaluationRunnerError, "exited 9"):
                runner.execute_run(
                    corpus=corpus,
                    baseline=baseline,
                    executor_argv=[sys.executable, str(self.executor), "exit"],
                    run_id="exit",
                    output_path=self.root / "exit.json",
                    evidence_root=self.root / "exit.evidence",
                    repo_root=self.repo,
                )

    def test_pinned_repo_path_is_materialized_from_surface_authority(self):
        corpus, baseline = self._fixture(kind="repoPath", value="sample/project")
        (self.repo / "sample/project/base.aidl").write_text(
            "module changed.after.authority\n", encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "-m", "advance"],
            check=True,
        )
        record, _, _ = self._execute("echo-source", corpus=corpus, baseline=baseline)
        raw = record["tasks"][0]["attempts"][0]["evidence"]["rawModelOutput"]
        self.assertIn("module sample.base", raw)
        self.assertNotIn("changed.after.authority", raw)

    def test_run_record_generation_is_stable_for_same_inputs(self):
        first, _, _ = self._execute("valid", run_id="stable")
        first_path = self.root / "first-copy.json"
        first_path.write_text(json.dumps(first, sort_keys=True), encoding="utf-8")
        second, _, _ = self._execute("valid", run_id="stable")
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(first, second)

    def test_missing_factual_identity_fails_closed(self):
        corpus, baseline = self._fixture()
        with patch.dict(os.environ, {"PATH": self.path_env}):
            with self.assertRaisesRegex(runner.EvaluationRunnerError, "exact fields required"):
                runner.execute_run(
                    corpus=corpus,
                    baseline=baseline,
                    executor_argv=[sys.executable, str(self.executor), "missing-identity"],
                    run_id="missing-identity",
                    output_path=self.root / "missing-identity.json",
                    evidence_root=self.root / "missing-identity.evidence",
                    repo_root=self.repo,
                )

    def test_missing_external_command_is_rejected_before_run(self):
        with self.assertRaisesRegex(runner.EvaluationRunnerError, "command not found"):
            runner._executor_command("definitely-not-an-m16-executor-command")

    def test_malformed_compiler_json_fails_closed(self):
        corpus, baseline = self._fixture()
        with patch.dict(
            os.environ, {"PATH": self.path_env, "AIDL_FAKE_MALFORMED": "1"}
        ):
            with self.assertRaisesRegex(
                runner.EvaluationRunnerError, "malformed aidl check JSON"
            ):
                runner.execute_run(
                    corpus=corpus,
                    baseline=baseline,
                    executor_argv=[sys.executable, str(self.executor), "valid"],
                    run_id="bad-compiler",
                    output_path=self.root / "bad-compiler.json",
                    evidence_root=self.root / "bad-compiler.evidence",
                    repo_root=self.repo,
                )


if __name__ == "__main__":
    unittest.main()
