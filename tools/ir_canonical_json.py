from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


# These arrays are semantic sets in the M3 canonical IR contract. Their member
# order carries no meaning, so the serializer sorts their recursively canonical
# JSON representations. Arrays absent from this table are positional and remain
# in input order; this is especially important for source-map/profile-extension
# JSON pointers and ordered read/transaction/orchestration steps.
_UNORDERED_ARRAY_PATHS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("profiles",),
        ("app", "apiIds"),
        ("app", "auth", "roles"),
        ("app", "auth", "scopes"),
        ("declarations", "*", "errorIds"),
        ("declarations", "*", "eventIds"),
        ("system", "services", "*", "owns"),
        ("system", "services", "*", "uses"),
        ("system", "services", "*", "exposes"),
        ("system", "services", "*", "runs"),
        ("system", "resources", "*", "transactionIsolation"),
        ("system", "topicIds"),
        ("system", "apiIds"),
        ("system", "consumerGroups", "*", "consumerIds"),
    }
)


def _json_text(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonicalize(value: Any, path: tuple[str, ...] = ()) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _canonicalize(value[key], path + (key,))
            for key in sorted(value)
        }

    if isinstance(value, list):
        items = [_canonicalize(item, path + ("*",)) for item in value]
        if path in _UNORDERED_ARRAY_PATHS:
            items.sort(key=_json_text)
        return items

    return value


def canonical_ir_json_text(document: Mapping[str, Any]) -> str:
    """Return canonical AIDL IR JSON text with exactly one trailing LF.

    The input is an already semantic, schema-conformant IR structure. This
    boundary performs serialization normalization only; it does not create IR,
    identifiers, defaults, semantic hashes, plans, or CLI output.
    """

    return _json_text(_canonicalize(document)) + "\n"


def canonical_ir_json_bytes(document: Mapping[str, Any]) -> bytes:
    """Return the canonical AIDL IR JSON byte representation as UTF-8."""

    return canonical_ir_json_text(document).encode("utf-8")
