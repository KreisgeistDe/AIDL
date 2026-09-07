from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "spec" / "m9-main-protection.json"


def _load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _workflow_job_names(text: str) -> set[str]:
    return {
        match.group(1).strip().strip('"\'')
        for match in re.finditer(r"(?m)^\s{4}name:\s*(.+?)\s*$", text)
    }


def validate() -> list[str]:
    errors: list[str] = []
    contract = _load_contract()

    if contract.get("branch") != "main":
        errors.append("contract branch must be main")

    checks = contract.get("requiredPullRequestChecks")
    if not isinstance(checks, list) or not checks:
        errors.append("requiredPullRequestChecks must be a non-empty list")
        return errors

    contexts = [entry.get("context") for entry in checks if isinstance(entry, dict)]
    if len(contexts) != len(set(contexts)):
        errors.append("required check contexts must be unique")

    workflows: dict[str, str] = {}
    for entry in checks:
        if not isinstance(entry, dict):
            errors.append("required check entries must be objects")
            continue
        context = entry.get("context")
        workflow = entry.get("workflow")
        if not isinstance(context, str) or not context:
            errors.append("required check context must be a non-empty string")
            continue
        if not isinstance(workflow, str) or not workflow:
            errors.append(f"{context}: workflow must be a non-empty string")
            continue
        path = ROOT / workflow
        if not path.is_file():
            errors.append(f"{context}: workflow does not exist: {workflow}")
            continue
        text = workflows.setdefault(workflow, path.read_text(encoding="utf-8"))
        if "pull_request:" not in text or re.search(r"(?m)^\s{6}- main\s*$", text) is None:
            errors.append(f"{context}: workflow must run for pull requests targeting main")
        if context not in _workflow_job_names(text):
            errors.append(f"{context}: named job context not found in {workflow}")

    expected_rules = {
        "pull_request",
        "required_status_checks",
        "deletion",
        "non_fast_forward",
        "required_linear_history",
    }
    rules = contract.get("requiredRepositoryRules")
    if set(rules or []) != expected_rules:
        errors.append("requiredRepositoryRules must match the M9-06 rule set")

    if contract.get("allowedMergeMethods") != ["squash"]:
        errors.append("allowedMergeMethods must contain only squash")
    if contract.get("requireReviewThreadResolution") is not True:
        errors.append("requireReviewThreadResolution must be true")
    if contract.get("allowBypass") is not False:
        errors.append("allowBypass must be false")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(error)
        return 1
    print("main protection contract: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
