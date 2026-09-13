from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.core_bootstrap import parse_source, projection_text
from tools.core_semantics import CoreContractError, load_semantic_registry, validate_source


ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "spec" / "core.aidl"
CORE_PROJECTION_PATH = ROOT / "spec" / "core-registry-v1.json"
CORE_DOMAIN_PATH = ROOT / "spec" / "core.domain.aidl"
AUTHORITY_PATH = ROOT / "spec" / "core.authority.aidl"
COMPATIBILITY_BINDING_PATH = ROOT / "spec" / "core.compatibility.aidl"
REVISION4_PATH = ROOT / "spec" / "language-surface-v1.json"
REVISION4_REPO_PATH = "spec/language-surface-v1.json"


class CoreAuthorityError(ValueError):
    """Raised when a compatibility artifact is not authorized by normative Core."""


def git_blob_sha1(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def _string_slot(declaration: Any, body_type: str) -> str:
    entries = [item for item in declaration.body if item.body_type == body_type]
    if len(entries) != 1 or entries[0].value is None or entries[0].value.kind != "string":
        raise CoreAuthorityError(
            f"compatibility projection {declaration.name!r} requires one string {body_type!r} slot"
        )
    return str(entries[0].value.value)


def _binding(
    *,
    core_source: str,
    core_projection: str,
    domain_source: str,
    authority_source: str,
    binding_source: str,
) -> dict[str, str]:
    if core_projection != projection_text(core_source):
        raise CoreAuthorityError(
            "Core projection drift: spec/core-registry-v1.json does not match normative spec/core.aidl"
        )
    try:
        registry = load_semantic_registry(
            domain_source,
            authority_source,
            core_source=core_source,
            core_projection=core_projection,
        )
    except CoreContractError as exc:
        raise CoreAuthorityError(f"invalid Core authority registry: {exc}") from exc

    diagnostics = validate_source(binding_source, registry)
    if diagnostics:
        first = diagnostics[0]
        raise CoreAuthorityError(
            f"invalid Core compatibility binding: {first.code} {first.message}"
        )
    program = parse_source(binding_source)
    matches = [
        item
        for item in program.declarations
        if item.kind == "compatibilityProjection" and item.name == "revision4"
    ]
    if len(matches) != 1:
        raise CoreAuthorityError(
            "Core compatibility binding must declare exactly one compatibilityProjection revision4"
        )
    declaration = matches[0]
    return {
        "source": _string_slot(declaration, "source"),
        "gitBlobSha1": _string_slot(declaration, "gitBlobSha1"),
        "role": _string_slot(declaration, "role"),
    }


def assert_revision4_compatibility_authorized(
    contract_path: Path = REVISION4_PATH,
    *,
    contract_bytes: bytes | None = None,
    core_source: str | None = None,
    core_projection: str | None = None,
    domain_source: str | None = None,
    authority_source: str | None = None,
    binding_source: str | None = None,
) -> dict[str, Any]:
    """Return the revision-4 compatibility JSON only after Core authorizes it exactly."""

    core_source = core_source if core_source is not None else CORE_PATH.read_text(encoding="utf-8")
    core_projection = (
        core_projection
        if core_projection is not None
        else CORE_PROJECTION_PATH.read_text(encoding="utf-8")
    )
    domain_source = (
        domain_source
        if domain_source is not None
        else CORE_DOMAIN_PATH.read_text(encoding="utf-8")
    )
    authority_source = (
        authority_source
        if authority_source is not None
        else AUTHORITY_PATH.read_text(encoding="utf-8")
    )
    binding_source = (
        binding_source
        if binding_source is not None
        else COMPATIBILITY_BINDING_PATH.read_text(encoding="utf-8")
    )
    binding = _binding(
        core_source=core_source,
        core_projection=core_projection,
        domain_source=domain_source,
        authority_source=authority_source,
        binding_source=binding_source,
    )
    if binding["source"] != REVISION4_REPO_PATH:
        raise CoreAuthorityError(
            f"revision4 compatibility source must be {REVISION4_REPO_PATH!r}, found {binding['source']!r}"
        )
    if binding["role"] != "compatibility-only":
        raise CoreAuthorityError(
            f"revision4 compatibility role must be 'compatibility-only', found {binding['role']!r}"
        )

    content = contract_bytes if contract_bytes is not None else contract_path.read_bytes()
    actual = git_blob_sha1(content)
    expected = binding["gitBlobSha1"]
    if actual != expected:
        raise CoreAuthorityError(
            "revision4 compatibility projection drift: "
            f"Core authorizes git blob {expected}, found {actual}"
        )
    try:
        contract = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoreAuthorityError(f"revision4 compatibility projection is not valid UTF-8 JSON: {exc}") from exc
    if contract.get("authority") != "M10.1" or contract.get("status") != "frozen":
        raise CoreAuthorityError(
            "revision4 compatibility projection must remain the frozen M10.1 evidence artifact"
        )
    return contract
