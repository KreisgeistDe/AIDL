from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


EXIT_PASS = 0
EXIT_INPUT_ERROR = 1
EXIT_REVIEW = 2
EXIT_FAIL = 3
EXIT_INTERNAL_ERROR = 70

_DECISION_RANK = {"pass": 0, "review": 1, "fail": 2}
_CLASS_DECISION = {
    "safe": "pass",
    "conditional": "review",
    "migration-required": "review",
    "breaking": "fail",
}


class CompatibilityCiError(ValueError):
    """Raised when authoritative M7 output violates the CI policy contract."""


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def resolve_baseline_ref(
    event_name: str,
    *,
    pull_request_base_sha: str = "",
    push_before_sha: str = "",
    head_sha: str = "",
) -> str:
    if event_name == "pull_request":
        candidate = pull_request_base_sha.strip()
        if not candidate:
            raise CompatibilityCiError("pull_request event requires the pull request base SHA")
        return candidate
    if event_name == "push":
        candidate = push_before_sha.strip()
        if not candidate or set(candidate) == {"0"}:
            raise CompatibilityCiError("push event requires a non-zero previous SHA")
        if head_sha and candidate == head_sha.strip():
            raise CompatibilityCiError("push baseline must differ from the pushed head SHA")
        return candidate
    raise CompatibilityCiError(f"unsupported CI event: {event_name}")


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise CompatibilityCiError(f"{name} must be a JSON array")
    return value


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CompatibilityCiError(f"{name} must be a JSON object")
    return value


def evaluate_authoritative_m7(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("command") != "diff":
        raise CompatibilityCiError("input must be an aidl diff JSON envelope")
    if payload.get("ok") is not True:
        error = payload.get("error")
        return {
            "schemaVersion": 1,
            "status": "error",
            "decision": None,
            "exitCode": EXIT_INPUT_ERROR,
            "error": error if isinstance(error, Mapping) else {"kind": "diffInput", "message": "aidl diff failed"},
            "changes": [],
            "classifications": [],
            "guidance": [],
            "summary": {"safe": 0, "conditional": 0, "migration-required": 0, "breaking": 0},
            "items": [],
        }

    result = _require_mapping(payload.get("result"), "result")
    changes = _require_list(result.get("changes"), "result.changes")
    classifications = _require_list(result.get("classifications"), "result.classifications")
    guidance = _require_list(result.get("guidance"), "result.guidance")
    if not (len(changes) == len(classifications) == len(guidance)):
        raise CompatibilityCiError("changes, classifications, and guidance counts must match")

    summary = {"safe": 0, "conditional": 0, "migration-required": 0, "breaking": 0}
    items: list[dict[str, Any]] = []
    aggregate = "pass"

    for index, (change_raw, classification_raw, guidance_raw) in enumerate(
        zip(changes, classifications, guidance, strict=True)
    ):
        change = _require_mapping(change_raw, f"changes[{index}]")
        classification = _require_mapping(classification_raw, f"classifications[{index}]")
        migration = _require_mapping(guidance_raw, f"guidance[{index}]")

        kind = change.get("kind")
        path = change.get("path")
        if classification.get("kind") != kind or classification.get("path") != path:
            raise CompatibilityCiError(f"classification {index} does not reference the same authoritative change")
        if migration.get("kind") != kind or migration.get("path") != path:
            raise CompatibilityCiError(f"guidance {index} does not reference the same authoritative change")

        class_name = classification.get("classification")
        if class_name not in _CLASS_DECISION:
            raise CompatibilityCiError(f"unsupported compatibility class at index {index}: {class_name!r}")
        if migration.get("classification") != class_name:
            raise CompatibilityCiError(f"guidance {index} classification does not match classification output")
        if migration.get("classificationRule") != classification.get("rule"):
            raise CompatibilityCiError(f"guidance {index} rule does not match classification output")

        phases = _require_list(migration.get("phases"), f"guidance[{index}].phases")
        preconditions = _require_list(migration.get("preconditions"), f"guidance[{index}].preconditions")
        if class_name == "safe" and (phases or preconditions):
            raise CompatibilityCiError("safe guidance must not contain rollout phases or preconditions")
        if class_name == "conditional" and phases:
            raise CompatibilityCiError("conditional guidance must not contain rollout phases")
        if class_name == "breaking" and phases:
            raise CompatibilityCiError("breaking guidance must not contain rollout phases")

        decision = _CLASS_DECISION[class_name]
        summary[class_name] += 1
        if _DECISION_RANK[decision] > _DECISION_RANK[aggregate]:
            aggregate = decision
        items.append(
            {
                "index": index,
                "kind": kind,
                "path": path,
                "classification": class_name,
                "rule": classification.get("rule"),
                "decision": decision,
                "guidanceState": {
                    "phaseCount": len(phases),
                    "preconditionCount": len(preconditions),
                },
            }
        )

    exit_code = {"pass": EXIT_PASS, "review": EXIT_REVIEW, "fail": EXIT_FAIL}[aggregate]
    return {
        "schemaVersion": 1,
        "status": "complete",
        "decision": aggregate,
        "exitCode": exit_code,
        "changes": changes,
        "classifications": classifications,
        "guidance": guidance,
        "summary": summary,
        "items": items,
    }


def aggregate_reports(target_reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    aggregate = "pass"
    exit_code = EXIT_PASS
    for report in target_reports:
        if report.get("status") == "error":
            return {
                "schemaVersion": 1,
                "status": "error",
                "decision": None,
                "exitCode": int(report.get("exitCode", EXIT_INPUT_ERROR)),
                "targets": list(target_reports),
            }
        decision = report.get("decision")
        if decision not in _DECISION_RANK:
            raise CompatibilityCiError(f"target report has invalid decision: {decision!r}")
        if _DECISION_RANK[decision] > _DECISION_RANK[aggregate]:
            aggregate = decision
            exit_code = int(report["exitCode"])
    return {
        "schemaVersion": 1,
        "status": "complete",
        "decision": aggregate,
        "exitCode": exit_code,
        "targets": list(target_reports),
    }


def _load_targets(config_path: Path) -> list[dict[str, str]]:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping) or raw.get("version") != 1:
        raise CompatibilityCiError("compatibility target config must be version 1")
    targets = _require_list(raw.get("targets"), "targets")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, target_raw in enumerate(targets):
        target = _require_mapping(target_raw, f"targets[{index}]")
        target_id = target.get("id")
        path = target.get("path")
        if not isinstance(target_id, str) or not target_id:
            raise CompatibilityCiError(f"targets[{index}].id must be a non-empty string")
        if target_id in seen:
            raise CompatibilityCiError(f"duplicate target id: {target_id}")
        if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
            raise CompatibilityCiError(f"targets[{index}].path must be a repository-relative path")
        seen.add(target_id)
        normalized.append({"id": target_id, "path": path})
    return normalized


def _run_authoritative_diff(old_path: Path, new_path: Path) -> tuple[int, Mapping[str, Any]]:
    command = [
        sys.executable,
        "-m",
        "tools.aidl_cli",
        "diff",
        "--old",
        str(old_path),
        "--new",
        str(new_path),
        "--format",
        "json",
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CompatibilityCiError(
            f"aidl diff did not emit a JSON envelope for {old_path} -> {new_path}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise CompatibilityCiError("aidl diff JSON envelope must be an object")
    return completed.returncode, payload


def run_targets(baseline_root: Path, current_root: Path, config_path: Path) -> dict[str, Any]:
    target_reports: list[dict[str, Any]] = []
    for target in _load_targets(config_path):
        old_path = baseline_root / target["path"]
        new_path = current_root / target["path"]
        returncode, payload = _run_authoritative_diff(old_path, new_path)
        report = evaluate_authoritative_m7(payload)
        report = {"id": target["id"], "path": target["path"], "producerExitCode": returncode, **report}
        if report["status"] == "complete" and returncode != 0:
            raise CompatibilityCiError(
                f"aidl diff returned {returncode} despite a successful JSON envelope for {target['id']}"
            )
        target_reports.append(report)
    return aggregate_reports(target_reports)


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.write_text(_compact(report) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate authoritative M7 compatibility output for CI")
    sub = parser.add_subparsers(dest="command", required=True)

    baseline = sub.add_parser("baseline-ref", help="resolve the comparison baseline for a CI event")
    baseline.add_argument("--event-name", required=True)
    baseline.add_argument("--pull-request-base-sha", default="")
    baseline.add_argument("--push-before-sha", default="")
    baseline.add_argument("--head-sha", default="")

    evaluate = sub.add_parser("evaluate", help="evaluate one aidl diff JSON envelope")
    evaluate.add_argument("--input", required=True, type=Path)
    evaluate.add_argument("--output", required=True, type=Path)

    run = sub.add_parser("run", help="run configured authoritative diffs and aggregate the CI decision")
    run.add_argument("--baseline-root", required=True, type=Path)
    run.add_argument("--current-root", required=True, type=Path)
    run.add_argument("--config", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "baseline-ref":
            sys.stdout.write(
                resolve_baseline_ref(
                    args.event_name,
                    pull_request_base_sha=args.pull_request_base_sha,
                    push_before_sha=args.push_before_sha,
                    head_sha=args.head_sha,
                )
                + "\n"
            )
            return EXIT_PASS
        if args.command == "evaluate":
            payload = json.loads(args.input.read_text(encoding="utf-8"))
            report = evaluate_authoritative_m7(_require_mapping(payload, "input"))
            _write_report(args.output, report)
            return int(report["exitCode"])
        if args.command == "run":
            report = run_targets(args.baseline_root, args.current_root, args.config)
            _write_report(args.output, report)
            return int(report["exitCode"])
        raise AssertionError("unreachable")
    except (CompatibilityCiError, OSError, json.JSONDecodeError) as exc:
        report = {
            "schemaVersion": 1,
            "status": "error",
            "decision": None,
            "exitCode": EXIT_INTERNAL_ERROR,
            "error": {"kind": "policyInvariant", "message": str(exc)},
        }
        output = getattr(args, "output", None)
        if isinstance(output, Path):
            _write_report(output, report)
        else:
            sys.stderr.write(f"aidl compatibility ci: {exc}\n")
        return EXIT_INTERNAL_ERROR
    except Exception as exc:
        report = {
            "schemaVersion": 1,
            "status": "error",
            "decision": None,
            "exitCode": EXIT_INTERNAL_ERROR,
            "error": {"kind": "internal", "message": f"{type(exc).__name__}: {exc}"},
        }
        output = getattr(args, "output", None)
        if isinstance(output, Path):
            _write_report(output, report)
        else:
            sys.stderr.write(f"aidl compatibility ci: internal error: {type(exc).__name__}: {exc}\n")
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
