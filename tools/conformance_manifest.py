from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CORE_LAYERS = ("parse", "resolve", "validate", "ir", "generate", "ide")
CORE_SUPPORTED_LAYERS = ("parse", "resolve", "validate", "ir")
CORE_DECLARATION_IDS = (
    "decl.alias", "decl.api", "decl.app", "decl.consumer", "decl.entity", "decl.enum", "decl.error", "decl.event",
    "decl.import", "decl.module", "decl.mutation", "decl.opaque", "decl.query", "decl.service", "decl.topic",
    "decl.transaction", "decl.value",
)
CORE_RULE_IDS = (
    "rule.api.exposure-version-compatibility", "rule.consumer.at-least-once", "rule.consumer.idempotency",
    "rule.entity.cross-service-ref-rejected", "rule.entity.owner-local-access", "rule.entity.single-owner",
    "rule.module.cyclic-dependency", "rule.module.duplicate-declaration", "rule.module.unresolved-name",
    "rule.mutation.required-clauses", "rule.mutation.single-root-effect", "rule.names.stable-fqn",
    "rule.query.side-effect-free", "rule.transaction.cross-resource-rejected", "rule.transaction.cross-service-rejected",
    "rule.transaction.outbox-atomic", "rule.transaction.resource-owner", "rule.types.int-to-decimal-only",
)
EXECUTABLE_EVIDENCE_TYPES = {"source", "test", "schema", "workflow"}
FIXTURE_EVIDENCE_TYPES = {"fixture", "test", "snapshot", "matrix"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(root: Path = ROOT) -> dict[str, Any]:
    return _load_json(root / "spec" / "conformance-manifest.json")


def load_core_matrix(root: Path = ROOT) -> dict[str, Any]:
    return _load_json(root / "spec" / "core-conformance.json")


def load_core_fixture_matrix(root: Path = ROOT) -> dict[str, Any]:
    return _load_json(root / "spec" / "core-fixture-conformance.json")


def _schema_errors(data: dict[str, Any], schema_path: Path) -> list[str]:
    validator = Draft202012Validator(_load_json(schema_path))
    errors: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"schema {location}: {error.message}")
    return errors


def core_supported_ids(data: dict[str, Any]) -> list[str]:
    supported: list[str] = []
    for feature in data["features"]:
        statuses = feature["layerStatus"]
        required = [statuses[layer] for layer in CORE_SUPPORTED_LAYERS]
        if all(status in {"implemented", "not-applicable"} for status in required) and "implemented" in required:
            supported.append(feature["id"])
    return sorted(supported)


def validate_core_data(data: dict[str, Any], *, root: Path = ROOT) -> list[str]:
    errors = _schema_errors(data, root / "spec" / "core-conformance.schema.json")
    if errors:
        return errors

    if tuple(data["layers"]) != CORE_LAYERS:
        errors.append("core layers drift from Parse/Resolve/Validate/IR/Generate/IDE contract")
    if tuple(data["declarationIds"]) != CORE_DECLARATION_IDS:
        errors.append("core declaration inventory drift")
    if tuple(data["ruleIds"]) != CORE_RULE_IDS:
        errors.append("core rule inventory drift")

    features = data["features"]
    feature_ids = [item["id"] for item in features]
    expected_ids = sorted((*CORE_DECLARATION_IDS, *CORE_RULE_IDS))
    if feature_ids != expected_ids:
        errors.append("core feature rows must be unique, complete, and sorted by stable id")

    catalog = data["evidenceCatalog"]
    if not (root / data["source"]).is_file():
        errors.append(f"missing normative Core contract {data['source']}")
    for feature in features:
        feature_id = feature["id"]
        expected_category = "declaration" if feature_id.startswith("decl.") else "rule"
        if feature["category"] != expected_category:
            errors.append(f"{feature_id}: category does not match stable id")

        for layer in CORE_LAYERS:
            status = feature["layerStatus"][layer]
            refs = feature["layerEvidence"][layer]
            resolved: list[dict[str, str]] = []
            for evidence_id in refs:
                if evidence_id not in catalog:
                    errors.append(f"{feature_id}/{layer}: unknown evidence id {evidence_id}")
                    continue
                resolved.extend(catalog[evidence_id])
            if not resolved:
                errors.append(f"{feature_id}/{layer}: missing evidence")
                continue
            for item in resolved:
                path = Path(item["path"])
                if path.is_absolute() or ".." in path.parts:
                    errors.append(f"{feature_id}/{layer}: evidence path must stay repository-relative: {item['path']}")
                elif not (root / path).is_file():
                    errors.append(f"{feature_id}/{layer}: missing evidence path {item['path']}")
            if status == "implemented" and not any(item["type"] in EXECUTABLE_EVIDENCE_TYPES for item in resolved):
                errors.append(f"{feature_id}/{layer}: implemented status requires executable or machine-readable evidence")
            if status == "not-applicable" and any(item["type"] != "documentation" for item in resolved):
                errors.append(f"{feature_id}/{layer}: not-applicable status may only cite the normative contract")

    return errors


def validate_core_fixture_data(
    data: dict[str, Any], core_data: dict[str, Any], *, root: Path = ROOT
) -> list[str]:
    errors = _schema_errors(data, root / "spec" / "core-fixture-conformance.schema.json")
    if errors:
        return errors

    if data["source"] != "spec/core-conformance.json":
        errors.append("Core fixture coverage must derive from spec/core-conformance.json")
    if tuple(data["supportedLayers"]) != CORE_SUPPORTED_LAYERS:
        errors.append("Core fixture supported layers drift from Parse/Resolve/Validate/IR definition")
    if tuple(data["requiredKinds"]) != ("positive", "negative", "ir", "compatibility"):
        errors.append("Core fixture kinds must be positive/negative/ir/compatibility")

    expected_ids = core_supported_ids(core_data)
    if data["featureIds"] != expected_ids:
        missing = sorted(set(expected_ids) - set(data["featureIds"]))
        stale = sorted(set(data["featureIds"]) - set(expected_ids))
        if missing:
            errors.append(f"Core fixture coverage missing supported ids: {missing}")
        if stale:
            errors.append(f"Core fixture coverage contains non-supported ids: {stale}")
        if not missing and not stale:
            errors.append("Core fixture feature ids must be sorted deterministically")

    catalog = data["evidenceCatalog"]
    resolved_by_kind: dict[str, list[dict[str, str]]] = {}
    for kind in data["requiredKinds"]:
        resolved: list[dict[str, str]] = []
        for evidence_id in data["defaultEvidence"][kind]:
            if evidence_id not in catalog:
                errors.append(f"Core fixture {kind}: unknown evidence id {evidence_id}")
                continue
            resolved.extend(catalog[evidence_id])
        resolved_by_kind[kind] = resolved
        if not resolved:
            errors.append(f"Core fixture {kind}: missing evidence")
            continue
        if not any(item["type"] == "test" for item in resolved):
            errors.append(f"Core fixture {kind}: executable test evidence required")
        for item in resolved:
            if item["type"] not in FIXTURE_EVIDENCE_TYPES:
                errors.append(f"Core fixture {kind}: unsupported evidence type {item['type']}")
            path = Path(item["path"])
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"Core fixture {kind}: evidence path must stay repository-relative: {item['path']}")
            elif not (root / path).is_file():
                errors.append(f"Core fixture {kind}: missing evidence path {item['path']}")

    if resolved_by_kind.get("positive") and not any(item["type"] == "fixture" for item in resolved_by_kind["positive"]):
        errors.append("Core fixture positive: source fixture evidence required")
    if resolved_by_kind.get("ir") and not any(item["type"] == "snapshot" for item in resolved_by_kind["ir"]):
        errors.append("Core fixture ir: Canonical-IR snapshot evidence required")
    if resolved_by_kind.get("compatibility") and not any(item["type"] == "matrix" for item in resolved_by_kind["compatibility"]):
        errors.append("Core fixture compatibility: compatibility matrix evidence required")

    return errors


def validate_data(data: dict[str, Any], *, root: Path = ROOT, support_text: str | None = None) -> list[str]:
    errors = _schema_errors(data, root / "spec" / "conformance-manifest.schema.json")
    if errors:
        return errors

    surfaces = data["surfaces"]
    ids = [surface["id"] for surface in surfaces]
    if ids != sorted(ids):
        errors.append("surfaces must be sorted by stable id")
    if len(ids) != len(set(ids)):
        errors.append("surface ids must be unique")

    known = set(ids)
    for surface in surfaces:
        surface_id = surface["id"]
        for required in surface.get("requires", []):
            if required not in known:
                errors.append(f"{surface_id}: unknown required surface id {required}")
            if required == surface_id:
                errors.append(f"{surface_id}: surface cannot require itself")
        for item in surface["evidence"]:
            evidence_path = Path(item["path"])
            if evidence_path.is_absolute() or ".." in evidence_path.parts:
                errors.append(f"{surface_id}: evidence path must stay repository-relative: {item['path']}")
            elif not (root / evidence_path).is_file():
                errors.append(f"{surface_id}: missing evidence path {item['path']}")

    registry = _load_json(root / "spec" / "profile-registry.json")
    expected_profiles = {f"profile.{item['id']}" for item in registry["profiles"]}
    manifest_profiles = {surface["id"] for surface in surfaces if surface["kind"] == "profile"}
    if missing := sorted(expected_profiles - manifest_profiles):
        errors.append(f"manifest is missing registry profile ids: {missing}")
    if unknown := sorted(manifest_profiles - expected_profiles):
        errors.append(f"manifest has unknown registry profile ids: {unknown}")

    support = support_text if support_text is not None else (root / "SUPPORT.md").read_text(encoding="utf-8")
    for surface in surfaces:
        if f"`{surface['id']}`" not in support:
            errors.append(f"{surface['id']}: SUPPORT.md is missing stable id marker")
        if surface["supportStatement"] not in support:
            errors.append(f"{surface['id']}: SUPPORT.md support statement drift")
    return errors


def validate_manifest(root: Path = ROOT) -> list[str]:
    errors = validate_data(load_manifest(root), root=root)
    core_data = load_core_matrix(root)
    errors.extend(validate_core_data(core_data, root=root))
    errors.extend(validate_core_fixture_data(load_core_fixture_matrix(root), core_data, root=root))
    support = (root / "SUPPORT.md").read_text(encoding="utf-8")
    marker = f"Core conformance matrix: {len(CORE_DECLARATION_IDS)} declarations, {len(CORE_RULE_IDS)} semantic rules, {len(CORE_LAYERS)} layers."
    if marker not in support:
        errors.append("SUPPORT.md Core matrix summary drift")
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate AIDL support and Core conformance manifests")
    parser.add_argument("command", choices=["validate"])
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    errors = validate_manifest(args.root.resolve())
    if errors:
        for error in errors:
            print(f"conformance-manifest: {error}", file=sys.stderr)
        return 1
    core_data = load_core_matrix(args.root.resolve())
    print(
        "conformance-manifest: valid "
        f"({len(load_manifest(args.root.resolve())['surfaces'])} surfaces, "
        f"{len(core_data['features'])} Core rows, "
        f"{len(core_supported_ids(core_data))} Core Supported fixture rows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
