from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("spec/m10-2-language-surface-classification.json")
SCHEMA_VERSION = "aidl.m10.2-language-surface-classification/v1"
CLASSES = {
    "production-admitted-canonical",
    "canonical-but-not-yet-admitted",
    "legacy-readable-compatibility",
    "negative-rejection-fixture",
    "illustrative-aspirational",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def _repo_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def validate(root: Path = ROOT, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    data = manifest or _load(root / MANIFEST)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("classification schema version drift")
    if data.get("authority") != "M10.2-01":
        raise ValueError("classification authority drift")
    if set(data.get("classes", [])) != CLASSES or len(data.get("classes", [])) != len(CLASSES):
        raise ValueError("classification vocabulary drift")

    frozen = data.get("frozen_language_contract", {})
    contract_path = root / str(frozen.get("path", ""))
    contract = _load(contract_path)
    expected = {"authority": "M10.1", "status": "frozen", "contract_revision": 4}
    actual = {key: contract.get(key) for key in expected}
    if actual != expected or {key: frozen.get(key) for key in expected} != expected:
        raise ValueError("frozen M10.1 contract identity drift")

    compiled: list[tuple[str, re.Pattern[str], str]] = []
    ids: set[str] = set()
    for rule in data.get("source_rules", []):
        rid = rule.get("id")
        cls = rule.get("class")
        if not isinstance(rid, str) or rid in ids:
            raise ValueError("source rule ids must be unique")
        if cls not in CLASSES:
            raise ValueError(f"invalid class for source rule {rid}")
        ids.add(rid)
        compiled.append((rid, re.compile(str(rule.get("pattern", ""))), cls))

    source_rows: list[dict[str, str]] = []
    for path in sorted(root.rglob("*.aidl")):
        rel = _repo_path(root, path)
        matches = [(rid, cls) for rid, pattern, cls in compiled if pattern.fullmatch(rel)]
        if len(matches) != 1:
            raise ValueError(f"AIDL source must match exactly one classification rule: {rel} matched {matches}")
        source_rows.append({"path": rel, "rule": matches[0][0], "class": matches[0][1]})

    docs = data.get("document_surfaces", [])
    doc_paths = [row.get("path") for row in docs if isinstance(row, dict)]
    if len(doc_paths) != len(docs) or len(set(doc_paths)) != len(doc_paths):
        raise ValueError("document surfaces must have unique paths")
    doc_map = {row["path"]: row["class"] for row in docs}
    for path, cls in doc_map.items():
        if cls not in CLASSES:
            raise ValueError(f"invalid document class: {path}")
        if not (root / path).is_file():
            raise ValueError(f"classified document is missing: {path}")
    required = data.get("required_document_surfaces", [])
    if len(required) != len(set(required)):
        raise ValueError("required document surfaces must be unique")
    missing = sorted(set(required) - set(doc_map))
    extra = sorted(set(doc_map) - set(required))
    if missing or extra:
        raise ValueError(f"document classification drift: missing={missing}, extra={extra}")

    if not data.get("m10_3_mismatches"):
        raise ValueError("M10.3 mismatch handoff must not be empty")

    return {
        "schema_version": SCHEMA_VERSION,
        "contract_revision": 4,
        "source_count": len(source_rows),
        "source_classes": {cls: sum(row["class"] == cls for row in source_rows) for cls in sorted(CLASSES)},
        "document_count": len(doc_map),
        "document_classes": {cls: sum(value == cls for value in doc_map.values()) for cls in sorted(CLASSES)},
        "sources": source_rows,
    }


def main() -> int:
    print(json.dumps(validate(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
