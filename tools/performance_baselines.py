from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .compiler_project import load_compiler_project

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path("spec/performance-baselines.json")
SCHEMA_PATH = Path("spec/performance-baselines.schema.json")
WORKLOAD_IDS = ("small", "medium", "large")
METRICS = (
    "sourceFiles",
    "sourceBytes",
    "declarations",
    "symbols",
    "importResolutions",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    return _load_json(root / CONTRACT_PATH)


def render_workload(workload: dict[str, Any]) -> dict[str, str]:
    """Render one synthetic Core project without randomness or wall-clock input."""

    modules = int(workload["modules"])
    declarations_per_module = int(workload["declarationsPerModule"])
    fields_per_declaration = int(workload["fieldsPerDeclaration"])
    rendered: dict[str, str] = {}

    for module_index in range(modules):
        module_name = f"performance.m{module_index:03d}"
        lines = [f"module {module_name}", ""]
        if module_index:
            lines.extend(
                [f"import performance.m{module_index - 1:03d}.Entity000", ""]
            )
        for declaration_index in range(declarations_per_module):
            lines.append(f"export entity Entity{declaration_index:03d} {{")
            lines.append("  id: uuid primary immutable")
            for field_index in range(fields_per_declaration - 1):
                lines.append(
                    f"  field{field_index:02d}: string(1..80) required mutable"
                )
            lines.extend(["}", ""])
        rendered[f"m{module_index:03d}.aidl"] = "\n".join(lines).rstrip() + "\n"
    return rendered


def measure_workload(workload: dict[str, Any]) -> dict[str, int]:
    """Measure deterministic structural compiler work for one generated project."""

    rendered = render_workload(workload)
    with tempfile.TemporaryDirectory(prefix="aidl-performance-") as temporary:
        root = Path(temporary)
        for relative_path, source in rendered.items():
            (root / relative_path).write_text(source, encoding="utf-8")
        project = load_compiler_project([root])

    return {
        "sourceFiles": len(rendered),
        "sourceBytes": sum(len(source.encode("utf-8")) for source in rendered.values()),
        "declarations": len(project.declaration_names),
        "symbols": sum(
            len(matches) for matches in project.symbol_table.declarations_by_fqn.values()
        ),
        "importResolutions": len(project.import_resolutions),
    }


def _schema_errors(data: dict[str, Any], root: Path) -> list[str]:
    validator = Draft202012Validator(_load_json(root / SCHEMA_PATH))
    errors: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"schema {location}: {error.message}")
    return errors


def validate_data(data: dict[str, Any], *, root: Path = ROOT) -> list[str]:
    errors = _schema_errors(data, root)
    if errors:
        return errors

    workloads = data["workloads"]
    ids = tuple(workload["id"] for workload in workloads)
    if ids != WORKLOAD_IDS:
        errors.append("workloads must be exactly small, medium, large in that order")

    observed_by_id: dict[str, dict[str, int]] = {}
    for workload in workloads:
        workload_id = workload["id"]
        first_render = render_workload(workload)
        second_render = render_workload(workload)
        if first_render != second_render:
            errors.append(f"{workload_id}: workload rendering is not byte-deterministic")
            continue

        observed = measure_workload(workload)
        observed_by_id[workload_id] = observed
        for metric in METRICS:
            expected = workload["baseline"][metric]
            if observed[metric] != expected:
                errors.append(
                    f"{workload_id}/{metric}: baseline {expected} != observed {observed[metric]}"
                )
            limit = data["resourceLimits"][metric]
            if observed[metric] > limit:
                errors.append(
                    f"{workload_id}/{metric}: observed {observed[metric]} exceeds resource limit {limit}"
                )

    if all(workload_id in observed_by_id for workload_id in WORKLOAD_IDS):
        for metric in METRICS:
            sequence = [observed_by_id[workload_id][metric] for workload_id in WORKLOAD_IDS]
            if not all(left < right for left, right in zip(sequence, sequence[1:])):
                errors.append(f"{metric}: small/medium/large workloads must increase strictly")

        large = observed_by_id["large"]
        for metric in METRICS:
            limit = data["resourceLimits"][metric]
            if limit > large[metric] * 2:
                errors.append(
                    f"{metric}: resource limit {limit} exceeds 2x the large baseline {large[metric]}"
                )

    return errors


def validate_contract(root: Path = ROOT) -> list[str]:
    return validate_data(load_contract(root), root=root)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate deterministic AIDL compiler performance baselines"
    )
    parser.add_argument("command", choices=("check", "measure"))
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    contract = load_contract(root)
    if args.command == "measure":
        payload = {
            workload["id"]: measure_workload(workload)
            for workload in contract["workloads"]
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    errors = validate_data(contract, root=root)
    if errors:
        for error in errors:
            print(f"performance-baselines: {error}")
        return 1
    print(
        "performance-baselines: valid "
        f"({len(contract['workloads'])} workloads; model {contract['measurementModel']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
