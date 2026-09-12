from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = Path("roadmap/v1/index.json")
SCHEMA_PATH = Path("spec/roadmap-v1.schema.json")
OUTPUT_VERSION = "aidl.roadmap-output/v1"
TERMINAL_SATISFIED = {"complete", "not_applicable", "excluded"}
NONTERMINAL = {"open", "in_progress"}

MARKDOWN_PROJECTIONS = {
    "M10": Path("backlog/m9-m10-release-conformance.md"),
    "M10.1": Path("backlog/m10-1-language-freeze.md"),
    "M10.2": Path("backlog/m10-2-m10-3-language-example-migration.md"),
    "M10.3": Path("backlog/m10-2-m10-3-language-example-migration.md"),
}
TODO_PROJECTIONS = {"M10.1", "M10.2", "M10.3"}
TODO_PATH = Path("TODO.md")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _error(code: str, subject: str, message: str) -> dict[str, str]:
    return {"code": code, "subject": subject, "message": message}


def _schema_errors(data: dict[str, Any], schema: dict[str, Any], subject: str) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    validator = Draft202012Validator(schema)
    for issue in sorted(validator.iter_errors(data), key=lambda item: (list(item.absolute_path), item.message)):
        location = ".".join(str(part) for part in issue.absolute_path) or "<root>"
        errors.append(_error("ROADMAP-E001", subject, f"schema {location}: {issue.message}"))
    return errors


def _read_documents(root: Path) -> tuple[dict[str, Any], list[tuple[Path, dict[str, Any]]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    try:
        schema = _load(root / SCHEMA_PATH)
        index = _load(root / INDEX_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [], [_error("ROADMAP-E001", str(INDEX_PATH), str(exc))]
    errors.extend(_schema_errors(index, schema, str(INDEX_PATH)))
    milestones: list[tuple[Path, dict[str, Any]]] = []
    if errors:
        return index, milestones, errors
    for entry in index["milestones"]:
        path = Path(entry["path"])
        try:
            data = _load(root / path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(_error("ROADMAP-E007", str(path), str(exc)))
            continue
        errors.extend(_schema_errors(data, schema, str(path)))
        milestones.append((path, data))
    return index, milestones, errors


def _markdown_rows(text: str, prefix: str) -> list[tuple[str, bool, str | None]]:
    rows: list[tuple[str, bool, str | None]] = []
    pattern = re.compile(r"^- \[([ xX])\].*?\b(" + re.escape(prefix) + r"-\d{2})\b", re.MULTILINE)
    for match in pattern.finditer(text):
        end = text.find("\n", match.start())
        line = text[match.start(): end if end >= 0 else len(text)]
        priority_match = re.search(r"\*\*(P[0-2])\*\*", line)
        rows.append((match.group(2), match.group(1).lower() == "x", priority_match.group(1) if priority_match else None))
    return rows


def _check_projection(root: Path, milestone: dict[str, Any], path: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    text = (root / path).read_text(encoding="utf-8")
    rows = _markdown_rows(text, milestone["id"])
    expected = [(p["id"], p["status"] in TERMINAL_SATISFIED, p["priority"]) for p in milestone["packages"]]
    actual = [(pid, checked, priority) for pid, checked, priority in rows]
    if [row[0] for row in actual] != [row[0] for row in expected]:
        errors.append(_error("ROADMAP-E008", str(path), f"{milestone['id']} package IDs/order drift from JSON authority"))
        return errors
    for (pid, checked, priority), (_, expected_checked, expected_priority) in zip(actual, expected):
        if checked != expected_checked:
            errors.append(_error("ROADMAP-E008", str(path), f"{pid} checkbox drift from status"))
        if priority is not None and priority != expected_priority:
            errors.append(_error("ROADMAP-E008", str(path), f"{pid} priority drift from JSON authority"))
    return errors


def validate_repository(root: Path = ROOT, *, check_markdown: bool = True) -> list[dict[str, str]]:
    index, milestone_docs, errors = _read_documents(root)
    if errors:
        return sorted(errors, key=lambda item: (item["code"], item["subject"], item["message"]))

    entries = index["milestones"]
    entry_ids = [entry["id"] for entry in entries]
    authoritative = index["migration"]["authoritative_milestones"]
    pending = index["migration"]["pending_milestones"]
    order = index["milestone_order"]

    if entry_ids != authoritative:
        errors.append(_error("ROADMAP-E009", str(INDEX_PATH), "milestone entries must exactly match authoritative_milestones in order"))
    if set(authoritative) & set(pending):
        errors.append(_error("ROADMAP-E009", str(INDEX_PATH), "authoritative and pending milestones must be disjoint"))
    if set(authoritative) | set(pending) != set(order):
        errors.append(_error("ROADMAP-E009", str(INDEX_PATH), "migration scope must partition milestone_order"))
    if len(entry_ids) != len(set(entry_ids)):
        errors.append(_error("ROADMAP-E002", str(INDEX_PATH), "duplicate milestone id"))
    if len([entry["order"] for entry in entries]) != len(set(entry["order"] for entry in entries)):
        errors.append(_error("ROADMAP-E002", str(INDEX_PATH), "duplicate milestone order"))

    packages: dict[str, dict[str, Any]] = {}
    package_owner: dict[str, str] = {}
    milestone_by_id: dict[str, dict[str, Any]] = {}
    for path, milestone in milestone_docs:
        milestone_by_id[milestone.get("id", "")] = milestone
        entry = next((item for item in entries if item["path"] == str(path)), None)
        if entry is None or any(milestone.get(key) != entry.get(key) for key in ("id", "title", "order", "priority")):
            errors.append(_error("ROADMAP-E007", str(path), "index/file identity mismatch"))
        seen_orders: set[int] = set()
        for package in milestone.get("packages", []):
            pid = package["id"]
            if pid in packages:
                errors.append(_error("ROADMAP-E002", pid, f"duplicate package id; also owned by {package_owner[pid]}"))
            else:
                packages[pid] = package
                package_owner[pid] = milestone["id"]
            if package["order"] in seen_orders:
                errors.append(_error("ROADMAP-E002", milestone["id"], f"duplicate package order {package['order']}"))
            seen_orders.add(package["order"])
            for link in [*package["evidence"], *package["references"]]:
                if link["kind"] in {"path", "test", "schema"}:
                    ref = Path(link["ref"])
                    if ref.is_absolute() or ".." in ref.parts or not (root / ref).is_file():
                        errors.append(_error("ROADMAP-E006", pid, f"invalid or missing repository-relative {link['kind']} ref {link['ref']}"))

    for pid, package in packages.items():
        for dependency in package["depends_on"]:
            if dependency == pid:
                errors.append(_error("ROADMAP-E004", pid, "package cannot depend on itself"))
            elif dependency not in packages:
                errors.append(_error("ROADMAP-E003", pid, f"unknown dependency {dependency}"))

    graph = {pid: [dependency for dependency in package["depends_on"] if dependency in packages and dependency != pid] for pid, package in packages.items()}
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for dependency in graph[node]:
            if state.get(dependency) == 1:
                cycle = stack[stack.index(dependency):] + [dependency]
                errors.append(_error("ROADMAP-E005", node, "dependency cycle " + " -> ".join(cycle)))
            elif state.get(dependency, 0) == 0:
                visit(dependency)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)

    if check_markdown:
        for milestone_id, markdown_path in MARKDOWN_PROJECTIONS.items():
            if milestone_id in milestone_by_id:
                errors.extend(_check_projection(root, milestone_by_id[milestone_id], markdown_path))
        for milestone_id in sorted(TODO_PROJECTIONS):
            if milestone_id in milestone_by_id:
                errors.extend(_check_projection(root, milestone_by_id[milestone_id], TODO_PATH))

    return sorted(errors, key=lambda item: (item["code"], item["subject"], item["message"]))


def load_authority(root: Path = ROOT) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    errors = validate_repository(root)
    if errors:
        raise ValueError(json.dumps(errors, sort_keys=True, separators=(",", ":")))
    index = _load(root / INDEX_PATH)
    milestones = [_load(root / Path(entry["path"])) for entry in index["milestones"]]
    packages = {package["id"]: package for milestone in milestones for package in milestone["packages"]}
    return index, milestones, packages


def is_blocked(package: dict[str, Any], packages: dict[str, dict[str, Any]]) -> bool:
    return package["status"] in NONTERMINAL and any(packages[dependency]["status"] not in TERMINAL_SATISFIED for dependency in package["depends_on"])


def _ordered(milestones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [package for milestone in sorted(milestones, key=lambda value: (value["order"], value["id"])) for package in sorted(milestone["packages"], key=lambda value: (value["order"], value["id"]))]


def summary_data(root: Path = ROOT) -> dict[str, Any]:
    index, milestones, packages = load_authority(root)
    ordered = _ordered(milestones)
    counts = {status: sum(package["status"] == status for package in ordered) for status in ("open", "in_progress", "complete", "not_applicable", "excluded")}
    return {
        "authoritative_milestones": index["migration"]["authoritative_milestones"],
        "pending_migration_milestones": index["migration"]["pending_milestones"],
        "milestones": len(milestones),
        "packages": len(ordered),
        "status_counts": counts,
        "blocked": sum(is_blocked(package, packages) for package in ordered),
        "ready": sum(package["status"] in NONTERMINAL and not is_blocked(package, packages) for package in ordered),
    }


def next_data(root: Path = ROOT, milestone_id: str | None = None) -> dict[str, Any] | None:
    _, milestones, packages = load_authority(root)
    for package in _ordered(milestones):
        if milestone_id and not package["id"].startswith(milestone_id + "-"):
            continue
        if package["status"] in NONTERMINAL and not is_blocked(package, packages):
            return {"id": package["id"], "title": package["title"], "status": package["status"], "depends_on": package["depends_on"]}
    return None


def blocker_ids(packages: dict[str, dict[str, Any]], package_id: str, transitive: bool) -> list[str]:
    if package_id not in packages:
        raise KeyError(package_id)
    result: set[str] = set()

    def walk(pid: str) -> None:
        for dependency in packages[pid]["depends_on"]:
            if packages[dependency]["status"] not in TERMINAL_SATISFIED and dependency not in result:
                result.add(dependency)
                if transitive:
                    walk(dependency)

    walk(package_id)
    return sorted(result)


def completed_data(root: Path = ROOT) -> dict[str, Any]:
    _, milestones, _ = load_authority(root)
    ordered = _ordered(milestones)
    return {
        "complete": [package["id"] for package in ordered if package["status"] == "complete"],
        "not_applicable": [{"id": package["id"], "reason": package["disposition_reason"]} for package in ordered if package["status"] == "not_applicable"],
        "excluded": [{"id": package["id"], "reason": package["disposition_reason"]} for package in ordered if package["status"] == "excluded"],
        "complete_milestones": [milestone["id"] for milestone in sorted(milestones, key=lambda value: (value["order"], value["id"])) if all(package["status"] in TERMINAL_SATISFIED for package in milestone["packages"])],
    }


def _emit(command: str, data: Any) -> None:
    print(json.dumps({"schema_version": OUTPUT_VERSION, "command": command, "roadmap_version": 1, "data": data}, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and query the versioned AIDL roadmap authority")
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--format", choices=["json", "text"], default="text")
    summary = sub.add_parser("summary")
    summary.add_argument("--format", choices=["json", "text"], default="text")
    next_parser = sub.add_parser("next")
    next_parser.add_argument("--milestone")
    next_parser.add_argument("--format", choices=["json", "text"], default="text")
    blockers = sub.add_parser("blockers")
    blockers.add_argument("package_id")
    blockers.add_argument("--transitive", action="store_true")
    blockers.add_argument("--format", choices=["json", "text"], default="text")
    completed = sub.add_parser("completed")
    completed.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        if args.command == "validate":
            errors = validate_repository(root)
            data = {"valid": not errors, "errors": errors}
            if args.format == "json":
                _emit("validate", data)
            elif errors:
                for error in errors:
                    print(f"{error['code']} {error['subject']}: {error['message']}", file=sys.stderr)
            else:
                print("roadmap: valid")
            return 1 if errors else 0

        if args.command == "summary":
            data = summary_data(root)
        elif args.command == "next":
            data = next_data(root, args.milestone)
        elif args.command == "blockers":
            _, _, packages = load_authority(root)
            data = {"id": args.package_id, "blockers": blocker_ids(packages, args.package_id, args.transitive), "transitive": args.transitive}
        else:
            data = completed_data(root)

        if args.format == "json":
            _emit(args.command, data)
        else:
            print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except KeyError as exc:
        print(f"ROADMAP-E003 {exc.args[0]}: unknown package id", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"roadmap tool failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
