from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


class IrDefaultError(ValueError):
    """Raised when a value at the semantic IR boundary has an invalid shape."""


_FIELD_DEFAULTS: dict[str, object] = {
    "primary": False,
    "concurrencyToken": False,
    "onDelete": "none",
}


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise IrDefaultError(f"{path} must be an object")
    return value


def _array(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise IrDefaultError(f"{path} must be an array")
    return value


def _field(value: object, path: str) -> dict[str, Any]:
    result = dict(_mapping(value, path))
    for name, default in _FIELD_DEFAULTS.items():
        result.setdefault(name, default)
    return result


def materialize_semantic_defaults(document: Mapping[str, Any]) -> dict[str, Any]:
    """Return an IR structure with every core semantic default made explicit.

    This boundary accepts an already semantic IR structure, does not mutate it,
    and deliberately owns only defaults whose omission has one unambiguous core
    meaning. Optional values where absence itself is meaningful stay absent.
    """

    if not isinstance(document, Mapping):
        raise IrDefaultError("IR document must be an object")

    result = deepcopy(dict(document))
    declarations = _array(result.get("declarations"), "/declarations")
    materialized: list[dict[str, Any]] = []
    for index, value in enumerate(declarations):
        path = f"/declarations/{index}"
        declaration = dict(_mapping(value, path))
        kind = declaration.get("kind")

        if kind in {"value", "entity", "event"}:
            fields = _array(declaration.get("fields"), f"{path}/fields")
            declaration["fields"] = [
                _field(field, f"{path}/fields/{field_index}")
                for field_index, field in enumerate(fields)
            ]

        if kind in {"workflow", "saga", "task"}:
            declaration.setdefault("retry", {"kind": "none"})

        materialized.append(declaration)

    result["declarations"] = materialized
    return result
