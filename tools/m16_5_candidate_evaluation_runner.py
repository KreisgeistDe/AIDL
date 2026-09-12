"""M16.5 candidate-surface external-executor adapter for a later E8 run.

Evaluation-only prerequisite. This module preserves the frozen M16 external executor
protocol and run contract, but candidate work products are accepted only after the
integrated exact candidate->current projection and unchanged production compiler.
It does not invoke a provider by itself and does not execute E8.
"""
from __future__ import annotations

import argparse
import copy
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from tools import m16_5_candidate_projection as projection
from tools import m16_5_e5_migration as e5
from tools import m16_evaluation_harness as harness
from tools import m16_evaluation_runner as current

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_SURFACE = "candidate"
RUNNER_ID = "urn:aidl:evaluation:m16-candidate-runner-v1"
RUNNER_VERSION = "1"
IMPLEMENTATION_PROJECT_BASE = "411f3b375a014cedfe4d6899e996f225ee07eefb"
REQUIRED_PROJECTION_ID = "urn:aidl:evaluation:m16.5-candidate-current-projection"
REQUIRED_PROJECTION_VERSION = "1"
REQUIRED_PROJECTION_FINGERPRINT = (
    "sha256:a99667aecc90877da362f51fdf4fb7f5775b2f3ceb5a2911871f73443f52136c"
)

EvaluationRunnerError = current.EvaluationRunnerError


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvaluationRunnerError(message)


def _projection_context() -> projection.ProjectionContext:
    context = projection.exact_context()
    ref = context.projection_ref
    _require(
        (ref.projection_id, ref.semantic_version, ref.content_fingerprint)
        == (REQUIRED_PROJECTION_ID, REQUIRED_PROJECTION_VERSION, REQUIRED_PROJECTION_FINGERPRINT),
        "integrated candidate projection identity/fingerprint mismatch",
    )
    _require(
        projection.projection_ref() == ref,
        "integrated candidate projection reference is not self-consistent",
    )
    return context


def _external_request(
    task: dict[str, Any], baseline: dict[str, Any], attempt_number: int, worktree: Path
) -> dict[str, Any]:
    """Reuse the frozen external request contract, changing only the surface value."""
    request = current._external_request(task, baseline, attempt_number, worktree)
    request["surface"] = CANDIDATE_SURFACE
    return request


def _validate_response(
    response: dict[str, Any], request: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    """Delegate the exact response contract to the frozen current runner."""
    task_id = request["task"]["id"]
    attempt_number = request["attempt"]["number"]
    _require(
        response.get("surface") == CANDIDATE_SURFACE,
        f"{task_id} attempt {attempt_number}: response surface mismatch",
    )
    current_request = copy.deepcopy(request)
    current_request["surface"] = current.CURRENT_SURFACE
    current_response = copy.deepcopy(response)
    current_response["surface"] = current.CURRENT_SURFACE
    return current._validate_response(current_response, current_request, baseline)


def _migration_kwargs(source: str) -> dict[str, Any]:
    return {
        "source_version": e5.OLD_VERSION,
        "old_version": e5.OLD_VERSION,
        "target_version": e5.TARGET_VERSION,
        "source_schema_fingerprint": e5.OLD_SCHEMA_FINGERPRINT,
        "target_schema_fingerprint": e5.TARGET_SCHEMA_FINGERPRINT,
        "expected_source_fingerprint": e5.source_fingerprint(source),
    }


def _candidateize_source(source: str, context: projection.ProjectionContext) -> str:
    """Convert a frozen current initial source through exact E5 authority only."""
    try:
        candidate = e5.migrate(source, **_migration_kwargs(source)).source
        witness = projection.project_source(candidate, context=context)
        old_facts = e5.extract_facts(source, source_version=e5.OLD_VERSION)
    except (e5.MigrationError, projection.ProjectionError) as error:
        raise EvaluationRunnerError(
            f"cannot materialize exact candidate initial source: {error}"
        ) from error
    _require(
        witness.current_facts == old_facts,
        "candidate initial-source projection changed E5 semantic facts",
    )
    return candidate


def _candidateize_worktree(worktree: Path, context: projection.ProjectionContext) -> None:
    for path in sorted(item for item in worktree.rglob("*.aidl") if item.is_file()):
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise EvaluationRunnerError(
                f"{path}: candidate initial source must be UTF-8"
            ) from error
        path.write_text(_candidateize_source(source, context), encoding="utf-8")


def _projection_command_payload(command: projection.CompilerCommandEvidence) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "command": command.command,
        "ok": command.ok,
        "diagnostics": copy.deepcopy(list(command.diagnostics)),
    }
    if command.result is not None:
        payload["result"] = copy.deepcopy(command.result)
    return payload


def _compiler_from_projection(evidence: projection.CompilerEvidence) -> dict[str, Any]:
    check = _projection_command_payload(evidence.check)
    ir = _projection_command_payload(evidence.ir)
    parse_errors = [
        item
        for item in check.get("diagnostics", [])
        if isinstance(item, dict)
        and item.get("severity") == "error"
        and item.get("phase") == "parse"
    ]
    parse_success = not parse_errors
    return {
        "parseSuccess": parse_success,
        "semanticValidationSuccess": parse_success and bool(evidence.check.ok),
        "compileSuccess": bool(evidence.ir.ok),
        "diagnostics": current._diagnostic_strings(check),
        "check": check,
        "ir": ir,
        "checkExitCode": evidence.check.exit_code,
        "irExitCode": evidence.ir.exit_code,
        "checkStdoutSha256": evidence.check.stdout_sha256,
        "irStdoutSha256": evidence.ir.stdout_sha256,
    }


def _unavailable_compiler(reason: str, detail: str) -> dict[str, Any]:
    diagnostic = json.dumps(
        {
            "phase": "candidate-projection",
            "severity": "error",
            "reason": reason,
            "message": detail,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "parseSuccess": False,
        "semanticValidationSuccess": False,
        "compileSuccess": False,
        "diagnostics": [diagnostic],
        "check": None,
        "ir": None,
        "checkExitCode": None,
        "irExitCode": None,
        "checkStdoutSha256": None,
        "irStdoutSha256": None,
    }


def _project_candidate_attempt(
    candidate_worktree: Path,
    projected_root: Path,
    context: projection.ProjectionContext,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reject unsupported candidate work products without inventing compiler evidence."""
    try:
        result = projection.project_worktree(candidate_worktree, projected_root, context=context)
    except projection.ProjectionError as error:
        if error.reason == "compiler-rejected" and isinstance(
            error.evidence, projection.CompilerEvidence
        ):
            compiler = _compiler_from_projection(error.evidence)
        else:
            compiler = _unavailable_compiler(error.reason, error.detail)
        return compiler, {
            "accepted": False,
            "reason": error.reason,
            "detail": error.detail,
            "projectionRef": asdict(context.projection_ref),
        }
    compiler = _compiler_from_projection(result.compiler)
    _require(result.compiler.accepted, "candidate projection returned non-accepted result")
    return compiler, {
        "accepted": True,
        "reason": None,
        "detail": None,
        "projectionRef": asdict(result.projection_ref),
        "projectedFiles": [name for name, _ in result.files],
    }


def _attempt_record(
    validated: dict[str, Any],
    compiler: dict[str, Any],
    projection_evidence: dict[str, Any],
    patch: dict[str, int],
    source_lines: int,
    before_fingerprint: str,
    after_fingerprint: str,
    request: dict[str, Any],
    raw_stdout: str,
    raw_stderr: str,
) -> dict[str, Any]:
    record = current._attempt_record(
        validated,
        compiler,
        patch,
        source_lines,
        before_fingerprint,
        after_fingerprint,
        request,
        raw_stdout,
        raw_stderr,
    )
    record["evidence"]["candidateProjection"] = copy.deepcopy(projection_evidence)
    return record


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
    """Execute candidate-surface tasks through the frozen external protocol."""
    current._nonempty_string(run_id, "runId")
    _require(
        tuple(baseline["executionContract"].get("acceptanceChecks", []))
        == current.EXPECTED_ACCEPTANCE_CHECKS,
        "frozen acceptance checks differ from external executor protocol",
    )
    _require(
        baseline.get("surface") == current.CURRENT_SURFACE,
        "candidate runner requires the frozen current before-baseline contract",
    )
    _require(
        baseline.get("projectBase") == baseline.get("surfaceAuthority", {}).get("commit"),
        "baseline projectBase/surfaceAuthority mismatch",
    )
    _require(
        baseline.get("corpusFingerprint") == corpus.get("fingerprint"),
        "baseline/corpus fingerprint mismatch",
    )
    _require(executor_argv, "external executor command is required")
    context = _projection_context()

    evidence_root.mkdir(parents=True, exist_ok=True)
    tasks: list[dict[str, Any]] = []
    retry_limit = int(baseline["executionContract"]["retryLimit"])

    with tempfile.TemporaryDirectory(prefix="aidl-m16-candidate-eval-") as temporary:
        temp_root = Path(temporary)
        for task in corpus["tasks"]:
            task_id = task["id"]
            attempts: list[dict[str, Any]] = []
            previous_worktree: Path | None = None
            for attempt_index in range(retry_limit + 1):
                attempt_number = attempt_index + 1
                attempt_root = temp_root / task_id / f"attempt-{attempt_number}"
                if previous_worktree is None:
                    worktree = current._materialize_initial_project(
                        task, baseline, attempt_root, repo_root
                    )
                    _candidateize_worktree(worktree, context)
                else:
                    worktree = current._copy_attempt(previous_worktree, attempt_root)

                before_files = current._file_bytes(worktree)
                before_fingerprint = current._tree_fingerprint(worktree)
                request = _external_request(task, baseline, attempt_number, worktree)
                response, raw_stdout, raw_stderr = current._invoke_external(
                    executor_argv, request, evidence_root
                )
                validated = _validate_response(response, request, baseline)
                projected_root = attempt_root / "accepted-current-projection"
                compiler, projection_evidence = _project_candidate_attempt(
                    worktree, projected_root, context
                )
                current._write_evidence(
                    evidence_root,
                    task_id,
                    attempt_number,
                    "candidate-projection.json",
                    json.dumps(
                        projection_evidence,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                )

                after_files = current._file_bytes(worktree)
                after_fingerprint = current._tree_fingerprint(worktree)
                patch = current._patch_counts(before_files, after_files)
                attempt_record = _attempt_record(
                    validated,
                    compiler,
                    projection_evidence,
                    patch,
                    current._source_lines(worktree),
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
        "surface": CANDIDATE_SURFACE,
        "corpusId": corpus["corpusId"],
        "corpusFingerprint": corpus["fingerprint"],
        "baselineId": baseline["baselineId"],
        "baselineFingerprint": baseline["fingerprint"],
        "executionContract": copy.deepcopy(baseline["executionContract"]),
        "runner": {
            "id": RUNNER_ID,
            "version": RUNNER_VERSION,
            "protocolId": current.PROTOCOL_ID,
            "protocolVersion": current.PROTOCOL_VERSION,
            "implementationProjectBase": IMPLEMENTATION_PROJECT_BASE,
            "surfaceAuthorityCommit": baseline["surfaceAuthority"]["commit"],
            "executorCommand": current._command_identity(executor_argv),
            "candidateProjection": asdict(context.projection_ref),
            "candidateInputMigration": {
                "currentVersion": e5.OLD_VERSION,
                "currentFingerprint": e5.OLD_SCHEMA_FINGERPRINT,
                "candidateVersion": e5.TARGET_VERSION,
                "candidateFingerprint": e5.TARGET_SCHEMA_FINGERPRINT,
            },
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
        description=(
            "Run the frozen M16 candidate surface through the external executor "
            "protocol and exact evaluation-only projection"
        )
    )
    parser.add_argument(
        "--executor-command",
        required=True,
        help=(
            "external command; same JSON request/response contract as current runner; "
            "do not place credentials in argv"
        ),
    )
    parser.add_argument("--run-id", required=True, help="stable factual run identifier")
    parser.add_argument(
        "--output", required=True, type=Path, help="completed candidate run-record JSON path"
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="raw attempt evidence directory; defaults beside output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(arvv)
    executor_argv = current._executor_command(args.executor_command)
    corpus, baseline = harness.validate_frozen_prerequisite(ROOT)
    readiness = harness.prototype_candidate_status(corpus)
    _require(
        readiness.get("ready") is True and readiness.get("unavailableTaskCount") == 0,
        "integrated candidate readiness is not complete for the frozen corpus",
    )
    _projection_context()
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
        raise SystemExit(f"M16 candidate evaluation runner failed closed: {error}") from error
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
