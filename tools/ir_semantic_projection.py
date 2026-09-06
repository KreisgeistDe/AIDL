from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from tools.ir_defaults import materialize_semantic_defaults


class IrSemanticProjectionError(ValueError):
    """Raised when the pre-canonical semantic IR boundary has an invalid shape."""


# These names describe source presentation, never AIDL meaning. The list is
# intentionally closed: other unknown fields survive this boundary so the
# closed IR schema can reject them instead of silently losing semantics.
_SOURCE_SYNTAX_KEYS: frozenset[str] = frozenset(
    {
        "sourceText",
        "rawText",
        "tokens",
        "comments",
        "whitespace",
        "punctuation",
        "clauseOrder",
        "syntaxForm",
    }
)


def _strip(value: Any, path: tuple[str, ...]) -> Any:
    if isinstance(value, Mapping):
        # Source maps are an explicit canonical IR traceability contract.
        # Profile extension values are owned by their versioned profile schema.
        if path == ("sourceMap",) or path[:1] == ("profileExtensions",):
            return deepcopy(dict(value))
        return {
            key: _strip(item, path + (key,))
            for key, item in value.items()
            if key not in _SOURCE_SYNTAX_KEYS
        }
    if isinstance(value, list):
        return [_strip(item, path + ("*",)) for item in value]
    return deepcopy(value)


def prepare_canonical_ir(document: Mapping[str, Any]) -> dict[str, Any]:
    """Project already-resolved semantics into canonical IR.

    Presentation-only source metadata is removed before the M3-04 semantic
    defaults are materialized. Semantically relevant values, ordering,
    traceability source maps, and versioned profile payloads remain untouched.
    """

    if not isinstance(document, Mapping):
        raise IrSemanticProjectionError("semantic IR document must be an object")
    stripped = _strip(document, ())
    assert isinstance(stripped, dict)
    return materialize_semantic_defaults(stripped)
