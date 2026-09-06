from __future__ import annotations

import hashlib
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from tools.ir_canonical_json import canonical_ir_json_bytes
from tools.ir_version import IrCompatibilityError, IrVersion


class IrSemanticHashError(ValueError):
    """Raised when the semantic-hash boundary receives an invalid IR shape."""


_HASH_FIELD = "semanticHash"
_SOURCE_MAP_FIELD = "sourceMap"


def _sha256(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_ir_json_bytes(value)).hexdigest()


def _without_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(value))
    result.pop(_HASH_FIELD, None)
    return result


def _declaration_hash(declaration: Mapping[str, Any]) -> str:
    # The one-element envelope intentionally places the declaration at the
    # canonical /declarations/* path so M3-02's documented set normalization
    # (for example errorIds/eventIds) is reused without inventing a second
    # serializer. The static envelope is not part of IR output.
    return _sha256({"declarations": [_without_hash(declaration)]})


def _document_preimage(document: Mapping[str, Any]) -> dict[str, Any]:
    preimage = deepcopy(dict(document))
    preimage.pop(_HASH_FIELD, None)
    preimage.pop(_SOURCE_MAP_FIELD, None)

    declarations = preimage.get("declarations")
    if not isinstance(declarations, list):
        raise IrSemanticHashError("/declarations must be an array")

    normalized: list[dict[str, Any]] = []
    for index, declaration in enumerate(declarations):
        if not isinstance(declaration, Mapping):
            raise IrSemanticHashError(f"/declarations/{index} must be an object")
        normalized.append(_without_hash(declaration))
    preimage["declarations"] = normalized
    return preimage


def apply_semantic_hashes(document: Mapping[str, Any]) -> dict[str, Any]:
    """Return canonical IR with deterministic document/declaration fingerprints.

    The input is the already-semantic M3-05/M3-06 IR boundary. Hashes are
    lowercase SHA-256 values prefixed with ``sha256:`` and reuse M3-02 canonical
    JSON bytes. A declaration hash covers its Core declaration object except
    its own hash field. The document hash covers the complete canonical IR
    semantics except the derived root/declaration hash fields and ``sourceMap``.

    ``sourceMap`` remains untouched in the returned IR but is traceability, not
    semantic input, so source-location changes cannot perturb the fingerprint.
    Profile declarations and ``profileExtensions`` remain in the document
    preimage and therefore contribute to the document fingerprint.
    """

    if not isinstance(document, Mapping):
        raise IrSemanticHashError("IR document must be an object")

    try:
        IrVersion.parse(document.get("irVersion"))
    except IrCompatibilityError as exc:
        raise IrSemanticHashError(str(exc)) from exc

    declarations = document.get("declarations")
    if not isinstance(declarations, list):
        raise IrSemanticHashError("/declarations must be an array")

    result = deepcopy(dict(document))
    hashed_declarations: list[dict[str, Any]] = []
    for index, declaration in enumerate(declarations):
        if not isinstance(declaration, Mapping):
            raise IrSemanticHashError(f"/declarations/{index} must be an object")
        hashed = deepcopy(dict(declaration))
        hashed[_HASH_FIELD] = _declaration_hash(declaration)
        hashed_declarations.append(hashed)

    result["declarations"] = hashed_declarations
    result[_HASH_FIELD] = _sha256(_document_preimage(result))
    return result
