from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "aidl.m10.5-reference-contract/v1"
REQUIRED_SURFACES = (
    "source_projection",
    "diagnostics",
    "production_semantics",
    "canonical_ir",
    "cli_and_semantic_queries",
    "fixtures_and_reference_apps",
    "ci_gates",
)
REQUIRED_DIMENSIONS = (
    "accepted_rejected",
    "diagnostics",
    "canonical_ir",
    "stable_identities",
    "ordering",
    "source_locations",
    "exit_behavior",
)


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_reference_contract(
    *,
    repo_root: Path | None = None,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = (repo_root or _root()).resolve()
    source = dict(manifest) if manifest is not None else _load_json(root / "tools/m10_5_reference_contract.json")

    if source.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("reference contract schema version drift detected")
    if source.get("authority") != "M10.5-01":
        raise ValueError("reference contract authority drift detected")
    if source.get("normative_language_source") is not False:
        raise ValueError("M10.5 inventory must not become a normative language source")
    if source.get("reference_implementation") != "python":
        raise ValueError("Python must remain the M10.5 reference implementation")

    frozen = source.get("frozen_language_contract")
    if not isinstance(frozen, Mapping) or frozen.get("path") != "spec/language-surface-v1.json":
        raise ValueError("frozen language contract path drift detected")
    contract_path = root / str(frozen["path"])
    contract = _load_json(contract_path)
    expected = {
        "authority": frozen.get("authority"),
        "status": frozen.get("status"),
        "contract_revision": frozen.get("contract_revision"),
    }
    actual = {key: contract.get(key) for key in expected}
    if expected != {"authority": "M10.1", "status": "frozen", "contract_revision": 4} or actual != expected:
        raise ValueError("frozen language contract identity drift detected")

    surfaces = source.get("observable_surfaces")
    if not isinstance(surfaces, list):
        raise ValueError("observable_surfaces must be a list")
    ids = [item.get("id") for item in surfaces if isinstance(item, Mapping)]
    if len(ids) != len(surfaces) or len(set(ids)) != len(ids):
        raise ValueError("observable surface ids must be unique")
    if tuple(sorted(ids)) != tuple(sorted(REQUIRED_SURFACES)):
        raise ValueError("observable surface inventory drift detected")

    evidence_rows: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for surface in surfaces:
        evidence = surface.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"surface {surface.get('id')} has no evidence")
        for raw in evidence:
            if not isinstance(raw, str) or not raw or raw.startswith(".ai/") or "/.ai/" in raw:
                raise ValueError("invalid or project-.ai evidence path")
            path = (root / raw).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ValueError("evidence path escapes repository") from exc
            if not path.is_file():
                raise ValueError(f"missing evidence path: {raw}")
            identity = f"{surface['id']}:{raw}"
            if identity in seen_paths:
                raise ValueError(f"duplicate evidence path within surface: {raw}")
            seen_paths.add(identity)
            evidence_rows.append({"surface": str(surface["id"]), "path": raw, "sha256": _sha256(path)})

    differential = source.get("differential_contract")
    if not isinstance(differential, Mapping):
        raise ValueError("missing differential contract")
    if differential.get("comparison") != "exact_canonical_json":
        raise ValueError("differential comparison drift detected")
    if differential.get("transport_only_differences") != []:
        raise ValueError("transport-only differences require a separately reviewed contract change")
    if tuple(differential.get("semantic_dimensions", ())) != REQUIRED_DIMENSIONS:
        raise ValueError("differential semantic dimensions drift detected")
    if differential.get("runner_implementations") != ["python", "kotlin"]:
        raise ValueError("differential runner implementation contract drift detected")
    if differential.get("kotlin_required_for_m10_5_01") is not False:
        raise ValueError("M10.5-01 must not require or implement Kotlin semantics")

    fingerprint_payload = {
        "schema_version": SCHEMA_VERSION,
        "frozen_language_contract_sha256": _sha256(contract_path),
        "evidence": sorted(evidence_rows, key=lambda item: (item["surface"], item["path"])),
        "differential_contract": differential,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "authority": "M10.5-01",
        "reference_implementation": "python",
        "frozen_contract": {
            "path": str(frozen["path"]),
            "authority": "M10.1",
            "status": "frozen",
            "contract_revision": 4,
            "sha256": _sha256(contract_path),
        },
        "observable_surfaces": sorted(ids),
        "evidence": fingerprint_payload["evidence"],
        "differential_contract": differential,
        "fingerprint": "sha256:" + hashlib.sha256(_canonical(fingerprint_payload).encode("utf-8")).hexdigest(),
    }


def reference_contract_json(**kwargs: Any) -> str:
    return _canonical(build_reference_contract(**kwargs))


if __name__ == "__main__":
    print(reference_contract_json())
