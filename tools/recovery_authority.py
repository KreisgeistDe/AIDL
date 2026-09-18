#!/usr/bin/env python3
"""Deterministic Recovery R2 authority-chain validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSITION = ROOT / "spec" / "core-authority-transition-v1.json"
M165 = ROOT / "roadmap" / "v1" / "milestones" / "m16.5.json"
TRANSITION_REF = "spec/core-authority-transition-v1.json"
ACTIVE_AUTHORITY = "spec/core-self-description-v1.aidl"
HISTORICAL = "historical_nonblocking"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _links_transition(value: object) -> bool:
    return isinstance(value, list) and any(
        isinstance(link, dict)
        and link.get("kind") == "path"
        and link.get("ref") == TRANSITION_REF
        for link in value
    )


def validate_authority(transition: dict, milestone: dict) -> list[str]:
    errors: list[str] = []
    active = transition.get("activeLanguageAuthority")
    if not isinstance(active, dict) or active.get("path") != ACTIVE_AUTHORITY:
        errors.append("active language authority must remain spec/core-self-description-v1.aidl")
    r2 = transition.get("recoveryR2")
    if not isinstance(r2, dict) or r2.get("roadmapMilestone") != "M16.5":
        errors.append("transition must record Recovery R2 reconciliation for M16.5")
    elif r2.get("authorityStatus") != HISTORICAL or r2.get("activeBlockingAuthority") != ACTIVE_AUTHORITY:
        errors.append("Recovery R2 must classify M16.5 historical_nonblocking behind Core authority")
    historical = transition.get("historicalAuthorities")
    if not isinstance(historical, list) or not any(
        isinstance(item, dict)
        and item.get("path") == "roadmap/v1/milestones/m16.5.json"
        and item.get("currentRole") == "historical-nonblocking-design-and-evaluation-evidence"
        and item.get("activeLanguageAuthority") is False
        for item in historical
    ):
        errors.append("M16.5 must be preserved as historical nonblocking authority evidence")
    if milestone.get("id") != "M16.5" or milestone.get("authority_status") != HISTORICAL:
        errors.append("M16.5 milestone must be historical_nonblocking")
    if not _links_transition(milestone.get("superseded_by_authority")):
        errors.append("M16.5 must point to the Core authority transition as superseding authority")
    packages = {item.get("id"): item for item in milestone.get("packages", []) if isinstance(item, dict)}
    for package_id in [f"M16.5-E{i}" for i in range(3, 10)]:
        package = packages.get(package_id)
        if not isinstance(package, dict):
            errors.append(f"missing historical package {package_id}")
            continue
        if package.get("status") not in {"excluded", "superseded"}:
            errors.append(f"{package_id} must be terminal and nonblocking")
        if package.get("authority_status") != HISTORICAL:
            errors.append(f"{package_id} must be historical_nonblocking")
        if not package.get("disposition_reason"):
            errors.append(f"{package_id} must retain an explicit disposition reason")
        if not _links_transition(package.get("superseded_by_authority")):
            errors.append(f"{package_id} must point to the Core transition as superseding authority")
    return errors


def repository_errors(root: Path = ROOT) -> list[str]:
    transition = _load(root / TRANSITION.relative_to(ROOT))
    milestone = _load(root / M165.relative_to(ROOT))
    return validate_authority(transition, milestone)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = repository_errors(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Recovery R2 authority chain: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
