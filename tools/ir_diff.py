from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator, FormatChecker

from tools.ir_canonical_json import canonical_ir_json_text
from tools.ir_version import CURRENT_IR_VERSION, IrCompatibilityError, IrVersion


class IrDiffError(ValueError):
    """Raised when an input is not a supported valid Canonical IR state."""


IrDiffKind = Literal["added", "removed", "changed"]
_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _ROOT / "spec" / "ir.schema.json"
_IDENTITY_ARRAY_PATHS = frozenset(
    {
        "/declarations",
        "/deployments",
        "/system/resources",
        "/system/services",
    }
)


@dataclass(frozen=True)
class IrDiffChange:
    kind: IrDiffKind
    path: str
    old_value: Any
    new_value: Any

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "oldValue": deepcopy(self.old_value),
            "newValue": deepcopy(self.new_value),
        }


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _path(parent: str, part: str | int) -> str:
    return f"{parent}/{_pointer_part(str(part))}"


def _validate(document: Mapping[str, Any], label: str) -> None:
    try:
        version = IrVersion.parse(document.get("irVersion"))
    except IrCompatibilityError as exc:
        raise IrDiffError(f"{label}: {exc}") from exc
    if str(version) != CURRENT_IR_VERSION:
        raise IrDiffError(
            f"{label}: unsupported Canonical IR version {version}; expected {CURRENT_IR_VERSION}"
        )

    errors = sorted(
        _validator().iter_errors(document),
        key=lambda item: (
            -len(tuple(item.absolute_path)),
            tuple(str(part) for part in item.absolute_path),
            item.message,
        ),
    )
    if errors:
        error = errors[0]
        location = "/" + "/".join(_pointer_part(str(part)) for part in error.absolute_path)
        if location == "/":
            location = "<root>"
        raise IrDiffError(f"{label}: schema-invalid at {location}: {error.message}")


def _strip_nonsemantic(value: Any, path: tuple[str, ...] = ()) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        in_profile_extensions = path[:1] == ("profileExtensions",)
        for key, item in value.items():
            if path == () and key == "sourceMap":
                continue
            if not in_profile_extensions and key == "semanticHash":
                continue
            result[key] = _strip_nonsemantic(item, path + (key,))
        return result
    if isinstance(value, list):
        return [_strip_nonsemantic(item, path + ("*",)) for item in value]
    return deepcopy(value)


def _semantic_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Reuse the canonical serializer's existing set-order semantics."""
    stripped = _strip_nonsemantic(document)
    assert isinstance(stripped, dict)
    return json.loads(canonical_ir_json_text(stripped))


def _stable_item_key(item: Any, path: str) -> tuple[str, str] | None:
    if not isinstance(item, Mapping):
        return None
    declaration_id = item.get("declarationId")
    fqn = item.get("fqn")
    if isinstance(declaration_id, str) and declaration_id and isinstance(fqn, str) and fqn:
        kind = item.get("kind")
        if path == "/declarations" and isinstance(kind, str) and kind:
            return (f"{kind}:{declaration_id}", fqn)
        return (declaration_id, fqn)
    return None


def _keyed_items(items: list[Any], path: str) -> dict[tuple[str, str], Any] | None:
    if not items:
        return {} if path in _IDENTITY_ARRAY_PATHS else None
    result: dict[tuple[str, str], Any] = {}
    for item in items:
        key = _stable_item_key(item, path)
        if key is None:
            return None
        if key in result:
            raise IrDiffError(f"duplicate stable identity at {path}: {key[0]} ({key[1]})")
        result[key] = item
    return result


def _walk(old: Any, new: Any, path: str, changes: list[IrDiffChange]) -> None:
    if type(old) is not type(new):
        changes.append(IrDiffChange("changed", path or "/", old, new))
        return

    if isinstance(old, Mapping):
        old_keys = set(old)
        new_keys = set(new)
        for key in sorted(old_keys | new_keys):
            child = _path(path, key)
            if key not in old:
                changes.append(IrDiffChange("added", child, None, new[key]))
            elif key not in new:
                changes.append(IrDiffChange("removed", child, old[key], None))
            else:
                _walk(old[key], new[key], child, changes)
        return

    if isinstance(old, list):
        old_keyed = _keyed_items(old, path)
        new_keyed = _keyed_items(new, path)
        if old_keyed is not None and new_keyed is not None:
            for key in sorted(set(old_keyed) | set(new_keyed)):
                selector, _fqn = key
                child = _path(path, selector)
                if key not in old_keyed:
                    changes.append(IrDiffChange("added", child, None, new_keyed[key]))
                elif key not in new_keyed:
                    changes.append(IrDiffChange("removed", child, old_keyed[key], None))
                else:
                    _walk(old_keyed[key], new_keyed[key], child, changes)
            return

        common = min(len(old), len(new))
        for index in range(common):
            _walk(old[index], new[index], _path(path, index), changes)
        for index in range(common, len(old)):
            changes.append(IrDiffChange("removed", _path(path, index), old[index], None))
        for index in range(common, len(new)):
            changes.append(IrDiffChange("added", _path(path, index), None, new[index]))
        return

    if old != new:
        changes.append(IrDiffChange("changed", path or "/", old, new))


def diff_canonical_ir(
    old_document: Mapping[str, Any],
    new_document: Mapping[str, Any],
) -> list[IrDiffChange]:
    """Return deterministic semantic changes between two current Canonical IR states.

    Both inputs must satisfy the current closed Canonical IR schema exactly.
    Root ``sourceMap`` traceability and Core-derived ``semanticHash`` fields are
    excluded, while versioned ``profileExtensions`` payloads remain semantic.
    Existing canonical JSON normalization defines set-like array semantics,
    while identity-bearing declaration/resource/service/deployment objects are
    matched by their stable canonical IDs instead of list position.

    This boundary reports structural semantic changes only. It deliberately
    performs no compatibility classification and suggests no migration steps.
    """

    if not isinstance(old_document, Mapping):
        raise IrDiffError("old: IR document must be an object")
    if not isinstance(new_document, Mapping):
        raise IrDiffError("new: IR document must be an object")
    _validate(old_document, "old")
    _validate(new_document, "new")

    old_semantic = _semantic_document(old_document)
    new_semantic = _semantic_document(new_document)

    changes: list[IrDiffChange] = []
    _walk(old_semantic, new_semantic, "", changes)
    return sorted(changes, key=lambda item: (item.path, item.kind))


def semantic_ir_diff_to_json(changes: list[IrDiffChange]) -> list[dict[str, Any]]:
    return [change.to_json() for change in changes]
