"""M16 bounded vendor-neutral agent evaluation prerequisite.

This module freezes and validates the M16 task corpus/current-surface "before"
protocol and deterministically aggregates completed run records.  It does not
invoke a model, vendor API, compiler mutation, formatter, IDE, or network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = Path("fixtures/m16-5/m16-agent-task-corpus.json")
BASELINE_PATH = Path("fixtures/m16-5/m16-before-baseline.json")
PROJECT_BASE = "a5c359b501913f7adce92792dec244add0452909"

E4_SCHEMA_ID = "urn:aidl:schema:meta:m16.5-e4-introspection"
E4_SCHEMA_VERSION = "0.1.0-e4"
E4_SCHEMA_FINGERPRINT = "sha256:1c870ed29b4621ae108a64c6fd8ffecd48e7b984d38afee393c23a33cc5da542"

E5_OLD_SCHEMA_ID = "urn:aidl:schema:language:m16.5-e5-current"
E5_OLD_VERSION = "m16.5-e5-current-v1"
E5_OLD_FINGERPRINT = "sha256:3964b3c5cf72fb67a0ef17e0ea2e7d7fb288359250e3b1e130db2c021a69f822"
E5_TARGET_SCHEMA_ID = "urn:aidl:schema:language:m16.5-e5-candidate"
E5_TARGET_VERSION = "m16.5-e5-candidate-v1"
E5_TARGET_FINGERPRINT = "sha256:c702262d2f5374d8eda54a028923d00d7d21e45d3980c62f32d472392ccc8c30"

HUMAN_REWRITE = ("none", "minor", "substantial", "rejected", "not-reviewed")
KNOWN_CANDIDATE_GAP_SURFACES = {
    "multi-source-projection": "E5 fails closed on multi-source projection fact loss.",
    "index-direction": "E3/E5 candidate index shape is not fact-complete for field direction.",
    "dead-letter-threshold": "E3/E5 candidate dead-letter shape is not fact-complete for the threshold.",
    "schedule-lease": "E3/E5 schedule-lease shape/tooling-parser coverage is incomplete.",
    "sync-outbox": "E3/E5 Sync outbox shape is not fact-complete.",
    "profileProperty": "E4 does not export concrete profile-property vocabulary.",
    "uiStatement": "E4 does not export concrete UI-statement vocabulary.",
    "testStatement": "E4 does not export concrete test-statement vocabulary.",
}
E4_DECLARATION_SURFACES = {"app", "entity", "service", "sync"}
E4_AUXILIARY_SURFACES = {"field"}
CANDIDATE_NEUTRALITY_PATTERNS = (
    "source:", "target:", "service:", "deadLetter:", "singleton:", "changes:",
)


class EvaluationContractError(ValueError):
    """Fail-closed fixture/run contract error."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvaluationContractError(f"{path}: expected a JSON object")
    return value


def _canonical_fingerprint(value: dict[str, Any]) -> str:
    unsigned = dict(value)
    unsigned.pop("fingerprint", None)
    payload = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvaluationContractError(message)


def _non_negative_int(value: Any, path: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0,
        f"{path}: expected non-negative integer",
    )
    return value


def _ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def load_corpus(root: Path = ROOT) -> dict[str, Any]:
    return _load(root / CORPUS_PATH)


def load_baseline(root: Path = ROOT) -> dict[str, Any]:
    return _load(root / BASELINE_PATH)


def validate_corpus(corpus: dict[str, Any]) -> None:
    _require(corpus.get("schemaVersion") == 1, "corpus.schemaVersion must be 1")
    _require(corpus.get("projectBase") == PROJECT_BASE, "corpus projectBase mismatch")
    _require(corpus.get("taskCount") == 50, "corpus must freeze exactly 50 tasks")
    tasks = corpus.get("tasks")
    _require(
        isinstance(tasks, list) and len(tasks) == 50,
        "corpus.tasks must contain 50 tasks",
    )
    ids = [task.get("id") for task in tasks]
    expected_ids = [f"m16-{index:03d}" for index in range(1, 51)]
    _require(
        ids == expected_ids,
        "corpus task IDs/order must be the frozen m16-001..m16-050 sequence",
    )
    for index, task in enumerate(tasks):
        path = f"corpus.tasks[{index}]"
        _require(task.get("mode") in {"construct", "change"}, f"{path}.mode invalid")
        _require(
            isinstance(task.get("family"), str) and task["family"],
            f"{path}.family required",
        )
        requirement = task.get("requirement")
        _require(
            isinstance(requirement, str) and requirement.strip(),
            f"{path}.requirement required",
        )
        lowered = requirement.lower()
        for marker in CANDIDATE_NEUTRALITY_PATTERNS:
            _require(
                marker.lower() not in lowered,
                f"{path}.requirement teaches candidate spelling {marker!r}",
            )
        initial = task.get("initialProject")
        _require(isinstance(initial, dict), f"{path}.initialProject required")
        _require(
            initial.get("kind") in {"repoPath", "emptyModule"},
            f"{path}.initialProject.kind invalid",
        )
        _require(
            isinstance(initial.get("value"), str) and initial["value"],
            f"{path}.initialProject.value required",
        )
        facts = task.get("expectedSemanticFacts")
        _require(
            isinstance(facts, list) and facts,
            f"{path}.expectedSemanticFacts required",
        )
        _require(
            all(isinstance(item, str) and item for item in facts),
            f"{path}.expectedSemanticFacts invalid",
        )
        _require(
            len(facts) == len(set(facts)),
            f"{path}.expectedSemanticFacts must be unique",
        )
        surfaces = task.get("requiredSurfaces")
        _require(
            isinstance(surfaces, list) and surfaces,
            f"{path}.requiredSurfaces required",
        )
        _require(
            all(isinstance(item, str) and item for item in surfaces),
            f"{path}.requiredSurfaces invalid",
        )
    _require(
        corpus.get("fingerprint") == _canonical_fingerprint(corpus),
        "corpus fingerprint mismatch",
    )


def validate_baseline(
    baseline: dict[str, Any],
    corpus: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(baseline.get("schemaVersion") == 1, "baseline.schemaVersion must be 1")
    _require(baseline.get("projectBase") == PROJECT_BASE, "baseline projectBase mismatch")
    _require(baseline.get("surface") == "current", "baseline surface must be current")
    _require(baseline.get("corpusId") == corpus["corpusId"], "baseline corpusId mismatch")
    _require(
        baseline.get("corpusFingerprint") == corpus["fingerprint"],
        "baseline corpus fingerprint mismatch",
    )
    authority = baseline.get("surfaceAuthority")
    _require(isinstance(authority, dict), "baseline.surfaceAuthority required")
    _require(authority.get("commit") == PROJECT_BASE, "baseline authority commit mismatch")
    _require(
        authority.get("candidateSyntaxAuthorized") is False,
        "baseline must not authorize candidate syntax",
    )
    contract = baseline.get("executionContract")
    _require(isinstance(contract, dict), "baseline.executionContract required")
    _non_negative_int(
        contract.get("contextBudgetTokens"),
        "baseline.executionContract.contextBudgetTokens",
    )
    _non_negative_int(contract.get("retryLimit"), "baseline.executionContract.retryLimit")
    seed = contract.get("seedPolicy")
    _require(
        isinstance(seed, dict) and seed.get("kind") == "fixed-when-supported",
        "baseline seed policy must be explicit fixed-when-supported",
    )
    _non_negative_int(seed.get("seed"), "baseline.executionContract.seedPolicy.seed")
    checks = contract.get("acceptanceChecks")
    _require(
        isinstance(checks, list)
        and checks
        == [
            "aidl check <task-worktree> --format json",
            "aidl ir <task-worktree> --format json",
        ],
        "baseline acceptance checks changed",
    )
    for task in corpus["tasks"]:
        initial = task["initialProject"]
        if initial["kind"] == "repoPath":
            _require(
                (root / initial["value"]).exists(),
                f"{task['id']}: pinned repoPath missing: {initial['value']}",
            )
    _require(
        baseline.get("fingerprint") == _canonical_fingerprint(baseline),
        "baseline fingerprint mismatch",
    )


def validate_frozen_prerequisite(
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    corpus = load_corpus(root)
    baseline = load_baseline(root)
    validate_corpus(corpus)
    validate_baseline(baseline, corpus, root=root)
    return corpus, baseline


def prototype_candidate_status(corpus: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return explicit E3-E7 candidate readiness without inventing missing facts."""
    if corpus is None:
        corpus = load_corpus()
        validate_corpus(corpus)

    from tools import m16_5_e4_introspection as e4
    from tools import m16_5_e5_migration as e5

    catalog = e4.build_catalog()
    ref = catalog.schema_ref
    _require(
        (ref.schema_id, ref.semantic_version, ref.content_fingerprint)
        == (E4_SCHEMA_ID, E4_SCHEMA_VERSION, E4_SCHEMA_FINGERPRINT),
        "integrated E4 exact schema tuple differs from the frozen evaluation prerequisite",
    )
    _require(
        (e5.OLD_SCHEMA_ID, e5.OLD_VERSION, e5.OLD_SCHEMA_FINGERPRINT)
        == (E5_OLD_SCHEMA_ID, E5_OLD_VERSION, E5_OLD_FINGERPRINT),
        "integrated E5 old context differs from the frozen evaluation prerequisite",
    )
    _require(
        (e5.TARGET_SCHEMA_ID, e5.TARGET_VERSION, e5.TARGET_SCHEMA_FINGERPRINT)
        == (E5_TARGET_SCHEMA_ID, E5_TARGET_VERSION, E5_TARGET_FINGERPRINT),
        "integrated E5 target context differs from the frozen evaluation prerequisite",
    )

    unavailable: dict[str, list[str]] = {}
    modeled = E4_DECLARATION_SURFACES | E4_AUXILIARY_SURFACES
    for task in corpus["tasks"]:
        reasons: list[str] = []
        for surface in task["requiredSurfaces"]:
            if surface in KNOWN_CANDIDATE_GAP_SURFACES:
                reasons.append(KNOWN_CANDIDATE_GAP_SURFACES[surface])
            elif surface not in modeled:
                reasons.append(
                    "E4 does not export complete compiler-owned construction metadata "
                    f"for surface {surface!r}."
                )
        if reasons:
            unavailable[task["id"]] = sorted(set(reasons))

    blockers = [
        "E4 introspection is representative App/Core/Backend/Sync metadata, not the complete declaration corpus.",
        "E4 concrete profile/UI/test vocabularies are not exported.",
        "E5/E3 remain fact-incomplete for multi-source projection, index direction, dead-letter threshold, schedule lease/tooling-parser coverage, and Sync outbox.",
    ]
    return {
        "ready": False,
        "e4Schema": {
            "id": ref.schema_id,
            "version": ref.semantic_version,
            "fingerprint": ref.content_fingerprint,
        },
        "e5Old": {
            "id": e5.OLD_SCHEMA_ID,
            "version": e5.OLD_VERSION,
            "fingerprint": e5.OLD_SCHEMA_FINGERPRINT,
        },
        "e5Target": {
            "id": e5.TARGET_SCHEMA_ID,
            "version": e5.TARGET_VERSION,
            "fingerprint": e5.TARGET_SCHEMA_FINGERPRINT,
        },
        "unavailableTaskCount": len(unavailable),
        "unavailableTasks": unavailable,
        "blockers": blockers,
    }


def _validate_token_cost(value: Any, path: str) -> None:
    _require(isinstance(value, dict), f"{path}: tokenCost must be object")
    available = value.get("available")
    _require(isinstance(available, bool), f"{path}.available must be boolean")
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
            f"{path}: unavailable token cost must use null numeric values",
        )
        _require(
            isinstance(value.get("unavailableReason"), str)
            and value["unavailableReason"].strip(),
            f"{path}.unavailableReason required when unavailable",
        )


def _validate_attempt(attempt: Any, path: str) -> None:
    _require(isinstance(attempt, dict), f"{path}: attempt must be object")
    for name in ("parseSuccess", "semanticValidationSuccess", "compileSuccess"):
        _require(isinstance(attempt.get(name), bool), f"{path}.{name} must be boolean")
    for name in (
        "observedSemanticFacts",
        "falseAssumptions",
        "invalidCombinations",
        "errors",
        "inventedSyntax",
        "wrongPlacement",
        "diagnostics",
    ):
        value = attempt.get(name)
        _require(
            isinstance(value, list) and all(isinstance(item, str) for item in value),
            f"{path}.{name} must be string array",
        )
    _validate_token_cost(attempt.get("tokenCost"), f"{path}.tokenCost")
    patch = attempt.get("patch")
    _require(isinstance(patch, dict), f"{path}.patch must be object")
    for name in ("filesTouched", "linesAdded", "linesDeleted", "unnecessaryEdits"):
        _non_negative_int(patch.get(name), f"{path}.patch.{name}")
    _non_negative_int(attempt.get("sourceLines"), f"{path}.sourceLines")
    _non_negative_int(attempt.get("regressions"), f"{path}.regressions")
    _require(attempt.get("humanRewrite") in HUMAN_REWRITE, f"{path}.humanRewrite invalid")


def validate_run_record(
    record: dict[str, Any],
    corpus: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    _require(record.get("schemaVersion") == 1, "run.schemaVersion must be 1")
    _require(isinstance(record.get("runId"), str) and record["runId"], "run.runId required")
    _require(record.get("surface") in {"current", "candidate"}, "run.surface invalid")
    _require(record.get("corpusId") == corpus["corpusId"], "run corpusId mismatch")
    _require(
        record.get("corpusFingerprint") == corpus["fingerprint"],
        "run corpus fingerprint mismatch",
    )
    _require(record.get("baselineId") == baseline["baselineId"], "run baselineId mismatch")
    _require(
        record.get("baselineFingerprint") == baseline["fingerprint"],
        "run baseline fingerprint mismatch",
    )
    protocol = record.get("executionContract")
    _require(
        protocol == baseline["executionContract"],
        "run executionContract must byte-semantically equal frozen before contract",
    )
    entries = record.get("tasks")
    _require(
        isinstance(entries, list) and len(entries) == len(corpus["tasks"]),
        "run.tasks must contain one result for every frozen task",
    )
    ids = [entry.get("taskId") for entry in entries]
    expected_ids = [task["id"] for task in corpus["tasks"]]
    _require(ids == expected_ids, "run task IDs/order must equal frozen corpus")
    retry_limit = baseline["executionContract"]["retryLimit"]
    for index, entry in enumerate(entries):
        path = f"run.tasks[{index}]"
        _require(isinstance(entry, dict), f"{path} must be object")
        attempts = entry.get("attempts")
        _require(
            isinstance(attempts, list) and attempts,
            f"{path}.attempts must be non-empty",
        )
        _require(
            len(attempts) <= retry_limit + 1,
            f"{path}.attempts exceeds frozen retry limit",
        )
        for attempt_index, attempt in enumerate(attempts):
            _validate_attempt(attempt, f"{path}.attempts[{attempt_index}]")
    _require(
        record.get("fingerprint") == _canonical_fingerprint(record),
        "run fingerprint mismatch",
    )


def _task_correct(task: dict[str, Any], attempt: dict[str, Any]) -> tuple[bool, list[str]]:
    observed = set(attempt["observedSemanticFacts"])
    expected = set(task["expectedSemanticFacts"])
    missing = sorted(expected - observed)
    correct = (
        attempt["parseSuccess"]
        and attempt["semanticValidationSuccess"]
        and attempt["compileSuccess"]
        and not missing
        and not attempt["falseAssumptions"]
        and not attempt["invalidCombinations"]
        and not attempt["errors"]
        and attempt["regressions"] == 0
    )
    return correct, missing


def summarize_run(
    record: dict[str, Any],
    corpus: dict[str, Any] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if corpus is None or baseline is None:
        corpus, baseline = validate_frozen_prerequisite()
    validate_run_record(record, corpus, baseline)
    total = len(corpus["tasks"])
    task_by_id = {task["id"]: task for task in corpus["tasks"]}

    output_correct = first_pass_success = first_parse = first_semantic = first_compile = 0
    missing_facts = false_assumptions = invalid_combinations = retries = errors = 0
    invented = wrong_placement = regressions = diagnostics = source_lines = 0
    files_touched = lines_added = lines_deleted = unnecessary_edits = 0
    input_tokens = output_tokens = token_available_tasks = token_unavailable_tasks = 0
    rewrite = Counter()
    raw_failures: list[dict[str, Any]] = []

    for entry in record["tasks"]:
        task = task_by_id[entry["taskId"]]
        attempts = entry["attempts"]
        first = attempts[0]
        final = attempts[-1]
        first_correct, _ = _task_correct(task, first)
        final_correct, final_missing = _task_correct(task, final)
        first_pass_success += int(first_correct)
        output_correct += int(final_correct)
        first_parse += int(first["parseSuccess"])
        first_semantic += int(first["semanticValidationSuccess"])
        first_compile += int(first["compileSuccess"])
        retries += len(attempts) - 1
        missing_facts += len(final_missing)
        false_assumptions += len(final["falseAssumptions"])
        invalid_combinations += len(final["invalidCombinations"])
        errors += len(final["errors"])
        invented += len(final["inventedSyntax"])
        wrong_placement += len(final["wrongPlacement"])
        regressions += final["regressions"]
        diagnostics += len(final["diagnostics"])
        source_lines += final["sourceLines"]
        patch = final["patch"]
        files_touched += patch["filesTouched"]
        lines_added += patch["linesAdded"]
        lines_deleted += patch["linesDeleted"]
        unnecessary_edits += patch["unnecessaryEdits"]
        rewrite[final["humanRewrite"]] += 1
        cost = final["tokenCost"]
        if cost["available"]:
            token_available_tasks += 1
            input_tokens += cost["inputTokens"]
            output_tokens += cost["outputTokens"]
        else:
            token_unavailable_tasks += 1
        if not final_correct:
            raw_failures.append(
                {
                    "taskId": entry["taskId"],
                    "missingFacts": final_missing,
                    "falseAssumptions": list(final["falseAssumptions"]),
                    "invalidCombinations": list(final["invalidCombinations"]),
                    "errors": list(final["errors"]),
                    "regressions": final["regressions"],
                }
            )

    expected_fact_count = sum(
        len(task["expectedSemanticFacts"]) for task in corpus["tasks"]
    )
    observed_expected = expected_fact_count - missing_facts
    return {
        "runId": record["runId"],
        "surface": record["surface"],
        "taskCount": total,
        "raw": {
            "outputCorrectTasks": output_correct,
            "firstPassSuccessTasks": first_pass_success,
            "firstPassParseTasks": first_parse,
            "firstPassSemanticValidationTasks": first_semantic,
            "firstPassCompileTasks": first_compile,
            "missingFacts": missing_facts,
            "falseAssumptions": false_assumptions,
            "invalidCombinations": invalid_combinations,
            "retries": retries,
            "errors": errors,
            "inventedSyntax": invented,
            "wrongPlacement": wrong_placement,
            "regressions": regressions,
            "diagnostics": diagnostics,
            "sourceLines": source_lines,
            "filesTouched": files_touched,
            "linesAdded": lines_added,
            "linesDeleted": lines_deleted,
            "unnecessaryEdits": unnecessary_edits,
            "expectedSemanticFacts": expected_fact_count,
            "recalledSemanticFacts": observed_expected,
        },
        "rates": {
            "outputCorrectness": _ratio(output_correct, total),
            "firstPassSuccess": _ratio(first_pass_success, total),
            "firstPassParse": _ratio(first_parse, total),
            "firstPassSemanticValidation": _ratio(first_semantic, total),
            "firstPassCompile": _ratio(first_compile, total),
            "inventedSyntaxTaskEventRate": _ratio(invented, total),
            "wrongPlacementTaskEventRate": _ratio(wrong_placement, total),
            "semanticFactRecall": _ratio(observed_expected, expected_fact_count),
            "diagnosticsPer100SourceLines": (
                0.0 if source_lines == 0 else diagnostics * 100.0 / source_lines
            ),
        },
        "tokenCost": {
            "availableTasks": token_available_tasks,
            "unavailableTasks": token_unavailable_tasks,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "totalTokens": input_tokens + output_tokens,
        },
        "humanRewrite": {name: rewrite.get(name, 0) for name in HUMAN_REWRITE},
        "rawFailures": raw_failures,
    }


def compare_runs(
    before: dict[str, Any],
    candidate: dict[str, Any],
    corpus: dict[str, Any] | None = None,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare like-for-like records; refuse while prototype coverage is incomplete."""
    if corpus is None or baseline is None:
        corpus, baseline = validate_frozen_prerequisite()
    validate_run_record(before, corpus, baseline)
    validate_run_record(candidate, corpus, baseline)
    _require(before["surface"] == "current", "before run must use current surface")
    _require(candidate["surface"] == "candidate", "candidate run must use candidate surface")
    status = prototype_candidate_status(corpus)
    _require(
        status["ready"],
        "candidate comparison unavailable: integrated E3-E7 prototype coverage is incomplete",
    )
    before_summary = summarize_run(before, corpus, baseline)
    candidate_summary = summarize_run(candidate, corpus, baseline)
    raw_delta = {
        key: candidate_summary["raw"][key] - before_summary["raw"][key]
        for key in before_summary["raw"]
    }
    rate_delta = {
        key: candidate_summary["rates"][key] - before_summary["rates"][key]
        for key in before_summary["rates"]
    }
    return {
        "before": before_summary,
        "candidate": candidate_summary,
        "rawDeltaCandidateMinusBefore": raw_delta,
        "rateDeltaCandidateMinusBefore": rate_delta,
        "interpretation": "raw deltas only; no preferred-language conclusion is implied",
    }


def fingerprint_run_record(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["fingerprint"] = _canonical_fingerprint(result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="M16 vendor-neutral evaluation prerequisite"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    summary = sub.add_parser("summarize")
    summary.add_argument("record", type=Path)
    compare = sub.add_parser("compare")
    compare.add_argument("before", type=Path)
    compare.add_argument("candidate", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    corpus, baseline = validate_frozen_prerequisite()
    if args.command == "verify":
        status = prototype_candidate_status(corpus)
        payload = {
            "corpusId": corpus["corpusId"],
            "corpusFingerprint": corpus["fingerprint"],
            "taskCount": corpus["taskCount"],
            "baselineId": baseline["baselineId"],
            "baselineFingerprint": baseline["fingerprint"],
            "candidateReady": status["ready"],
            "candidateUnavailableTaskCount": status["unavailableTaskCount"],
            "candidateBlockers": status["blockers"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "summarize":
        record = _load(args.record)
        print(json.dumps(summarize_run(record, corpus, baseline), indent=2, sort_keys=True))
        return 0
    before = _load(args.before)
    candidate = _load(args.candidate)
    print(json.dumps(compare_runs(before, candidate, corpus, baseline), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
