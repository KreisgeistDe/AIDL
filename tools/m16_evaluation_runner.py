"""M16 external-executor bridge for the frozen current-surface evaluation.

This module is evaluation-only infrastructure. It does not call a model provider,
embed credentials, reinterpret AIDL semantics, or execute candidate/E8 comparison.
A user supplies an external command that speaks the versioned JSON protocol below;
this bridge owns isolated task worktrees, frozen-contract checks, compiler acceptance
checks, evidence retention, and assembly of a run record accepted by
``tools.m16_evaluation_harness``.
"""
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Sequence

from tools import m16_evaluation_harness as harness

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ID = "urn:aidl:evaluation:m16-external-executor-v1"
PROTOCOL_VERSION = 1
RUNNER_ID = "urn:aidl:evaluation:m16-current-runner-v1"
RUNNER_VERSION = "1"
CURRENT_SURFACE = "current"
EXPECTED_ACCEPTANCE_CHECKS = (
    "aidl check <task-worktree> --format json",
    "aidl ir <task-worktree> --format json",
)


class EvaluationRunnerError(RuntimeError):
    """Fail-closed runner/protocol error."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvaluationRunnerError(message)


def _nonempty_string(value: Any, path: str) -> str:
    _require(isinstance(value, str) and value.strip(), f"{path}: non-empty string required")
    return value


def _non_negative_int(value: Any, path: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0,
        f"{path}: non-negative integer required",
    )
    return value


def _string_array(value: Any, path: str) -> list[str]:
    _require(
        isinstance(value, list) and all(isinstance(item, str) for item in value),
        f"{path}: string array required",
    )
    return list(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_relative_path(value: str, path: str) -> Path:
    candidate = Path(value)
    _require(not candidate.is_absolute(), f"{path}: absolute paths are forbidden")
    _require(".." not in candidate.parts, f"{path}: parent traversal is forbidden")
    _require(candidate.parts, f"{path}: empty path forbidden")
    return candidate


def _file_bytes(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    if not root.exists():
        return files
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if ".git" in path.parts:
            continue
        files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def _tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for relative, payload in _file_bytes(root).items():
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(payload).digest())
    return "sha256:" + digest.hexdigest()


def _source_lines(root: Path) -> int:
    total = 0
    for path in sorted(root.rglob("*.aidl")):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            total += len(text.splitlines())
    return total


def _patch_counts(before: dict[str, bytes], after: dict[str, bytes]) -> dict[str, int]:
    touched = added = deleted = 0
    for relative in sorted(set(before) | set(after)):
        old = before.get(relative)
        new = after.get(relative)
        if old == new:
            continue
        touched += 1
        old_text = "" if old is None else old.decode("utf-8", errors="replace")
        new_text = "" if new is None else new.decode("utf-8", errors="replace")
        for line in difflib.ndiff(old_text.splitlines(), new_text.splitlines()):
            if line.startswith("+ "):
                added += 1
            elif line.startswith("- "):
                deleted += 1
    return {"filesTouched": touched, "linesAdded": added, "linesDeleted": deleted}


def _git_archive(repo_root: Path, commit: str, relative: Path, destination: Path) -> None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "archive", "--format=tar", commit, relative.as_posix()],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise EvaluationRunnerError(f"cannot execute git archive: {error}") from error
    _require(
        completed.returncode == 0,
        "cannot resolve frozen initial project from exact surface authority "
        f"{commit}: {completed.stderr.decode('utf-8', errors='replace').strip()}",
    )
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(completed.stdout), mode="r:") as archive:
            for member in archive.getmembers():
                member_path = Path(member.name)
                _require(
                    not member_path.is_absolute() and ".." not in member_path.parts,
                    f"git archive returned unsafe path {member.name!r}",
                )
            archive.extractall(destination, filter="data")
    except (tarfile.TarError, OSError) as error:
        raise EvaluationRunnerError(f"cannot extract frozen initial project: {error}") from error


def _materialize_initial_project(
    task: dict[str, Any], baseline: dict[str, Any], attempt_root: Path, repo_root: Path
) -> Path:
    initial = task["initialProject"]
    kind = initial["kind"]
    value = _nonempty_string(initial["value"], f"{task['id']}.initialProject.value")
    if kind == "repoPath":
        relative = _safe_relative_path(value, f"{task['id']}.initialProject.value")
        _git_archive(repo_root, baseline["surfaceAuthority"]["commit"], relative, attempt_root)
        worktree = attempt_root / relative
        _require(worktree.is_dir(), f"{task['id']}: archived repoPath is missing")
        return worktree
    if kind == "emptyModule":
        worktree = attempt_root / "project"
        worktree.mkdir(parents=True, exist_ok=False)
        (worktree / "main.aidl").write_text(f"module {value}\n", encoding="utf-8")
        return worktree
    raise EvaluationRunnerError(f"{task['id']}: unsupported initialProject.kind {kind!r}")


def _copy_attempt(previous: Path, attempt_root: Path) -> Path:
    worktree = attempt_root / previous.name
    shutil.copytree(previous, worktree)
    return worktree


def _recorded_request(request: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(request)
    result["attempt"]["worktreePath"] = "<task-worktree>"
    return result


def _external_request(
    task: dict[str, Any], baseline: dict[str, Any], attempt_number: int, worktree: Path
) -> dict[str, Any]:
    contract = copy.deepcopy(baseline["executionContract"])
    return {
        "schemaVersion": PROTOCOL_VERSION,
        "protocolId": PROTOCOL_ID,
        "surface": CURRENT_SURFACE,
        "task": {
            "id": task["id"],
            "mode": task["mode"],
            "family": task["family"],
            "requirement": task["requirement"],
            "initialProject": copy.deepcopy(task["initialProject"]),
        },
        "attempt": {
            "number": attempt_number,
            "maximum": int(contract["retryLimit"]) + 1,
            "worktreePath": str(worktree.resolve()),
        },
        "frozenExecutionContract": contract,
        "corpusFingerprint": baseline["corpusFingerprint"],
        "baselineFingerprint": baseline["fingerprint"],
    }


def _write_evidence(evidence_root: Path, task_id: str, attempt_number: int, name: str, content: str) -> None:
    directory = evidence_root / task_id / f"attempt-{attempt_number}"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(content, encoding="utf-8")


def _invoke_external(
    executor_argv: Sequence[str], request: dict[str, Any], evidence_root: Path
) -> tuple[dict[str, Any], str, str]:
    task_id = request["task"]["id"]
    attempt_number = request["attempt"]["number"]
    request_text = _canonical_json(request) + "\n"
    _write_evidence(
        evidence_root,
        task_id,
        attempt_number,
        "request.json",
        json.dumps(_recorded_request(request), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    try:
        completed = subprocess.run(
            list(executor_argv),
            input=request_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise EvaluationRunnerError(f"external executor invocation failed: {error}") from error
    _write_evidence(evidence_root, task_id, attempt_number, "executor-stdout.txt", completed.stdout)
    _write_evidence(evidence_root, task_id, attempt_number, "executor-stderr.txt", completed.stderr)
    _require(
        completed.returncode == 0,
        f"{task_id} attempt {attempt_number}: external executor exited {completed.returncode}",
    )
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise EvaluationRunnerError(
            f"{task_id} attempt {attempt_number}: malformed external executor JSON: {error}"
        ) from error
    _require(isinstance(response, dict), f"{task_id} attempt {attempt_number}: response must be object")
    return response, completed.stdout, completed.stderr


def _validate_token_cost(value: Any, path: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{path}: object required")
    available = value.get("available")
    _require(isinstance(available, bool), f"{path}.available: boolean required")
    if available:
        input_tokens = _non_negative_int(value.get("inputTokens"), f"{path}.inputTokens")
        output_tokens = _non_negative_int(value.get("outputTokens"), f"{path}.outputTokens")
        _require(
            value.get("totalTokens") == input_tokens + output_tokens,
            f"{path}.totalTokens must equal inputTokens + outputTokens",
        )
        _require(value.get("unavailableReason") is None, f"{path}.unavailableReason must be null")
    else:
        _require(
            value.get("inputTokens") is None
            and value.get("outputTokens") is None
            and value.get("totalTokens") is None,
            f"{path}: unavailable token totals must be null",
        )
        _nonempty_string(value.get("unavailableReason"), f"{path}.unavailableReason")
    return copy.deepcopy(value)


def _validate_identity(value: Any, path: str) -> dict[str, str]:
    _require(isinstance(value, dict), f"{path}: object required")
    required = {
        "provider",
        "model",
        "modelVersion",
        "executor",
        "executorVersion",
        "executorBuild",
        "invocationId",
    }
    _require(set(value) == required, f"{path}: exact fields required: {sorted(required)}")
    return {name: _nonempty_string(value[name], f"{path}.{name}") for name in sorted(required)}


def _validate_seed(value: Any, baseline: dict[str, Any], path: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{path}: object required")
    _require(set(value) == {"supported", "used", "unavailableReason"}, f"{path}: exact seed fields required")
    supported = value.get("supported")
    _require(isinstance(supported, bool), f"{path}.supported: boolean required")
    frozen_seed = baseline["executionContract"]["seedPolicy"]["seed"]
    if supported:
        _require(value.get("used") == frozen_seed, f"{path}.used must equal frozen seed {frozen_seed}")
        _require(value.get("unavailableReason") is None, f"{path}.unavailableReason must be null")
    else:
        _require(value.get("used") is None, f"{path}.used must be null when unsupported")
        _nonempty_string(value.get("unavailableReason"), f"{path}.unavailableReason")
    return copy.deepcopy(value)


def _validate_response(
    response: dict[str, Any], request: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    task_id = request["task"]["id"]
    attempt_number = request["attempt"]["number"]
    required = {
        "schemaVersion",
        "protocolId",
        "surface",
        "taskId",
        "attemptNumber",
        "corpusFingerprint",
        "baselineFingerprint",
        "acceptedExecutionContract",
        "identity",
        "networkPolicy",
        "seed",
        "tokenCost",
        "rawModelOutput",
        "assessment",
        "retryRequested",
    }
    _require(set(response) == required, f"{task_id} attempt {attempt_number}: response fields mismatch")
    _require(response["schemaVersion"] == PROTOCOL_VERSION, f"{task_id}: response schemaVersion mismatch")
    _require(response["protocolId"] == PROTOCOL_ID, f"{task_id}: response protocolId mismatch")
    _require(response["surface"] == CURRENT_SURFACE, f"{task_id}: response surface mismatch")
    _require(response["taskId"] == task_id, f"{task_id}: response taskId mismatch")
    _require(response["attemptNumber"] == attempt_number, f"{task_id}: response attemptNumber mismatch")
    _require(
        response["corpusFingerprint"] == request["corpusFingerprint"],
        f"{task_id}: response corpus fingerprint mismatch",
    )
    _require(
        response["baselineFingerprint"] == request["baselineFingerprint"],
        f"{task_id}: response baseline fingerprint mismatch",
    )
    _require(
        response["acceptedExecutionContract"] == baseline["executionContract"],
        f"{task_id}: external executor did not attest the exact frozen execution contract",
    )
    identity = _validate_identity(response["identity"], f"{task_id}.identity")
    network_policy = _nonempty_string(response["networkPolicy"], f"{task_id}.networkPolicy")
    seed = _validate_seed(response["seed"], baseline, f"{task_id}.seed")
    token_cost = _validate_token_cost(response["tokenCost"], f"{task_id}.tokenCost")
    raw_model_output = response["rawModelOutput"]
    _require(isinstance(raw_model_output, str), f"{task_id}.rawModelOutput: string required")
    retry_requested = response["retryRequested"]
    _require(isinstance(retry_requested, bool), f"{task_id}.retryRequested: boolean required")
    assessment = response["assessment"]
    _require(isinstance(assessment, dict), f"{task_id}.assessment: object required")
    assessment_fields = {
        "observedSemanticFacts",
        "falseAssumptions",
        "invalidCombinations",
        "errors",
        "inventedSyntax",
        "wrongPlacement",
        "regressions",
        "unnecessaryEdits",
        "humanRewrite",
    }
    _require(set(assessment) == assessment_fields, f"{task_id}.assessment: response fields mismatch")
    result = {
        "identity": identity,
        "networkPolicy": network_policy,
        "seed": seed,
        "tokenCost": token_cost,
        "rawModelOutput": raw_model_output,
        "retryRequested": retry_requested,
        "assessment": {
            "observedSemanticFacts": _string_array(
                assessment["observedSemanticFacts"], f"{task_id}.assessment.observedSemanticFacts"
            ),
            "falseAssumptions": _string_array(
                assessment["falseAssumptions"], f"{task_id}.assessment.falseAssumptions"
            ),
            "invalidCombinations": _string_array(
                assessment["invalidCombinations"], f"{task_id}.assessment.invalidCombinations"
            ),
            "errors": _string_array(assessment["errors"], f"{task_id}.assessment.errors"),
            "inventedSyntax": _string_array(
                assessment["inventedSyntax"], f"{task_id}.assessment.inventedSyntax"
            ),
            "wrongPlacement": _string_array(
                assessment["wrongPlacement"], f"{task_id}.assessment.wrongPlacement"
            ),
            "regressions": _non_negative_int(
                assessment["regressions"], f"{task_id}.assessment.regressions"
            ),
            "unnecessaryEdits": _non_negative_int(
                assessment["unnecessaryEdits"], f"{task_id}.assessment.unnecessaryEdits"
            ),
            "humanRewrite": assessment["humanRewrite"],
        },
    }
    _require(
        result["assessment"]["humanRewrite"] in harness.HUMAN_REWRITE,
        f"{task_id}.assessment.humanRewrite invalid",
    )
    return result


def _parse_compiler_payload(stdout: str, command: str, path: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise EvaluationRunnerError(f"{path}: malformed aidl {command} JSON: {error}") from error
    _require(isinstance(payload, dict), f"{path}: aidl {command} response must be object")
    _require(payload.get("command") == command, f"{path}: aidl {command} command identity mismatch")
    _require(isinstance(payload.get("ok"), bool), f"{path}: aidl {command} ok must be boolean")
    diagnostics = payload.get("diagnostics", [])
    _require(isinstance(diagnostics, list), f"{path}: aidl {command} diagnostics must be array")
    return payload


def _run_aidl(worktree: Path, command: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    argv = ["aidl", command, str(worktree), "--format", "json"]
    try:
        completed = subprocess.run(
            argv,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise EvaluationRunnerError(f"cannot execute {' '.join(argv[:2])}: {error}") from error
    payload = _parse_compiler_payload(completed.stdout, command, str(worktree))
    expected_code = 0 if payload["ok"] else 1
    _require(
        completed.returncode == expected_code,
        f"aidl {command}: exit {completed.returncode} disagrees with JSON ok={payload['ok']}",
    )
    return completed, payload


def _diagnostic_strings(payload: dict[str, Any]) -> list[str]:
    return [_canonical_json(item) for item in payload.get("diagnostics", [])]


def _compiler_evidence(
    worktree: Path, evidence_root: Path, task_id: str, attempt_number: int
) -> dict[str, Any]:
    check_process, check = _run_aidl(worktree, "check")
    ir_process, ir = _run_aidl(worktree, "ir")
    _write_evidence(
        evidence_root, task_id, attempt_number, "aidl-check-stdout.json", check_process.stdout
    )
    _write_evidence(
        evidence_root, task_id, attempt_number, "aidl-check-stderr.txt", check_process.stderr
    )
    _write_evidence(evidence_root, task_id, attempt_number, "aidl-ir-stdout.json", ir_process.stdout)
    _write_evidence(evidence_root, task_id, attempt_number, "aidl-ir-stderr.txt", ir_process.stderr)
    parse_errors = [
        item
        for item in check.get("diagnostics", [])
        if isinstance(item, dict)
        and item.get("severity") == "error"
        and item.get("phase") == "parse"
    ]
    parse_success = not parse_errors
    semantic_success = parse_success and bool(check["ok"])
    compile_success = bool(ir["ok"])
    return {
        "parseSuccess": parse_success,
        "semanticValidationSuccess": semantic_success,
        "compileSuccess": compile_success,
        "diagnostics": _diagnostic_strings(check),
        "check": check,
        "ir": ir,
        "checkExitCode": check_process.returncode,
        "irExitCode": ir_process.returncode,
        "checkStdoutSha256": _sha256_text(check_process.stdout),
        "irStdoutSha256": _sha256_text(ir_process.stdout),
    }


def _executor_command(command: str) -> list[str]:
    argv = shlex.split(command)
    _require(argv, "external executor command is required")
    executable = argv[0]
    if os.path.sep not in executable:
        _require(
            shutil.which(executable) is not None,
            f"external executor command not found: {executable}",
        )
    else:
        _require(Path(executable).is_file(), f"external executor command not found: {executable}")
    return argv


def _command_identity(argv: Sequence[str]) -> dict[str, Any]:
    return {
        "argv": list(argv),
        "fingerprint": _sha256_text(_canonical_json(list(argv))),
    }


def _attempt_record(
    validated: dict[str, Any],
    compiler: dict[str, Any],
    patch: dict[str, int],
    source_lines: int,
    before_fingerprint: str,
    after_fingerprint: str,
    request: dict[str, Any],
    raw_stdout: str,
    raw_stderr: str,
) -> dict[str, Any]:
    assessment = validated["assessment"]
    errors = list(assessment["errors"])
    return {
        "parseSuccess": compiler["parseSuccess"],
        "semanticValidationSuccess": compiler["semanticValidationSuccess"],
        "compileSuccess": compiler["compileSuccess"],
        "observedSemanticFacts": assessment["observedSemanticFacts"],
        "falseAssumptions": assessment["falseAssumptions"],
        "invalidCombinations": assessment["invalidCombinations"],
        "errors": errors,
        "inventedSyntax": assessment["inventedSyntax"],
        "wrongPlacement": assessment["wrongPlacement"],
        "diagnostics": compiler["diagnostics"],
        "sourceLines": source_lines,
        "regressions": assessment["regressions"],
        "tokenCost": validated["tokenCost"],
        "patch": {
            **patch,
            "unnecessaryEdits": assessment["unnecessaryEdits"],
        },
        "humanRewrite": assessment["humanRewrite"],
        "evidence": {
            "protocolId": PROTOCOL_ID,
            "identity": validated["identity"],
            "networkPolicy": validated["networkPolicy"],
            "seed": validated["seed"],
            "retryRequested": validated["retryRequested"],
            "rawModelOutput": validated["rawModelOutput"],
            "rawExecutorStdout": raw_stdout,
            "rawExecutorStderr": raw_stderr,
            "request": _recorded_request(request),
            "worktreeBefore": before_fingerprint,
            "worktreeAfter": after_fingerprint,
            "compiler": {
                "acceptanceChecks": list(EXPECTED_ACCEPTANCE_CHECKS),
                "check": compiler["check"],
                "ir": compiler["ir"],
                "checkExitCode": compiler["checkExitCode"],
                "irExitCode": compiler["irExitCode"],
                "checkStdoutSha256": compiler["checkStdoutSha256"],
                "irStdoutSha256": compiler["irStdoutSha256"],
            },
        },
    }


def execute_run(
    *,
    corpus: dict[str, Any],
    baseline: dict[str, Any],
    executor_argv: Sequence[str],
    run_id: str,
    output_path: Path,
    evidence_root: Path,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    _nonempty_string(run_id, "runId")
    _require(
        tuple(baseline["executionContract"].get("acceptanceChecks", []))
        == EXPECTED_ACCEPTANCE_CHECKS,
        "frozen acceptance checks differ from runner protocol",
    )
    _require(baseline.get("surface") == CURRENT_SURFACE, "runner supports current surface only")
    _require(
        baseline.get("projectBase") == baseline.get("surfaceAuthority", {}).get("commit"),
        "baseline projectBase/surfaceAuthority mismatch",
    )
    _require(
        baseline.get("corpusFingerprint") == corpus.get("fingerprint"),
        "baseline/corpus fingerprint mismatch",
    )
    _require(executor_argv, "external executor command is required")

    evidence_root.mkdir(parents=True, exist_ok=True)
    tasks: list[dict[str, Any]] = []
    retry_limit = int(baseline["executionContract"]["retryLimit"])

    with tempfile.TemporaryDirectory(prefix="aidl-m16-eval-") as temporary:
        temp_root = Path(temporary)
        for task in corpus["tasks"]:
            task_id = task["id"]
            attempts: list[dict[str, Any]] = []
            previous_worktree: Path | None = None
            for attempt_index in range(retry_limit + 1):
                attempt_number = attempt_index + 1
                attempt_root = temp_root / task_id / f"attempt-{attempt_number}"
                if previous_worktree is None:
                    worktree = _materialize_initial_project(task, baseline, attempt_root, repo_root)
                else:
                    worktree = _copy_attempt(previous_worktree, attempt_root)
                before_files = _file_bytes(worktree)
                before_fingerprint = _tree_fingerprint(worktree)
                request = _external_request(task, baseline, attempt_number, worktree)
                response, raw_stdout, raw_stderr = _invoke_external(
                    executor_argv, request, evidence_root
                )
                validated = _validate_response(response, request, baseline)
                compiler = _compiler_evidence(worktree, evidence_root, task_id, attempt_number)
                after_files = _file_bytes(worktree)
                after_fingerprint = _tree_fingerprint(worktree)
                patch = _patch_counts(before_files, after_files)
                attempt_record = _attempt_record(
                    validated,
                    compiler,
                    patch,
                    _source_lines(worktree),
                    before_fingerprint,
                    after_fingerprint,
                    request,
                    raw_stdout,
                    raw_stderr,
                )
                attempts.append(attempt_record)
                previous_worktree = worktree
                compiler_failed = not (
                    compiler["parseSuccess"]
                    and compiler["semanticValidationSuccess"]
                    and compiler["compileSuccess"]
                )
                if attempt_index < retry_limit and (
                    compiler_failed or validated["retryRequested"]
                ):
                    continue
                if attempt_index == retry_limit and validated["retryRequested"]:
                    attempt_record["errors"] = list(attempt_record["errors"]) + [
                        "external executor requested retry after frozen retry limit"
                    ]
                break
            tasks.append({"taskId": task_id, "attempts": attempts})

    record = {
        "schemaVersion": 1,
        "runId": run_id,
        "surface": CURRENT_SURFACE,
        "corpusId": corpus["corpusId"],
        "corpusFingerprint": corpus["fingerprint"],
        "baselineId": baseline["baselineId"],
        "baselineFingerprint": baseline["fingerprint"],
        "executionContract": copy.deepcopy(baseline["executionContract"]),
        "runner": {
            "id": RUNNER_ID,
            "version": RUNNER_VERSION,
            "protocolId": PROTOCOL_ID,
            "protocolVersion": PROTOCOL_VERSION,
            "implementationProjectBase": "9bf261c6867708a6fc2304eedec11891e85d904d",
            "surfaceAuthorityCommit": baseline["surfaceAuthority"]["commit"],
            "executorCommand": _command_identity(executor_argv),
        },
        "tasks": tasks,
    }
    record = harness.fingerprint_run_record(record)
    harness.validate_run_record(record, corpus, baseline)
    harness.summarize_run(record, corpus, baseline)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output_path.with_name(output_path.name + ".tmp")
    temporary_output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_output.replace(output_path)
    return record


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the frozen M16 current-surface evaluation through an external executor command"
    )
    parser.add_argument(
        "--executor-command",
        required=True,
        help="external command; JSON request on stdin, one JSON response on stdout; do not place credentials in argv",
    )
    parser.add_argument("--run-id", required=True, help="stable factual run identifier")
    parser.add_argument("--output", required=True, type=Path, help="completed run-record JSON path")
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="raw attempt evidence directory; defaults beside output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    executor_argv = _executor_command(args.executor_command)
    corpus, baseline = harness.validate_frozen_prerequisite(ROOT)
    evidence_root = args.evidence_dir or args.output.with_name(args.output.name + ".evidence")
    try:
        record = execute_run(
            corpus=corpus,
            baseline=baseline,
            executor_argv=executor_argv,
            run_id=args.run_id,
            output_path=args.output,
            evidence_root=evidence_root,
            repo_root=ROOT,
        )
    except EvaluationRunnerError as error:
        raise SystemExit(f"M16 evaluation runner failed closed: {error}") from error
    summary = harness.summarize_run(record, corpus, baseline)
    print(
        json.dumps(
            {"run": str(args.output), "fingerprint": record["fingerprint"], "summary": summary},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
