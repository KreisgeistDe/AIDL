from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from tools.core_bootstrap import TypeRef, parse_type_ref


@dataclass(frozen=True)
class RangeConstraint:
    minimum: str
    maximum: str

    def to_json(self) -> dict[str, Any]:
        return {"kind": "range", "min": self.minimum, "max": self.maximum}


@dataclass(frozen=True)
class NormalizedTypeRef:
    """Compatibility envelope: Core TypeRef plus lossless legacy constraint facts."""

    type_ref: TypeRef
    constraints: tuple[RangeConstraint, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "typeRef": self.type_ref.to_json(),
            "constraints": [item.to_json() for item in self.constraints],
        }


_RANGE = re.compile(
    r"^(?P<base>[A-Za-z_][A-Za-z0-9_.]*)\(\s*(?P<min>-?\d+(?:\.\d+)?)\s*\.\.\s*(?P<max>-?\d+(?:\.\d+)?)\s*\)(?P<optional>\?)?$"
)


def normalize_legacy_type_ref(source: str) -> NormalizedTypeRef:
    text = source.strip()
    if not text:
        raise ValueError("legacy TypeRef must not be blank")

    optional = text.endswith("?")
    core = text[:-1].strip() if optional else text

    if core.startswith("[") and core.endswith("]"):
        nested = core[1:-1].strip()
        if not nested:
            raise ValueError("legacy list TypeRef requires an element type")
        element = normalize_legacy_type_ref(nested)
        if element.constraints:
            raise ValueError("legacy constrained list elements require an explicit migration disposition")
        return NormalizedTypeRef(TypeRef("list", (element.type_ref,), optional))

    match = _RANGE.fullmatch(text)
    if match is not None:
        base = TypeRef(match.group("base"), (), bool(match.group("optional")))
        return NormalizedTypeRef(
            base,
            (RangeConstraint(match.group("min"), match.group("max")),),
        )

    return NormalizedTypeRef(parse_type_ref(text))


def semantic_hash(value: Any) -> str:
    if hasattr(value, "to_json"):
        value = value.to_json()
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_client_header(source: str) -> dict[str, Any]:
    """Normalize the revision-4 compatibility spelling `client C for Service`."""

    match = re.fullmatch(
        r"\s*client\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+for\s+(?P<service>[A-Za-z_][A-Za-z0-9_.]*)\s*",
        source,
    )
    if match is None:
        raise ValueError("unsupported legacy client header")
    return {
        "kind": "client",
        "name": match.group("name"),
        "arguments": {"service": {"declarationRef": match.group("service")}},
    }


def normalize_migration_header(source: str) -> dict[str, Any]:
    """Normalize the revision-4 compatibility spelling `migration M from \"a\" to \"b\"`."""

    match = re.fullmatch(
        r'\s*migration\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+from\s+"(?P<from>[^"]+)"\s+to\s+"(?P<to>[^"]+)"\s*',
        source,
    )
    if match is None:
        raise ValueError("unsupported legacy migration header")
    return {
        "kind": "migration",
        "name": match.group("name"),
        "arguments": {
            "fromVersion": match.group("from"),
            "toVersion": match.group("to"),
        },
    }


def canonical_header(kind: str, name: str, **arguments: Any) -> dict[str, Any]:
    return {"kind": kind, "name": name, "arguments": arguments}
