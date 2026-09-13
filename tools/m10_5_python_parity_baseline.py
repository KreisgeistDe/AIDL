from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "aidl.m10.5-python-parity-baseline/v1"
AUTHORITY = "M10.5-01"
RUNNER_INPUTS = ("source", "config", "profile")
SEMANTIC_DIMENSIONS = (
    "accepted_rejected",
    "diagnostics",
    "canonical_ir",
    "stable_identities",
    "ordering",
    "source_locations",
    "exit_behavior",
)
REQUIRED_BINDINGS = {
    "spec/language-surface-v1.json",
    "spec/ir.schema.json",
    "spec/profile-registry.json",
    "spec/m10-2-language-surface-classification.json",
    "spec/m10-3-shared-disposition.json",
    "spec/m10-3-closure-certification.json",
}
REQUIRED_SURFACES = {
    "source_projection",
    "diagnostics",
    "canonical_ir",
    "cli_and_semantic_queries",
    "fixtures_compatibility_reference_apps",
    "intellij_integration",
    "ci_gates",
}


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_manifest(root: Path, manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    if manifest is not None:
        return dict(manifest)
    value = json.loads((root / "spec/m10-5-parity-manifest.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("parity manifest must be a JSON object")
    return value


def validate_manifest(
    *,
    repo_root: Path | None = None,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = (repo_root or _root()).resolve()
    source = _load_manifest(root, manifest)

    if source.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("parity manifest schema version drift detected")
    if source.get("authority") != AUTHORITY:
        raise ValueError("parity authority drift detected")
    if source.get("normative_language_source") is not False:
        raise ValueError("parity evidence must not become a normative language source")
    if source.get("reference_implementation") != "python":
        raise ValueError("Python must remain the M10.5-01 reference implementation")
    if not isinstance(source.get("baseline_base_commit"), str) or len(source["baseline_base_commit"]) != 40:
        raise ValueError("baseline base commit identity is missing or invalid")

    runner_inputs = source.get("runner_inputs")
    if runner_inputs != list(RUNNER_INPUTS):
        raise ValueError("runner_inputs must be exactly [source, config, profile]")

    identity = source.get("input_identity")
    if not isinstance(identity, Mapping):
        raise ValueError("input identity contract is missing")
    if identity.get("algorithm") != "sha256":
        raise ValueError("input identity algorithm drift detected")
    if identity.get("exact_key_set") is not True:
        raise ValueError("input identity must require an exact key set")
    if identity.get("required_keys") != list(RUNNER_INPUTS):
        raise ValueError("input identity required_keys drift detected")

    comparison = source.get("comparison_contract")
    if not isinstance(comparison, Mapping):
        raise ValueError("comparison contract is missing")
    if comparison.get("mode") != "exact_structured":
        raise ValueError("comparison mode drift detected")
    if comparison.get("semantic_dimensions") != list(SEMANTIC_DIMENSIONS):
        raise ValueError("semantic comparison dimensions drift detected")
    if comparison.get("semantic_allowlists") != []:
        raise ValueError("semantic allowlists are forbidden")
    if comparison.get("transport_normalization") != [
        "repository_relative_path_rendering",
        "json_object_key_order",
    ]:
        raise ValueError("transport normalization drift detected")

    bindings = source.get("normative_bindings")
    if not isinstance(bindings, list) or set(bindings) != REQUIRED_BINDINGS or len(bindings) != len(REQUIRED_BINDINGS):
        raise ValueError("normative binding inventory drift detected")

    surfaces = source.get("parity_inventory")
    if not isinstance(surfaces, list):
        raise ValueError("parity inventory must be a list")
    ids = [row.get("id") for row in surfaces if isinstance(row, Mapping)]
    if len(ids) != len(surfaces) or set(ids) != REQUIRED_SURFACES or len(ids) != len(REQUIRED_SURFACES):
        raise ValueError("parity inventory surface drift detected")

    corpus = source.get("parity_corpus")
    if not isinstance(corpus, Mapping):
        raise ValueError("parity corpus is missing")

    paths: set[str] = set(bindings)
    for surface in surfaces:
        evidence = surface.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"surface {surface.get('id')} has no evidence")
        for raw in evidence:
            if not isinstance(raw, str) or not raw or raw.startswith(".ai/") or "/.ai/" in raw:
                raise ValueError("invalid evidence path")
            paths.add(raw)
    for group, values in corpus.items():
        if not isinstance(values, list) or not values:
            raise ValueError(f"parity corpus group {group} must be a non-empty list")
        for raw in values:
            if not isinstance(raw, str) or not raw:
                raise ValueError(f"invalid parity corpus path in {group}")
            paths.add(raw)

    for raw in sorted(paths):
        path = (root / raw).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"path escapes repository: {raw}") from exc
        if not path.is_file():
            raise ValueError(f"missing parity evidence path: {raw}")

    return source


def build_input_identity(*, source: bytes, config: bytes, profile: bytes) -> dict[str, str]:
    return {
        "source": _sha256_bytes(source),
        "config": _sha256_bytes(config),
        "profile": _sha256_bytes(profile),
    }


def validate_input_identity(value: Mapping[str, Any]) -> dict[str, str]:
    if set(value) != set(RUNNER_INPUTS):
        raise ValueError("runner input identity must contain exactly source, config, profile")
    normalized: dict[str, str] = {}
    for key in RUNNER_INPUTS:
        raw = value.get(key)
        if not isinstance(raw, str) or not raw.startswith("sha256:") or len(raw) != 71:
            raise ValueError(f"invalid sha256 identity for runner input {key}")
        try:
            int(raw[7:], 16)
        except ValueError as exc:
            raise ValueError(f"invalid sha256 identity for runner input {key}") from exc
        normalized[key] = raw
    return normalized


def build_parity_evidence(
    *,
    repo_root: Path | None = None,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = (repo_root or _root()).resolve()
    source = validate_manifest(repo_root=root, manifest=manifest)

    normative = [
        {"path": raw, "sha256": _sha256_file(root / raw)}
        for raw in sorted(source["normative_bindings"])
    ]
    inventory: list[dict[str, Any]] = []
    for surface in sorted(source["parity_inventory"], key=lambda row: row["id"]):
        rows = [
            {"path": raw, "sha256": _sha256_file(root / raw)}
            for raw in sorted(surface["evidence"])
        ]
        inventory.append({"id": surface["id"], "evidence": rows})

    corpus = {
        group: [
            {"path": raw, "sha256": _sha256_file(root / raw)}
            for raw in sorted(values)
        ]
        for group, values in sorted(source["parity_corpus"].items())
    }

    fingerprint_payload = {
        "schema_version": SCHEMA_VERSION,
        "authority": AUTHORITY,
        "baseline_base_commit": source["baseline_base_commit"],
        "runner_inputs": list(RUNNER_INPUTS),
        "input_identity_contract": source["input_identity"],
        "comparison_contract": source["comparison_contract"],
        "normative_bindings": normative,
        "parity_inventory": inventory,
        "parity_corpus": corpus,
    }
    return {
        **fingerprint_payload,
        "reference_implementation": "python",
        "fingerprint": _sha256_bytes(_canonical(fingerprint_payload).encode("utf-8")),
    }


def assert_fingerprint(expected: str, actual: str) -> None:
    if expected != actual:
        raise ValueError(f"parity fingerprint drift detected: expected {expected}, got {actual}")


def compare_results(
    *,
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    expected_fingerprint: str,
    actual_fingerprint: str,
) -> dict[str, Any]:
    assert_fingerprint(expected_fingerprint, actual_fingerprint)
    reference_identity = validate_input_identity(reference.get("input_identity", {}))
    candidate_identity = validate_input_identity(candidate.get("input_identity", {}))
    if reference_identity != candidate_identity:
        raise ValueError("runner input identity drift detected")

    mismatches: list[dict[str, Any]] = []
    for dimension in SEMANTIC_DIMENSIONS:
        if dimension not in reference or dimension not in candidate:
            mismatches.append({
                "dimension": dimension,
                "kind": "missing_dimension",
                "reference_present": dimension in reference,
                "candidate_present": dimension in candidate,
            })
            continue
        if _canonical(reference[dimension]) != _canonical(candidate[dimension]):
            mismatches.append({
                "dimension": dimension,
                "kind": "semantic_mismatch",
                "reference": reference[dimension],
                "candidate": candidate[dimension],
            })

    return {
        "status": "match" if not mismatches else "mismatch",
        "input_identity": reference_identity,
        "fingerprint": actual_fingerprint,
        "mismatches": mismatches,
    }


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        nargs="?",
        default="evidence",
        choices=("evidence",),
        help="emit deterministic refreshed Python parity evidence",
    )
    args = parser.parse_args(argv)
    if args.command == "evidence":
        print(_canonical(build_parity_evidence()))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(_main())
