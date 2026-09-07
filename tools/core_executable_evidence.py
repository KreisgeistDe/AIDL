from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.conformance_manifest import CORE_LAYERS, ROOT, load_core_matrix

EVIDENCE = ROOT / "spec" / "core-executable-evidence.json"


def load_evidence(root: Path = ROOT) -> dict[str, Any]:
    return json.loads((root / "spec" / "core-executable-evidence.json").read_text(encoding="utf-8"))


def implemented_cells(core: dict[str, Any]) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    cells: list[tuple[str, str, tuple[str, ...]]] = []
    for feature in core["features"]:
        for layer in CORE_LAYERS:
            if feature["layerStatus"][layer] == "implemented":
                cells.append((feature["id"], layer, tuple(feature["layerEvidence"][layer])))
    return tuple(cells)


def open_cells(core: dict[str, Any]) -> tuple[tuple[str, str, str], ...]:
    cells: list[tuple[str, str, str]] = []
    for feature in core["features"]:
        for layer in CORE_LAYERS:
            status = feature["layerStatus"][layer]
            if status in {"missing", "partial"}:
                cells.append((feature["id"], layer, status))
    return tuple(cells)


def violations(data: dict[str, Any], core: dict[str, Any], *, root: Path = ROOT) -> tuple[str, ...]:
    errors: list[str] = []
    if data.get("schemaVersion") != 1:
        errors.append("core executable evidence schemaVersion must be 1")
    if data.get("source") != "spec/core-conformance.json":
        errors.append("core executable evidence must derive from spec/core-conformance.json")

    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        return (*errors, "core executable evidence must contain an evidence object")

    matrix_catalog = core["evidenceCatalog"]
    implemented = implemented_cells(core)
    used_ids = {evidence_id for _, _, refs in implemented for evidence_id in refs}
    required_ids = {
        evidence_id
        for _, _, refs in implemented
        for evidence_id in refs
        if any(item["type"] != "documentation" for item in matrix_catalog[evidence_id])
    }

    unknown = sorted(set(evidence) - set(matrix_catalog))
    if unknown:
        errors.append(f"unknown Core evidence ids: {unknown}")
    stale = sorted(set(evidence) - used_ids)
    if stale:
        errors.append(f"executable evidence ids are not used by implemented cells: {stale}")

    for evidence_id, paths in sorted(evidence.items()):
        if not isinstance(paths, list) or not paths or not all(isinstance(path, str) and path for path in paths):
            errors.append(f"{evidence_id}: executable evidence must be a non-empty test path list")
            continue
        if paths != sorted(set(paths)):
            errors.append(f"{evidence_id}: executable evidence paths must be unique and sorted")
        for value in paths:
            path = Path(value)
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"{evidence_id}: executable evidence path must stay repository-relative: {value}")
            elif not (root / path).is_file():
                errors.append(f"{evidence_id}: missing executable evidence path {value}")
            elif not (path.name.startswith("test_") and path.suffix in {".py", ".kt"}):
                errors.append(f"{evidence_id}: executable evidence must name a focused test file: {value}")

    for feature_id, layer, refs in implemented:
        executable_refs = sorted(set(refs) & set(evidence))
        if not executable_refs:
            errors.append(
                f"{feature_id}/{layer}: implemented status lacks linked executable test evidence "
                f"for matrix refs {list(refs)}"
            )

    missing_registry = sorted(required_ids - set(evidence))
    if missing_registry:
        errors.append(f"implemented Core evidence ids missing executable registry entries: {missing_registry}")

    return tuple(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate executable evidence linked from implemented Core conformance cells")
    parser.add_argument("command", choices=["validate"])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    core = load_core_matrix(root)
    data = load_evidence(root)
    errors = violations(data, core, root=root)
    if errors:
        for error in errors:
            print(f"core-executable-evidence: {error}", file=sys.stderr)
        return 1
    print(
        "core-executable-evidence: valid "
        f"({len(implemented_cells(core))} implemented cells linked; "
        f"{len(open_cells(core))} partial/missing cells remain explicitly open)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
