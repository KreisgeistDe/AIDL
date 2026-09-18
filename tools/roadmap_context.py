from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from tools import roadmap
except ModuleNotFoundError:  # direct `python3 tools/roadmap_context.py`
    import roadmap  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_VERSION = "aidl.roadmap-context/v1"
DEFAULT_LIMIT = 16
MAX_LIMIT = 64


def _bounded(values: list[Any], limit: int) -> dict[str, Any]:
    return {"items": values[:limit], "total": len(values), "truncated": len(values) > limit}


def _links(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((dict(value) for value in values), key=lambda value: (value.get("kind", ""), value.get("ref", ""), value.get("note", "")))


def _authority(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "authority_status": value.get("authority_status"),
        "supersedes": list(value.get("supersedes", [])),
        "superseded_by": list(value.get("superseded_by", [])),
        "superseded_by_authority": _links(value.get("superseded_by_authority", [])),
    }


def _package_row(package: dict[str, Any], packages: dict[str, dict[str, Any]], owners: dict[str, str]) -> dict[str, Any]:
    blocked_by = [dep for dep in package["depends_on"] if packages[dep]["status"] not in roadmap.TERMINAL_SATISFIED]
    if package["status"] in roadmap.TERMINAL_SATISFIED:
        state = "terminal"
    elif blocked_by:
        state = "blocked"
    elif package["status"] == "in_progress":
        state = "in_progress"
    else:
        state = "ready"
    return {
        "id": package["id"],
        "kind": "package",
        "milestone": owners[package["id"]],
        "title": package["title"],
        "status": package["status"],
        "state": state,
        "priority": package["priority"],
        "depends_on": list(package["depends_on"]),
        "blocked_by": blocked_by,
    }


def _ranks(milestones: list[dict[str, Any]], packages: dict[str, dict[str, Any]], owners: dict[str, str]) -> dict[str, tuple[int, int, str]]:
    milestone_rank = {milestone["id"]: index for index, milestone in enumerate(milestones)}
    return {pid: (milestone_rank[owners[pid]], package["order"], pid) for pid, package in packages.items()}


def _transitive_blocker_ids(start_ids: list[str], packages: dict[str, dict[str, Any]], rank: dict[str, tuple[int, int, str]]) -> list[str]:
    seen: set[str] = set()

    def visit(pid: str) -> None:
        for dep in packages[pid]["depends_on"]:
            if packages[dep]["status"] in roadmap.TERMINAL_SATISFIED or dep in seen:
                continue
            seen.add(dep)
            visit(dep)

    for pid in start_ids:
        visit(pid)
    return sorted(seen, key=rank.__getitem__)


def _milestone_state(packages_in_scope: list[dict[str, Any]], packages: dict[str, dict[str, Any]]) -> str:
    if all(package["status"] in roadmap.TERMINAL_SATISFIED for package in packages_in_scope):
        return "terminal"
    if any(package["status"] == "in_progress" for package in packages_in_scope):
        return "in_progress"
    if any(package["status"] == "open" and not [dep for dep in package["depends_on"] if packages[dep]["status"] not in roadmap.TERMINAL_SATISFIED] for package in packages_in_scope):
        return "ready"
    return "blocked"


def context_data(selector: str, root: Path = ROOT, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    limit = max(1, min(MAX_LIMIT, limit))
    _, milestones, packages, owners = roadmap.load_authority(root)
    milestone_by_id = {milestone["id"]: milestone for milestone in milestones}
    rank = _ranks(milestones, packages, owners)

    if selector in packages:
        package = packages[selector]
        milestone = milestone_by_id[owners[selector]]
        selected = _package_row(package, packages, owners) | {"authority": _authority(package)}
        start_ids = [selector]
        direct_ids = list(package["depends_on"])
        candidate_ids = [selector, *_transitive_blocker_ids(start_ids, packages, rank)]
        remaining = [] if package["status"] in roadmap.TERMINAL_SATISFIED else list(package["acceptance_criteria"])
        evidence = _links(package["evidence"])
        references = _links(package["references"])
        source = milestone.get("source")
    elif selector in milestone_by_id:
        milestone = milestone_by_id[selector]
        scoped = sorted(milestone["packages"], key=lambda package: (package["order"], package["id"]))
        selected = {
            "id": milestone["id"],
            "kind": "milestone",
            "title": milestone["title"],
            "status": None,
            "state": _milestone_state(scoped, packages),
            "priority": milestone["priority"],
            "authority": _authority(milestone),
        }
        start_ids = [package["id"] for package in scoped if package["status"] not in roadmap.TERMINAL_SATISFIED]
        direct_ids = sorted({dep for pid in start_ids for dep in packages[pid]["depends_on"]}, key=rank.__getitem__)
        candidate_ids = [package["id"] for package in scoped]
        remaining = [] if selected["state"] == "terminal" else list(milestone.get("acceptance_criteria", []))
        evidence = _links([link for package in scoped for link in package["evidence"]])
        references = _links([link for package in scoped for link in package["references"]])
        source = milestone.get("source")
    else:
        raise KeyError(f"unknown roadmap selector: {selector}")

    blockers = _transitive_blocker_ids(start_ids, packages, rank)
    candidates = []
    for pid in sorted(set(candidate_ids), key=rank.__getitem__):
        row = _package_row(packages[pid], packages, owners)
        if row["state"] in {"ready", "in_progress"} and packages[pid]["status"] not in roadmap.TERMINAL_SATISFIED:
            candidates.append(row)

    return {
        "schema_version": OUTPUT_VERSION,
        "selector": selector,
        "selected": selected,
        "source": dict(source) if isinstance(source, dict) else None,
        "direct_dependencies": _bounded([_package_row(packages[pid], packages, owners) for pid in sorted(set(direct_ids), key=rank.__getitem__)], limit),
        "transitive_blockers": _bounded([_package_row(packages[pid], packages, owners) for pid in blockers], limit),
        "next_candidates": _bounded(candidates, limit),
        "remaining_acceptance_criteria": _bounded(remaining, limit),
        "evidence": _bounded(evidence, limit),
        "references": _bounded(references, limit),
        "limits": {"requested": limit, "maximum": MAX_LIMIT},
    }


def _emit(value: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(value, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit bounded deterministic context for one authoritative roadmap selector.")
    parser.add_argument("selector", help="Exact roadmap milestone or package ID")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--format", choices=("human", "json"), default="json")
    args = parser.parse_args(argv)
    try:
        _emit(context_data(args.selector, limit=args.limit), args.format)
        return 0
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
