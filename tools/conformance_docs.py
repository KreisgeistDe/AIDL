from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from tools.conformance_manifest import ROOT, core_supported_ids, load_core_fixture_matrix, load_core_matrix, load_manifest

SURFACE_MARKER = "conformance-surface-coverage"
CORE_MARKER = "core-supported-coverage"


def _table(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> str:
    header = tuple(headers)
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def render_surface_table(manifest: dict) -> str:
    return _table(
        ("Manifest ID", "Kind", "Status", "Canonical support statement"),
        (
            (
                f"`{surface['id']}`",
                surface["kind"],
                surface["status"],
                surface["supportStatement"],
            )
            for surface in manifest["surfaces"]
        ),
    )


def render_core_supported_table(core: dict, fixture: dict) -> str:
    supported = core_supported_ids(core)
    if fixture["featureIds"] != supported:
        raise ValueError("Core fixture featureIds drift from Core Supported rows")
    by_id = {feature["id"]: feature for feature in core["features"]}
    layers = tuple(fixture["supportedLayers"])
    return _table(
        ("Core Supported feature", "Category", *(layer.capitalize() for layer in layers)),
        (
            (
                f"`{feature_id}`",
                by_id[feature_id]["category"],
                *(by_id[feature_id]["layerStatus"][layer] for layer in layers),
            )
            for feature_id in supported
        ),
    )


def generated_block(marker: str, body: str) -> str:
    return f"<!-- BEGIN GENERATED: {marker} -->\n{body}\n<!-- END GENERATED: {marker} -->"


def replace_generated_block(text: str, marker: str, body: str) -> str:
    begin = f"<!-- BEGIN GENERATED: {marker} -->"
    end = f"<!-- END GENERATED: {marker} -->"
    start = text.find(begin)
    finish = text.find(end)
    if start < 0 or finish < 0 or finish < start:
        raise ValueError(f"missing generated documentation markers for {marker}")
    finish += len(end)
    return text[:start] + generated_block(marker, body) + text[finish:]


def expected_documents(root: Path = ROOT) -> dict[Path, str]:
    manifest = load_manifest(root)
    core = load_core_matrix(root)
    fixture = load_core_fixture_matrix(root)
    expected: dict[Path, str] = {}
    support_path = root / "SUPPORT.md"
    coverage_path = root / "docs" / "12-coverage-and-limits.md"
    expected[support_path] = replace_generated_block(
        support_path.read_text(encoding="utf-8"),
        SURFACE_MARKER,
        render_surface_table(manifest),
    )
    expected[coverage_path] = replace_generated_block(
        coverage_path.read_text(encoding="utf-8"),
        CORE_MARKER,
        render_core_supported_table(core, fixture),
    )
    return expected


def validate_documentation(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        expected = expected_documents(root)
    except ValueError as exc:
        return [str(exc)]
    for path, rendered in expected.items():
        current = path.read_text(encoding="utf-8")
        if current != rendered:
            errors.append(f"{path.relative_to(root)} generated conformance coverage drift")
    return errors


def write_documentation(root: Path = ROOT) -> None:
    for path, rendered in expected_documents(root).items():
        path.write_text(rendered, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate deterministic conformance coverage tables")
    parser.add_argument("command", choices=("check", "write"))
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    if args.command == "write":
        write_documentation(root)
        return 0
    errors = validate_documentation(root)
    if errors:
        for error in errors:
            print(f"conformance-docs: {error}", file=sys.stderr)
        return 1
    print("conformance-docs: generated coverage tables are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
